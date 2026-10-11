"""Quiet hours models from trees: small LightGBM, small random forest, LightGBM on every column, Gaussian naive Bayes.

The question (docs/adr/0011-quiet-hours.md): at the start of hour t, will the next 3 hours in Kyiv be quiet, drones
counted. Three models use the same 13 features chosen by meaning before scoring; lgbm_all is the negative control on
every numeric or bool column. No class weights, fixed seeds, at most 2 threads, fit on every labelled hour.
Variants, their dev scores and the frozen choice (the defaults below): docs/models/quiet_trees.md.

    .venv/bin/python -I -m airalerts.modeling.quiet_models.trees    write the predictions of the four models
"""
import sys

import lightgbm
import numpy as np
import pyarrow as pa
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB

TARGET = "y_busy_3h"
TARGETS = ("y_busy_3h", "y_drone_3h", "y_missile_3h")
TIME = "t_utc"
FEATURES = ("hour_kyiv", "dark_share_3h", "hours_since_busy", "hours_since_drone", "busy_hours_24h", "drone_hours_24h",
            "posts_jev_1h", "posts_jev_3h", "p_drone_max_1h", "s4_3h", "s4_kyiv_6h", "s1_takeoff_6h",
            "hours_since_alert_end")
N_ALL = 66  # numeric or bool columns of kyiv_quiet without t_utc and the three targets


def matrix(rows, cols):
    """The given columns as a float matrix; a null (unknown) stays NaN, never 0."""
    return np.column_stack([np.asarray(rows[c].cast(pa.float64()).to_numpy(zero_copy_only=False), dtype=float)
                            for c in cols])


def every_column(rows):
    """Every numeric or bool column except t_utc and the targets, in table order."""
    kinds = (pa.types.is_integer, pa.types.is_floating, pa.types.is_boolean)
    return tuple(f.name for f in rows.schema
                 if f.name != TIME and f.name not in TARGETS and any(k(f.type) for k in kinds))


def training(rows, cols):
    """Features and target of the hours whose target is known."""
    y = rows[TARGET].to_pylist()
    keep = np.array([v is not None for v in y], dtype=bool)
    return matrix(rows, cols)[keep], np.array([bool(v) for v in y], dtype=int)[keep]


def booster(x, y, min_child_samples):
    return lightgbm.LGBMClassifier(
        n_estimators=300, learning_rate=0.03, num_leaves=7, max_depth=3, min_child_samples=min_child_samples,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0, n_jobs=2, random_state=0,
        deterministic=True, force_col_wise=True, verbose=-1).fit(x, y)


def fit_lgbm(rows, min_child_samples=80):
    return booster(*training(rows, FEATURES), min_child_samples), FEATURES


def fit_lgbm_all(rows, min_child_samples=80):
    cols = every_column(rows)
    return booster(*training(rows, cols), min_child_samples), cols


def fit_forest(rows, max_depth=4, min_samples_leaf=20):
    x, y = training(rows, FEATURES)
    forest = RandomForestClassifier(n_estimators=500, max_depth=max_depth, min_samples_leaf=min_samples_leaf, n_jobs=2,
                                    random_state=0).fit(x, y)
    return forest.set_params(n_jobs=1), FEATURES  # 2 threads add the trees' votes in a random order


def fit_nb(rows, var_smoothing=1.0):
    return GaussianNB(var_smoothing=var_smoothing).fit(*training(rows, FEATURES)), FEATURES


def predict_p(model, rows):
    """P(busy in the next 3 hours) for each hour, in the order given."""
    est, cols = model
    return [min(1.0, max(0.0, float(v))) for v in est.predict_proba(matrix(rows, cols))[:, 1]]


MODELS = {
    "lgbm_small": {"fit": fit_lgbm, "predict": predict_p, "n_features": len(FEATURES),
                   "description": "LightGBM, 300 trees of depth 3, at least 80 hours per leaf, 13 features chosen by meaning"},
    "rf_small": {"fit": fit_forest, "predict": predict_p, "n_features": len(FEATURES),
                 "description": "random forest, 500 trees of depth 4, at least 20 hours per leaf, 13 features chosen by meaning"},
    "lgbm_all": {"fit": fit_lgbm_all, "predict": predict_p, "n_features": N_ALL,
                 "description": "negative control: the same LightGBM (80 hours per leaf) on every numeric or bool column (66)"},
    "gaussian_nb": {"fit": fit_nb, "predict": predict_p, "n_features": len(FEATURES),
                    "description": "Gaussian naive Bayes, var_smoothing 1, 13 features chosen by meaning"},
}


def main():
    from threadpoolctl import threadpool_limits

    from .. import quiet
    with threadpool_limits(2):
        quiet.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
