"""Silver kyiv_alerts: air raid alerts of Kyiv city as intervals, from VA_Kyiv plus the eTryvoga patch.
Rules: docs/PARSING.md section 1. Table and features: docs/data/silver/kyiv_alerts.md.
Build:     .venv/bin/python -I -m airalerts.silver.alerts
Self-test: .venv/bin/python -I -m airalerts.silver.alerts check"""
import ast
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect, register_layers
from ..paths import ROOT, SILVER, T0
from ..telegram import TG, load

TABLE = SILVER / "kyiv_alerts.parquet"
LEAD = r"^[^0-9A-Za-zА-Яа-яЄєІіЇїҐґ]+"  # leading emoji and signs
START = re.compile(r"(м\.\s*Київ\s*[-–]\s*)?[Пп]овітряна тривога|(Червоний|Жовтий) рівень небезпеки"
                   r"|(У Києві |У столиці )?[Оо]голошено повітряну тривогу")
END = re.compile(r"(м\.\s*Київ\s*[-–]\s*)?[Вв]ідбій")
RANK = {"alert": 0, "yellow": 1, "red": 2}
BULLET = "•"
LEVELS = (("Червоний рівень тривоги", "red"), ("Жовтий рівень тривоги", "yellow"), ("Повітряна тривога", "alert"))
SCHEMA = pa.schema([
    ("alert_id", pa.int64()), ("start_utc", pa.timestamp("us")), ("end_utc", pa.timestamp("us")),
    ("duration_min", pa.float64()), ("max_level", pa.string()), ("start_source", pa.string()),
    ("start_post_id", pa.int64()), ("end_post_id", pa.int64()), ("gap_from_prev_min", pa.float64()),
    ("available_at", pa.timestamp("us"))])

# What was known before {t}: only alerts that started, the end only if it is already over. The level of an open
# alert may still rise, so max_level and duration_min are hidden together with the end.
ASOF = {"kyiv_alerts": """SELECT alert_id, start_utc,
       CASE WHEN end_utc < {t} THEN end_utc END AS end_utc,
       CASE WHEN end_utc < {t} THEN duration_min END AS duration_min,
       CASE WHEN end_utc < {t} THEN max_level END AS max_level,
       start_source, start_post_id,
       CASE WHEN end_utc < {t} THEN end_post_id END AS end_post_id,
       gap_from_prev_min, available_at
FROM kyiv_alerts WHERE available_at < {t}"""}

SQL = """
WITH h AS (SELECT DISTINCT t_utc, CAST(t_utc AS TIMESTAMP) AS t FROM {t_table}),
j AS (SELECT h.t_utc, h.t, a.start_utc AS s, a.end_utc AS e FROM h LEFT JOIN kyiv_alerts a ON a.available_at < h.t)
SELECT t_utc,
  COUNT(*) FILTER (WHERE s IS NOT NULL AND COALESCE(e, t) >= t) > 0 AS alert_active,
  COALESCE(MAX(date_diff('microsecond', s, t)) FILTER (WHERE s IS NOT NULL AND COALESCE(e, t) >= t), 0)
    / 60000000.0 AS alert_active_min,
  COUNT(*) FILTER (WHERE s >= t - INTERVAL 3 HOUR) AS alerts_started_3h,
  COUNT(*) FILTER (WHERE s >= t - INTERVAL 6 HOUR) AS alerts_started_6h,
  COUNT(*) FILTER (WHERE s >= t - INTERVAL 24 HOUR) AS alerts_started_24h,
  COALESCE(SUM(date_diff('microsecond', GREATEST(s, t - INTERVAL 24 HOUR), LEAST(COALESCE(e, t), t)))
    FILTER (WHERE s IS NOT NULL AND COALESCE(e, t) > t - INTERVAL 24 HOUR), 0) / 60000000.0 AS alert_minutes_24h,
  COUNT(*) FILTER (WHERE s >= t - INTERVAL 7 DAY) AS alerts_7d,
  COUNT(*) FILTER (WHERE s >= t - INTERVAL 14 DAY) AS alerts_14d,
  CASE WHEN COUNT(*) FILTER (WHERE s IS NOT NULL AND COALESCE(e, t) >= t) > 0 THEN 0.0
       ELSE date_diff('microsecond', MAX(e) FILTER (WHERE e < t), t) / 3600000000.0 END AS hours_since_alert_end
FROM j GROUP BY t_utc, t ORDER BY t_utc"""


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def head(text):
    return re.sub(LEAD, "", text).strip()[:120]


