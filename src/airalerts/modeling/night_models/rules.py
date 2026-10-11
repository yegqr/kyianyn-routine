"""Night rule models: the recent attack rate, the quiet night after an attack, nights since the last attack
(docs/models/night_rules.md). Pure Python plus scipy; settings are plain arguments with the frozen defaults.

    .venv/bin/python -I -m airalerts.modeling.night_models.rules    fit and predict every fold, write the predictions
"""
import sys
from datetime import date

from scipy.stats import nbinom

LABEL = "y_night"
START = "2026-05-13"          # no strike data before 2026-05-14: the night of 05-13 is the first that can be an attack
W_CLIM = 10                   # clim_recent: the fit base weighs as 10 nights
W_QUIET = 8                   # refractory, hazard_table: the fit rate of nights not after an attack weighs as 8 nights
W_BUCKET = 6                  # hazard_table: each bucket is pulled to the fit base with the weight of 6 nights
W_GAPS = 3                    # renewal_nb: the recent mean gap is pulled to the mean of all fit gaps with 3 gaps
BUCKETS = ((2, 2), (3, 4), (5, 7), (8, 10 ** 6))  # nights since the last attack; 1 is the night after an attack
MIN_DISPERSION = 1.2          # renewal_nb: variance of (gap - 2) at least 1.2 x its mean
CLIP = (0.01, 0.95)
CLIP_RENEWAL = (0.03, 0.8)


def _fit_nights(rows, start):
    """(night date, attack 0/1, nights since the last attack) of the labelled nights from start (None: all)."""
    first = date.fromisoformat(start) if start else date.min
    got = zip(rows["night_date"].to_pylist(), rows[LABEL].to_pylist(), rows["nights_since_attack"].to_pylist())
    return [(d, int(bool(y)), k) for d, y, k in got if d >= first]


def _share(ys, default=0.0):
    return sum(ys) / len(ys) if ys else default


def _clip(p, box=CLIP):
    return min(max(p, box[0]), box[1])


def _odds(p):
    p = _clip(p)
    return p / (1 - p)


def _past(rows, window):
    """Attack 0/1 by night ordinal, kept only for windows longer than 28 nights (the part before D - 28)."""
    if window <= 28:
        return {}
    return {d.toordinal(): int(bool(y)) for d, y in zip(rows["night_date"].to_pylist(), rows[LABEL].to_pylist())}


def _recent(model, rows):
    """Attack nights among the `window` nights before each night: attack_nights_28 plus, for a longer window, the
    nights D - window .. D - 29 from the fit rows (all known at the fold origin; a night missing there counts as quiet)."""
    a28 = rows["attack_nights_28"].to_pylist()
    if model["window"] <= 28:
        return a28
    days = [d.toordinal() for d in rows["night_date"].to_pylist()]
    return [a + sum(model["past"].get(o - k, 0) for k in range(29, model["window"] + 1)) for o, a in zip(days, a28)]


def _quiet_level(model, recent):
    """Rate of nights not after an attack: recent attacks over the recent nights not after one (about window - a),
    pulled to the fit-row rate of such nights with the weight of W_QUIET nights."""
    return _clip((W_QUIET * model["base_quiet"] + recent) / (W_QUIET + model["window"] - recent))


def _refractory_parts(ns, window, rows):
    after = [y for _, y, k in ns if k == 1]
    return {"after": (sum(after) + 0.5) / (len(after) + 1), "base_quiet": _share([y for _, y, k in ns if k != 1]),
            "window": window, "past": _past(rows, window)}


# clim_recent ---------------------------------------------------------------------------------------------------------

def fit_clim(rows, window=28, start=START):
    return {"base": _share([y for _, y, _ in _fit_nights(rows, start)]), "window": window, "past": _past(rows, window)}


def predict_clim(model, rows):
    return [float((W_CLIM * model["base"] + a) / (W_CLIM + model["window"])) for a in _recent(model, rows)]


# refractory ----------------------------------------------------------------------------------------------------------

def fit_refractory(rows, window=28, start=START):
    return _refractory_parts(_fit_nights(rows, start), window, rows)


