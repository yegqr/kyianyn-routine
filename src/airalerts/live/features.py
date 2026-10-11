"""Live features: a row per hour t from T0 to the latest hour the live silver data covers, with the 7 inputs of the quiet
model logit_signals (docs/quiet/model.md section 3), the status columns and the targets of gold kyiv_quiet. Read only:
silver kyiv_alerts, kyiv_threat_hourly, kyiv_threat_posts, prep_signal_events and tg_posts (VA_Kyiv and
UkraineAlarmSignal, for the alert level); the only builder imported is silver/alerts.py. Gold kyiv_quiet.py imports
kyiv_hourly.py, which loads every silver builder (weather, astro, calendar_dates, political_events, rf_strikes) and the
Jev client, so its rules for these columns (read_flags, read_drone_max, read_s4, build_table) are restated here and
tests/test_live_features.py holds them equal to gold on every historical hour. Two descriptive columns are never
features: alert_level_now (the level of the alert active at t as known before t) and y_alert_3h (an alert is active at
some moment of [t, t + 3 h); null when t + 3 h is after the end of the alert data). AIRALERTS_DATA (paths.py) moves the
silver tables read, never REFERENCE, the research gold in git that check compares with.

    .venv/bin/python -I -m airalerts.live.features          rows, first and last hour, nulls per column
    .venv/bin/python -I -m airalerts.live.features check    mismatches per column against REFERENCE
"""
import sys
from bisect import bisect_left
from datetime import timedelta

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .. import paths
from ..db import connect
from ..silver import alerts

INPUTS = ("hour_kyiv", "hours_since_busy", "p_drone_max_1h", "s4_kyiv_6h", "s4_3h", "posts_jev_1h", "hours_since_drone")
STATUS = ("quiet_now", "alert_active", "busy_prev_1h")
TARGETS = ("y_busy_3h", "y_drone_3h", "y_missile_3h")  # look ahead; null when an hour of [t, t + 3 h) is not labelled
EXTRA = ("alert_level_now", "y_alert_3h")  # descriptive, never features
SCHEMA = pa.schema([("t_utc", pa.timestamp("us")), ("hour_kyiv", pa.int64()), ("hours_since_busy", pa.float64()),
                    ("p_drone_max_1h", pa.float64()), ("s4_kyiv_6h", pa.int64()), ("s4_3h", pa.int64()),
                    ("posts_jev_1h", pa.int64()), ("hours_since_drone", pa.float64())]
                   + [(c, pa.bool_()) for c in STATUS + TARGETS]
                   + [("alert_level_now", pa.string()), ("y_alert_3h", pa.bool_())])
COLUMNS = tuple(SCHEMA.names)  # t_utc, INPUTS, STATUS, TARGETS, EXTRA
TABLES = ("kyiv_alerts", "kyiv_threat_hourly", "kyiv_threat_posts", "prep_signal_events", "tg_posts")
FLAGS = ("drone_threat", "missile_threat", "missile_strike")
H = 3                      # the targets of row t are known at t + 3 h
CAP = 336                  # ceiling of hours_since_busy and hours_since_drone, as in gold
HOUR = timedelta(hours=1)
T_TABLE = "live_t"
REFERENCE = paths.ROOT / "data" / "gold" / "kyiv_quiet.parquet"  # research gold in git


def iso(t):
    return f"{t:%Y-%m-%dT%H:%M:%SZ}"


def tables(silver=None):
    """{name: path} of the silver tables the live product updates, under silver (default paths.SILVER at call time)."""
    s = paths.SILVER if silver is None else silver
    return {n: s / f"{n}.parquet" for n in TABLES}


def meta(path, key):
    return alerts.ts(pq.read_metadata(path).metadata[key.encode()].decode())


def covered_end(src):
    """The latest hour the data covers, the rule of gold: t <= data_until of the alerts (alerts.features) and
    t <= floor_hour(label_end), so the hour before t is labelled (threat_hourly.features)."""
    last = min(meta(src["kyiv_alerts"], "data_until"), meta(src["kyiv_threat_hourly"], "label_end"))
    return last.replace(minute=0, second=0, microsecond=0)


def read_flags(path):
    """{hour_utc: (drone_threat, missile_threat, missile_strike, n_posts_jev)} of every hour of kyiv_threat_hourly."""
    rows = duckdb.sql(f"SELECT hour_utc, {', '.join(FLAGS)}, n_posts_jev FROM '{path}'").fetchall()
    return {r[0]: tuple(bool(v) for v in r[1:4]) + (int(r[4]),) for r in rows}


