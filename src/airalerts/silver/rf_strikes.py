"""Silver rf_strikes: strikes on Russia and launches at Ukraine per day, from the dronestrikemap.com API. Two tables.

strike_points  one row per strike point of a day (country RU or UA): place, region, target summary, weapons, confidence,
               the articles behind it; flags is_energy, is_moscow, occupied (occupied Ukraine that the site files under RU).
strike_days    one row per (day, country): drones and missiles launched (min, max) and intercepted, from the site's daily totals
               (RU: Russian MoD briefings; UA: Ukrainian Air Force).
The site gives a day (UTC, checked against the MoD reports: the RU intercepted total of day d is the sum of the MoD reports
published on UTC day d) and no time of day, no publication time and no revision history. So a day is known only from
d + 1 day + 6 h (user decision 2026-10-11): available_at = d 00:00Z + 30 h. Bronze is one snapshot per fetch; the newest
snapshot is used. Gold: features(con, t_table). Documentation: docs/data/silver/rf_strikes.md

Run (from the project root):
  .venv/bin/python -I -m airalerts.silver.rf_strikes                  build both tables from the newest snapshot
  .venv/bin/python -I -m airalerts.silver.rf_strikes checks           bronze, consistency of the API answers, MoD cross-check
  .venv/bin/python -I -m airalerts.silver.rf_strikes features-check   hourly features, nulls, plain-Python recomputation, ASOF
"""
import json
import random
import re
import sys
from datetime import date, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect, register_layers
from ..paths import BRONZE, FETCH_FROM, ROOT, SILVER, T0

POINTS, DAYS = "strike_points", "strike_days"
SRC = BRONZE / "strikes_rf" / "dronestrikemap"
LAG = timedelta(hours=30)          # day d is known from d + 1 day + 6 h (UTC)
CAP_HOURS = 336.0                  # hours_since_rf_energy is capped here (14 days)
FIRST_DAY = FETCH_FROM[:10]        # 2026-04-16: days before it are not kept
ENERGY = re.compile(r"refinery|fuel depot|oil|power grid|power plant|substation|gas facility|energy", re.I)
MOSCOW = ("Moscow", "Moscow Oblast")
ASOF = {t: f"SELECT * FROM {t} WHERE available_at < {{t}}" for t in (POINTS, DAYS)}
TS = pa.timestamp("us")
SCHEMAS = {
    POINTS: pa.schema([("date", pa.date32()), ("country", pa.string()), ("place", pa.string()), ("region", pa.string()),
                       ("occupied", pa.bool_()), ("lat", pa.float64()), ("lon", pa.float64()), ("summary", pa.string()),
                       ("confidence", pa.string()), ("weapons", pa.list_(pa.string())), ("n_articles", pa.int32()),
                       ("article_sources", pa.list_(pa.string())), ("is_energy", pa.bool_()), ("is_moscow", pa.bool_()),
                       ("available_at", TS)]),
    DAYS: pa.schema([("date", pa.date32()), ("country", pa.string()), ("launched_min", pa.int64()), ("launched_max", pa.int64()),
                     ("intercepted", pa.int64()), ("estimated", pa.bool_()), ("drones_max", pa.int64()), ("drones_intercepted", pa.int64()),
                     ("missiles_max", pa.int64()), ("missiles_intercepted", pa.int64()), ("basis", pa.string()), ("available_at", TS)]),
}


def snapshot():
    """The newest snapshot directory and its fetch time (the last request of its fetch log)."""
    snap = sorted(p for p in SRC.iterdir() if p.is_dir())[-1]
    log = [json.loads(x) for x in (snap / "fetch_log.jsonl").read_text().splitlines()]
    bad = [x for x in log if x["status"] != 200]
    if bad:
        raise SystemExit(f"{snap}: requests without HTTP 200: {bad[:3]}")
    return snap, datetime.strptime(log[-1]["fetched_at"], "%Y-%m-%dT%H:%M:%SZ")


def known_from(d):
    return datetime.combine(date.fromisoformat(d), datetime.min.time()) + LAG