def etryvoga_kyiv_start(text):
    """Level of an alert start in Kyiv city in an eTryvoga post, else None (docs/PARSING.md section 1).
    Single post: first line only "Київ", second line begins with a level. Group post: line "- Київ" under a
    header that is exactly "Червоний рівень тривоги" or "Жовтий рівень тривоги" (other sections do not count)."""
    raw = [l.strip() for l in text.split("\n") if l.strip()]
    clean = [re.sub(LEAD, "", l).strip() for l in raw]
    if len(raw) >= 2 and clean[0] == "Київ" and not raw[0].startswith(BULLET):
        return next((lvl for pre, lvl in LEVELS if clean[1].startswith(pre)), None)
    header = None
    for r, c in zip(raw, clean):
        if not r.startswith(BULLET):
            header = c
        elif c == "Київ" and header in ("Червоний рівень тривоги", "Жовтий рівень тривоги"):
            return "red" if header.startswith("Червоний") else "yellow"
    return None


def build():
    """Alert rows from the bronze posts and the end of the data (last VA_Kyiv post time)."""
    va = load("VA_Kyiv")
    patch = TG / "UkraineAlarmSignal.jsonl"
    starts = sorted((r["published_at"], r["post_id"], lvl) for r in (load("UkraineAlarmSignal") if patch.exists() else [])
                    if (lvl := etryvoga_kyiv_start(r["text"])))
    alerts, cur, prev_end = [], None, None
    for r in va:
        h, t = head(r["text"]), r["published_at"]
        if END.match(h):
            if cur is None:  # end without a start: the last Kyiv start of eTryvoga before it (PARSING 1)
                c = [s for s in starts if s[0] < t and (prev_end is None or s[0] > prev_end)]
                if not c:
                    sys.exit(f"VA_Kyiv {r['post_id']}: end without a start and no Kyiv start in UkraineAlarmSignal "
                             "(run scripts/bronze/etryvoga_patch.py)")
                cur = dict(start=c[-1][0], level=c[-1][2], src="UkraineAlarmSignal", sid=c[-1][1])
            alerts.append(dict(cur, end=t, eid=r["post_id"]))
            cur, prev_end = None, t
        elif START.match(h):
            lvl = "red" if "Червоний" in h else "yellow" if "Жовтий" in h else "alert"
            if cur is None:
                cur = dict(start=t, level=lvl, src="VA_Kyiv", sid=r["post_id"])
            elif RANK[lvl] > RANK[cur["level"]]:  # a start while open: explanation or level change
                cur["level"] = lvl
    if cur:
        alerts.append(dict(cur, end=None, eid=None))
    rows, prev = [], None
    for i, a in enumerate(alerts, 1):
        s, e = ts(a["start"]), ts(a["end"]) if a["end"] else None
        rows.append(dict(alert_id=i, start_utc=s, end_utc=e, duration_min=(e - s).total_seconds() / 60 if e else None,
                         max_level=a["level"], start_source=a["src"], start_post_id=a["sid"], end_post_id=a["eid"],
                         gap_from_prev_min=(s - prev).total_seconds() / 60 if prev else None, available_at=s))
        prev = e
    return rows, max(r["published_at"] for r in va)


def main():
    rows, until = build()
    table = pa.Table.from_pylist(rows, schema=SCHEMA).replace_schema_metadata({"data_until": until})
    tmp = TABLE.with_suffix(".tmp")
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, TABLE)
    print({"rows": len(rows), "first_start": str(rows[0]["start_utc"]), "last_start": str(rows[-1]["start_utc"]),
           "open": sum(r["end_utc"] is None for r in rows), "data_until": until,
           "patched_alert_ids": [r["alert_id"] for r in rows if r["start_source"] != "VA_Kyiv"]})


