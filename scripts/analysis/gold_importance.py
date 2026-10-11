"""Which data sources of the gold table kyiv_quiet drive the forecast "will the next 3 hours in Kyiv be quiet"
(docs/adr/0011-quiet-hours.md), so that a live product parses only what pays off. Plain write-up: docs/quiet/sources.md.
Prints only, writes nothing.

Rules fixed before anything was scored:
- target y_busy_3h; t_utc and the three targets are never features; every other column of the table is used;
- every score is on the development weekly walk-forward folds (quiet.score), pooled over the quiet-now hours; the model
  learns from all hours of the fold, like the finalist and logit_all_l2 (training on quiet-now hours never helped,
  docs/quiet/linear.md);
- the model: standardized L2 logistic regression (quiet.linear.logit), C = 0.03, the value already chosen on development
  for the same 66 columns (logit_all_l2), not tuned again; transforms by meaning, as in the finalist: the Kyiv hour as
  sin, cos and an evening flag, every hours_since_* as log(1 + x), the rest raw; a null ua_missiles_launched_1d is -1
  plus a 0/1 unknown column; quiet_now is in a set only when both alerts and the Jev flags are (it is made of them);
- permutation importance: shuffle the columns of a source (or one column) together among the quiet-now hours of each
  development week, 20 repeats, seed 20261011; the drop in BSS and ROC AUC against the unshuffled model;
- the source rule: the time of day is always in (free); the recommended live set is the smallest number of other sources
  whose development BSS is at least BSS(all sources) - 0.01; among sets of that size the highest development BSS;
- the test is scored once, only as a report, for that set, the all-sources model and the finalist logit_signals;
- near constant: the most common value covers at least 95% of development quiet-now hours.

    .venv/bin/python -I scripts/analysis/gold_importance.py    (from the project root, about two minutes)
"""
import math
from itertools import combinations

import numpy as np

from airalerts.evaluation import metrics, split
from airalerts.quiet import linear, score as quiet

SEED, REPEATS, C, TOL, NEAR_CONSTANT = 20261011, 20, 0.03, 0.01, 0.95

# key, what it is, how a live product gets it, columns
SOURCES = (
    ("time", "hour and weekday in Kyiv", "free: the clock", ("hour_kyiv", "dow_kyiv")),
    ("astro", "darkness and moon", "free: computed offline (NOAA, Meeus)", ("dark_share_3h", "moon_illum")),
    ("alerts", "Kyiv air raid alerts", "1 Telegram channel VA_Kyiv, regex, no LLM",
     ("alert_active", "alert_active_min", "alerts_started_3h", "alerts_started_6h", "alerts_started_24h",
      "alert_minutes_24h", "alerts_7d", "alerts_14d", "hours_since_alert_end")),
    ("jev_flags", "Kyiv threat and strike flags", "7 Kyiv Telegram channels, Jev (LLM) on every post",
     ("threat_prev_1h", "threat_hours_6h", "threat_hours_24h", "ballistic_hours_3h", "ballistic_hours_6h",
      "ballistic_hours_24h", "drone_threat_prev_1h", "strikes_7d", "strikes_14d", "hours_since_strike",
      "drone_hours_3h", "drone_hours_6h", "drone_hours_24h", "busy_hours_3h", "busy_hours_6h", "busy_hours_24h",
      "busy_hours_168h", "busy_prev_1h", "hours_since_busy", "hours_since_drone", "p_drone_max_1h")),
    ("posts_regex", "how many Kyiv posts pass the regex prefilter", "the same 7 channels, regex only, no LLM",
     ("posts_jev_1h", "posts_jev_3h")),
    ("signals", "preparation signals S1, S2, S4", "6 monitor Telegram channels, regex then Jev on candidates",
     ("s1_takeoff_6h", "s1_takeoff_24h", "hours_since_s1", "s2_mig31k_airborne", "s4_drone_waves_6h", "s4_3h",
      "s4_kyiv_6h")),
    ("weather", "weather forecast", "Open-Meteo API, no LLM",
     ("wx_cloud_mean_3h", "wx_precip_sum_3h", "wx_wind_max_3h", "wx_visibility_min_3h")),
    ("calendar", "symbolic dates", "a fixed list of dates, scored by Jev once",
     ("hol_rf_symb_today", "hol_ua_symb_today", "hol_high_tomorrow", "hol_days_to_next_high")),
    ("political", "visits and political events", "Kremlin site, OP and Zelensky Telegram, Wikipedia, plus Jev",
     ("kyiv_imp_today", "russia_imp_today", "kyiv_days_to_imp4", "russia_days_to_imp4")),
    ("rf_strikes", "strikes on Russia, launches on Ukraine", "dronestrikemap API, a day known 30 h later",
     ("rf_points_1d", "rf_points_3d", "rf_regions_3d", "rf_energy_1d", "rf_energy_3d", "rf_moscow_3d",
      "rf_drones_intercepted_1d", "ua_missiles_launched_1d", "ua_drones_launched_1d", "hours_since_rf_energy")),
)
DERIVED = {"quiet_now": ("alerts", "jev_flags")}
KEYS = [s[0] for s in SOURCES]
GROUP = {c: s[0] for s in SOURCES for c in s[3]} | {c: "+".join(g) for c, g in DERIVED.items()}


