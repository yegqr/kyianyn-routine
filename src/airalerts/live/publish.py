"""The publisher of the live site: writes the four JSON files the site reads into DIR/api (now, history, model, meta),
each atomically (a temporary file, then os.replace), from the hours table and the daily model of live/model.py.

- now: the forecast for the latest hour with all its inputs, from the saved model (trained first when it is missing or
  older than 26 h); that forecast is appended once per hour to DATA/live_forecasts.jsonl, which is never rewritten;
- history: the daily-retrain replay before the first logged hour, the log from it; targets once the table knows them;
- tiers, calibration and kind: replay hours that are quiet now with a known target. busy_share and alert_share are
  shares of those hours, missile_share and drone_only_share shares of their busy windows; alert_share counts only the
  hours whose y_alert_3h is known (null when the table has no such column);
- meta: quality from docs/quiet/model.md section 10, the live channels from DATA/bronze/telegram, the Jev spend.

    .venv/bin/python -I -m airalerts.live.publish --out DIR [--pipeline-json FILE_OR_JSON] [--gold]
"""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

from .. import paths
from ..evaluation import split
from . import model
from .fetch import CHANNELS
from .model import DRONE, MISSILE, TARGET, iso, utc

LABEL = {"low": "швидше тихо", "medium": "середній ризик", "high": "високий ризик"}
LOG = "live_forecasts.jsonl"
FRESH = timedelta(minutes=30)  # older posts make the page stale
WAVES = timedelta(hours=6)
DAY, HOUR = timedelta(days=1), timedelta(hours=1)
QUALITY = {  # quiet-now hours, copied from docs/quiet/model.md section 10
    "source": "docs/quiet/model.md", "section": "10. Якість і межі",
    "dev": {"hours": 1067, "busy_share": 0.31, "bss": 0.094, "bss_ci": [0.045, 0.148], "roc_auc": 0.684,
            "roc_auc_ci": [0.621, 0.746], "low_truly_quiet": 0.83, "busy_warned": 0.80, "low_share": 0.37},
    "test": {"hours": 412, "busy_share": 0.71, "bss": 0.284, "bss_ci": [0.189, 0.370], "roc_auc": 0.749,
             "roc_auc_ci": [0.594, 0.837], "low_truly_quiet": 0.83, "busy_warned": 0.98, "low_share": 0.07}}


def parsed(lines):
    """The JSON objects of the lines that hold one; a line cut mid-write is skipped."""
    out = []
    for x in lines:
        try:
            out.append(json.loads(x))
        except ValueError:
            pass
    return out


def logged(data):
    """The issued forecasts of DATA/live_forecasts.jsonl, in file order."""
    path = Path(data) / LOG
    return parsed(path.read_text(encoding="utf-8").splitlines()) if path.exists() else []


