"""Test breakdown of the frozen hourly models (thresholds from the development folds): confusion matrix, day against
night, and every test attack with the warning of each model. Descriptive only, run after `evaluate final`.

    .venv/bin/python -I scripts/analysis/hourly_test_breakdown.py    (from the project root)
"""
from datetime import timedelta
from airalerts.modeling import evaluate as ev, split

h = ev.Hours(split.load())
models, _ = ev.load_models(h.at)
names = ("share_table", "logistic", "lgbm", "naive_7d")
dev = [i for i, k in enumerate(h.test) if not k]
thr = {m: ev.best_threshold([h.y[i] for i in dev], [models[m][i] for i in dev]) for m in names}
kyiv_hour = [(x + timedelta(hours=3)).hour for x in h.at]  # EEST, the test ends before 2026-10-25
test = [i for i, k in enumerate(h.test) if k]
day = [i for i in test if 8 <= kyiv_hour[i] < 20]
night = [i for i in test if not 8 <= kyiv_hour[i] < 20]
weeks = len(test) / 168
print(f"test hours {len(test)}, true {sum(h.y[i] for i in test)}; day 08-19: {len(day)} hours, {sum(h.y[i] for i in day)} true; night 20-07: {len(night)} hours, {sum(h.y[i] for i in night)} true")
print("confusion matrix on the test (threshold from development):")
for m in names:
    p = models[m]
    a = {i: p[i] >= thr[m] for i in test}
    tp = sum(a[i] and h.y[i] for i in test); fp = sum(a[i] and not h.y[i] for i in test)
    fn = sum(not a[i] and h.y[i] for i in test); tn = len(test) - tp - fp - fn
    print(f"  {m:12s} thr {thr[m]:.3f} TP {tp:3d} FP {fp:4d} FN {fn:3d} TN {tn:4d} recall {tp/max(1,tp+fn):.2f} precision {tp/max(1,tp+fp):.2f} alarm h/week {(tp+fp)/weeks:.1f}")
for label, idx in (("day 08-19", day), ("night 20-07", night)):
    y = [h.y[i] for i in idx]; c = [h.clim[i] for i in idx]
    print(f"{label}:")
    for m in names:
        q = [models[m][i] for i in idx]
        s = ev.score(y, q, c, thr[m])
        print(f"  {m:12s} BSS {s['bss']:+.3f} PR AUC {s['pr_auc'] if s['pr_auc'] is None else round(s['pr_auc'],3)} ROC AUC {s['roc_auc'] if s['roc_auc'] is None else round(s['roc_auc'],3)} recall {s['recall'] if s['recall'] is None else round(s['recall'],2)} mean p {sum(q)/len(q):.3f} share true {sum(y)/len(y):.3f}")
pos = {x: i for i, x in enumerate(h.at)}
print("attacks of the test (first hour of the run, Kyiv): warned by each model (max p over its first 3 hours vs threshold)")
for a in h.first_rows:
    if a[0] < split.TEST_START:
        continue
    cells = []
    for m in names:
        mx = max(models[m][pos[x]] for x in a if x in pos)
        cells.append(f"{m} {'YES' if mx >= thr[m] else 'no '} {mx:.3f}")
    print(f"  {a[0] + timedelta(hours=3):%m-%d %H:%M}  " + " | ".join(cells))
