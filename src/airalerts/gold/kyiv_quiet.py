"""Gold table kyiv_quiet: a row per hour t for the question "will [t, t + 3 h) be quiet in Kyiv", drones counted
(docs/data/gold/kyiv_quiet.md). Features: every feature of the gold hourly row t (known before t) and aggregates of the
hour flags of silver kyiv_threat_hourly whose hour has ended by t (an hour's flags are known at its end, as in the
ASOF of threat_hourly), the Jev answers of the posts of hours that ended by t, and S4 drone wave events known before t
(their direction toward Kyiv only once their last post is before t). Target y_busy_3h: drone_threat, missile_threat or
missile_strike in one of the hours t, t + 1 h, t + 2 h; null when one of them is past the end of the label data. Two
more targets split it for models with two heads: y_drone_3h (drone_threat) and y_missile_3h (the other two).

    .venv/bin/python -I -m airalerts.gold.kyiv_quiet           build data/gold/kyiv_quiet.parquet, then report
    .venv/bin/python -I -m airalerts.gold.kyiv_quiet report    report on the existing file
"""
import sys
from bisect import bisect_left
from datetime import timedelta

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from . import kyiv_hourly as hourly
from ..modeling.split import TEST_START
from ..paths import GOLD, SILVER

PATH = GOLD / "kyiv_quiet.parquet"
THREAT = SILVER / "kyiv_threat_hourly.parquet"
POSTS = SILVER / "kyiv_threat_posts.parquet"
EVENTS = SILVER / "prep_signal_events.parquet"
LABEL = "y_busy_3h"
TARGETS = (LABEL, "y_drone_3h", "y_missile_3h")  # every column that looks ahead; models never see them
H = 3                                  # the target of row t is known at t + 3 h
HOUR = timedelta(hours=1)
FLAGS = ("drone_threat", "missile_threat", "missile_strike")
CAP = 336                              # hours_since_busy ceiling, as hours_since_strike in gold
COUNTS = {"drone_hours_3h": ("drone", 3), "drone_hours_6h": ("drone", 6), "drone_hours_24h": ("drone", 24),
          "busy_hours_3h": ("busy", 3), "busy_hours_6h": ("busy", 6), "busy_hours_24h": ("busy", 24),
          "busy_hours_168h": ("busy", 168)}


def read_flags(path=THREAT):
    """{hour_utc: (drone_threat, missile_threat, missile_strike, n_posts_jev)} of every hour of the silver table."""
    rows = duckdb.sql(f"SELECT hour_utc, {', '.join(FLAGS)}, n_posts_jev FROM '{path}'").fetchall()
    return {r[0]: tuple(bool(v) for v in r[1:4]) + (int(r[4]),) for r in rows}


def read_drone_max(path=POSTS):
    """{hour_utc: highest p_drone of its posts}; a post is known at the end of its hour (available_at)."""
    rows = duckdb.sql(f"SELECT hour_utc, max(p_drone) FROM '{path}' WHERE available_at = hour_utc + INTERVAL 1 HOUR "
                      "GROUP BY 1").fetchall()
    return {r[0]: float(r[1]) for r in rows}


def read_s4(path=EVENTS):
    """S4 drone wave launches: (available_at, last_post_at, toward_kyiv)."""
    return duckdb.sql(f"SELECT available_at, last_post_at, toward_kyiv FROM '{path}' WHERE signal = 'S4' AND "
                      "subtype = 'launch' ORDER BY 1").fetchall()


def build_table(h, flags, drone_max, s4):
    """The table from the gold hourly table h, the hour flags, the post answers and the S4 events; row t reads only
    hours that ended by t and events known before t."""
    out = []
    known_at = [a for a, _, _ in s4]  # s4 is sorted by available_at
    for r in h.to_pylist():
        t = r["t_utc"]
        row = {c: v for c, v in r.items() if c != hourly.LABEL}
        i3, i6, now = bisect_left(known_at, t - 3 * HOUR), bisect_left(known_at, t - 6 * HOUR), bisect_left(known_at, t)
        past = [flags.get(t - k * HOUR) for k in range(1, CAP + 1)]        # hours [t - k, t - k + 1), ended by t
        busy = [f is not None and any(f[:3]) for f in past]
        drone = [f is not None and f[0] for f in past]
        for name, (kind, n) in COUNTS.items():
            row[name] = sum((drone if kind == "drone" else busy)[:n])
        row["busy_prev_1h"] = busy[0]
        row["hours_since_busy"] = float(next((k - 1 for k, b in enumerate(busy, 1) if b), CAP))
        row["hours_since_drone"] = float(next((k - 1 for k, b in enumerate(drone, 1) if b), CAP))
        row["posts_jev_1h"] = sum(f[3] for f in past[:1] if f)
        row["posts_jev_3h"] = sum(f[3] for f in past[:3] if f)
        row["p_drone_max_1h"] = drone_max.get(t - HOUR, 0.0)
        row["s4_3h"] = now - i3
        row["s4_kyiv_6h"] = sum(1 for _, last, kyiv in s4[i6:now] if kyiv and last < t)
        row["quiet_now"] = not r["alert_active"] and not busy[0]
        ahead = [flags.get(t + k * HOUR) for k in range(H)]
        known = None not in ahead
        row[LABEL] = any(any(f[:3]) for f in ahead) if known else None
        row["y_drone_3h"] = any(f[0] for f in ahead) if known else None
        row["y_missile_3h"] = any(f[1] or f[2] for f in ahead) if known else None
        out.append(row)
    return pa.Table.from_pylist(out)


def build():
    t = build_table(pq.read_table(hourly.PATH).sort_by("t_utc"), read_flags(), read_drone_max(), read_s4())
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