def log(data, entry):
    """Append an issued forecast unless its hour is logged already; True when appended. The log is never rewritten."""
    if any(e.get("t") == entry["t"] for e in logged(data)):
        return False
    Path(data).mkdir(parents=True, exist_ok=True)
    with (Path(data) / LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return True


def channel(path, now):
    """(newest post at or before now, the posts of the 24 h before now) of one bronze Telegram file, read from its end."""
    if not path.exists():
        return None, []
    size, block = path.stat().st_size, 1 << 20
    while True:
        with path.open("rb") as f:
            f.seek(max(0, size - block))
            lines = f.read().decode("utf-8", "replace").splitlines()
        posts = [(utc(p["published_at"]), p) for p in parsed(lines if block >= size else lines[1:])
                 if p.get("published_at")]
        if block >= size or any(t <= now - DAY for t, _ in posts):
            break
        block *= 4
    posts = [(t, p) for t, p in posts if t <= now]
    return max((t for t, _ in posts), default=None), [p for t, p in posts if t > now - DAY]


def channels(data, now):
    """[{name, last_post, posts_24h}] of the live channels, and {channel/post_id: text} of their posts of the day."""
    out, texts = [], {}
    for name in CHANNELS:
        newest, posts = channel(Path(data) / "bronze" / "telegram" / f"{name}.jsonl", now)
        out.append({"name": name, "last_post": newest and iso(newest), "posts_24h": len(posts)})
        texts.update((f"{name}/{p.get('post_id')}", p.get("text") or "") for p in posts)
    return out, texts


def waves(data, now, texts):
    """S4 drone wave events of the 6 h before now from the silver prep_signal_events, newest first: when, toward Kyiv,
    how many drones its first post names (null when none) and the text of its first post that has text."""
    path = Path(data) / "silver" / "prep_signal_events.parquet"
    if not path.exists():
        return []
    e = pq.read_table(path, columns=["signal", "available_at", "toward_kyiv", "aircraft_n", "post_refs"])
    out = []
    for r in e.filter(pc.equal(e["signal"], "S4")).to_pylist():
        at = utc(r["available_at"])
        if now - WAVES < at <= now:
            text = next((" ".join(texts[ref].split()) for ref in r["post_refs"] or [] if texts.get(ref, "").strip()), "")
            out.append({"at": iso(at), "kyiv": r["toward_kyiv"], "count": r["aircraft_n"],
                        "text": text if len(text) <= 200 else text[:197] + "..."})
    return sorted(out, key=lambda w: w["at"], reverse=True)


def shown(name, v):
    """A value as quiet/forecast.py reasons() writes it."""
    if name == "hour_kyiv":
        return f"{int(v):02d}:00"
    return f"до {v:.2f}" if name == "p_drone_max_1h" else f"{v:g}"


def reasons(m, row, parts, k=3):
    """The k largest parts of the log-odds, as the site shows them."""
    text = {f["column"]: f["text"] for f in m["features"]}
    top = sorted(parts.items(), key=lambda kv: -abs(kv[1]))[:k]
    return [{"key": c, "text": text[c], "value": shown(c, row[c]), "logit": round(v, 3)} for c, v in top]


def share(k, n):
    return round(k / n, 3) if n else None


def summary(rows):
    """What happened in scored replay hours: busy and alert shares of the hours, missile and drone-only shares of
    their busy windows."""
    busy = [x["row"] for x in rows if x["row"][TARGET]]
    alerts = [a for a in (x["row"].get("y_alert_3h") for x in rows) if a is not None]
    return {"hours": len(rows), "busy_share": share(len(busy), len(rows)),
            "alert_share": share(sum(alerts), len(alerts)),
            "missile_share": share(sum(1 for r in busy if r[MISSILE]), len(busy)),
            "drone_only_share": share(sum(1 for r in busy if not r[MISSILE]), len(busy))}


def tiers(rows):
    out = {}
    for k in ("low", "medium", "high"):
        s = summary([x for x in rows if x["tier"] == k])
        out[k] = {key: s[key] for key in ("hours", "busy_share", "alert_share", "missile_share")}
    return out


def calibration(rows):
    """10 bins of p over scored replay hours: count, mean p and busy share (null in an empty bin)."""
    bins = [[] for _ in range(10)]
    for x in rows:
        bins[min(int(x["p"] * 10), 9)].append(x)
    return [{"from": k / 10, "to": (k + 1) / 10, "n": len(b),
             "p_mean": round(sum(x["p"] for x in b) / len(b), 4) if b else None,
             "busy_share": share(sum(1 for x in b if x["row"][TARGET]), len(b))} for k, b in enumerate(bins)]


def hour_row(t, p, tier, source, row, issued=None):
    """One hour of history.json; the targets stay null until the table knows them."""
    row = row or {}
    quiet_now, alert = (issued["quiet_now"], issued["alert"]) if issued else (row.get("quiet_now"), row.get("alert_active"))
    return {"t": iso(t), "p": round(p, 4), "tier": tier, "source": source, "quiet_now": quiet_now, "alert": alert,
            "busy_3h": row.get(TARGET), "drone_3h": row.get(DRONE), "missile_3h": row.get(MISSILE),
            "alert_3h": row.get("y_alert_3h")}


def history(rep, live, rows):
    """Every hour from the replay start: the replay before the first logged hour, the live log from it."""
    first = min((utc(e["t"]) for e in live), default=datetime.max)
    hours = [hour_row(x["t"], x["p"], x["tier"], "replay", rows.get(x["t"])) for x in rep if x["t"] < first]
    for e in sorted(live, key=lambda e: e["t"]):
        hours.append(hour_row(utc(e["t"]), e["p"], e["tier"], "live", rows.get(utc(e["t"])), e))
    return hours


def jev_spend():
    from .. import jev
    u = jev.usage()
    return {"calls": u["calls"], "usd": u["usd"]}


def publish(out, table=None, data=None, now=None, pipeline=None):
    """Write out/api/{now,history,model,meta}.json and return now.json as a dict; now is naive UTC."""
    now = now or datetime.now(model.UTC).replace(tzinfo=None, microsecond=0)
    data = paths.DATA if data is None else Path(data)
    table = model.load()[0] if table is None else model.prepare(table)
    m = model.current(table, data, now)
    ready = model.has_inputs(table)
    ready = ready.filter(pc.less_equal(ready["t_utc"], now))
    if not ready.num_rows:
        raise SystemExit("no hour with all the model inputs")
    row = ready.slice(ready.num_rows - 1).to_pylist()[0]
    hour = row["t_utc"]
    p, parts = model.predict(m, row)
    tier = model.tier(p)
    log(data, {"t": iso(hour), "p": p, "tier": tier, "quiet_now": row["quiet_now"], "alert": row["alert_active"],
               "issued_at": iso(now), "trained_at": m["trained_at"]})

    rep = model.replay(table)
    rows = {r["t_utc"]: r for r in table.to_pylist()}
    scored = model.scored(rep, rows)
    chans, texts = channels(data, now)
    data_until = max((c["last_post"] for c in chans if c["last_post"]), default=None)
    stale = []
    if data_until is None:
        stale.append("немає постів живих каналів")
    elif now - utc(data_until) > FRESH:
        stale.append("останній пост каналів старший за 30 хв")
    if hour < now.replace(minute=0, second=0) - HOUR:
        stale.append("немає вхідних даних за останню годину")
    if pipeline and (pipeline.get("ok") is False or pipeline.get("error")):
        stale.append("останній цикл оновлення не вдався")
    same = [x for x in scored if x["tier"] == tier]
    s = summary(same)
    now_json = {
        "schema": 1, "generated_at": iso(now), "data_until": data_until, "stale": bool(stale),
        "stale_reason": "; ".join(stale) or None, "hour": iso(hour), "window_end": iso(hour + model.H * HOUR),
        "now": {"alert": row["alert_active"], "level": row.get("alert_level_now", "alert" if row["alert_active"] else None),
                "alert_since": row.get("alert_since") and iso(utc(row["alert_since"])), "quiet_now": row["quiet_now"]},
        "forecast": {"p": round(p, 4), "tier": tier, "label": LABEL[tier], "busy_at": model.BUSY_AT,
                     "high_at": model.HIGH_AT, "reasons": reasons(m, row, parts),
                     "kind": {"n": s["hours"], "busy_share": s["busy_share"], "missile_share": s["missile_share"],
                              "drone_only_share": s["drone_only_share"], "alert_share": s["alert_share"],
                              "period": f"{scored[0]['t']:%Y-%m-%d}..{scored[-1]['t']:%Y-%m-%d}" if scored else None}},
        "model": {"name": m["name"], "trained_at": m["trained_at"], "rows": m["rows"]},
        "waves": waves(data, now, texts)}
    since = [x for x in scored if x["t"] >= split.TEST_START]
    api = Path(out) / "api"
    model.write_json(api / "model.json", m)
    model.write_json(api / "history.json", {
        "schema": 1, "generated_at": iso(now), "hours": history(rep, logged(data), rows), "tiers": tiers(scored),
        "tiers_since_test": tiers(since), "calibration": calibration(scored)}, indent=None)
    model.write_json(api / "meta.json", {"schema": 1, "generated_at": iso(now), "quality": QUALITY, "channels": chans,
                                         "pipeline": pipeline, "jev": jev_spend()})
    model.write_json(api / "now.json", now_json)
    return now_json


def pipeline_arg(text):
    """--pipeline-json: a JSON object, or the path of a file with one."""
    if not text:
        return None
    return json.loads(text if text.lstrip().startswith("{") else Path(text).read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -I -m airalerts.live.publish")
    ap.add_argument("--out", required=True, type=Path, help="the site folder; the files go to OUT/api/")
    ap.add_argument("--pipeline-json", help="the cycle runner's state: a JSON object or a file with one")
    ap.add_argument("--gold", action="store_true", help="read the gold kyiv_quiet, not the live features")
    a = ap.parse_args(argv)
    table, source = model.load(a.gold)
    n = publish(a.out, table, pipeline=pipeline_arg(a.pipeline_json))
    f = n["forecast"]
    print(f"{a.out / 'api'}: hour {n['hour']} from {source}, p {f['p']:.3f} {f['tier']}, "
          f"model trained at {n['model']['trained_at']}" + (f"; stale: {n['stale_reason']}" if n["stale"] else ""))


if __name__ == "__main__":
    main()