def read_drone_max(path):
    """{hour_utc: highest p_drone of its posts}; a post is known at the end of its hour (available_at)."""
    rows = duckdb.sql(f"SELECT hour_utc, max(p_drone) FROM '{path}' WHERE available_at = hour_utc + INTERVAL 1 HOUR "
                      "GROUP BY 1").fetchall()
    return {r[0]: float(r[1]) for r in rows}


def read_s4(path):
    """S4 drone wave launches (available_at, last_post_at, toward_kyiv), sorted by available_at."""
    return duckdb.sql(f"SELECT available_at, last_post_at, toward_kyiv FROM '{path}' WHERE signal = 'S4' AND "
                      "subtype = 'launch' ORDER BY 1").fetchall()


def threat_columns(t, flags, drone_max, s4, known_at):
    """The columns of row t of gold kyiv_quiet (build_table) from the flags of the hours that ended by t, the post answers
    of the hour before t and the S4 events known before t; the targets read the hours t, t + 1 h and t + 2 h."""
    past = [flags.get(t - k * HOUR) for k in range(1, CAP + 1)]  # hours [t - k, t - k + 1), ended by t
    busy = [f is not None and any(f[:3]) for f in past]
    drone = [f is not None and f[0] for f in past]
    i3, i6, now = (bisect_left(known_at, t - k * HOUR) for k in (3, 6, 0))
    ahead = [flags.get(t + k * HOUR) for k in range(H)]
    known = None not in ahead
    return {"hours_since_busy": float(next((k for k, b in enumerate(busy) if b), CAP)),
            "p_drone_max_1h": drone_max.get(t - HOUR, 0.0),
            "s4_kyiv_6h": sum(1 for _, last, kyiv in s4[i6:now] if kyiv and last < t),  # direction known at the last post
            "s4_3h": now - i3,
            "posts_jev_1h": past[0][3] if past[0] else 0,
            "hours_since_drone": float(next((k for k, b in enumerate(drone) if b), CAP)),
            "busy_prev_1h": busy[0],
            "y_busy_3h": any(any(f[:3]) for f in ahead) if known else None,
            "y_drone_3h": any(f[0] for f in ahead) if known else None,
            "y_missile_3h": any(f[1] or f[2] for f in ahead) if known else None}


def read_alerts(path):
    """Alert intervals sorted by available_at, and the end of the alert data."""
    return pq.read_table(path).sort_by("available_at").to_pylist(), meta(path, "data_until")


def read_starts(path):
    """Alert start posts of tg_posts by the rules of silver alerts: VA_Kyiv starts as (available_at, level) in time
    order, and {post_id: level} of the Kyiv starts of eTryvoga (UkraineAlarmSignal)."""
    rows = duckdb.sql(f"SELECT channel, post_id, available_at, text FROM '{path}' WHERE channel IN ('VA_Kyiv', "
                      "'UkraineAlarmSignal') ORDER BY available_at, post_id").fetchall()
    va, etryvoga = [], {}
    for channel, post_id, at, text in rows:
        if channel == "UkraineAlarmSignal":
            if level := alerts.etryvoga_kyiv_start(text or ""):
                etryvoga[post_id] = level
            continue
        h = alerts.head(text or "")
        if alerts.START.match(h) and not alerts.END.match(h):
            va.append((at, "red" if "Червоний" in h else "yellow" if "Жовтий" in h else "alert"))
    return va, etryvoga


def levels(ts, al, va, etryvoga):
    """Level of the alert active at each t as known before t, else None. Silver alerts raise the level of an open alert
    with each VA_Kyiv start post, so max_level is known only at the end (ASOF in silver/alerts.py); here it is the
    highest start before t. An eTryvoga alert has one start post and its level never rises: max_level stands in when
    that post is not in tg_posts."""
    known, va_at, out = [a["available_at"] for a in al], [at for at, _ in va], []
    for t in ts:
        i = bisect_left(known, t) - 1  # the last alert known before t; alerts do not overlap
        a = al[i] if i >= 0 else None
        if a is None or (a["end_utc"] is not None and a["end_utc"] < t):
            out.append(None)
        elif a["start_source"] == "VA_Kyiv":
            seen = [lvl for _, lvl in va[bisect_left(va_at, a["start_utc"]):bisect_left(va_at, t)]]
            out.append(max(seen, key=alerts.RANK.get, default="alert"))
        else:
            out.append(etryvoga.get(a["start_post_id"], a["max_level"]))
    return out


