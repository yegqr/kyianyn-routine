"""Risk tiers of the frozen quiet-hours models (docs/adr/0011-quiet-hours.md): cut points are the tertiles of each
model's development predictions on quiet-now hours; then the share of busy 3 h windows per tier on development and on
the test, all hours and daytime 08..19 Kyiv. Descriptive only, run after `quiet final`.

    .venv/bin/python -I scripts/analysis/quiet_tiers.py    (from the project root)
"""
from airalerts.modeling import quiet, split, tasks

t = quiet.load()
at = tasks.scored(quiet.SPEC, t)
folds = quiet.dev_folds(t) + quiet.test_folds(t)
rows = [r for _, _, ev in folds for r in ev.select([quiet.LABEL, "quiet_now", "hour_kyiv"]).to_pylist()]
models, _ = tasks.load_predictions(quiet.SPEC, at)
for m in ("logit_signals", "two_heads", "naive_7d"):
    p = models[m]
    dev = sorted(p[i] for i, x in enumerate(at) if x < split.TEST_START and rows[i]["quiet_now"])
    c1, c2 = dev[len(dev) // 3], dev[2 * len(dev) // 3]
    print(f"{m}: cut points from development {c1:.3f}, {c2:.3f}")
    for part, keep in (("dev ", lambda x: x < split.TEST_START), ("test", lambda x: x >= split.TEST_START)):
        cells = []
        for name, lo, hi in (("low", -1, c1), ("mid", c1, c2), ("high", c2, 2)):
            idx = [i for i, x in enumerate(at) if keep(x) and rows[i]["quiet_now"] and lo < p[i] <= hi]
            day = [i for i in idx if 8 <= rows[i]["hour_kyiv"] < 20]
            busy = sum(rows[i][quiet.LABEL] for i in idx) / max(1, len(idx))
            busy_day = sum(rows[i][quiet.LABEL] for i in day) / max(1, len(day))
            cells.append(f"{name}: {len(idx):4d} h busy {busy:.0%} (day {busy_day:.0%})")
        print(f"  {part}  " + " | ".join(cells))