def parts(rows, name):
    """The model columns of one table column, by meaning (see the docstring)."""
    v = linear.column(rows, name)
    if name == "hour_kyiv":
        return [np.sin(2 * math.pi * v / 24), np.cos(2 * math.pi * v / 24),
                ((v >= linear.EVENING[0]) & (v <= linear.EVENING[1])).astype(float)]
    if name.startswith("hours_since_"):
        return [np.log1p(v)]
    if name == linear.UNKNOWN:
        return [np.where(np.isnan(v), -1.0, v), np.isnan(v).astype(float)]
    return [v]


def design(rows, names):
    """The matrix and {table column: [matrix column indices]}."""
    out, where = [], {}
    for n in names:
        p = parts(rows, n)
        where[n] = list(range(len(out), len(out) + len(p)))
        out += p
    return np.column_stack(out), where


def columns_of(keys):
    keys = set(keys)
    cols = [c for s in SOURCES if s[0] in keys for c in s[3]]
    return cols + [c for c, need in DERIVED.items() if keys >= set(need)]


class Folds:
    """The weekly folds once: the training matrix of all hours, the quiet-now hours of the evaluation week."""

    def __init__(self, t, folds):
        self.names = list(GROUP)
        self.data = []
        for _, rows, ev in folds:
            x, self.where = design(rows, self.names)
            q = ev.filter(ev[linear.NOW])
            xq, _ = design(q, self.names)
            y = linear.labels(rows, linear.TARGET)
            self.data.append((x, y, xq, linear.labels(q, linear.TARGET), float(y.mean())))
        self.y = np.concatenate([d[3] for d in self.data])
        self.clim = np.concatenate([np.full(len(d[3]), d[4]) for d in self.data])

    def idx(self, cols):
        return [i for c in cols for i in self.where[c]]

    def fit(self, cols):
        idx = self.idx(cols)
        return idx, [linear.logit(x[:, idx], y, C) for x, y, *_ in self.data]

    def predict(self, model, shuffle=None, rng=None):
        idx, pipes = model
        out = []
        for pipe, (_, _, xq, _, _) in zip(pipes, self.data):
            if not len(xq):  # a week without a quiet-now hour
                continue
            x = xq[:, idx].copy()
            if shuffle:
                pos = [idx.index(i) for i in shuffle]
                x[:, pos] = x[rng.permutation(len(x))][:, pos]
            out.append(linear.proba(pipe, x))
        return np.concatenate(out)

    def scores(self, p):
        return scores(self.y, p, self.clim)


def scores(y, p, clim):
    y, p = list(map(int, y)), list(map(float, p))
    return 1 - metrics.brier(y, p) / metrics.brier(y, list(clim)), metrics.roc_auc(y, p)


def section(title):
    print(f"\n## {title}\n")


def source_map(t):
    section("1. Columns by source")
    names = [f.name for f in t.schema if f.name not in linear.NOT_FEATURES]
    missing, extra = set(names) - set(GROUP), set(GROUP) - set(names)
    assert not missing and not extra, (missing, extra)
    for key, what, cost, cols in SOURCES:
        print(f"{key:12s} {len(cols):2d} columns | {what} | {cost}\n             {', '.join(cols)}")
    print(f"quiet_now: made of alerts and jev_flags; in a set only with both. Feature columns {len(names)}, "
          f"model columns {design(t, names)[0].shape[1]}")