def arrow(con, sql):
    r = con.execute(sql)
    return (r.to_arrow_table if hasattr(r, "to_arrow_table") else r.fetch_arrow_table)()


def features(con, t_table):
    """Alert features of Kyiv city for every t_utc of t_table, from alerts known before t_utc.
    Columns: see docs/data/silver/kyiv_alerts.md, "Ознаки для gold". t_utc must not be after the end of the data."""
    until = pq.read_metadata(TABLE).metadata.get(b"data_until")
    last = con.execute(f"SELECT MAX(CAST(t_utc AS TIMESTAMP)) FROM {t_table}").fetchone()[0]
    if until and last and last > ts(until.decode()):
        raise ValueError(f"t_utc {last} is after the end of the VA_Kyiv data {until.decode()}")
    return arrow(con, SQL.format(t_table=t_table))


def reference(alerts, t):
    """The same features by plain loops over (start, end) pairs, for the self-test. An end at or after t is unknown."""
    known = [(s, e) for s, e in alerts if s < t]
    act = [s for s, e in known if e is None or e >= t]
    ends = [e for s, e in known if e is not None and e < t]
    end = lambda e: e if e is not None and e < t else t
    minutes = lambda d: d.total_seconds() / 60
    f = {"alert_active": bool(act), "alert_active_min": minutes(t - min(act)) if act else 0.0}
    for name, d in (("alerts_started_3h", timedelta(hours=3)), ("alerts_started_6h", timedelta(hours=6)),
                    ("alerts_started_24h", timedelta(hours=24))):
        f[name] = sum(1 for s, e in known if s >= t - d)
    d24 = t - timedelta(hours=24)
    f["alert_minutes_24h"] = sum(minutes(end(e) - max(s, d24)) for s, e in known if end(e) > d24)
    for name, d in (("alerts_7d", timedelta(days=7)), ("alerts_14d", timedelta(days=14))):
        f[name] = sum(1 for s, e in known if s >= t - d)
    f["hours_since_alert_end"] = 0.0 if act else (minutes(t - max(ends)) / 60 if ends else None)
    return f


