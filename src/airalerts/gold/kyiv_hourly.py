"""Gold table kyiv_hourly: a row per hour t from T0 to the cutoff, the features() of every silver module (only what is known
before t) and the label y_strike_3h (a missile strike on Kyiv in [t, t + 3 h)). Documentation: docs/data/gold/kyiv_hourly.md.

    .venv/bin/python -I -m airalerts.gold.kyiv_hourly           build data/gold/kyiv_hourly.parquet, then report
    .venv/bin/python -I -m airalerts.gold.kyiv_hourly report    report on the existing file
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import pyarrow.parquet as pq

from ..db import connect, register_layers
from ..paths import GOLD, T0
from ..silver import alerts, astro, calendar_dates, political_events, rf_strikes, signals, threat_hourly, weather

TABLE = "kyiv_hourly"
PATH = GOLD / f"{TABLE}.parquet"
T_TABLE = "gold_t"  # the table of hours that features() and labels() read
HOUR = timedelta(hours=1)
LABEL = "y_strike_3h"
# The column groups follow t_utc, hour_kyiv and dow_kyiv in this order; the label comes last.
MODULES = (("alerts", alerts), ("threat_hourly", threat_hourly), ("signals", signals), ("weather", weather),
           ("astro", astro), ("calendar_dates", calendar_dates), ("political_events", political_events),
           ("rf_strikes", rf_strikes))


def parse_utc(s):
    """'2026-04-30T21:00:00Z' to a naive datetime (UTC)."""
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def iso(t):
    return f"{t:%Y-%m-%dT%H:%M:%SZ}"


def sql_ts(t):
    return f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'"


def arrow(con, sql):
    r = con.execute(sql)
    return (r.to_arrow_table if hasattr(r, "to_arrow_table") else r.fetch_arrow_table)()


def rejections(con, t):
    """{module: message} of the features() that refuse a t_table with the single hour t (ValueError after the data end)."""
    con.execute(f"CREATE OR REPLACE TABLE _probe AS SELECT {sql_ts(t)} AS t_utc")
    out = {}
    for name, mod in MODULES:
        try:
            mod.features(con, "_probe")
        except ValueError as e:
            out[name] = str(e)
    return out


def find_cutoff(con, t0, upper):
    """The last hour in [t0, upper] that every features() accepts, and the refusals of the next hour. A module accepts t up
    to the end of its data, so the accepted hours are a prefix of the timeline and a bisection finds its end."""
    first = rejections(con, t0)
    if first:
        raise ValueError(f"features() refuse T0 {iso(t0)}: {first}")
    lo, hi = 0, int((upper - t0) / HOUR)  # t0 + lo hours is accepted
    if not rejections(con, t0 + hi * HOUR):
        lo = hi
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if rejections(con, t0 + mid * HOUR):
            hi = mid
        else:
            lo = mid
    cutoff = t0 + lo * HOUR
    return cutoff, rejections(con, cutoff + HOUR)


def build():
    con = register_layers(connect())
    t0 = parse_utc(T0)
    upper = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    cutoff, why = find_cutoff(con, t0, upper)
    con.execute(f"CREATE OR REPLACE TABLE {T_TABLE} AS SELECT t AS t_utc FROM generate_series({sql_ts(t0)}, {sql_ts(cutoff)}, "
                f"INTERVAL 1 HOUR) AS g(t)")
    kyiv = "timezone('Europe/Kyiv', timezone('UTC', t_utc))"  # Kyiv wall clock of the naive UTC t_utc
    table = arrow(con, f"SELECT t_utc, CAST(extract(hour FROM {kyiv}) AS INTEGER) AS hour_kyiv, "
                       f"CAST(extract(isodow FROM {kyiv}) - 1 AS INTEGER) AS dow_kyiv FROM {T_TABLE} ORDER BY t_utc")
    n = table.num_rows
    parts = [(name, mod.features(con, T_TABLE)) for name, mod in MODULES] + [("labels", threat_hourly.labels(con, T_TABLE))]
    for name, f in parts:
        f = f.sort_by("t_utc")
        if f.column_names[0] != "t_utc" or f.num_rows != n or not f["t_utc"].equals(table["t_utc"]):
            raise ValueError(f"{name}: expected t_utc first and exactly one row per hour ({n} rows)")
        for c in f.column_names[1:]:
            if c in table.column_names:
                raise ValueError(f"{name}: column {c} is already in the table")
            table = table.append_column(c, f[c])
    if table.column_names[-1] != LABEL:
        raise ValueError(f"the last column is {table.column_names[-1]}, not {LABEL}")
    table = table.replace_schema_metadata({"t0_utc": T0, "cutoff_utc": iso(cutoff)})
    GOLD.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, PATH)
    print(f"built {PATH}: {n} rows, {table.num_columns} columns, T0 {iso(t0)}, cutoff {iso(cutoff)} "
          f"(the search looked for the last accepted hour up to the current hour {iso(upper)})")
    print(f"the hour after the cutoff, {iso(cutoff + HOUR)}, is refused by:" if why else "no features() refuses the hour after the cutoff")
    for name, msg in why.items():
        print(f"  {name}: {msg}")


def fmt(v):
    if v is None:
        return "null"
    if isinstance(v, datetime):
        return iso(v)
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def report(n_rows=5, seed=2026):
    """Rows, continuity, label base rate, null share per column and a few random rows of the existing file."""
    t = pq.read_table(PATH)
    meta = {k.decode(): v.decode() for k, v in (pq.read_metadata(PATH).metadata or {}).items()}
    n, ts = t.num_rows, t["t_utc"].to_pylist()
    t0, cut = parse_utc(meta["t0_utc"]), parse_utc(meta["cutoff_utc"])
    want = int((cut - t0) / HOUR) + 1
    print(f"file {PATH}: rows {n}, columns {t.num_columns}, T0 {iso(t0)}, cutoff {iso(cut)}, hours from T0 to cutoff inclusive {want}")
    print(f"t_utc first {iso(ts[0])}, last {iso(ts[-1])}, rows = hours {n == want}, unique {len(set(ts)) == n}, "
          f"continuous (every step 1 h) {all(b - a == HOUR for a, b in zip(ts, ts[1:]))}")
    y = t[LABEL].to_pylist()
    known = [v for v in y if v is not None]
    pos = sum(known)
    print(f"{LABEL}: labelled rows {len(known)}, true {pos}, false {len(known) - pos}, null {n - len(known)} at "
          f"{[iso(a) for a, v in zip(ts, y) if v is None]}")
    print(f"{LABEL} base rate = true / labelled = {pos}/{len(known)} = {pos / len(known):.4f}")
    con = register_layers(connect())
    hours, strikes = con.execute(f"SELECT count(*), count(*) FILTER (WHERE missile_strike) FROM kyiv_threat_hourly "
                                 f"WHERE hour_utc >= {sql_ts(t0)}").fetchone()
    print(f"strike hours (kyiv_threat_hourly.missile_strike) from T0: {strikes} of {hours} hours of the table")
    print("null share per column: column, type, nulls, share")
    for f in t.schema:
        k = t[f.name].null_count
        print(f"  {f.name:<24} {str(f.type):<18} {k:>5} {k / n:.6f}")
    idx = sorted(random.Random(seed).sample(range(n), n_rows))
    rows = t.take(idx).to_pylist()
    print(f"{n_rows} random rows (seed {seed}, row index {idx}), every column:")
    w = max(len(c) for c in t.column_names)
    for c in t.column_names:
        print(f"  {c:<{w}} " + " ".join(f"{fmt(r[c]):>20}" for r in rows))


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd in ([], ["build"]):
        build()
        report()
    elif cmd == ["report"]:
        report()
    else:
        sys.exit("usage: python -I -m airalerts.gold.kyiv_hourly [report]")


if __name__ == "__main__":
    main()
