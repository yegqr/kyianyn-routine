"""Which inputs drive the quiet finalist logit_signals, and how few sources a live product could parse
(docs/quiet/importance.md). Descriptive, prints only, writes nothing. Quiet-now hours (the main evaluation), the weekly
walk-forward folds of airalerts.quiet.score: development folds to choose, test folds only to report.

1. Standardized coefficients of logit_signals fitted on every development row (C 0.3, all hours, as in the model):
   the odds multiplier per one standard deviation of each of the 9 design columns.
2. Mean absolute contribution of each input to the log-odds, w * (x - training mean) / training sd summed over the
   columns of the input (the hour has 3); for a linear model this is SHAP with the training rows as background. Each
   scored hour uses the model of its own fold.
3. Permutation importance: one input (or one source group) shuffled across the scored quiet-now hours of a part,
   PERM_REPEATS repeats from a fixed seed, every hour still predicted by its own fold model; drop in BSS and ROC AUC.
4. Source groups and reduced models refitted through the same folds (the same C 0.3, all hours):
     A  time only: the Kyiv hour (sin, cos, evening flag)
     B  attack history: hours_since_busy, hours_since_drone (the Jev threat flags of 7 Kyiv channels)
     C  post activity and Jev post answers: posts_jev_1h, p_drone_max_1h
     D  drone wave events S4: s4_3h, s4_kyiv_6h (monitor channels plus Jev S4 events)
   Rule, written before any subset was scored: among A, A+B, A+B+C, A+B+D and all, keep the subsets whose development
   BSS on quiet-now hours is lower than the full model's by less than 0.01 (as the finalist rule); choose the one with
   the fewest source groups, and of two with as many, the higher development BSS. The chosen subset is then scored on
   the test once, only as a report. Paired bootstrap over noon-to-noon days (1000 resamples) is printed as a report too.
5. PCA of the 9 standardized design columns on every development row: which inputs move together (structure of the
   inputs, not their weight in the forecast).

    .venv/bin/python -I scripts/analysis/quiet_importance.py    (from the project root, about half a minute)
"""
import math
import random

import numpy as np

from airalerts.evaluation import metrics, split, walkforward
from airalerts.quiet import linear, score as quiet

C = 0.3                      # the frozen C of logit_signals (docs/quiet/linear.md)
PERM_REPEATS = 20
SPEC = linear.SIGNALS
COLS = [f"{n}:{h}" for n, h in SPEC]
INPUTS = {}                  # input -> indices of its design columns
for j, (n, _) in enumerate(SPEC):
    INPUTS.setdefault(n, []).append(j)
GROUPS = {"A": ("hour_kyiv",), "B": ("hours_since_busy", "hours_since_drone"),
          "C": ("posts_jev_1h", "p_drone_max_1h"), "D": ("s4_3h", "s4_kyiv_6h")}
SUBSETS = {"A": "A", "A+B": "AB", "A+B+C": "ABC", "A+B+D": "ABD", "all": "ABCD"}


def spec_of(letters):
    names = {n for g in letters for n in GROUPS[g]}
    return tuple(s for s in SPEC if s[0] in names)


def bss(y, p, clim):
    return 1 - metrics.brier(y, p) / metrics.brier(y, clim)


t = quiet.load()
parts = {"dev": quiet.dev_folds(t), "test": quiet.test_folds(t)}
data = {}
for part, folds in parts.items():
    pipes, xs, fold_of = [], [], []
    for k, (_, rows, ev) in enumerate(folds):
        pipes.append(linear.fit_signals(rows)[1])
        xs.append(linear.design(ev, SPEC))
        fold_of += [k] * ev.num_rows
    rows = [r for _, _, ev in folds for r in ev.select([quiet.LABEL, "quiet_now", "t_utc"]).to_pylist()]
    q = np.array([i for i, r in enumerate(rows) if r["quiet_now"]])
    data[part] = {"pipes": pipes, "x": np.vstack(xs), "fold": np.array(fold_of), "q": q,
                  "y": np.array([int(r[quiet.LABEL]) for r in rows]), "at": [r["t_utc"] for r in rows],
                  "clim": np.array(walkforward.climatology(quiet.SPEC, folds))}


def predict(d, x):
    """Every row of x by the model of its own fold."""
    p = np.empty(len(x))
    for k, pipe in enumerate(d["pipes"]):
        m = d["fold"] == k
        if m.any():
            p[m] = linear.proba(pipe, x[m])
    return p


def contributions(d):
    """Per row and design column: w * (x - mean) / sd of the fold model."""
    out = np.empty(d["x"].shape)
    for k, pipe in enumerate(d["pipes"]):
        m = d["fold"] == k
        sc, lr = pipe[0], pipe[1]
        out[m] = (d["x"][m] - sc.mean_) / sc.scale_ * lr.coef_[0]
    return out


for d in data.values():
    d["p"] = predict(d, d["x"])
