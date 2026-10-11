"""Walk-forward runner for every fitted model. A model module defines NAME, DESCRIPTION, fit(rows) -> model and
predict(model, rows) -> [p], and its main() calls run(module).

Each fold fits on the rows whose label is known at its origin (split.py) and predicts its evaluation week from features
only: the label column is dropped before predict. dev_scores() scores a variant on the development folds only, with the
same metrics as evaluate.py, so settings are chosen there and never on the test.
"""
from . import evaluate, split
from ..gold.kyiv_hourly import LABEL


def features_only(rows):
    return rows.drop_columns([LABEL])


def fold_predictions(fit, predict, folds):
    """Probabilities for the evaluation rows of every fold, in order."""
    out = []
    for _, rows, ev in folds:
        p = list(predict(fit(rows), features_only(ev)))
        if len(p) != ev.num_rows or any(v is None or not 0 <= v <= 1 for v in p):
            raise ValueError(f"predict must return {ev.num_rows} probabilities in [0, 1]")
        out += p
    return out


def dev_scores(fit, predict, t=None):
    """BSS, Brier, PR AUC, ROC AUC over the development folds, BSS per fold, and the mean p against the share of true."""
    t = split.load() if t is None else t
    folds = split.dev_folds(t)
    p = fold_predictions(fit, predict, folds)
    y, clim, per_fold = [], [], []
    for _, rows, ev in folds:
        ys = [int(v) for v in ev[LABEL].to_pylist()]
        c = sum(rows[LABEL].to_pylist()) / rows.num_rows
        q = p[len(y):len(y) + len(ys)]
        per_fold.append(round(1 - evaluate.brier(ys, q) / evaluate.brier(ys, [c] * len(ys)), 3))
        y, clim = y + ys, clim + [c] * len(ys)
    s = evaluate.score(y, p, clim, 1.0)
    return {"bss": s["bss"], "brier": s["brier"], "pr_auc": s["pr_auc"], "roc_auc": s["roc_auc"],
            "bss_per_fold": per_fold, "mean_p": sum(p) / len(p), "share_true": sum(y) / len(y)}


def run(mod):
    """Fit and predict every development and test fold, then write data/predictions/<NAME>.parquet."""
    t = split.load()
    p = fold_predictions(mod.fit, mod.predict, split.dev_folds(t) + split.test_folds(t))
    evaluate.save(mod.NAME, mod.DESCRIPTION, evaluate.hours(t), p)