def predict_refractory(model, rows):
    out = []
    for after, a in zip(rows["attack_last_night"].to_pylist(), _recent(model, rows)):
        out.append(_clip(model["after"]) if after else _quiet_level(model, a))
    return [float(p) for p in out]


# hazard_table --------------------------------------------------------------------------------------------------------

def _bucket(k):
    k = max(2, 30 if k is None else k)
    return next(i for i, (lo, hi) in enumerate(BUCKETS) if lo <= k <= hi)


def fit_hazard(rows, window=28, start=None):
    ns = _fit_nights(rows, start)
    base = _share([y for _, y, _ in ns])
    table = []
    for i in range(len(BUCKETS)):
        ys = [y for _, y, k in ns if k != 1 and _bucket(k) == i]
        table.append((sum(ys) + W_BUCKET * base) / (len(ys) + W_BUCKET))
    return {**_refractory_parts(ns, window, rows), "table": table}


def predict_hazard(model, rows):
    out = []
    for k, a in zip(rows["nights_since_attack"].to_pylist(), _recent(model, rows)):
        if k == 1:
            out.append(_clip(model["after"]))
            continue
        o = _odds(model["table"][_bucket(k)]) * _odds(_quiet_level(model, a)) / _odds(model["base_quiet"])
        out.append(_clip(o / (1 + o)))
    return [float(p) for p in out]


# renewal_nb ----------------------------------------------------------------------------------------------------------

def fit_renewal(rows, last=4, start=START):
    """Gaps between attack nights in the fit rows; gap - 2 ~ negative binomial with a recent mean and the dispersion
    of all gaps. last=0 uses the mean of all gaps."""
    ns = _fit_nights(rows, start)
    days = [d for d, y, _ in ns if y]
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    after = [y for _, y, k in ns if k == 1]
    model = {"after": (sum(after) + 0.5) / (len(after) + 1)}
    if not gaps:  # no two attacks yet: a geometric gap from the fit base
        return {**model, "mu": max(1 / max(_share([y for _, y, _ in ns]), 0.02) - 2, 0.5), "dispersion": MIN_DISPERSION}
    prior = sum(gaps) / len(gaps)
    tail = gaps[-last:] if last else []
    mean = (sum(tail) + W_GAPS * prior) / (len(tail) + W_GAPS)
    xs = [max(g - 2, 0) for g in gaps]
    mx = sum(xs) / len(xs)
    var = sum((x - mx) ** 2 for x in xs) / (len(xs) - 1) if len(xs) > 1 else 0.0
    return {**model, "mu": max(mean - 2, 0.5), "dispersion": max(var / mx if mx > 0 else 0.0, MIN_DISPERSION)}


def _hazard(model, k):
    """P(gap = k | gap >= k) with gap - 2 ~ NB(mean mu, variance dispersion x mu)."""
    d = model["dispersion"]
    dist = nbinom(model["mu"] / (d - 1), 1 / d)
    x = max(k - 2, 0)
    return float(dist.pmf(x) / dist.sf(x - 1))


def predict_renewal(model, rows):
    out = []
    for k in rows["nights_since_attack"].to_pylist():
        k = 30 if k is None else k
        out.append(_clip(model["after"]) if k == 1 else _clip(_hazard(model, k), CLIP_RENEWAL))
    return [float(p) for p in out]


MODELS = {
    "clim_recent": {"fit": fit_clim, "predict": predict_clim, "n_features": 1,
                    "description": "recent attack rate: 28-night share pulled to the fit share from 2026-05-13 (10 nights)"},
    "refractory": {"fit": fit_refractory, "predict": predict_refractory, "n_features": 2,
                   "description": "Jeffreys rate after an attack night, else the recent rate of nights not after one"},
    "hazard_table": {"fit": fit_hazard, "predict": predict_hazard, "n_features": 2,
                     "description": "smoothed attack share by nights since the last attack (all fit nights), scaled to the recent level"},
    "renewal_nb": {"fit": fit_renewal, "predict": predict_renewal, "n_features": 1,
                   "description": "renewal model: negative binomial gaps between attack nights, hazard of the current gap"},
}


def main():
    from .. import nights as scorer
    scorer.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
