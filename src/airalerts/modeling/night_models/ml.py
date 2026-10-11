"""Night models from machine learning: tiny LightGBM, random forest, k nearest nights, Gaussian naive Bayes.

The question (docs/adr/0010-night-question.md): at 22:00 Kyiv, sleep in the corridor or in the room tonight. All four
models use the same 7 features chosen by meaning before scoring, fit only on nights from 2026-05-13 (no strike data
before 2026-05-14, so older nights have nights_since_attack 30 by construction) and use no class weights.
Variants, their dev scores and the frozen choice (the defaults below): docs/models/night_ml.md.

    .venv/bin/python -I -m airalerts.modeling.night_models.ml    write the predictions of the four models
"""
import sys
from datetime import datetime

import lightgbm
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TARGET = "y_night"
FIT_FROM = (2026, 5, 13, 19)  # UTC: 22:00 Kyiv of night 2026-05-13
SINCE, SINCE_CAP = "nights_since_attack", 14
FEATURES = (SINCE, "attack_last_night", "s1_takeoff_24h", "alerts_started_3h", "threat_hours_6h", "alert_active",
            "s4_drone_waves_6h")


def features(rows):
    """The 7 features as floats, nights_since_attack capped at 14 (a longer pause says nothing new)."""
    cols = [np.asarray(rows[c].to_numpy(zero_copy_only=False), dtype=float) for c in FEATURES]
    cols[0] = np.minimum(cols[0], SINCE_CAP)
    return np.column_stack(cols)


def training(rows):
    """Features and target of the labelled nights from FIT_FROM on."""
    start = datetime(*FIT_FROM)
    keep = np.array([x >= start for x in rows["t_utc"].to_pylist()], dtype=bool)
    y = np.array([bool(v) for v in rows[TARGET].to_pylist()], dtype=int)
    return features(rows)[keep], y[keep]


def predict_p(model, rows):
    """P(missile strike on Kyiv from 22:00 to 08:00) for each night, in the order given."""
    return [float(v) for v in model.predict_proba(features(rows))[:, 1]]


def fit_lgbm(rows, min_child_samples=12):
    x, y = training(rows)
    return lightgbm.LGBMClassifier(
        n_estimators=100, learning_rate=0.05, num_leaves=3, max_depth=2, min_child_samples=min_child_samples,
        reg_lambda=5.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, n_jobs=2, random_state=0,
        deterministic=True, force_col_wise=True, verbose=-1).fit(x, y)


def fit_forest(rows, max_depth=3, min_samples_leaf=10):
    x, y = training(rows)
    forest = RandomForestClassifier(n_estimators=500, max_depth=max_depth, min_samples_leaf=min_samples_leaf, n_jobs=2,
                                    random_state=0).fit(x, y)
    return forest.set_params(n_jobs=1)  # 2 threads add the trees' votes in a random order: p differs in the last digit


def fit_knn(rows, n_neighbors=25, weights="uniform"):
    x, y = training(rows)
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights, n_jobs=1)).fit(x, y)


def fit_nb(rows, var_smoothing=1.0):
    x, y = training(rows)
    return GaussianNB(var_smoothing=var_smoothing).fit(x, y)


MODELS = {
    "lgbm_tiny": {"fit": fit_lgbm, "predict": predict_p, "n_features": len(FEATURES),
                  "description": "LightGBM, 100 trees of depth 2, 7 features chosen by meaning, fit from 2026-05-13"},
    "random_forest": {"fit": fit_forest, "predict": predict_p, "n_features": len(FEATURES),
                      "description": "random forest, 500 trees of depth 3, at least 10 nights per leaf, 7 features chosen by meaning, fit from 2026-05-13"},
    "knn": {"fit": fit_knn, "predict": predict_p, "n_features": len(FEATURES),
            "description": "share of attacks among the 25 nearest nights on 7 scaled features, fit from 2026-05-13"},
    "gaussian_nb": {"fit": fit_nb, "predict": predict_p, "n_features": len(FEATURES),
                    "description": "Gaussian naive Bayes, var_smoothing 1, 7 features chosen by meaning, fit from 2026-05-13"},
}


def main():
    from threadpoolctl import threadpool_limits

    from .. import nights
    with threadpool_limits(2):
        nights.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