saved = walkforward.load_predictions(quiet.SPEC, walkforward.scored(quiet.SPEC, t), {"logit_signals"})[0]["logit_signals"]
print(f"check: max |p - saved logit_signals| {np.max(np.abs(np.concatenate([data['dev']['p'], data['test']['p']]) - saved)):.1e}")
for part, d in data.items():
    q = d["q"]
    y, p, c = d["y"][q], d["p"][q], d["clim"][q]
    d["base"] = (bss(y, p, c), metrics.roc_auc(list(y), list(p)))
    print(f"{part}: quiet-now hours {len(q)}, busy {y.sum()} ({y.mean():.0%}); logit_signals BSS {d['base'][0]:.3f}, "
          f"ROC AUC {d['base'][1]:.3f}")

dev_rows = split.dev(t, quiet.H)
x_dev = linear.design(dev_rows, SPEC)
spec_dev, pipe_dev = linear.fit_signals(dev_rows)
w = pipe_dev[1].coef_[0]
print(f"\n1. Standardized coefficients, logit_signals fitted on all {dev_rows.num_rows} development rows "
      f"(busy share {linear.labels(dev_rows, linear.TARGET).mean():.3f}), C {C}")
print(f"   {'column':26s} {'mean':>7s} {'sd':>7s} {'weight':>7s} {'odds x per sd':>13s}")
for j in np.argsort(-np.abs(w)):
    print(f"   {COLS[j]:26s} {pipe_dev[0].mean_[j]:7.3f} {pipe_dev[0].scale_[j]:7.3f} {w[j]:+7.3f} {math.exp(w[j]):13.2f}")
share = linear.labels(dev_rows, linear.TARGET).mean()
for j in np.argsort(-np.abs(w)):
    if SPEC[j][1] == "log1p":
        print(f"   {COLS[j]}: one sd means (1 + x) times {math.exp(pipe_dev[0].scale_[j]):.2f}")
q0 = data["dev"]["y"][data["dev"]["q"]].mean()
odds = q0 / (1 - q0) * math.exp(w[COLS.index("s4_kyiv_6h:raw")])
print(f"   example: p {q0:.2f} (busy share of dev quiet-now hours) with one sd more of s4_kyiv_6h becomes {odds / (1 + odds):.2f}")
hours = np.arange(24, dtype=float)
hx = np.column_stack([np.sin(2 * math.pi * hours / 24), np.cos(2 * math.pi * hours / 24),
                      ((hours >= linear.EVENING[0]) & (hours <= linear.EVENING[1])).astype(float)])
hc = ((hx - pipe_dev[0].mean_[:3]) / pipe_dev[0].scale_[:3]) @ w[:3]
lo, hi = int(np.argmin(hc)), int(np.argmax(hc))
print(f"   the hour as a whole: safest Kyiv hour {lo}:00, riskiest {hi}:00, odds x {math.exp(hc[hi] - hc[lo]):.2f} between them")
for name, what in (("hours_since_busy", "hours"), ("hours_since_drone", "hours"), ("posts_jev_1h", "posts"),
                   ("s4_kyiv_6h", "events"), ("s4_3h", "events")):
    v = linear.column(dev_rows, name)
    print(f"   {name} ({what}) on development rows: 10% {np.percentile(v, 10):.0f}, median {np.median(v):.0f}, "
          f"90% {np.percentile(v, 90):.0f}, share of zero {np.mean(v == 0):.0%}")

print("\n2. Mean |contribution| to the log-odds per input (SHAP of a linear model), quiet-now hours, fold models")
contrib = {part: contributions(d) for part, d in data.items()}
shap = {part: {n: np.mean(np.abs(contrib[part][d["q"]][:, js].sum(axis=1))) for n, js in INPUTS.items()}
        for part, d in data.items()}
print(f"   {'input':20s} {'dev':>6s} {'test':>6s}")
for n in sorted(INPUTS, key=lambda n: -shap["dev"][n]):
    print(f"   {n:20s} {shap['dev'][n]:6.3f} {shap['test'][n]:6.3f}")
for part in data:
    tot = sum(shap[part].values())
    grp = {g: sum(shap[part][n] for n in ns) for g, ns in GROUPS.items()}
    print(f"   {part} by source group (share of the sum of the inputs): " +
          ", ".join(f"{g} {v:.3f} ({v / tot:.0%})" for g, v in grp.items()))

print(f"\n3. Permutation importance, quiet-now hours, {PERM_REPEATS} repeats, seed {walkforward.SEED}: "
      "drop of BSS and ROC AUC, mean [min, max]")