def build_points(snap, fetched):
    rows = []
    for f in sorted((snap / "days").glob("*.json")):
        x = json.loads(f.read_text())
        d = x["date"]
        if d < FIRST_DAY or known_from(d) > fetched:  # a day not complete at the fetch is left out
            continue
        for s in x["strikes"]:
            arts = s.get("articles") or []
            region = s.get("region") or ""
            rows.append({"date": date.fromisoformat(d), "country": s["country"], "place": s.get("place"), "region": region,
                         "occupied": "(occupied)" in region, "lat": s.get("lat"), "lon": s.get("lon"), "summary": s.get("summary") or "",
                         "confidence": s.get("confidence"), "weapons": s.get("weapons") or [], "n_articles": len(arts),
                         "article_sources": [a.get("source") or "" for a in arts],
                         "is_energy": bool(ENERGY.search(s.get("summary") or "")), "is_moscow": region in MOSCOW,
                         "available_at": known_from(d)})
    return rows


def build_days(snap, fetched):
    rows = []
    for r in json.loads((snap / "timeline.json").read_text()):
        d = r["date"]
        if d < FIRST_DAY or known_from(d) > fetched:
            continue
        for c in ("RU", "UA"):
            t = r.get(c)
            if not t:
                continue
            w = t.get("by_weapon") or {}
            dr, mi = w.get("drone") or {}, w.get("missile") or {}
            rows.append({"date": date.fromisoformat(d), "country": c, "launched_min": t.get("min"), "launched_max": t.get("max"),
                         "intercepted": t.get("intercepted"), "estimated": t.get("estimated"), "drones_max": dr.get("max"),
                         "drones_intercepted": dr.get("intercepted"), "missiles_max": mi.get("max"),
                         "missiles_intercepted": mi.get("intercepted"), "basis": t.get("basis"), "available_at": known_from(d)})
    return rows


def write(name, rows, meta):
    SILVER.mkdir(parents=True, exist_ok=True)
    path = SILVER / f"{name}.parquet"
    tmp = path.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[name]).replace_schema_metadata(meta), tmp)
    tmp.replace(path)
    return len(rows)


def main():
    snap, fetched = snapshot()
    meta = {"snapshot": snap.name, "fetched_at": f"{fetched:%Y-%m-%dT%H:%M:%SZ}", "lag_hours": str(LAG.total_seconds() / 3600)}
    print({POINTS: write(POINTS, build_points(snap, fetched), meta), DAYS: write(DAYS, build_days(snap, fetched), meta), **meta})


# ------------------------------------------------------------------------------- features for gold

SQL = """
WITH t AS (SELECT DISTINCT CAST(t_utc AS TIMESTAMP) AS t_utc FROM {t_table}),
p AS (SELECT * FROM strike_points WHERE country = 'RU' AND NOT occupied)
SELECT t.t_utc,
  (SELECT count(*) FROM p WHERE p.available_at >= t.t_utc - INTERVAL 24 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_points_1d,
  (SELECT count(*) FROM p WHERE p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_points_3d,
  (SELECT count(DISTINCT region) FROM p WHERE p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_regions_3d,
  (SELECT count(*) FROM p WHERE p.is_energy AND p.available_at >= t.t_utc - INTERVAL 24 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_energy_1d,
  (SELECT count(*) FROM p WHERE p.is_energy AND p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_energy_3d,
  (SELECT count(*) > 0 FROM p WHERE p.is_moscow AND p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_moscow_3d,
  COALESCE((SELECT sum(drones_intercepted) FROM strike_days d WHERE d.country = 'RU'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS rf_drones_intercepted_1d,
  (SELECT sum(missiles_max) FROM strike_days d WHERE d.country = 'UA'
   AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc)::INTEGER AS ua_missiles_launched_1d,
  COALESCE((SELECT sum(drones_max) FROM strike_days d WHERE d.country = 'UA'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS ua_drones_launched_1d,
  LEAST({cap}, COALESCE((SELECT date_diff('second', max(p.available_at), t.t_utc) / 3600.0 FROM p
                          WHERE p.is_energy AND p.available_at < t.t_utc), {cap}))::DOUBLE AS hours_since_rf_energy
FROM t ORDER BY t.t_utc"""
COLS = ["rf_points_1d", "rf_points_3d", "rf_regions_3d", "rf_energy_1d", "rf_energy_3d", "rf_moscow_3d", "rf_drones_intercepted_1d",
        "ua_missiles_launched_1d", "ua_drones_launched_1d", "hours_since_rf_energy"]


def data_end():
    """The last hour t that features() accepts: the snapshot fetch time floored to the hour (what came later is unknown)."""
    f = datetime.strptime(pq.read_metadata(SILVER / f"{POINTS}.parquet").metadata[b"fetched_at"].decode(), "%Y-%m-%dT%H:%M:%SZ")
    return f.replace(minute=0, second=0)


