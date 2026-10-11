"""Quiet hours from logistic regression: four linear models of p(the next 3 hours in Kyiv are busy), drones counted.

The question and the rules: docs/adr/0011-quiet-hours.md. scikit-learn LogisticRegression (lbfgs, max_iter 1000, no
class weights), every feature standardized inside fit, features chosen by meaning before scoring. The variants, their
development scores and the frozen choice (the defaults of the fit functions): docs/quiet/linear.md.

    .venv/bin/python -I -m airalerts.quiet.linear    write the predictions of the four models
"""
import math
import sys

import numpy as np
import pyarrow as pa
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

TARGET, DRONE, MISSILE = "y_busy_3h", "y_drone_3h", "y_missile_3h"
NOT_FEATURES = ("t_utc", TARGET, DRONE, MISSILE)
NOW = "quiet_now"                   # the hours the main evaluation is on
UNKNOWN = "ua_missiles_launched_1d"  # null means unknown, not 0
EVENING = (18, 23)                   # Kyiv hours, both included

# A feature is (column, how): "sin" and "cos" of the Kyiv hour on the 24 h circle, "evening" a 0/1 flag, "log1p", "raw".
SMALL = (("hour_kyiv", "sin"), ("hour_kyiv", "cos"), ("hour_kyiv", "evening"), ("hours_since_busy", "log1p"))
SIGNALS = SMALL + (("p_drone_max_1h", "raw"), ("s4_kyiv_6h", "raw"), ("s4_3h", "raw"), ("posts_jev_1h", "log1p"),
                   ("hours_since_drone", "log1p"))
DRONE_HEAD = (("hour_kyiv", "sin"), ("hour_kyiv", "cos"), ("p_drone_max_1h", "raw"), ("s4_kyiv_6h", "raw"),
              ("s4_3h", "raw"), ("hours_since_drone", "log1p"), ("drone_hours_24h", "raw"))
MISSILE_HEAD = (("hour_kyiv", "sin"), ("hour_kyiv", "cos"), ("hour_kyiv", "evening"), ("dark_share_3h", "raw"),
                ("hours_since_s1", "log1p"), ("s1_takeoff_6h", "raw"), ("hours_since_busy", "log1p"),
                ("hours_since_strike", "log1p"))


def column(rows, name):
    """A column as floats; a null becomes nan."""
    return np.asarray(rows[name].to_numpy(zero_copy_only=False), dtype=float)


def design(rows, spec):
    """The feature matrix of a spec of (column, how)."""
    out = []
    for name, how in spec:
        v = column(rows, name)
        if how == "sin":
            v = np.sin(2 * math.pi * v / 24)
        elif how == "cos":
            v = np.cos(2 * math.pi * v / 24)
        elif how == "evening":
            v = ((v >= EVENING[0]) & (v <= EVENING[1])).astype(float)
        elif how == "log1p":
            v = np.log1p(v)
        out.append(v)
    return np.column_stack(out)


def wide_columns(rows):
    """Every numeric or bool column but t_utc and the targets, in table order."""
    kinds = (pa.types.is_integer, pa.types.is_floating, pa.types.is_boolean)
    return tuple(f.name for f in rows.schema if f.name not in NOT_FEATURES and any(k(f.type) for k in kinds))


def wide(rows, names):
    """The given columns as floats; a null ua_missiles_launched_1d becomes -1 plus a 0/1 unknown column."""
    out = []
    for name in names:
        v = column(rows, name)
        if name == UNKNOWN:
            out += [np.where(np.isnan(v), -1.0, v), np.isnan(v).astype(float)]
        else:
            out.append(v)
    return np.column_stack(out)


def labels(rows, name):
    return np.array([bool(v) for v in rows[name].to_pylist()], dtype=int)


def training(rows, subset):
    """The hours a model learns from: "all", or only the hours that are quiet now."""
    if subset == "all":
        return rows
    if subset == NOW:
        return rows.filter(rows[NOW])
    raise ValueError(f"unknown subset {subset!r}")


def logit(x, y, c):
    with threadpool_limits(2):
        return make_pipeline(StandardScaler(), LogisticRegression(C=c, solver="lbfgs", max_iter=1000)).fit(x, y)


def proba(pipe, x):
    with threadpool_limits(2):
        return pipe.predict_proba(x)[:, 1]


def unit(p):
    return [min(1.0, max(0.0, float(v))) for v in p]


def fit_spec(rows, spec, c, subset):
    r = training(rows, subset)
    return spec, logit(design(r, spec), labels(r, TARGET), c)


def predict_spec(model, rows):
    """P(busy in the next 3 hours) for each hour, in the order given."""
    spec, pipe = model
    return unit(proba(pipe, design(rows, spec)))


def fit_small(rows, C=1.0, subset="all"):
    return fit_spec(rows, SMALL, C, subset)


def fit_signals(rows, C=0.3, subset="all"):
    return fit_spec(rows, SIGNALS, C, subset)


def fit_heads(rows, C=0.3, subset="all"):
    """A drone head on y_drone_3h and a missile head on y_missile_3h; predict never sees either target."""
    r = training(rows, subset)
    return (logit(design(r, DRONE_HEAD), labels(r, DRONE), C),
            logit(design(r, MISSILE_HEAD), labels(r, MISSILE), C))


def predict_heads(model, rows):
    """1 - (1 - p_drone)(1 - p_missile): busy when either part is."""
    p_d, p_m = proba(model[0], design(rows, DRONE_HEAD)), proba(model[1], design(rows, MISSILE_HEAD))
    return unit(1 - (1 - p_d) * (1 - p_m))


def fit_wide(rows, C=0.03, subset="all"):
    r = training(rows, subset)
    names = wide_columns(r)
    return names, logit(wide(r, names), labels(r, TARGET), C)


def predict_wide(model, rows):
    names, pipe = model
    return unit(proba(pipe, wide(rows, names)))


MODELS = {
    "logit_small": {"fit": fit_small, "predict": predict_spec, "n_features": 2,
                    "description": "logistic regression on the Kyiv hour (sin, cos, evening flag) and log hours since the last busy hour"},
    "logit_signals": {"fit": fit_signals, "predict": predict_spec, "n_features": 7,
                      "description": "logit_small plus drone signals: Jev drone p, S4 waves to Kyiv and launched, Jev posts, hours since a drone"},
    "two_heads": {"fit": fit_heads, "predict": predict_heads, "n_features": 11,
                  "description": "a drone logistic head and a missile logistic head joined as 1 - (1 - p_drone)(1 - p_missile)"},
    "logit_all_l2": {"fit": fit_wide, "predict": predict_wide, "n_features": 66,
                     "description": "negative control: L2 logistic regression with C 0.03 on every numeric or bool column"},
}


def main():
    from . import score as quiet
    quiet.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