def univariate(t, folds):
    section("2. One column at a time: ROC AUC on development quiet-now hours (no model)")
    rows = [ev.filter(ev[linear.NOW]) for _, _, ev in folds]
    y = np.concatenate([linear.labels(r, linear.TARGET) for r in rows])
    print(f"hours {len(y)}, busy windows {int(y.sum())} ({y.mean():.3f})")
    out = []
    for c in GROUP:
        v = np.concatenate([linear.column(r, c) for r in rows])
        ok = ~np.isnan(v)
        vals, counts = np.unique(v[ok], return_counts=True)
        top = counts.max() / ok.sum()
        auc = metrics.roc_auc(list(map(int, y[ok])), list(v[ok]))
        out.append((c, auc if auc is not None else 0.5, top, int(ok.sum()), len(vals)))
    print("| column | source | ROC AUC | strength max(AUC, 1-AUC) | higher value means | most common value share | distinct | hours |")
    print("|---|---|---|---|---|---|---|---|")
    for c, auc, top, n, k in sorted(out, key=lambda r: -abs(r[1] - 0.5)):
        side = "busier" if auc > 0.5 else "quieter" if auc < 0.5 else "nothing"
        flag = " NEAR CONSTANT" if top >= NEAR_CONSTANT else ""
        print(f"| {c} | {GROUP[c]} | {auc:.3f} | {max(auc, 1 - auc):.3f} | {side} | {top:.3f}{flag} | {k} | {n} |")


def importance(f):
    section(f"3. One model on all columns (L2 logistic, C {C}): permutation importance, development quiet-now hours")
    allc = columns_of(KEYS)
    model = f.fit(allc)
    base = f.scores(f.predict(model))
    print(f"all sources: model columns {len(model[0])}, BSS {base[0]:.3f}, ROC AUC {base[1]:.3f}")
    s = quiet.dev_scores(linear.fit_wide, linear.predict_wide)
    print(f"check: logit_all_l2 (raw columns, quiet.dev_scores): BSS {s['bss']:.3f}, ROC AUC {s['roc_auc']:.3f}")
    s = quiet.dev_scores(linear.fit_signals, linear.predict_spec)
    print(f"finalist logit_signals (quiet.dev_scores): BSS {s['bss']:.3f}, ROC AUC {s['roc_auc']:.3f}")

    def drop(cols, rng):
        got = [f.scores(f.predict(model, f.idx(cols), rng)) for _ in range(REPEATS)]
        b, a = np.array([base[0] - g[0] for g in got]), np.array([base[1] - g[1] for g in got])
        return b.mean(), b.std(), a.mean(), a.std()

    rng = np.random.default_rng(SEED)
    print(f"\nby source: shuffle all its columns together, {REPEATS} repeats; drop = unshuffled minus shuffled")
    print("| source | columns | BSS drop (sd) | ROC AUC drop (sd) |\n|---|---|---|---|")
    rows = [(k, cols, *drop(cols, rng)) for k, _, _, cols in SOURCES]
    for k, cols, b, bs, a, as_ in sorted(rows, key=lambda r: -r[2]):
        print(f"| {k} | {len(cols)} | {b:.4f} ({bs:.4f}) | {a:.4f} ({as_:.4f}) |")
    rng = np.random.default_rng(SEED)
    rows = [(c, *drop([c], rng)) for c in allc]
    print(f"\nby column, top 15 of {len(rows)} by BSS drop (quiet_now is constant on these hours: drop 0)")
    print("| column | source | BSS drop (sd) | ROC AUC drop (sd) |\n|---|---|---|---|")
    for c, b, bs, a, as_ in sorted(rows, key=lambda r: -r[1])[:15]:
        print(f"| {c} | {GROUP[c]} | {b:.4f} ({bs:.4f}) | {a:.4f} ({as_:.4f}) |")
    neg = [c for c, b, *_ in rows if b < 0]
    print(f"columns whose shuffling raises BSS (the model is better without them): {len(neg)}")
    return base