def _arrow(res):
    t = res.to_arrow_table() if hasattr(res, "to_arrow_table") else res.fetch_arrow_table()
    return t.read_all() if hasattr(t, "read_all") else t


def features(con, t_table):
    """Columns for gold, one row per t_utc, only rows with available_at < t_utc (a day is known 30 h after its start).
    Russia: points in Russia without occupied Ukraine; 1d = the newest known day ([t-24h, t)), 3d = the three newest ([t-72h, t)).
    rf_points_*: strike points; rf_regions_3d: distinct regions; rf_energy_*: points whose summary names a refinery, fuel or oil
    depot, power grid or plant, substation, gas facility; rf_moscow_3d: 1 if a point is in Moscow or Moscow Oblast;
    rf_drones_intercepted_1d: drones (without missiles) the Russian MoD said it intercepted on the newest known day;
    ua_missiles_launched_1d, ua_drones_launched_1d: missiles and drones launched at Ukraine on the newest known day (Air Force, max
    of the range); ua_missiles_launched_1d is NULL when the site has no missile figure for that day (55 of 178 days), not 0;
    hours_since_rf_energy: hours from the available_at of the last energy point to t, capped at 336. t must not be after data_end()."""
    last = con.execute(f"SELECT MAX(CAST(t_utc AS TIMESTAMP)) FROM {t_table}").fetchone()[0]
    if last and last > data_end():
        raise ValueError(f"t_utc {last} is after the dronestrikemap snapshot {data_end():%Y-%m-%dT%H:%M}Z")
    return _arrow(con.execute(SQL.format(t_table=t_table, cap=CAP_HOURS)))


def _py_features(points, days, t):
    """The same features for one t in plain Python (features-check)."""
    p = [r for r in points if r["country"] == "RU" and not r["occupied"] and r["available_at"] < t]
    in1 = [r for r in p if r["available_at"] >= t - timedelta(hours=24)]
    in3 = [r for r in p if r["available_at"] >= t - timedelta(hours=72)]
    d1 = [r for r in days if t - timedelta(hours=24) <= r["available_at"] < t]
    en = [r["available_at"] for r in p if r["is_energy"]]
    return {"rf_points_1d": len(in1), "rf_points_3d": len(in3), "rf_regions_3d": len({r["region"] for r in in3}),
            "rf_energy_1d": sum(r["is_energy"] for r in in1), "rf_energy_3d": sum(r["is_energy"] for r in in3),
            "rf_moscow_3d": int(any(r["is_moscow"] for r in in3)),
            "rf_drones_intercepted_1d": sum(r["drones_intercepted"] or 0 for r in d1 if r["country"] == "RU"),
            "ua_missiles_launched_1d": sum(m) if (m := [r["missiles_max"] for r in d1 if r["country"] == "UA"
                                                         and r["missiles_max"] is not None]) else None,
            "ua_drones_launched_1d": sum(r["drones_max"] or 0 for r in d1 if r["country"] == "UA"),
            "hours_since_rf_energy": min(CAP_HOURS, (t - max(en)).total_seconds() / 3600) if en else CAP_HOURS}


# ------------------------------------------------------------------------------- commands

