"""The model service of the live site: the quiet finalist logit_signals (docs/quiet/model.md) retrained every day,
exported as JSON (the site's api/model.json), run from that JSON in plain Python, and a daily-retrain replay of the
history. The thresholds stay frozen at the development values of quiet/forecast.py; nothing here refits them.

The hours table is airalerts.live.features.build() when that works, else the frozen gold kyiv_quiet (same columns).
DATA is paths.DATA: ROOT/data, or AIRALERTS_DATA when that is set (data/live for the live product).

    .venv/bin/python -I -m airalerts.live.model train [--at ISO] [--gold]   fit on the hours known now, write DATA/live_model/
    .venv/bin/python -I -m airalerts.live.model replay [--gold]             retrain at 04:00 Kyiv every day: tier stats
"""
import argparse
import json
import math
import os
import sys
from bisect import bisect_right
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .. import paths
from ..evaluation import split
from ..gold import kyiv_quiet as quiet_table
from ..quiet import forecast, linear

NAME = "logit_signals"
MODEL = linear.MODELS[NAME]
TARGET, DRONE, MISSILE, H = linear.TARGET, linear.DRONE, linear.MISSILE, quiet_table.H
INPUTS = tuple(dict.fromkeys(name for name, _ in linear.SIGNALS))  # the 7 columns the model reads
NEEDED = ("t_utc", *INPUTS, "quiet_now", "alert_active", TARGET, DRONE, MISSILE)
BUSY_AT, HIGH_AT = forecast.BUSY_AT, forecast.HIGH_AT
START = "2026-07-04T09:00:00Z"   # the first development fold, 2026-07-04 12:00 Kyiv
RETRAIN_HOUR = 4                 # Kyiv time
MAX_AGE = timedelta(hours=26)    # an older saved model is retrained before use
DOCS = {"development": (0.83, 0.50), "test": (0.83, 0.80)}  # docs/quiet/forecast.md: low tier quiet, high tier busy
UTC, KYIV = ZoneInfo("UTC"), ZoneInfo("Europe/Kyiv")


def utc(x):
    """A naive UTC datetime from ISO text ("...Z") or a datetime (a naive one is UTC already)."""
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    return x.astimezone(UTC).replace(tzinfo=None) if x.tzinfo else x


def iso(t):
    return f"{t:%Y-%m-%dT%H:%M:%S}Z"


def hour_now():
    return datetime.now(UTC).replace(tzinfo=None, minute=0, second=0, microsecond=0)


def write_json(path, obj, indent=1):
    """Write JSON atomically: a temporary file in the same folder, then os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")),
                   encoding="utf-8")
    os.replace(tmp, path)


def prepare(table):
    """The hours in time order, t_utc as naive UTC microseconds whatever the source stored."""
    if table.schema.field("t_utc").type != pa.timestamp("us"):
        ts = pa.array([utc(x) for x in table["t_utc"].to_pylist()], pa.timestamp("us"))
        table = table.set_column(table.schema.get_field_index("t_utc"), "t_utc", ts)
    return table.sort_by("t_utc")


def load(gold=False):
    """(the hours table, where it came from): the live features when they work, else the gold kyiv_quiet."""
    if not gold:
        try:
            from . import features
            t = features.build()
            missing = [c for c in NEEDED if c not in t.column_names]
            if not missing:
                return prepare(t), "live features"
            print(f"live features lack {missing}: using gold", file=sys.stderr)
        except Exception as e:  # not there yet or broken; only the type is shown, a message could carry a secret
            print(f"live features not usable ({type(e).__name__}): using gold", file=sys.stderr)
    return prepare(pq.read_table(quiet_table.PATH)), "gold kyiv_quiet"


def has_inputs(table):
    """The hours whose model inputs are all present."""
    ok = pc.is_valid(table[INPUTS[0]])
    for name in INPUTS[1:]:
        ok = pc.and_(ok, pc.is_valid(table[name]))
    return table.filter(ok)


def known_at(table, at):
    """The hours a model fitted at `at` learns from: inputs present, target known (t + 3 h <= at, split.known_by)."""
    t = has_inputs(table)
    return split.known_by(t.filter(pc.is_valid(t[TARGET])), utc(at), H)


def train(table, at):
    """logit_signals fitted on the hours whose target is known at `at`."""
    return MODEL["fit"](known_at(table, at))


def export(model, at, n_rows, busy_share):
    """A fitted model as api/model.json: p = 1 / (1 + exp(-(intercept + sum(coef * (x - mean) / scale))))."""
    spec, pipe = model
    scaler, logit = pipe.steps[0][1], pipe.steps[-1][1]
    return {"schema": 1, "name": NAME, "trained_at": iso(utc(at)), "rows": n_rows, "busy_share": round(busy_share, 4),
            "intercept": float(logit.intercept_[0]), "C": float(logit.C), "busy_at": BUSY_AT, "high_at": HIGH_AT,
            "evening": list(linear.EVENING),
            "features": [{"column": name, "how": how, "mean": float(m), "scale": float(s), "coef": float(w),
                          "text": forecast.WHY[name]}
                         for (name, how), m, s, w in zip(spec, scaler.mean_, scaler.scale_, logit.coef_[0])]}


def fitted(table, at):
    """train() at `at`, exported with the number of hours it learned from and their busy share."""
    y = known_at(table, at)[TARGET].to_pylist()
    return export(train(table, at), at, len(y), sum(y) / len(y))


def value(how, v, evening):
    """One input after its transform, as linear.design() makes it."""
    v = float(v)
    if how == "sin":
        return math.sin(2 * math.pi * v / 24)
    if how == "cos":
        return math.cos(2 * math.pi * v / 24)
    if how == "evening":
        return float(evening[0] <= v <= evening[1])
    if how == "log1p":
        return math.log1p(v)
    return v


def predict(model_json, row):
    """(p of a busy window, {column: its part of the log-odds}) for one hour (a dict of the table), in plain Python.
    The three hour features are summed into hour_kyiv, as quiet/forecast.py reasons() does."""
    m, parts = model_json, {}
    for f in m["features"]:
        x = (value(f["how"], row[f["column"]], m["evening"]) - f["mean"]) / f["scale"]
        parts[f["column"]] = parts.get(f["column"], 0.0) + f["coef"] * x
    z = m["intercept"] + sum(parts.values())
    return (1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))), parts


def tier(p):
    """low below BUSY_AT, high from HIGH_AT, medium between: the levels of quiet/forecast.py."""
    return "low" if p < BUSY_AT else ("medium" if p < HIGH_AT else "high")


def retrains(first, last, hour_kyiv=RETRAIN_HOUR):
    """Retrain moments (naive UTC) at hour_kyiv o'clock Kyiv time: the last one at or before first, then daily to last."""
    day = (first.replace(tzinfo=UTC).astimezone(KYIV) - timedelta(hours=hour_kyiv)).date()
    out = []
    while (r := utc(datetime.combine(day, time(hour_kyiv), KYIV))) <= last:
        out.append(r)
        day += timedelta(days=1)
    return out


