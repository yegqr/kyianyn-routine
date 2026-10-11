"""A forecast for the next 3 hours in Kyiv, for a person (docs/models/forecast.md): is it quiet now, will [t, t + 3 h) be
quiet or busy with drones or missiles, the probability, the risk level and the main reasons.

The model is the frozen quiet finalist logit_signals (docs/models/quiet_linear.md), refitted for each hour t on every
hour whose target is known at t (t' + 3 h <= t), as it would run in real time. Its scale was set on the development
folds only (quiet-now hours) by written rules, never on the test:
- busy from BUSY_AT: the highest threshold that still catches 80% of the busy windows (docs/METHODOLOGY.md 4.4);
- high risk from HIGH_AT: the upper third of the development predictions.
rules() recomputes both; tests/test_forecast.py checks they still hold.

    .venv/bin/python -I -m airalerts.modeling.forecast                      the latest hour of the data
    .venv/bin/python -I -m airalerts.modeling.forecast "2026-10-09 15:00"   a Kyiv hour
    .venv/bin/python -I -m airalerts.modeling.forecast day 2026-10-09       every hour of a Kyiv day, with what happened
"""
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import quiet, split, tasks
from .quiet_models import linear

MODEL = linear.MODELS["logit_signals"]
BUSY_AT = 0.197    # rules(): 80% of the busy windows caught on development
HIGH_AT = 0.300    # rules(): the upper third of the development predictions
RECALL = 0.8
HOUR = timedelta(hours=1)
UTC, KYIV = ZoneInfo("UTC"), ZoneInfo("Europe/Kyiv")
WHY = {  # feature columns of the model, grouped into reasons a person can read
    "hour_kyiv": "година доби",
    "hours_since_busy": "годин від останньої атаки",
    "p_drone_max_1h": "пости моніторів про дрони на Київ за минулу годину",
    "s4_kyiv_6h": "хвилі дронів з курсом на Київ за 6 год",
    "s4_3h": "запуски хвиль дронів за 3 год",
    "posts_jev_1h": "постів моніторів за минулу годину",
    "hours_since_drone": "годин від останніх дронів над Києвом",
}


def rules(t=None):
    """(BUSY_AT, HIGH_AT) recomputed from the development folds of the frozen model, quiet-now hours."""
    t = quiet.load() if t is None else t
    folds = quiet.dev_folds(t)
    p = tasks.fold_predictions(quiet.SPEC, MODEL["fit"], MODEL["predict"], folds)
    rows = [r for _, _, ev in folds for r in ev.select([quiet.LABEL, "quiet_now"]).to_pylist()]
    q = [i for i, r in enumerate(rows) if r["quiet_now"]]
    s = sorted(p[i] for i in q)
    return tasks.recall_threshold([int(rows[i][quiet.LABEL]) for i in q], [p[i] for i in q], RECALL), s[2 * len(s) // 3]


def level(p):
    if p < BUSY_AT:
        return "тихо", "швидше тихо"
    return ("неспокійно", "середній ризик") if p < HIGH_AT else ("неспокійно", "високий ризик")


def reasons(model, row):
    """[(reason, value text, contribution to the log-odds)] of one row, largest first."""
    spec, pipe = model
    x = linear.design(row, spec)[0]
    scaler, logit = pipe.steps[0][1], pipe.steps[-1][1]
    contrib = {}
    for (name, _), v, mean, scale, w in zip(spec, x, scaler.mean_, scaler.scale_, logit.coef_[0]):
        contrib[name] = contrib.get(name, 0.0) + w * (v - mean) / scale
    r = row.to_pylist()[0]
    value = {"hour_kyiv": f"{r['hour_kyiv']:02d}:00", "p_drone_max_1h": f"до {r['p_drone_max_1h']:.2f}"}
    return sorted(((WHY[n], value.get(n, f"{r[n]:g}"), c) for n, c in contrib.items()), key=lambda z: -abs(z[2]))


def tables():
    """(labelled hours for fitting, every hour of the table for forecasting, the latest ones included)."""
    return quiet.load(), pq.read_table(quiet.SPEC.path).sort_by("t_utc")


def forecast(t_utc, both=None):
    """The forecast for the hour starting at t_utc (naive UTC): a dict a person's text is made from."""
    labelled, every = tables() if both is None else both
    row = every.filter(pc.equal(every["t_utc"], pa.scalar(t_utc, pa.timestamp("us"))))
    if row.num_rows != 1:
        raise ValueError(f"no hour {t_utc} in {quiet.SPEC.path.name}")
    model = MODEL["fit"](split.known_by(labelled, t_utc, quiet.H))
    x = quiet.features_only(row)
    p = MODEL["predict"](model, x)[0]
    r = row.to_pylist()[0]
    return {"t_utc": t_utc, "p": p, "verdict": level(p), "quiet_now": r["quiet_now"], "alert": r["alert_active"],
            "reasons": reasons(model, x)[:3], "actual": r[quiet.LABEL],
            "actual_parts": (r["y_drone_3h"], r["y_missile_3h"])}


def kyiv(t_utc):
    return t_utc.replace(tzinfo=UTC).astimezone(KYIV)


def text(f):
    k = kyiv(f["t_utc"])
    now = "тихо" if f["quiet_now"] else ("тривога" if f["alert"] else "неспокійно (дрони або ракети в минулу годину)")
    word, risk = f["verdict"]
    head = "швидше тихо" if word == "тихо" else f"швидше неспокійно, {risk}"
    lines = [f"Київ, {k:%Y-%m-%d %H:%M}: прогноз на {k:%H:%M}..{k + 3 * HOUR:%H:%M}",
             f"  Зараз: {now}.",
             f"  Наступні 3 години: {head}.",
             f"  Ймовірність, що прилетять дрони або ракети: {f['p']:.0%}.",
             "  Чому: " + "; ".join(f"{name} {value} ({'+' if c > 0 else '-'})" for name, value, c in f["reasons"]) + "."]
    if f["actual"] is not None:
        drone, missile = f["actual_parts"]
        what = "тихо" if not f["actual"] else "неспокійно: " + ", ".join(
            x for x, b in (("дрони", drone), ("ракети", missile)) if b)
        lines.append(f"  Що сталося насправді: {what}.")
    return "\n".join(lines)


def to_utc(kyiv_text):
    return datetime.fromisoformat(kyiv_text).replace(tzinfo=KYIV).astimezone(UTC).replace(tzinfo=None)


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    both = tables()
    if not cmd:
        print(text(forecast(both[1]["t_utc"][-1].as_py(), both)))
    elif len(cmd) == 1:
        print(text(forecast(to_utc(cmd[0]), both)))
    elif len(cmd) == 2 and cmd[0] == "day":
        start = to_utc(f"{cmd[1]} 00:00")
        print(f"Київ, {cmd[1]}: година | зараз | прогноз на 3 год | ймовірність | що сталося")
        for k in range(24):
            f = forecast(start + k * HOUR, both)
            word, risk = f["verdict"]
            actual = "?" if f["actual"] is None else ("неспокійно" if f["actual"] else "тихо")
            print(f"  {kyiv(f['t_utc']):%H:%M} | {'тихо' if f['quiet_now'] else 'неспокійно'} | "
                  f"{'тихо' if word == 'тихо' else 'неспокійно, ' + risk} | {f['p']:.0%} | {actual}")
    else:
        sys.exit('usage: python -I -m airalerts.modeling.forecast ["YYYY-MM-DD HH:MM" | day YYYY-MM-DD]')


if __name__ == "__main__":
    main()