def alert_ahead(ts, al, until):
    """y_alert_3h: an alert starts before t + 3 h and does not end before t; null when t + 3 h is after until."""
    al = sorted(al, key=lambda a: a["start_utc"])
    starts, out = [a["start_utc"] for a in al], []
    for t in ts:
        stop = t + H * HOUR
        if stop > until:
            out.append(None)
        else:
            out.append(any(a["end_utc"] is None or a["end_utc"] >= t for a in al[:bisect_left(starts, stop)]))
    return out


def build(end=None, silver=None):
    """The table of every hour from T0 to end (default: the latest hour the data covers), sorted by t_utc."""
    src = tables(silver)
    last = covered_end(src)
    end = last if end is None else alerts.ts(end) if isinstance(end, str) else end
    if end > last:
        raise ValueError(f"end {iso(end)} is after the latest hour the data covers, {iso(last)}")
    con = connect()
    con.execute(f"CREATE VIEW kyiv_alerts AS SELECT * FROM read_parquet('{src['kyiv_alerts']}')")
    con.execute(f"CREATE TABLE {T_TABLE} AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '{alerts.ts(paths.T0)}', "
                f"TIMESTAMP '{end}', INTERVAL 1 HOUR) AS g(t)")
    kyiv = "timezone('Europe/Kyiv', timezone('UTC', t_utc))"  # the hour_kyiv of gold kyiv_hourly
    hours = alerts.arrow(con, f"SELECT t_utc, CAST(extract(hour FROM {kyiv}) AS INTEGER) AS hour_kyiv FROM {T_TABLE} "
                              "ORDER BY t_utc").to_pylist()
    active = alerts.features(con, T_TABLE).sort_by("t_utc").select(["t_utc", "alert_active"]).to_pylist()
    if [a["t_utc"] for a in active] != [h["t_utc"] for h in hours]:
        raise ValueError("alerts.features: expected exactly one row per hour")
    flags, drone_max = read_flags(src["kyiv_threat_hourly"]), read_drone_max(src["kyiv_threat_posts"])
    s4 = read_s4(src["prep_signal_events"])
    known_at = [a for a, _, _ in s4]
    al, until = read_alerts(src["kyiv_alerts"])
    ts = [h["t_utc"] for h in hours]
    level, ahead = levels(ts, al, *read_starts(src["tg_posts"])), alert_ahead(ts, al, until)
    rows = []
    for h, a, lvl, y in zip(hours, active, level, ahead):
        row = dict(h, alert_active=a["alert_active"], **threat_columns(h["t_utc"], flags, drone_max, s4, known_at))
        row.update(quiet_now=not row["alert_active"] and not row["busy_prev_1h"], alert_level_now=lvl, y_alert_3h=y)
        rows.append(row)
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def same(a, b):
    """Equal values: nulls in the same places, floats within 1e-12."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= 1e-12 if isinstance(a, float) or isinstance(b, float) else a == b


def compare(live, gold):
    """Hours of gold missing from live, and {column: mismatches} over the hours of gold for every shared column."""
    rows = {r["t_utc"]: r for r in live.to_pylist()}
    shared = [c for c in live.column_names if c in gold.column_names and c != "t_utc"]
    missing, bad = 0, dict.fromkeys(shared, 0)
    for g in gold.select(["t_utc"] + shared).to_pylist():
        r = rows.get(g["t_utc"])
        missing += r is None
        for c in shared:
            bad[c] += r is None or not same(r[c], g[c])
    return missing, bad


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd not in ([], ["check"]):
        sys.exit("usage: python -I -m airalerts.live.features [check]")
    t = build()
    ts = t["t_utc"].to_pylist()
    print(f"rows {t.num_rows}, first hour {iso(ts[0])}, last hour {iso(ts[-1])}")
    if not cmd:
        print("nulls per column:")
        for c in t.column_names:
            print(f"  {c:<18} {t[c].null_count}")
        return
    path = REFERENCE
    gold = pq.read_table(path)
    missing, bad = compare(t, gold)
    print(f"{path}: rows {gold.num_rows}, hours missing from live {missing}; mismatches per shared column:")
    for c, n in bad.items():
        print(f"  {c:<18} {n}")
    if missing or any(bad.values()):
        sys.exit("FAIL: the live features differ from gold kyiv_quiet")
    print("OK: every shared column equals gold kyiv_quiet on every hour")


if __name__ == "__main__":
    main()
