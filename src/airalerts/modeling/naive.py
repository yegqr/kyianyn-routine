"""Naive baseline (docs/METHODOLOGY.md 4.2): the probability of a strike in [t, t + H) is the share of true labels among the
hourly windows of the last 7 days whose label is already known at t, that is rows t' with t - 7 d <= t' <= t - H.
Nothing is fitted; the window moves every hour, as it would in real time.

    .venv/bin/python -I -m airalerts.modeling.naive    write data/predictions/naive_7d.parquet
"""
from bisect import bisect_left, bisect_right
from datetime import timedelta

from ..gold.kyiv_hourly import LABEL
from . import evaluate, split

NAME = "naive_7d"
DAYS = 7


def predict(t, at, h=split.H, days=DAYS):
    """p for every hour in at, from the labelled gold rows t (time order)."""
    ts = t["t_utc"].to_pylist()
    prefix = [0]
    for y in t[LABEL].to_pylist():
        prefix.append(prefix[-1] + y)
    out = []
    for x in at:
        i, j = bisect_left(ts, x - timedelta(days=days)), bisect_right(ts, x - h * split.HOUR)
        if j <= i:
            raise ValueError(f"no label known at {x} in the last {days} days")
        out.append((prefix[j] - prefix[i]) / (j - i))
    return out


def main():
    t = split.load()
    at = evaluate.hours(t)
    evaluate.save(NAME, "share of true labels among the windows of the last 7 days known at t", at, predict(t, at))


if __name__ == "__main__":
    main()
