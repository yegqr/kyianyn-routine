"""Gold table kyiv_nightly: a row per night D for the decision at 22:00 Kyiv, sleep in the corridor or in the room.
Built only from the gold table kyiv_hourly (docs/data/gold/kyiv_nightly.md):

- the features of the hourly row at 22:00 D, known before 22:00 D (t_utc is that hour);
- sums of hourly features at 24, 48 h (and 6, 12, 18 h) before it, which cover 48 and 72 h windows;
- the targets of past nights, each known at 08:00 of its morning, so always before 22:00 D;
- the target y_night: a missile strike on Kyiv in [22:00 D, 08:00 D+1), the OR of y_strike_3h of the hourly rows at
  22:00, 01:00, 04:00 and 05:00, whose windows [t, t + 3 h) cover the night exactly.

    .venv/bin/python -I -m airalerts.gold.kyiv_nightly           build data/gold/kyiv_nightly.parquet, then report
    .venv/bin/python -I -m airalerts.gold.kyiv_nightly report    report on the existing file
"""
import sys
from datetime import timedelta
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from . import kyiv_hourly as hourly
from ..paths import GOLD

PATH = GOLD / "kyiv_nightly.parquet"
LABEL = "y_night"
HOUR = timedelta(hours=1)
DECISION_HOUR = 22                            # Kyiv
LABEL_ROWS = (0, 3, 6, 7)                     # hours after 22:00 whose 3 h windows cover 22:00 .. 08:00
H = 10                                        # the target of night D is known at 08:00 D+1 = t_utc + 10 h
LOOKBACK = 72                                 # hours of hourly rows a night needs before its 22:00 row
NO_ATTACK_NIGHTS = 30                         # nights_since_attack when no attack night is known in the last 30
SUMS = {                                      # new column: (hourly column, hours back of each summed row)
    "s1_takeoff_48h": ("s1_takeoff_24h", (0, 24)),
    "s1_takeoff_72h": ("s1_takeoff_24h", (0, 24, 48)),
    "s4_drone_waves_24h": ("s4_drone_waves_6h", (0, 6, 12, 18)),
    "threat_hours_48h": ("threat_hours_24h", (0, 24)),
    "ballistic_hours_48h": ("ballistic_hours_24h", (0, 24)),
    "alert_minutes_48h": ("alert_minutes_24h", (0, 24)),
}
DROP = ("hour_kyiv", hourly.LABEL)            # hour_kyiv is always 22; the hourly label looks only 3 h ahead
KYIV = ZoneInfo("Europe/Kyiv")
UTC = ZoneInfo("UTC")


def kyiv(t):
    return t.replace(tzinfo=UTC).astimezone(KYIV)


def nights(h):
    """{night date: target or None} for every 22:00 row of the hourly table h whose label rows all exist."""
    y = dict(zip(h["t_utc"].to_pylist(), h[hourly.LABEL].to_pylist()))
    out = {}
    for t in y:
        if kyiv(t).hour == DECISION_HOUR:
            ys = [y.get(t + k * HOUR) for k in LABEL_ROWS]
            if all(t + k * HOUR in y for k in LABEL_ROWS):
                out[kyiv(t).date()] = None if None in ys else any(ys)
    return out


def build_table(h):
    """The nightly table from the hourly table h (any prefix of it gives the same features for the nights it covers)."""
    rows = {r["t_utc"]: r for r in h.to_pylist()}
    first = min(rows)
    targets = nights(h)
    out = []
    for t, r in sorted(rows.items()):
        k = kyiv(t)
        if k.hour != DECISION_HOUR or t - LOOKBACK * HOUR < first:
            continue
        d = k.date()
        row = {c: v for c, v in r.items() if c not in DROP}
        for name, (col, back) in SUMS.items():
            row[name] = sum(rows[t - b * HOUR][col] for b in back)
        past = [targets.get(d - timedelta(days=n)) for n in range(1, NO_ATTACK_NIGHTS + 1)]  # known by 08:00 D
        row["attack_last_night"] = bool(past[0])
        row["attack_nights_7"] = sum(bool(v) for v in past[:7])
        row["attack_nights_14"] = sum(bool(v) for v in past[:14])
        row["nights_since_attack"] = next((n for n, v in enumerate(past, 1) if v), NO_ATTACK_NIGHTS)
        row["night_date"] = d
        row[LABEL] = targets.get(d)
        out.append(row)
    return pa.Table.from_pylist(out)


def build():
    t = build_table(pq.read_table(hourly.PATH).sort_by("t_utc"))
    pq.write_table(t, PATH)
    report()


def report():
    t = pq.read_table(PATH)
    ys = t[LABEL].to_pylist()
    known = [v for v in ys if v is not None]
    print(f"rows {t.num_rows}, columns {t.num_columns}; nights {t['night_date'][0]} .. {t['night_date'][-1]}")
    print(f"labelled {len(known)}, attack nights {sum(known)}, quiet {len(known) - sum(known)}, null {ys.count(None)}")
    print("columns:", ", ".join(t.column_names))


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd in ([], ["build"]):
        build()
    elif cmd == ["report"]:
        report()
    else:
        sys.exit("usage: python -I -m airalerts.gold.kyiv_nightly [report]")


if __name__ == "__main__":
    main()