def check():
    """Self-test: counts vs va_count.py, intervals, features on every hour, two traces by hand, ASOF on 3 hours."""
    bad = []

    def ok(name, cond, info=""):
        print("OK  " if cond else "FAIL", name, info)
        if not cond:
            bad.append(name)

    fmt = lambda d: f"TIMESTAMP '{d:%Y-%m-%d %H:%M:%S}'"
    con = register_layers(connect())
    q = lambda sql: con.execute(sql).fetchone()[0]
    out = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/bronze/va_count.py"), str(TG / "VA_Kyiv.jsonl")],
                         capture_output=True, text=True, check=True).stdout
    exp = ast.literal_eval(re.search(r"\{.*?\}", out).group())
    month = "strftime(timezone('Europe/Kyiv', CAST(start_utc AS TIMESTAMPTZ)), '%m')"
    got = dict(con.execute(f"SELECT {month}, COUNT(*) FROM kyiv_alerts WHERE start_utc >= {fmt(ts(T0))} GROUP BY 1").fetchall())
    patched = dict(con.execute(f"SELECT {month}, COUNT(*) FROM kyiv_alerts WHERE start_source <> 'VA_Kyiv' GROUP BY 1").fetchall())
    ok("alerts per Kyiv month from T0 = va_count + patched", got == {m: n + patched.get(m, 0) for m, n in exp.items()},
       f"silver {dict(sorted(got.items()))} va_count {exp} patched {patched}")
    ok("alert_id unique", q("SELECT COUNT(DISTINCT alert_id) = COUNT(*) FROM kyiv_alerts"))
    ok("intervals do not overlap, end >= start, only the last may be open", q("""SELECT COUNT(*) = 0 FROM (
        SELECT start_utc, end_utc, LAG(end_utc) OVER w AS pe, ROW_NUMBER() OVER w AS rn
        FROM kyiv_alerts WINDOW w AS (ORDER BY start_utc))
        WHERE end_utc < start_utc OR (rn > 1 AND (pe IS NULL OR pe > start_utc))"""))
    ok("durations > 0", q("SELECT MIN(duration_min) > 0 FROM kyiv_alerts"), f"min {q('SELECT MIN(duration_min) FROM kyiv_alerts')} min")
    until = ts(pq.read_metadata(TABLE).metadata[b"data_until"].decode())
    last = until.replace(minute=0, second=0, microsecond=0)
    con.execute(f"CREATE OR REPLACE TEMP TABLE hours AS SELECT t_utc FROM generate_series({fmt(ts(T0))}, {fmt(last)}, INTERVAL 1 HOUR) AS g(t_utc)")
    f = features(con, "hours")
    n = int((last - ts(T0)).total_seconds() // 3600) + 1
    ok("features: one row per hour, t_utc first", f.num_rows == n and f.column_names[0] == "t_utc",
       f"{n} hours {ts(T0)} .. {last} (data ends {until}), columns {f.column_names}")
    ok("features: no nulls", all(f.column(c).null_count == 0 for c in f.column_names))
    rows = f.to_pylist()
    by_t = {r["t_utc"]: r for r in rows}
    alerts = con.execute("SELECT start_utc, end_utc FROM kyiv_alerts ORDER BY start_utc").fetchall()
    close = lambda a, b: a == b or (isinstance(a, float) and b is not None and abs(a - b) < 1e-6)
    diff = [r["t_utc"] for r in rows if not all(close(r[k], v) for k, v in reference(alerts, r["t_utc"]).items())]
    ok("features = plain Python reference on every hour", not diff, f"{len(diff)} differ")

    def trace(label, t):  # the alerts a person needs to recompute the features of hour t
        print(label, "t =", t, {k: v for k, v in by_t[t].items() if k != "t_utc"})
        for s, e in [a for a in alerts if a[0] < t - timedelta(hours=24)][-1:] + [a for a in alerts if t - timedelta(hours=24) <= a[0] < t]:
            print("      alert", s, e)

    a0 = next((a for a in alerts if datetime(2026, 10, 7, 0, 0) <= a[0] <= datetime(2026, 10, 7, 0, 40)), None)
    t_a = a0[0].replace(minute=0, second=0, microsecond=0) + timedelta(hours=1) if a0 else None
    ok("hour inside the alert that started near 2026-10-07T00:10Z", bool(a0) and a0[1] > t_a, f"alert {a0}, t {t_a}")
    if a0:
        trace("by hand A (inside the alert):", t_a)
    trace("by hand B (farthest from the last alert end):", max(rows, key=lambda r: r["hours_since_alert_end"])["t_utc"])
    inside = [r[0] for r in con.execute("SELECT t_utc FROM hours h WHERE EXISTS (SELECT 1 FROM kyiv_alerts a "
                                        "WHERE a.start_utc < h.t_utc AND a.end_utc > h.t_utc) ORDER BY 1").fetchall()]
    for t in random.Random(20261010).sample(inside, 3):
        asof = arrow(con, ASOF["kyiv_alerts"].format(t=fmt(t)))
        c2 = connect()
        c2.register("kyiv_alerts", asof)
        c2.execute(f"CREATE TEMP TABLE one AS SELECT {fmt(t)} AS t_utc")
        fa = features(c2, "one").to_pylist()[0]
        a = next(x for x in alerts if x[0] < t < x[1])
        hidden = c2.execute("SELECT end_utc FROM kyiv_alerts WHERE start_utc = ?", [a[0]]).fetchone()[0]
        known = sum(1 for x in alerts if x[0] < t)
        ok(f"ASOF t={t}", fa == by_t[t] and hidden is None and asof.num_rows == known,
           f"alert {a[0]} .. {a[1]} (end after t), ASOF end {hidden}, ASOF rows {asof.num_rows} of {len(alerts)}, features equal {fa == by_t[t]}")
    print("ALL OK" if not bad else f"FAILED: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        check()
    else:
        main()
