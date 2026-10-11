"""Night models from plain statistics with scikit-learn (docs/nights/stats.md): the pause after an attack night,
a few evening signals, a categorical naive Bayes and an L1 control on every column. Each fit uses nights from FIT_FROM
on, no class weights and a fixed random_state; the three logistic models standardize their features on those nights,
naive Bayes takes categories and has no scaler.

    .venv/bin/python -I -m airalerts.nights.stats    fit and predict every fold, write the predictions
"""
import sys
from datetime import date

import numpy as np
import pyarrow as pa
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import CategoricalNB
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

TARGET = "y_night"
FIT_FROM = "2026-05-13"  # no strike data before 2026-05-14: earlier nights have nights_since_attack 30 by construction
PAUSE_CAP = 14
EVENING = ("s1_takeoff_24h", "threat_hours_6h", "alerts_started_3h")
NOT_FEATURES = ("t_utc", "night_date", TARGET)
UNKNOWN_IF_NULL = ("ua_missiles_launched_1d",)  # null means unknown, not 0: -1 plus a 0/1 "unknown" column
BUCKETS = (1, 2, 3, 5, 8)  # lower edges of the nights_since_attack buckets {1}, {2}, {3..4}, {5..7}, {8+}
THREADS = 2
SEED = 0


def recent(rows):
    """The labelled nights from FIT_FROM on."""
    start = date.fromisoformat(FIT_FROM)
    return rows.filter(pa.array([d >= start for d in rows["night_date"].to_pylist()]))


def column(rows, name):
    return np.array([np.nan if v is None else float(v) for v in rows[name].to_pylist()])


def labels(rows):
    return np.array([int(v) for v in rows[TARGET].to_pylist()])


def age_weights(rows, half_life):
    """0.5 ** (age in nights / half_life), the age counted from the newest night of the fit; None: all weights 1."""
    if half_life is None:
        return np.ones(rows.num_rows)
    d = rows["night_date"].to_pylist()
    newest = max(d)
    return np.array([0.5 ** ((newest - x).days / half_life) for x in d])


def pause_x(rows, extra=()):
    """attack_last_night, min(nights_since_attack, PAUSE_CAP), then the extra columns as they are."""
    cols = [column(rows, "attack_last_night"), np.minimum(column(rows, "nights_since_attack"), PAUSE_CAP)]
    return np.column_stack(cols + [column(rows, c) for c in extra])


def every_x(rows, names):
    cols = []
    for c in names:
        v = column(rows, c)
        if c in UNKNOWN_IF_NULL:
            unknown = np.isnan(v)
            cols += [np.where(unknown, -1.0, v), unknown.astype(float)]
        else:
            cols.append(v)
    return np.column_stack(cols)


def bucket(v):
    return sum(v >= b for b in BUCKETS[1:])


def bayes_x(rows):
    since, s1 = rows["nights_since_attack"].to_pylist(), rows["s1_takeoff_6h"].to_pylist()
    return np.array([[bucket(a), int(b > 0)] for a, b in zip(since, s1)])


def fit_logit(x, y, w, C, l1):
    with threadpool_limits(limits=THREADS):
        scaler = StandardScaler().fit(x)
        if l1:
            clf = LogisticRegression(l1_ratio=1, solver="liblinear", C=C, intercept_scaling=100, random_state=SEED)
        else:
            clf = LogisticRegression(l1_ratio=0, solver="lbfgs", C=C, max_iter=1000, random_state=SEED)
        clf.fit(scaler.transform(x), y, sample_weight=w)
    return {"scaler": scaler, "clf": clf}


def proba(clf, x):
    return [float(v) for v in clf.predict_proba(x)[:, list(clf.classes_).index(1)]]


def fit_logit_2(rows, C=0.3, half_life=21):
    rows = recent(rows)
    return fit_logit(pause_x(rows), labels(rows), age_weights(rows, half_life), C, False)


def predict_logit_2(model, rows):
    return proba(model["clf"], model["scaler"].transform(pause_x(rows)))


def fit_logit_5(rows, C=0.3, half_life=21):
    rows = recent(rows)
    return fit_logit(pause_x(rows, EVENING), labels(rows), age_weights(rows, half_life), C, False)


def predict_logit_5(model, rows):
    return proba(model["clf"], model["scaler"].transform(pause_x(rows, EVENING)))


def fit_naive_bayes(rows, alpha=1.0, half_life=21):
    rows = recent(rows)
    with threadpool_limits(limits=THREADS):
        nb = CategoricalNB(alpha=alpha, min_categories=[len(BUCKETS), 2])
        return nb.fit(bayes_x(rows), labels(rows), sample_weight=age_weights(rows, half_life))


def predict_naive_bayes(model, rows):
    return proba(model, bayes_x(rows))


def fit_logit_all_l1(rows, C=0.03):
    rows = recent(rows)
    names = tuple(c for c in rows.column_names if c not in NOT_FEATURES)
    return {"names": names, **fit_logit(every_x(rows, names), labels(rows), None, C, True)}


def predict_logit_all_l1(model, rows):
    return proba(model["clf"], model["scaler"].transform(every_x(rows, model["names"])))


MODELS = {
    "logit_2": {"fit": fit_logit_2, "predict": predict_logit_2, "n_features": 2,
                "description": "L2 logistic regression on the pause after an attack: attack last night, nights since attack (cap 14)"},
    "logit_5": {"fit": fit_logit_5, "predict": predict_logit_5, "n_features": 5,
                "description": "logit_2 plus three evening signals: strategic aviation takeoffs 24 h, threat hours 6 h, alerts 3 h"},
    "naive_bayes": {"fit": fit_naive_bayes, "predict": predict_naive_bayes, "n_features": 2,
                    "description": "categorical naive Bayes: nights since attack in 5 buckets, strategic aviation takeoff in the last 6 h"},
    "logit_all_l1": {"fit": fit_logit_all_l1, "predict": predict_logit_all_l1, "n_features": 60,
                     "description": "negative control: L1 logistic regression on every column of the nightly table"},
}


def main():
    from . import score as nights
    nights.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
