"""Quiet hours baselines (docs/quiet/baselines.md): smoothed share tables, nothing else is learned. Each table
cell is the share of busy 3 h windows among its fit rows, pulled to the share of all fit rows with the weight of W fit
hours: (busy in the cell + W x base) / (hours in the cell + W). A cell with no fit rows, or a row whose value is
missing, gets the base share. Settings are plain arguments; the defaults are the variants frozen on development.

    clim_hour        the cell of hour_kyiv
    recency_table    the cell of hours_since_busy in bins [0,3) [3,6) [6,12) [12,24) [24,48) [48,inf)
    hour_recency_nb  naive Bayes in odds: odds(base) x odds ratio of the hour cell x odds ratio of the recency cell

    .venv/bin/python -I -m airalerts.quiet.baselines    fit and predict every fold, write the predictions
"""
import sys

LABEL = "y_busy_3h"
HOUR = "hour_kyiv"
SINCE = "hours_since_busy"
CALM_NOW = "quiet_now"         # fit filter of the calm_only variants: no alert at t, no flag in [t - 1 h, t)
SINCE_EDGES = (0, 3, 6, 12, 24, 48)  # lower edges of the hours_since_busy bins, the last bin is open
CLIP = (0.01, 0.99)            # hour_recency_nb output
EPS = 1e-6                     # keeps a share away from 0 and 1 before taking odds

# frozen defaults (docs/quiet/baselines.md, "Варіанти і вибір")
CLIM_HOUR = {"weight": 10, "calm_only": False}
RECENCY = {"weight": 10, "calm_only": False}
NB = {"weight": 10, "calm_only": False}


def since_bin(v):
    """Index of the hours_since_busy bin of v; None for a missing value."""
    if v is None:
        return None
    return sum(v >= e for e in SINCE_EDGES[1:])


def fit_rows(rows, calm_only):
    """(labels 0/1, kept row indices) of the fit rows: all of them, or only the hours that are quiet now."""
    ys = [int(bool(y)) for y in rows[LABEL].to_pylist()]
    if not calm_only:
        return ys, list(range(len(ys)))
    return ys, [i for i, c in enumerate(rows[CALM_NOW].to_pylist()) if c]


def share_table(keys, ys, idx, base, weight):
    """{key: smoothed share of busy windows} over the kept rows; a missing key is left out (it gets the base)."""
    n, busy = {}, {}
    for i in idx:
        k = keys[i]
        if k is not None:
            n[k], busy[k] = n.get(k, 0) + 1, busy.get(k, 0) + ys[i]
    return {k: (busy[k] + weight * base) / (n[k] + weight) for k in n}


def fit_tables(rows, weight, calm_only, columns):
    ys, idx = fit_rows(rows, calm_only)
    base = sum(ys[i] for i in idx) / len(idx)
    out = {"base": base}
    if HOUR in columns:
        out["hour"] = share_table(rows[HOUR].to_pylist(), ys, idx, base, weight)
    if SINCE in columns:
        out["since"] = share_table([since_bin(v) for v in rows[SINCE].to_pylist()], ys, idx, base, weight)
    return out


def cell(table, key, base):
    return base if key is None else table.get(key, base)


def odds(p):
    p = min(max(p, EPS), 1 - EPS)
    return p / (1 - p)


def fit_clim_hour(rows, weight=CLIM_HOUR["weight"], calm_only=CLIM_HOUR["calm_only"]):
    return fit_tables(rows, weight, calm_only, (HOUR,))


def predict_clim_hour(model, rows):
    return [float(cell(model["hour"], h, model["base"])) for h in rows[HOUR].to_pylist()]


def fit_recency(rows, weight=RECENCY["weight"], calm_only=RECENCY["calm_only"]):
    return fit_tables(rows, weight, calm_only, (SINCE,))


def predict_recency(model, rows):
    return [float(cell(model["since"], since_bin(v), model["base"])) for v in rows[SINCE].to_pylist()]


def fit_nb(rows, weight=NB["weight"], calm_only=NB["calm_only"]):
    return fit_tables(rows, weight, calm_only, (HOUR, SINCE))


def predict_nb(model, rows):
    base = model["base"]
    ob = odds(base)
    out = []
    for h, v in zip(rows[HOUR].to_pylist(), rows[SINCE].to_pylist()):
        o = ob * (odds(cell(model["hour"], h, base)) / ob) * (odds(cell(model["since"], since_bin(v), base)) / ob)
        out.append(float(min(max(o / (1 + o), CLIP[0]), CLIP[1])))
    return out


MODELS = {
    "clim_hour": {"fit": fit_clim_hour, "predict": predict_clim_hour, "n_features": 1,
                  "description": "share of busy 3 h windows per Kyiv hour of day, pulled to the fit share (10 hours)"},
    "recency_table": {"fit": fit_recency, "predict": predict_recency, "n_features": 1,
                      "description": "share of busy 3 h windows per bin of hours since the last busy hour, pulled to the fit share (10 hours)"},
    "hour_recency_nb": {"fit": fit_nb, "predict": predict_nb, "n_features": 2,
                        "description": "naive Bayes in odds: the fit odds times the odds ratios of the hour cell and the recency cell"},
}


def main():
    from . import score as quiet
    quiet.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