def cmd_checks():
    """Bronze snapshot, consistency between the two API answers, the UTC day against the MoD reports, the tables."""
    snap, fetched = snapshot()
    log = (snap / "fetch_log.jsonl").read_text().splitlines()
    print(f"snapshot {snap.name}: requests {len(log)}, all HTTP 200, last at {fetched:%Y-%m-%dT%H:%M:%SZ}")
    allp = json.loads((snap / "strikes.json").read_text())["strikes"]
    dayp = {}
    for f in (snap / "days").glob("*.json"):
        x = json.loads(f.read_text())
        dayp[x["date"]] = x["strikes"]
    diff = [(d, sum(1 for s in allp if s["date"] == d), len(v)) for d, v in sorted(dayp.items())
            if sum(1 for s in allp if s["date"] == d) != len(v)]
    print(f"day files {len(dayp)} ({min(dayp)}..{max(dayp)}); days whose point count differs between /api/strikes and /api/day: {len(diff)} {diff[:5]}")
    con = register_layers(connect())
    print("tables:", {t: con.execute(f"SELECT count(*), min(date), max(date) FROM {t}").fetchone() for t in (POINTS, DAYS)})
    print("points by country, occupied:", con.execute(f"SELECT country, occupied, count(*) FROM {POINTS} GROUP BY ALL ORDER BY ALL").fetchall())
    print("RU points without occupied, by month (points, energy, Moscow):",
          con.execute(f"""SELECT strftime(date, '%Y-%m'), count(*), count(*) FILTER (WHERE is_energy), count(*) FILTER (WHERE is_moscow)
                          FROM {POINTS} WHERE country = 'RU' AND NOT occupied GROUP BY 1 ORDER BY 1""").fetchall())
    print("UA launched by month (missiles max, drones max):",
          con.execute(f"SELECT strftime(date, '%Y-%m'), sum(missiles_max), sum(drones_max) FROM {DAYS} WHERE country = 'UA' GROUP BY 1 ORDER BY 1").fetchall())
    print("available_at = date + 30 h in every row:", all(con.execute(
        f"SELECT bool_and(available_at = CAST(date AS TIMESTAMP) + INTERVAL 30 HOUR) FROM {t}").fetchone()[0] for t in (POINTS, DAYS)))
    mod = ROOT / "data" / "verification" / "mod_russia_daily_drones.csv"  # drones the MoD reported per UTC publication day,
    if mod.exists():                                                      # parsed from @mod_russia by the previous rf_strikes
        rows = con.execute(f"""SELECT d.date, d.intercepted, (SELECT mod_drones_downed FROM read_csv('{mod}') m WHERE m.date_utc = d.date)
                                 FROM {DAYS} d WHERE d.country = 'RU' AND d.date BETWEEN DATE '2026-07-01' AND DATE '2026-10-09'
                                 ORDER BY 1""").fetchall()
        eq = sum(1 for _, a, b in rows if a == b)
        near = sum(1 for _, a, b in rows if a and b and abs(a - b) <= 0.1 * b)
        print(f"RU intercepted of the site vs sum of the MoD Telegram reports published on the same UTC day, 2026-07-01..2026-10-09: "
              f"days {len(rows)}, equal {eq}, within 10% {near}")


def cmd_features_check(seed=11):
    con = register_layers(connect())
    first, last = datetime.strptime(T0, "%Y-%m-%dT%H:%M:%SZ"), data_end()
    con.execute(f"CREATE OR REPLACE TABLE _t AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '{first}', TIMESTAMP '{last}', INTERVAL 1 HOUR) g(t)")
    f = features(con, "_t").to_pylist()
    print(f"hours {len(f)} ({first:%Y-%m-%dT%H}Z..{last:%Y-%m-%dT%H}Z), unique {len({r['t_utc'] for r in f}) == len(f)}, "
          f"nulls {sum(v is None for r in f for v in r.values())}")
    for c in COLS:
        v = [r[c] for r in f if r[c] is not None]
        print(f"  {c}: min {min(v)}, max {max(v)}, mean {sum(v) / len(v):.2f}, null {len(f) - len(v)}")
    points = _arrow(con.execute(f"SELECT * FROM {POINTS}")).to_pylist()
    days = _arrow(con.execute(f"SELECT * FROM {DAYS}")).to_pylist()
    bad = [r["t_utc"] for r in f if {c: r[c] for c in COLS} != _py_features(points, days, r["t_utc"])]
    print(f"plain-Python recomputation differs in {len(bad)} hours {bad[:3]}")
    ok = not bad and all(v is not None for r in f for c, v in r.items() if c != "ua_missiles_launched_1d")
    rnd = random.Random(seed)
    for t in sorted(rnd.sample([r["t_utc"] for r in f], 3)):
        c2 = connect()
        for name, sql in ASOF.items():
            c2.execute(f"CREATE VIEW {name} AS " + sql.format(t=f"TIMESTAMP '{t}'").replace(f"FROM {name}", f"FROM read_parquet('{SILVER / name}.parquet')"))
        c2.execute(f"CREATE TABLE _t AS SELECT TIMESTAMP '{t}' AS t_utc")
        same = features(c2, "_t").to_pylist()[0] == next(r for r in f if r["t_utc"] == t)
        ok &= same
        print(f"ASOF t={t:%Y-%m-%dT%H}Z identical to the full computation: {same}")
    print("FEATURES CHECK", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        main()
    elif cmd == "checks":
        cmd_checks()
    elif cmd == "features-check":
        sys.exit(0 if cmd_features_check() else 1)
    else:
        sys.exit(__doc__)