units = {n: js for n, js in INPUTS.items()}
units.update({f"group {g}": [j for n in ns for j in INPUTS[n]] for g, ns in GROUPS.items()})
for part, d in data.items():
    rng = np.random.default_rng(walkforward.SEED)
    q, y, c = d["q"], d["y"][d["q"]], d["clim"][d["q"]]
    print(f"   {part}: base BSS {d['base'][0]:.3f}, ROC AUC {d['base'][1]:.3f}")
    res = {}
    for u, js in units.items():
        db, da = [], []
        for _ in range(PERM_REPEATS):
            x = d["x"].copy()
            perm = rng.permutation(q)
            x[np.ix_(q, js)] = d["x"][np.ix_(perm, js)]
            p = predict(d, x)[q]
            db.append(d["base"][0] - bss(y, p, c))
            da.append(d["base"][1] - metrics.roc_auc(list(y), list(p)))
        res[u] = (db, da)
    for u in sorted(res, key=lambda u: (u.startswith("group"), -np.mean(res[u][0]))):
        db, da = res[u]
        print(f"     {u:20s} BSS drop {np.mean(db):+.3f} [{min(db):+.3f}, {max(db):+.3f}]   "
              f"ROC AUC drop {np.mean(da):+.3f} [{min(da):+.3f}, {max(da):+.3f}]")

print("\n4. Reduced models by source group, refitted through the same folds (C 0.3, all hours), quiet-now hours")
sub_p = {}
for name, letters in SUBSETS.items():
    spec = spec_of(letters)
    fit = lambda rows, spec=spec: linear.fit_spec(rows, spec, C, "all")
    sub_p[name] = {part: np.array(walkforward.fold_predictions(quiet.SPEC, fit, linear.predict_spec, folds))
                   for part, folds in parts.items()}


def days_boot(d, pa, pb):
    """95% interval of BSS(a) - BSS(b) over resampled noon-to-noon days of the quiet-now hours."""
    groups = quiet.days(list(d["q"]), d["at"])
    rnd, out = random.Random(walkforward.SEED), []
    for _ in range(walkforward.N_BOOT):
        b = np.array([i for g in [rnd.choice(groups) for _ in groups] for i in g])
        out.append(bss(d["y"][b], pa[b], d["clim"][b]) - bss(d["y"][b], pb[b], d["clim"][b]))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out)) - 1]


d = data["dev"]
dev_score = {name: bss(d["y"][d["q"]], sub_p[name]["dev"][d["q"]], d["clim"][d["q"]]) for name in SUBSETS}
for name, letters in SUBSETS.items():
    auc = metrics.roc_auc(list(d["y"][d["q"]]), list(sub_p[name]["dev"][d["q"]]))
    lo_, hi_ = days_boot(d, sub_p[name]["dev"], sub_p["all"]["dev"])
    print(f"   dev {name:6s} inputs {len({s[0] for s in spec_of(letters)})}, columns {len(spec_of(letters))}: "
          f"BSS {dev_score[name]:.3f}, ROC AUC {auc:.3f}, BSS minus all {dev_score[name] - dev_score['all']:+.3f} "
          f"[{lo_:+.3f}, {hi_:+.3f}]")
near = [n for n in SUBSETS if dev_score["all"] - dev_score[n] < 0.01]
chosen = min(near, key=lambda n: (len(SUBSETS[n]), -dev_score[n]))
print(f"   rule (development only): within 0.01 of all: {', '.join(near)}; chosen {chosen}")
d = data["test"]
for name in dict.fromkeys((chosen, "all")):
    p = sub_p[name]["test"][d["q"]]
    print(f"   test {name:6s} (report only): BSS {bss(d['y'][d['q']], p, d['clim'][d['q']]):.3f}, "
          f"ROC AUC {metrics.roc_auc(list(d['y'][d['q']]), list(p)):.3f}")
if chosen != "all":
    lo_, hi_ = days_boot(d, sub_p[chosen]["test"], sub_p["all"]["test"])
    print(f"   test {chosen} minus all, BSS, 95% bootstrap over days: [{lo_:+.3f}, {hi_:+.3f}]")

print(f"\n5. PCA of the 9 standardized design columns, all {dev_rows.num_rows} development rows")
z = (x_dev - x_dev.mean(axis=0)) / x_dev.std(axis=0)
corr = np.corrcoef(z, rowvar=False)
val, vec = np.linalg.eigh(corr)
order = np.argsort(-val)
val, vec = val[order], vec[:, order]
print("   variance share by component: " + ", ".join(f"PC{k + 1} {v / val.sum():.0%}" for k, v in enumerate(val)))
for k in range(4):
    v = vec[:, k] * np.sign(vec[np.argmax(np.abs(vec[:, k])), k])
    top = sorted(range(len(COLS)), key=lambda j: -abs(v[j]))[:4]
    print(f"   PC{k + 1} ({val[k] / val.sum():.0%}): " + ", ".join(f"{COLS[j]} {v[j]:+.2f}" for j in top))
print("   pairs with |correlation| >= 0.4:")
for i in range(len(COLS)):
    for j in range(i + 1, len(COLS)):
        if abs(corr[i, j]) >= 0.4:
            print(f"     {COLS[i]:26s} {COLS[j]:26s} {corr[i, j]:+.2f}")
