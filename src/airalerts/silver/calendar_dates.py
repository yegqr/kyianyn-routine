"""Silver calendar_dates: symbolic dates of Russia and Ukraine in 2026, each scored by Jev for symbolic weight.

Bronze: data/bronze/calendar/dates.csv (100 rows, docs/PARSING.md section 5) and dates_added.csv (confirmed additions).
One row = one observance on one Kyiv calendar day of 2026. Dates are known in advance, so available_at is 2000-01-01.
Jev: one Score question per date, levels 0..5, state = name, group and type only (no year, no date).
Gold: features(con, t_table). Documentation: docs/data/silver/calendar_dates.md

Run (from the project root):
  .venv/bin/python -I -m airalerts.silver.calendar_dates                    build data/silver/calendar_dates.parquet
  .venv/bin/python -I -m airalerts.silver.calendar_dates --report           ranked list and anchor checks
  .venv/bin/python -I -m airalerts.silver.calendar_dates --order-check      10 dates scored again with the levels reversed
  .venv/bin/python -I -m airalerts.silver.calendar_dates --features-check   hourly features, nulls, ASOF test
"""
import csv
import os
import random
import re
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect, register_layers
from ..jev import MODEL, ask_many
from ..paths import BRONZE, SILVER

TABLE = "calendar_dates"
PATH = SILVER / f"{TABLE}.parquet"
PROMPT_VERSION = "symb-v2"
HIGH = 3.5                       # high = symbolism >= HIGH
CAP_DAYS = 14                    # hol_days_to_next_high is capped here
AVAILABLE_AT = datetime(2000, 1, 1)  # dates are known in advance
KYIV = ZoneInfo("Europe/Kyiv")

# What the model is asked. Levels are described by situations, never by number or by neighbour (docs/JEV.md, Jev Score docs),
# so the same text works in any order. Tune these descriptions, never single dates.
INSTRUCTIONS = (
    "The state is one calendar observance, given as an object with three fields. `name` is the name of the observance "
    "(in Ukrainian). `group` is the country whose calendar it belongs to: RF means Russia, UA means Ukraine. `type` is a "
    "category label: state_holiday = official public holiday; military_glory = Russian day of military glory (anniversary "
    "of a historic battle); memorable_date = commemorative date; military_branch = professional day of a branch or service "
    "of the armed forces or of the armed forces as a whole; anniversary = anniversary of a historic political or military event; religious = religious "
    "feast; personal = birthday of a person; city_day = day of a city. "
    "Rate the symbolic weight of this observance for the political leadership and the public of the country in `group`: "
    "how strongly it stands for the identity of the state, its leader, its army or its wars, and so how much official "
    "ceremony and public attention it gets. Rate the observance itself, not any event that may happen on that day. "
    "Choose the description that fits best."
)
LEVELS = [  # index = level = score on the 0..5 scale
    "No symbolic weight. A social, folk, seasonal or professional observance that says nothing about the state, its "
    "leadership, its army or its wars; the leadership does not treat it as a political event.",
    "Minor memorable date. A commemoration known mainly to a narrow group (a profession, a community, a local or "
    "sectoral anniversary) or a commemoration of a scientific, technological, cultural or sporting achievement; "
    "it gets little attention from the leadership.",
    "Modest symbol. The professional day of a branch or service of the armed forces or of a security service, or a "
    "commemoration of an old historical battle or of a past event with limited present political meaning; marked by "
    "the institutions concerned, not by the whole country.",
    "Notable military or memorial day. A national commemoration of war, victory, sacrifice or statehood that the "
    "leadership marks officially and the media cover, but that is not among the main symbols of the country "
    "(for example a national day of remembrance of war victims, a state flag day).",
    "Major state holiday or major war anniversary. A principal public holiday with strong political meaning (the "
    "constitution, national unity, the defenders of the country, the state itself) or the anniversary of the start "
    "or of a turning point of a major war that the country treats as part of its identity (a world war, the "
    "full-scale war between Russia and Ukraine, an annexation, a major liberation or a major attack).",
    "Top national symbol of the country or of its leader. One of the very few dates of the year that stand for the "
    "identity of the state itself: the national day of independence, the main victory day, the birthday of the head "
    "of state.",
]
ANCHORS = [  # (group, name starts with, operator, level): checked on the ranked list
    ("RF", "День народження Путіна", ">=", 4), ("UA", "День Незалежності України", ">=", 4),
    ("RF", "День Перемоги", ">=", 4), ("UA", "День Конституції України", ">=", 4),
    ("RF", "День російського студентства", "<=", 2), ("RF", "День космонавтики", "<=", 2),
]
ASOF = {TABLE: f"SELECT * FROM {TABLE} WHERE available_at < {{t}}"}  # known in advance: every row, from 2000-01-01

