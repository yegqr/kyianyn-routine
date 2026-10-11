"""LightGBM model (docs/models/lgbm.md): many small decision trees, each one fixes part of the error of the trees before
it; the sum of their outputs is the log-odds of a strike in [t, t + 3 h). Objective binary, no class weights (they would
push p above the real share), no early stopping, a fixed seed and deterministic training on 2 threads.

Features are a short list chosen by meaning before any scoring: the hour and darkness, air raid alerts, missile threat and
strike history, preparation signals. Slow daily columns (rf_*, ua_*, hol_*, political events) are left out: with 26
attacks a tree can learn "this one day" from them. t_utc is never a feature; fit uses it only to drop early rows when
since is set. Settings were chosen on the development folds only (docs/models/lgbm.md, section "Варіанти і вибір").

    .venv/bin/python -I -m airalerts.modeling.lgbm    write data/predictions/lgbm.parquet
"""
import sys
from datetime import datetime

import lightgbm as lgb
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from ..gold.kyiv_hourly import LABEL
from . import runner

NAME = "lgbm"
DESCRIPTION = "LightGBM, 16 hourly features (hour, darkness, alerts, threats, strike pause, preparation signals), depth 3, 100 trees"
SEED = 20261011

FEATURES = (
    "hour_kyiv", "dark_share_3h",                                      # strikes come at night
    "alert_active", "alert_active_min", "alerts_started_3h", "alerts_started_24h", "hours_since_alert_end",
    "threat_prev_1h", "threat_hours_6h", "ballistic_hours_6h", "drone_threat_prev_1h",
    "hours_since_strike",                                              # the pause after each attack
    "s1_takeoff_24h", "hours_since_s1", "s2_mig31k_airborne", "s4_drone_waves_6h",  # preparation signals
)
WEATHER = ("wx_cloud_mean_3h", "wx_wind_max_3h", "wx_precip_sum_3h", "wx_visibility_min_3h")  # only the "broad" variant

PARAMS = {"objective": "binary", "max_depth": 3, "num_leaves": 7, "min_data_in_leaf": 50, "learning_rate": 0.05,
          "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 1.0, "seed": SEED,
          "deterministic": True, "force_col_wise": True, "num_threads": 2, "verbose": -1}
ROUNDS = 100  # chosen on the development folds: variant rounds100 (docs/models/lgbm.md)
SINCE = None  # keep every fit row; a datetime (UTC) drops fit rows before it


def matrix(rows, features):
    """The features as a float matrix in the given order: null becomes NaN (LightGBM gives it its own branch), true 1."""
    return np.column_stack([np.array(rows[c].to_pylist(), dtype=float) for c in features])


def fit_rows(rows, since=SINCE):
    """The fit rows from since on (all of them when since is None)."""
    if since is None:
        return rows
    return rows.filter(pc.greater_equal(rows["t_utc"], pa.scalar(since, pa.timestamp("us"))))


def fit(rows, features=FEATURES, rounds=ROUNDS, since=SINCE, **params):
    """A booster on the labelled rows; params override PARAMS."""
    if "t_utc" in features or LABEL in features:
        raise ValueError("t_utc and the label are never features")
    rows = fit_rows(rows, since)
    y = np.array(rows[LABEL].to_pylist(), dtype=float)
    data = lgb.Dataset(matrix(rows, features), label=y, feature_name=list(features))
    return lgb.train({**PARAMS, **params}, data, num_boost_round=rounds), tuple(features)


def predict(model, rows):
    booster, features = model
    return [float(v) for v in booster.predict(matrix(rows, features), num_threads=PARAMS["num_threads"])]


def main():
    runner.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
