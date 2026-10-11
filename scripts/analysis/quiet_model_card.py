"""The numbers of the model card of the quiet finalist logit_signals (docs/quiet/model.md). Prints only, writes nothing.

1. logit_signals (C 0.3, every hour, as frozen in docs/quiet/linear.md) fitted on every development row whose outcome
   is known before the test (split.known_by(t, split.TEST_START, 3)): the rows, the intercept, and for each of the 9
   design columns its mean, its spread (standard deviation), its weight per one spread and the odds multiplier
   exp(weight).
2. What-if: the probability of a busy next 3 hours for a base quiet hour, then one change at a time, then two combined
   scenarios. A drone hour is a busy hour, so hours_since_drone is never below hours_since_busy (the 48 h cases).
3. The verdict scale recomputed by airalerts.quiet.forecast.rules() on the development folds.

    .venv/bin/python -I scripts/analysis/quiet_model_card.py    (from the project root, a few seconds)
"""
import math

import pyarrow as pa

from airalerts.evaluation import split
from airalerts.quiet import forecast, linear, score as quiet

BASE = {"hour_kyiv": 14, "hours_since_busy": 12, "p_drone_max_1h": 0.05, "s4_kyiv_6h": 0, "s4_3h": 5,
        "posts_jev_1h": 8, "hours_since_drone": 24}
ONE_CHANGE = (
    ("21:00 instead of 14:00", {"hour_kyiv": 21}),
    ("04:00 instead of 14:00", {"hour_kyiv": 4}),
    ("attack 2 h ago", {"hours_since_busy": 2}),
    ("attack 48 h ago", {"hours_since_busy": 48}),
    ("drone posts 0.6", {"p_drone_max_1h": 0.6}),
    ("2 waves toward Kyiv", {"s4_kyiv_6h": 2}),
    ("15 launches anywhere", {"s4_3h": 15}),
    ("40 posts", {"posts_jev_1h": 40}),
)
COMBINED = (
    ("21:00 + attack 2 h ago + drone posts 0.6 + 2 waves toward Kyiv",
     {"hour_kyiv": 21, "hours_since_busy": 2, "p_drone_max_1h": 0.6, "s4_kyiv_6h": 2}),
    ("04:00 + 48 h quiet + no posts",
     {"hour_kyiv": 4, "hours_since_busy": 48, "hours_since_drone": 48, "p_drone_max_1h": 0.0, "posts_jev_1h": 0}),
)


def hour_row(change):
    r = {**BASE, **change}
    r["hours_since_drone"] = max(r["hours_since_drone"], r["hours_since_busy"])
    return r


def points(model, r):
    """The log-odds (points) of one hour and its probability."""
    spec, pipe = model
    x = linear.design(pa.table({k: [v] for k, v in r.items()}), spec)[0]
    scaler, logit = pipe.steps[0][1], pipe.steps[-1][1]
    s = float(logit.intercept_[0]) + sum(w * (v - m) / sd for v, m, sd, w in
                                         zip(x, scaler.mean_, scaler.scale_, logit.coef_[0]))
    return s, 1 / (1 + math.exp(-s))


def main():
    t = quiet.load()
    dev = split.known_by(t, split.TEST_START, quiet.H)
    y = dev[quiet.LABEL].to_pylist()
    model = linear.fit_signals(dev)
    spec, pipe = model
    scaler, logit = pipe.steps[0][1], pipe.steps[-1][1]
    print(f"1. logit_signals, C 0.3, fitted on {dev.num_rows} development rows known before the test "
          f"(busy {sum(y)}, {sum(y) / len(y):.1%})")
    print(f"   intercept {logit.intercept_[0]:+.3f} (points of an hour with every column at its mean, "
          f"p {1 / (1 + math.exp(-logit.intercept_[0])):.1%})")
    print(f"   {'column':<26} {'mean':>8} {'spread':>8} {'weight per spread':>18} {'odds x per spread':>18}")
    order = sorted(range(len(spec)), key=lambda j: -abs(logit.coef_[0][j]))
    for j in order:
        name, how = spec[j]
        print(f"   {name + ':' + how:<26} {scaler.mean_[j]:>8.3f} {scaler.scale_[j]:>8.3f} {logit.coef_[0][j]:>+18.3f} "
              f"{math.exp(logit.coef_[0][j]):>18.2f}")
    print("2. what-if: base quiet hour " + ", ".join(f"{k} {v}" for k, v in BASE.items()))
    s, p = points(model, hour_row({}))
    print(f"   {'base':<64} points {s:+.3f}  p {p:.0%}")
    for name, change in ONE_CHANGE + COMBINED:
        r = hour_row(change)
        s, p = points(model, r)
        extra = "" if r["hours_since_drone"] == {**BASE, **change}["hours_since_drone"] else \
            f" (hours_since_drone {r['hours_since_drone']})"
        print(f"   {name + extra:<64} points {s:+.3f}  p {p:.0%}")
    busy_at, high_at = forecast.rules(t)
    print(f"3. verdict scale from the development folds: busy from {busy_at:.3f} (80% of busy windows caught), "
          f"high risk from {high_at:.3f} (upper third); frozen in forecast.py {forecast.BUSY_AT}, {forecast.HIGH_AT}")


if __name__ == "__main__":
    main()