def replay(table, start=START, retrain_hour_kyiv=RETRAIN_HOUR):
    """The history as the live service would have made it: every day at retrain_hour_kyiv Kyiv time a model fitted on
    the hours known at that moment predicts each hour up to the next retrain. [{t, p, tier}] from start, in time order."""
    table = prepare(table)
    ready = has_inputs(table)
    hours = ready.filter(pc.greater_equal(ready["t_utc"], pa.scalar(utc(start), pa.timestamp("us")))).to_pylist()
    if not hours:
        return []
    moments = retrains(hours[0]["t_utc"], hours[-1]["t_utc"], retrain_hour_kyiv)
    out, k, m = [], None, None
    for r in hours:
        j = bisect_right(moments, r["t_utc"]) - 1
        if j != k:
            k, m = j, fitted(table, moments[j])
        p = predict(m, r)[0]
        out.append({"t": r["t_utc"], "p": p, "tier": tier(p)})
    return out


def scored(rep, rows):
    """The replay hours that are quiet now with a known target, each with its table row ({t: row}) as "row"."""
    return [{**x, "row": rows[x["t"]]} for x in rep if rows[x["t"]]["quiet_now"] and rows[x["t"]][TARGET] is not None]


def save(model_json, data):
    """DATA/live_model/logit_signals.json and its dated copy logit_signals-YYYY-MM-DD.json; returns the first."""
    folder = Path(data) / "live_model"
    for name in (f"{NAME}-{model_json['trained_at'][:10]}.json", f"{NAME}.json"):
        write_json(folder / name, model_json)
    return folder / f"{NAME}.json"


def current(table, data, now):
    """The saved model of DATA/live_model; trained at now and saved first when missing or older than MAX_AGE."""
    try:
        m = json.loads((Path(data) / "live_model" / f"{NAME}.json").read_text(encoding="utf-8"))
        if timedelta(0) <= now - utc(m["trained_at"]) <= MAX_AGE:
            return m
    except (OSError, ValueError, KeyError):
        pass
    m = fitted(table, now)
    save(m, data)
    return m


def report(rep, table):
    """Tier stats of the replay on quiet-now hours with a known target, next to the docs numbers."""
    s = scored(rep, {r["t_utc"]: r for r in table.to_pylist()})
    print(f"replay of {NAME}: retrain every day at {RETRAIN_HOUR:02d}:00 Kyiv on the hours known then, "
          f"{iso(rep[0]['t'])}..{iso(rep[-1]['t'])}, {len(rep)} hours, thresholds {BUSY_AT} and {HIGH_AT} frozen")
    print("quiet-now hours with a known target; docs numbers: weekly refit, docs/quiet/forecast.md")
    for part, lo, hi in (("development", utc(START), split.TEST_START), ("test", split.TEST_START, datetime.max)):
        rows = [x for x in s if lo <= x["t"] < hi]
        by = {k: [x for x in rows if x["tier"] == k] for k in ("low", "medium", "high")}
        busy = {k: sum(x["row"][TARGET] for x in v) for k, v in by.items()}
        print(f"  {part} from {iso(lo)}: {len(rows)} hours; " + ", ".join(
            f"{k} {len(v)} ({busy[k] / len(v):.0%} busy)" if v else f"{k} 0" for k, v in by.items()))
        low_quiet = 1 - busy["low"] / len(by["low"]) if by["low"] else float("nan")
        high_busy = busy["high"] / len(by["high"]) if by["high"] else float("nan")
        print(f"    low tier truly quiet {low_quiet:.0%} (docs {DOCS[part][0]:.0%}), "
              f"high tier busy {high_busy:.0%} (docs {DOCS[part][1]:.0%})")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -I -m airalerts.live.model")
    ap.add_argument("command", choices=("train", "replay"))
    ap.add_argument("--at", help="train as of this UTC time, ISO (default: the current hour)")
    ap.add_argument("--gold", action="store_true", help="read the gold kyiv_quiet, not the live features")
    a = ap.parse_args(argv)
    table, source = load(a.gold)
    if a.command == "train":
        m = fitted(table, utc(a.at) if a.at else hour_now())
        print(f"{save(m, paths.DATA)}: trained at {m['trained_at']} on {m['rows']} hours of {source}, "
              f"busy share {m['busy_share']:.3f}")
    else:
        print(f"hours from {source}")
        report(replay(table), table)


if __name__ == "__main__":
    main()