def ablation(f, base):
    section("4. Sources in and out, same model, development quiet-now hours")
    print(f"rule (fixed before scoring): time always in; the smallest number of other sources with BSS >= "
          f"{base[0]:.3f} - {TOL} = {base[0] - TOL:.3f}; among them the highest BSS")
    others = KEYS[1:]
    got = {}

    def score(keys):
        k = frozenset(keys)
        if k not in got:
            got[k] = f.scores(f.predict(f.fit(columns_of(k))))
        return got[k]

    for n in range(len(others) + 1):
        for combo in combinations(others, n):
            score(("time",) + combo)
    print(f"sets scored: {len(got)} (every subset of the {len(others)} sources besides time, time always in)")
    print("\n| row | BSS | ROC AUC |\n|---|---|---|")
    print(f"| all sources | {base[0]:.3f} | {base[1]:.3f} |")
    for k in KEYS:
        b, a = score(set(KEYS) - {k})
        print(f"| all minus {k} | {b:.3f} | {a:.3f} |")
    for k in others:
        b, a = score({"time", k})
        print(f"| time plus {k} | {b:.3f} | {a:.3f} |")
    b, a = score({"time"})
    print(f"| time only | {b:.3f} | {a:.3f} |")
    for k in others:
        if k != "signals":
            b, a = score({"time", "signals", k})
            print(f"| time plus signals plus {k} | {b:.3f} | {a:.3f} |")

    def name(k):
        return " + ".join(x for x in KEYS if x in k)

    print("\nbest 12 sets of all scored, by BSS")
    print("| sources | count besides time | BSS | ROC AUC |\n|---|---|---|---|")
    for k, (b, a) in sorted(got.items(), key=lambda kv: -kv[1][0])[:12]:
        print(f"| {name(k)} | {len(k) - ('time' in k)} | {b:.3f} | {a:.3f} |")
    print("\nbest set of each size")
    for n in range(len(others) + 1):
        k, (b, a) = max(((k, v) for k, v in got.items() if "time" in k and len(k) == n + 1), key=lambda kv: kv[1][0])
        print(f"  {n}: {name(k)}: BSS {b:.3f}, ROC AUC {a:.3f}")
    for n in range(len(others) + 1):
        ok = [(k, v) for k, v in got.items() if "time" in k and len(k) == n + 1 and v[0] >= base[0] - TOL]
        if ok:
            pick, (b, a) = max(ok, key=lambda kv: kv[1][0])
            break
    print(f"\nrecommended by the rule: {name(pick)} ({n} sources besides time): development BSS {b:.3f}, "
          f"ROC AUC {a:.3f}; sets of that size that pass: {len(ok)}")
    return pick


def test_report(t, pick):
    section("4b. Test, once, only a report (nothing is chosen here): quiet-now hours")
    tf = Folds(t, quiet.test_folds(t))
    print(f"test quiet-now hours {len(tf.y)}, busy windows {int(tf.y.sum())} ({tf.y.mean():.3f})")
    print(f"weeks {len(tf.data)}, quiet-now hours per week: {[len(d[3]) for d in tf.data]}")
    for label, keys in (("recommended by the rule", pick), ("all sources", KEYS),
                        ("time + signals (best single source on development; not the rule)", {"time", "signals"})):
        b, a = tf.scores(tf.predict(tf.fit(columns_of(keys))))
        print(f"{label}: BSS {b:.3f}, ROC AUC {a:.3f}")
    p, y, clim = [], [], []
    for _, rows, ev in quiet.test_folds(t):
        q = ev.filter(ev[linear.NOW])
        if not q.num_rows:
            continue
        p += linear.predict_spec(linear.fit_signals(rows), quiet.features_only(q))
        y += list(linear.labels(q, linear.TARGET))
        clim += [sum(rows[linear.TARGET].to_pylist()) / rows.num_rows] * q.num_rows
    b, a = scores(y, p, clim)
    print(f"finalist logit_signals: BSS {b:.3f}, ROC AUC {a:.3f} (reports/quiet_leaderboard.md: 0.284, 0.749)")


def pca(t):
    section("5. PCA of the standardized model columns, development hours (redundancy among inputs, not influence)")
    d = split.dev(t, quiet.H)
    x, where = design(d, list(GROUP))
    suffix = {"hour_kyiv": (":sin", ":cos", ":evening"), linear.UNKNOWN: ("", ":unknown")}
    label = {i: c for c, ix in where.items() for i in ix}
    shown = {i: c + (suffix[c][ix.index(i)] if c in suffix else "") for c, ix in where.items() for i in ix}
    keep = [i for i in range(x.shape[1]) if x[:, i].std() > 0]
    z = (x[:, keep] - x[:, keep].mean(0)) / x[:, keep].std(0)
    _, sv, vt = np.linalg.svd(z, full_matrices=False)
    var = sv ** 2 / (sv ** 2).sum()
    print(f"hours {x.shape[0]}, columns {len(keep)} (constant dropped: {x.shape[1] - len(keep)})")
    print("explained variance, first 10: " + " ".join(f"{v:.3f}" for v in var[:10]))
    print("cumulative: " + " ".join(f"{v:.3f}" for v in np.cumsum(var)[:10]))
    print(f"components for 80% of the variance: {int(np.searchsorted(np.cumsum(var), 0.8)) + 1}")
    for k in range(5):
        top = np.argsort(-np.abs(vt[k]))[:8]
        cells = [f"{shown[keep[i]]} ({GROUP[label[keep[i]]]}) {vt[k][i]:+.2f}" for i in top]
        print(f"PC{k + 1} {var[k]:.3f}: " + "; ".join(cells))


def main():
    t = quiet.load()
    np.seterr(all="ignore")
    source_map(t)
    dev = quiet.dev_folds(t)
    univariate(t, dev)
    f = Folds(t, dev)
    base = importance(f)
    pick = ablation(f, base)
    test_report(t, pick)
    pca(t)


if __name__ == "__main__":
    main()
