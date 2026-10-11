"""Gold table kyiv_quiet: a row per hour t for the question "will [t, t + 3 h) be quiet in Kyiv", drones counted
(docs/data/gold/kyiv_quiet.md). Features: every feature of the gold hourly row t (known before t) and aggregates of the
hour flags of silver kyiv_threat_hourly whose hour has ended by t (an hour's flags are known at its end, as in the
ASOF of threat_hourly). Target y_busy_3h: drone_threat, missile_threat or missile_strike in one of the hours t, t + 1 h,
t + 2 h; null when one of them is past the end of the label data.

    .venv/bin/python -I -m airalerts.gold.kyiv_quiet           build data/gold/kyiv_quiet.parquet, then report
    .venv/bin/python -I -m airalerts.gold.kyiv_quiet report    report on the existing file
"""
import sys
from datetime import timedelta

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from . import kyiv_hourly as hourly
from ..modeling.split import TEST_START
from ..paths import GOLD, SILVER

PATH = GOLD / "kyiv_quiet.parquet"
THREAT = SILVER / "kyiv_threat_hourly.parquet"
LABEL = "y_busy_3h"
H = 3                                  # the target of row t is known at t + 3 h
HOUR = timedelta(hours=1)
FLAGS = ("drone_threat", "missile_threat", "missile_strike")
CAP = 336                              # hours_since_busy ceiling, as hours_since_strike in gold
COUNTS = {"drone_hours_3h": ("drone", 3), "drone_hours_6h": ("drone", 6), "drone_hours_24h": ("drone", 24),
          "busy_hours_6h": ("busy", 6), "busy_hours_24h": ("busy", 24)}


def read_flags(path=THREAT):
    """{hour_utc: (drone_threat, missile_threat, missile_strike)} of every hour of the silver table."""
    rows = duckdb.sql(f"SELECT hour_utc, {', '.join(FLAGS)} FROM '{path}'").fetchall()
    return {r[0]: tuple(bool(v) for v in r[1:]) for r in rows}


def build_table(h, flags):
    """The table from the gold hourly table h and the hour flags; features of row t read only flags of hours < t."""
    out = []
    for r in h.to_pylist():
        t = r["t_utc"]
        row = {c: v for c, v in r.items() if c != hourly.LABEL}
        past = [flags.get(t - k * HOUR) for k in range(1, CAP + 1)]        # hours [t - k, t - k + 1), ended by t
        busy = [f is not None and any(f) for f in past]
        drone = [f is not None and f[0] for f in past]
        for name, (kind, n) in COUNTS.items():
            row[name] = sum((drone if kind == "drone" else busy)[:n])
        row["busy_prev_1h"] = busy[0]
        row["hours_since_busy"] = float(next((k - 1 for k, b in enumerate(busy, 1) if b), CAP))
        row["quiet_now"] = not r["alert_active"] and not busy[0]
        ahead = [flags.get(t + k * HOUR) for k in range(H)]
        row[LABEL] = None if None in ahead else any(any(f) for f in ahead)
        out.append(row)
    return pa.Table.from_pylist(out)


def build():
    t = build_table(pq.read_table(hourly.PATH).sort_by("t_utc"), read_flags())
    pq.write_table(t, PATH)
    report()


def report():
    """Shape of the whole table, counts of the development rows only: the test stays closed (docs/adr/0011-quiet-hours.md)."""
    t = pq.read_table(PATH)
    rows = [r for r in t.select(["t_utc", LABEL, "quiet_now"]).to_pylist() if r["t_utc"] + H * HOUR <= TEST_START]
    busy = [r[LABEL] for r in rows]
    quiet = [r[LABEL] for r in rows if r["quiet_now"]]
    print(f"rows {t.num_rows}, columns {t.num_columns}; {t['t_utc'][0]} .. {t['t_utc'][-1]}; null targets {t[LABEL].null_count}")
    print(f"development rows {len(rows)}: busy {sum(busy)} ({sum(busy) / len(busy):.1%}); "
          f"quiet now {len(quiet)}, of them busy next 3 h {sum(quiet)} ({sum(quiet) / len(quiet):.1%})")


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd in ([], ["build"]):
        build()
    elif cmd == ["report"]:
        report()
    else:
        sys.exit("usage: python -I -m airalerts.gold.kyiv_quiet [report]")


if __name__ == "__main__":
    main()