SCHEMA = pa.schema([
    ("date", pa.date32()), ("name", pa.string()), ("group", pa.string()), ("type", pa.string()),
    ("symbolism", pa.float64()), ("symbolism_confidence", pa.float64()), ("high", pa.bool_()),
    ("jev_model", pa.string()), ("prompt_version", pa.string()), ("source_url", pa.string()),
    ("available_at", pa.timestamp("us")),
])


def jev_name(name):
    """The name as Jev sees it: no years and no date rules (everything in brackets, and '1941 року')."""
    s = re.sub(r"\s*\([^)]*\)", "", name)
    return re.sub(r"\s+\d{4}\s+року", "", s).strip()


def state(row):
    return {"name": jev_name(row["name"]), "group": row["group"], "type": row["type"]}


def question(levels=LEVELS):
    return {"symbolism": {"type": "score", "instructions": INSTRUCTIONS, "criteria": list(levels)}}


def read_bronze():
    rows = []
    for fn in ("dates.csv", "dates_added.csv"):
        with open(BRONZE / "calendar" / fn, encoding="utf-8", newline="") as f:
            rows += [dict(r) for r in csv.DictReader(f)]
    keys = [(r["date"], r["group"], r["name"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate (date, group, name) in bronze")
    return rows


def main():
    rows = read_bronze()
    answers = ask_many([(state(r), question()) for r in rows], tag=TABLE, workers=4)
    out = []
    for r, a in zip(rows, answers):
        a = a["symbolism"]
        out.append({"date": date.fromisoformat(r["date"]), "name": r["name"], "group": r["group"], "type": r["type"],
                    "symbolism": float(a["score"]), "symbolism_confidence": float(a["confidence"]),
                    "high": float(a["score"]) >= HIGH, "jev_model": MODEL, "prompt_version": PROMPT_VERSION,
                    "source_url": r["source_url"], "available_at": AVAILABLE_AT})
    out.sort(key=lambda x: (x["date"], x["group"], x["name"]))
    SILVER.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(out, schema=SCHEMA), tmp)
    os.replace(tmp, PATH)
    print(f"{PATH}: {len(out)} rows, high {sum(x['high'] for x in out)}, model {MODEL}, prompt {PROMPT_VERSION}")


def load():
    return pq.read_table(PATH).to_pylist()


def report():
    """Ranked list (stdout) and the anchor checks; True if every anchor passes."""
    rows = sorted(load(), key=lambda r: (-r["symbolism"], r["date"], r["group"], r["name"]))
    print(f"prompt {rows[0]['prompt_version']}, model {rows[0]['jev_model']}, rows {len(rows)}")
    print("rank\tdate\tgroup\ttype\tsymbolism\tconf\thigh\tname")
    for i, r in enumerate(rows, 1):
        print(f"{i}\t{r['date']}\t{r['group']}\t{r['type']}\t{r['symbolism']:.2f}\t{r['symbolism_confidence']:.2f}\t{int(r['high'])}\t{r['name']}")
    ok = True
    for group, prefix, op, level in ANCHORS:
        hit = [r for r in rows if r["group"] == group and r["name"].startswith(prefix)]
        if len(hit) != 1:
            print(f"ANCHOR FAIL {group} {prefix}: {len(hit)} rows"); ok = False; continue
        v = hit[0]["symbolism"]
        good = v >= level if op == ">=" else v <= level
        ok &= good
        print(f"ANCHOR {'PASS' if good else 'FAIL'} {group} {prefix}: {v:.2f} {op} {level}")
    for g in ("RF", "UA"):
        print(f"high {g}: {sum(r['high'] for r in rows if r['group'] == g)} of {sum(r['group'] == g for r in rows)}")
    return ok


def order_check(n=10, tol=0.5):
    """Score n dates (evenly spread over the ranking) again with the levels listed from top to bottom, map back."""
    rows = sorted(load(), key=lambda r: (-r["symbolism"], r["date"], r["group"], r["name"]))
    picks = [rows[round(i * (len(rows) - 1) / (n - 1))] for i in range(n)]
    top = len(LEVELS) - 1
    answers = ask_many([(state(r), question(LEVELS[::-1])) for r in picks], tag=TABLE, workers=4)
    worst = 0.0
    print("date\tgroup\tfirst\treversed_mapped\tdiff\tname")
    for r, a in zip(picks, answers):
        back = top - a["symbolism"]["score"]
        worst = max(worst, abs(back - r["symbolism"]))
        print(f"{r['date']}\t{r['group']}\t{r['symbolism']:.2f}\t{back:.2f}\t{abs(back - r['symbolism']):.2f}\t{r['name']}")
    print(f"max diff {worst:.2f}, tolerance {tol}: {'PASS' if worst <= tol else 'FAIL'}")
    return worst <= tol


def _arrow(con, sql):
    res = con.execute(sql)
    for name in ("to_arrow_table", "fetch_arrow_table"):
        if hasattr(res, name):
            return getattr(res, name)()
    raise RuntimeError("no arrow export on this DuckDB result")


def features(con, t_table):
    """One row per t_utc of t_table: hol_rf_symb_today, hol_ua_symb_today, hol_high_tomorrow, hol_days_to_next_high.

    The day is the Kyiv calendar day of t_utc. Dates are known in advance, so nothing here looks at the future of t."""
    typ = con.execute(f"SELECT typeof(t_utc) FROM {t_table} LIMIT 1").fetchone()
    if typ is None:
        return pa.table({"t_utc": pa.array([], pa.timestamp("us")), "hol_rf_symb_today": pa.array([], pa.float64()),
                         "hol_ua_symb_today": pa.array([], pa.float64()), "hol_high_tomorrow": pa.array([], pa.bool_()),
                         "hol_days_to_next_high": pa.array([], pa.int32())})
    inner = "t_utc" if "WITH TIME ZONE" in typ[0].upper() else "timezone('UTC', t_utc)"  # naive t_utc means UTC
    return _arrow(con, f"""
        WITH k AS (SELECT t_utc, CAST(timezone('Europe/Kyiv', {inner}) AS DATE) AS d FROM (SELECT DISTINCT t_utc FROM {t_table}))
        SELECT t_utc,
          COALESCE((SELECT max(c.symbolism) FROM {TABLE} c WHERE c."date" = k.d AND c."group" = 'RF'), 0.0) AS hol_rf_symb_today,
          COALESCE((SELECT max(c.symbolism) FROM {TABLE} c WHERE c."date" = k.d AND c."group" = 'UA'), 0.0) AS hol_ua_symb_today,
          EXISTS (SELECT 1 FROM {TABLE} c WHERE c."date" = k.d + 1 AND c.high) AS hol_high_tomorrow,
          CAST(LEAST({CAP_DAYS}, COALESCE((SELECT min(c."date" - k.d) FROM {TABLE} c WHERE c.high AND c."date" >= k.d), {CAP_DAYS}))
               AS INTEGER) AS hol_days_to_next_high
        FROM k ORDER BY t_utc""")


def _py_features(rows, t):
    """The same four features in plain Python from the rows, as an independent check of the SQL."""
    d = t.replace(tzinfo=timezone.utc).astimezone(KYIV).date()
    rf = max([r["symbolism"] for r in rows if r["date"] == d and r["group"] == "RF"], default=0.0)
    ua = max([r["symbolism"] for r in rows if r["date"] == d and r["group"] == "UA"], default=0.0)
    tomorrow = any(r["high"] for r in rows if r["date"] == d + timedelta(days=1))
    ahead = sorted(r["date"] for r in rows if r["high"] and r["date"] >= d)
    return rf, ua, tomorrow, min(CAP_DAYS, (ahead[0] - d).days) if ahead else CAP_DAYS


def _hours(con, name, first, last):
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '{first}', "
                f"TIMESTAMP '{last}', INTERVAL 1 HOUR) AS g(t)")


def _asof_connection(t):
    """DuckDB where view calendar_dates is the table as it was known before t (the ASOF rule)."""
    con = connect()
    con.execute(f"CREATE TABLE _all AS SELECT * FROM read_parquet('{PATH}')")
    sql = ASOF[TABLE].format(t=f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'").replace(f"FROM {TABLE}", "FROM _all")
    con.execute(f"CREATE VIEW {TABLE} AS {sql}")
    return con


def features_check(first="2026-04-30 21:00:00", last="2026-10-12 21:00:00", seed=7):
    rows = load()
    con = register_layers(connect())
    ok = True
    for lo, hi in ((first, last), (first, "2026-12-25 21:00:00")):
        _hours(con, "t_hours", lo, hi)
        res = features(con, "t_hours")
        n_t = con.execute("SELECT count(*) FROM t_hours").fetchone()[0]
        nulls = {c: res[c].null_count for c in res.column_names}
        pyexp = [_py_features(rows, t) for t in res["t_utc"].to_pylist()]
        sql_rows = list(zip(*[res[c].to_pylist() for c in res.column_names[1:]]))
        same = all(abs(a[0] - b[0]) < 1e-12 and abs(a[1] - b[1]) < 1e-12 and a[2:] == b[2:] for a, b in zip(sql_rows, pyexp))
        good = res.num_rows == n_t and res.column_names[0] == "t_utc" and not any(nulls.values()) and same
        ok &= good
        print(f"t {lo}Z..{hi}Z: rows {res.num_rows} of {n_t} hours, columns {res.column_names}, nulls {nulls}, "
              f"equals plain-Python recomputation: {same} -> {'PASS' if good else 'FAIL'}")
    _hours(con, "t_hours", first, last)
    full = {r["t_utc"]: r for r in features(con, "t_hours").to_pylist()}
    t7 = datetime(2026, 10, 6, 21)
    v = full[t7]["hol_rf_symb_today"]
    ok &= v >= 4
    print(f"t=2026-10-06T21:00Z (00:00 Kyiv, 7 October): hol_rf_symb_today {v:.2f} {'PASS' if v >= 4 else 'FAIL'}; row {full[t7]}")
    for s in ("2026-05-08 20:00:00", "2026-05-09 20:00:00", "2026-06-27 21:00:00", "2026-08-24 05:00:00", "2026-10-12 21:00:00"):
        print("  sample", s, full.get(datetime.fromisoformat(s)))
    con.execute("CREATE OR REPLACE TABLE t_tz AS SELECT CAST(t_utc AS TIMESTAMPTZ) AS t_utc FROM t_hours")
    tz = features(con, "t_tz")
    same_tz = [tuple(x.values())[1:] for x in tz.to_pylist()] == [tuple(x.values())[1:] for x in features(con, "t_hours").to_pylist()]
    ok &= same_tz
    print(f"TIMESTAMPTZ t_table gives the same features: {same_tz}")
    picks = random.Random(seed).sample(sorted(full), 3)
    for t in picks:
        c2 = _asof_connection(t)
        c2.execute(f"CREATE TABLE t1 AS SELECT TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}' AS t_utc")
        got = features(c2, "t1").to_pylist()
        same_asof = got == [full[t]]
        ok &= same_asof
        print(f"ASOF t={t:%Y-%m-%dT%H:%M}Z rows {len(got)} identical to the full computation: {same_asof}")
    print("FEATURES CHECK", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "":
        main()
    elif cmd in ("--report", "--order-check", "--features-check"):
        sys.exit(0 if {"--report": report, "--order-check": order_check, "--features-check": features_check}[cmd]() else 1)
    else:
        sys.exit("usage: python -I -m airalerts.silver.calendar_dates [--report | --order-check | --features-check]")
