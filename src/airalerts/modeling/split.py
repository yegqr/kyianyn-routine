"""Time split of the gold table kyiv_hourly into development and test, without leakage (docs/adr/0008-time-split.md).

Test: every labelled hour from TEST_START, the last 6 full weeks of labels; it is opened once, for the final evaluation, and
the model is refitted every week of it. Development: every hour whose label is known at TEST_START; features, model and
threshold are chosen on weekly walk-forward folds inside it. The label of hour t covers [t, t + H), so it is known only at
t + H: whatever is fitted at an origin never sees the H - 1 hours just before it.

    .venv/bin/python -I -m airalerts.modeling.split    report: rows, true rows and attacks of every part and fold
"""
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..gold.kyiv_hourly import LABEL, PATH

H = 3                                  # hours of the label window [t, t + 3 h) of y_strike_3h
TEST_START = datetime(2026, 8, 29, 9)  # UTC: Saturday 2026-08-29 12:00 Kyiv
WEEK = timedelta(days=7)
DEV_FOLDS = 8                          # weekly folds before TEST_START, the first from 2026-07-04 12:00 Kyiv
HOUR = timedelta(hours=1)
KYIV = ZoneInfo("Europe/Kyiv")


def load(path=PATH):
    """Gold rows with a label, in time order (the last H rows have none)."""
    t = pq.read_table(path).sort_by("t_utc")
    return t.filter(pc.is_valid(t[LABEL]))


def known_by(t, origin, h=H):
    """Rows whose label is known at origin: t + h <= origin."""
    return t.filter(pc.less_equal(t["t_utc"], origin - h * HOUR))


def between(t, start, end):
    """Rows with start <= t < end."""
    return t.filter(pc.and_(pc.greater_equal(t["t_utc"], start), pc.less(t["t_utc"], end)))


def dev(t, h=H):
    return known_by(t, TEST_START, h)


def test(t):
    return t.filter(pc.greater_equal(t["t_utc"], TEST_START))


def folds(t, origins, end, h=H):
    """Walk-forward: [(origin, fit rows, evaluation rows)]; each origin fits on the rows known at it and evaluates the
    rows from it to the next origin (the last one to end)."""
    return [(o, known_by(t, o, h), between(t, o, nxt)) for o, nxt in zip(origins, origins[1:] + [end])]


def dev_folds(t, h=H):
    """DEV_FOLDS weekly folds that end at TEST_START, on development rows only."""
    return folds(dev(t, h), [TEST_START - k * WEEK for k in range(DEV_FOLDS, 0, -1)], TEST_START, h)


def test_folds(t, h=H):
    """Weekly folds over the test; each fits on every row known at its origin, development and earlier test weeks."""
    end = t["t_utc"][-1].as_py() + HOUR
    origins = [TEST_START]
    while origins[-1] + WEEK < end:
        origins.append(origins[-1] + WEEK)
    return folds(t, origins, end, h)


def attacks(t):
    """Attacks: runs of consecutive hours with a true label."""
    n, prev = 0, None
    for ts, y in zip(t["t_utc"].to_pylist(), t[LABEL].to_pylist()):
        if y and not (prev and prev[1] and ts - prev[0] == HOUR):
            n += 1
        prev = (ts, y)
    return n


def kyiv(ts):
    return f"{ts.replace(tzinfo=ZoneInfo('UTC')).astimezone(KYIV):%Y-%m-%d %H:%M}"


def line(name, part):
    ts, y = part["t_utc"].to_pylist(), part[LABEL].to_pylist()
    true = sum(y)
    return (f"  {name:<14} {kyiv(ts[0])}  {kyiv(ts[-1])}  {len(y):>5}  {true:>4}  {attacks(part):>3}  "
            f"{true / len(y):.4f}")


def report():
    t = load()
    head = f"  {'part':<14} {'first t (Kyiv)':<16}  {'last t (Kyiv)':<16}  {'rows':>5}  {'true':>4}  {'att':>3}  rate"
    print(f"gold rows with a label {t.num_rows}; H {H}; TEST_START {kyiv(TEST_START)} Kyiv ({TEST_START:%Y-%m-%dT%H:%MZ})")
    print(head)
    print(line("all", t))
    print(line("development", dev(t)))
    print(line("test", test(t)))
    purged = between(t, TEST_START - (H - 1) * HOUR, TEST_START)
    print(f"  purged before TEST_START: {purged.num_rows} rows, true {sum(purged[LABEL].to_pylist())}")
    for name, fs in (("development folds", dev_folds(t)), ("test folds", test_folds(t))):
        print(f"{name}: origin (Kyiv), fit rows, fit true, fit attacks | evaluation rows, true, attacks")
        for o, fit, ev in fs:
            print(f"  {kyiv(o)}  {fit.num_rows:>5} {sum(fit[LABEL].to_pylist()):>4} {attacks(fit):>3} | "
                  f"{ev.num_rows:>4} {sum(ev[LABEL].to_pylist()):>3} {attacks(ev):>3}")


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd in ([], ["report"]):
        report()
    else:
        sys.exit("usage: python -I -m airalerts.modeling.split [report]")


if __name__ == "__main__":
    main()
