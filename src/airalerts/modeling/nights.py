"""Night models: the decision at 22:00 Kyiv, sleep in the corridor or in the room (docs/adr/0010-night-question.md).

The same time split as the hourly models (split.py): test nights from 2026-08-29 stay closed until `final`. Development
nights are scored on the weekly walk-forward folds; each fold refits on every night whose target is known at the fold
origin (t_utc + 10 h <= origin). A model module in airalerts.modeling.night_models defines
MODELS = {name: {"fit": f, "predict": g, "description": str, "n_features": int}} with top-level functions
f(rows) -> model and g(model, rows) -> [p]: fit gets labelled nights, predict gets nights without the target.

Rules fixed before any night model was scored:
- threshold: the highest one that still catches at least 80% of the development attack nights;
- finalist: the best development BSS; a simpler model (fewer features) wins when it is within 0.01 (marked in the report);
- the test is scored once, with `final`, after the finalist is known.

    .venv/bin/python -I -m airalerts.modeling.nights               write naive_7n, score the development folds
    .venv/bin/python -I -m airalerts.modeling.nights final         also score the test: once, at the end
    .venv/bin/python -I -m airalerts.modeling.nights check NAME    NAME against naive_7n on development; writes only naive_7n
"""
import importlib
import pkgutil
import sys
from datetime import timedelta

from ..gold import kyiv_nightly as nightly
from ..paths import DATA, ROOT
from . import split, tasks

LABEL, H = nightly.LABEL, nightly.H
PREDICTIONS = DATA / "predictions" / "nights"
SPEC = tasks.Spec(nightly.PATH, LABEL, H, PREDICTIONS, "nights")
REPORT = ROOT / "reports" / "nights_leaderboard.md"
REFERENCE = "naive_7n"
RECALL = 0.8
N_BOOT = tasks.N_BOOT


def load():
    return tasks.load(SPEC)


def features_only(rows):
    return tasks.features_only(SPEC, rows)


def dev_folds(t):
    return tasks.dev_folds(SPEC, t)


def test_folds(t):
    return tasks.test_folds(SPEC, t)


def nights_scored(t):
    return tasks.scored(SPEC, t)


def fold_predictions(fit, predict, folds):
    return tasks.fold_predictions(SPEC, fit, predict, folds)


def climatology(folds):
    return tasks.climatology(SPEC, folds)


scores = tasks.scores


def naive_7n(t, at):
    """Share of attack nights among the 7 nights before each night (all known at its 22:00)."""
    y = dict(zip(t["t_utc"].to_pylist(), t[LABEL].to_pylist()))
    return [sum(bool(y.get(x - timedelta(days=n))) for n in range(1, 8)) / 7 for x in at]


def threshold(y, p, recall=RECALL):
    """The highest threshold whose alarms (p >= it) still catch at least `recall` of the true nights."""
    need = recall * sum(y)
    for v in sorted(set(p), reverse=True):
        if sum(1 for a, b in zip(p, y) if b and a >= v) >= need:
            return v
    return min(p)


def decisions(y, p, thr):
    caught = sum(1 for a, b in zip(p, y) if b and a >= thr)
    false = sum(1 for a, b in zip(p, y) if not b and a >= thr)
    return caught, sum(y), false, len(y) - sum(y)


def save(name, description, at, p):
    tasks.save(SPEC, name, description, at, p)


def run(mod):
    """Fit and predict every development and test fold for each model of a night model module, then save."""
    tasks.run(SPEC, mod)


def night_modules():
    from . import night_models
    return [importlib.import_module(f"{night_models.__name__}.{m.name}") for m in pkgutil.iter_modules(night_models.__path__)]


def dev_scores(fit, predict, t=None):
    """Development folds only: BSS, Brier, ROC AUC, PR AUC, BSS per fold, mean p, share true, and the alarms at the
    threshold that catches 80% of these attack nights (chosen on the same nights, so optimistic)."""
    t = load() if t is None else t
    folds = dev_folds(t)
    p = fold_predictions(fit, predict, folds)
    y = [int(v) for _, _, ev in folds for v in ev[LABEL].to_pylist()]
    clim = climatology(folds)
    out = scores(y, p, clim)
    per_fold, i = [], 0
    for _, _, ev in folds:
        j = i + ev.num_rows
        yy, cc = y[i:j], clim[i:j]
        per_fold.append(round(1 - evaluate.brier(yy, p[i:j]) / evaluate.brier(yy, cc), 3) if j > i else None)
        i = j
    thr = threshold(y, p)
    caught, att, false, quiet = decisions(y, p, thr)
    return {**out, "bss_per_fold": per_fold, "mean_p": sum(p) / len(p), "share_true": sum(y) / len(y),
            "threshold": thr, "caught": f"{caught}/{att}", "false_nights": f"{false}/{quiet}"}


def part_table(title, idx, y, clim, models, thr, n_features):
    """Markdown rows for one part: point scores, 95% bootstrap intervals over nights, alarms at the threshold."""
    box = tasks.bootstrap([[i] for i in idx], y, clim, models, REFERENCE)
    yy, cc = [y[i] for i in idx], [clim[i] for i in idx]
    point = {m: scores(yy, [p[i] for i in idx], cc) for m, p in models.items()}
    out = [f"## {title}: {len(idx)} ночей, {sum(yy)} з атакою", "",
           "| модель | ознак | BSS | ROC AUC | PR AUC | поріг | атак попереджено | зайвих ночей у коридорі | частка справжніх | ΔBSS з naive_7n | вердикт |",
           "|" + "---|" * 11]
    for m in sorted(models, key=lambda m: -point[m]["bss"]):
        s = point[m]
        caught, att, false, quiet = decisions(yy, [models[m][i] for i in idx], thr[m])
        prec = f"{caught / (caught + false):.2f}" if caught + false else "n/a"
        if m == REFERENCE:
            d, verdict = "", "опорна"
        else:
            lo, hi = box[(m, "d")]
            d = tasks.ci(s["bss"] - point[REFERENCE]["bss"], (lo, hi))
            verdict = "краще" if lo > 0 else "гірше" if hi < 0 else "не розрізнити"
        out.append(f"| `{m}` | {n_features.get(m, '')} | {tasks.ci(s['bss'], box.get((m, 'bss'), (0, 0)))} | "
                   f"{tasks.ci(s['roc_auc'], box.get((m, 'roc_auc'), (0, 0)))} | {tasks.ci(s['pr_auc'], box.get((m, 'pr_auc'), (0, 0)))} | "
                   f"{thr[m]:.3f} | {caught}/{att} | {false}/{quiet} | {prec} | {d} | {verdict} |")
    return out + [""]


HEADER = """# Нічне питання: чи йти спати в коридор

Згенеровано `.venv/bin/python -I -m airalerts.modeling.nights{final}`, не редагувати вручну. Рішення о 22:00 за Києвом; ціль: ракетний удар по Києву з 22:00 до 08:00 ([ADR-0010](../docs/adr/0010-night-question.md)). Поділ як у погодинних моделей ([ADR-0008](../docs/adr/0008-time-split.md)). {scope}

Як читати:

- **BSS**: на скільки прогноз кращий за «завжди частка ракетних ночей, відома на початок тижня». 0 це той самий рівень, більше 0 краще.
- **ROC AUC**: шанс, що ракетна ніч отримає вищий прогноз за тиху; 0.5 це монетка.
- **Поріг** (задано до запуску моделей): найвищий, за якого модель ще попереджає про 80% ракетних ночей розробки. Від нього: атак попереджено, зайвих ночей у коридорі, частка справжніх попереджень.
- **Вердикт**: різниця BSS з `naive_7n` (частка ракетних ночей за останні 7) на тих самих ночах, 95% інтервал bootstrap по ночах, {boot} повторів.
- **Фіналіст** (★, правило задано до запуску): найкращий BSS на розробці; модель з меншою кількістю ознак, якщо вона гірша менш ніж на 0.01.
"""


def report(final=False, only=None):
    t = load()
    at = nights_scored(t)
    save(REFERENCE, "share of attack nights among the 7 nights before", at, naive_7n(t, at))
    models, about = tasks.load_predictions(SPEC, at, only)
    from . import night_models
    n_features = tasks.n_features(night_models)
    n_features[REFERENCE] = 1
    folds = dev_folds(t) + test_folds(t)
    y = [int(v) for _, _, ev in folds for v in ev[LABEL].to_pylist()]
    clim = climatology(folds)
    dev = [i for i, x in enumerate(at) if x < split.TEST_START]
    test = [i for i, x in enumerate(at) if x >= split.TEST_START]
    thr = {m: threshold([y[i] for i in dev], [p[i] for i in dev]) for m, p in models.items()}
    dev_bss = {m: scores([y[i] for i in dev], [p[i] for i in dev], [clim[i] for i in dev])["bss"] for m, p in models.items()}
    star = tasks.finalist({m: v for m, v in dev_bss.items() if m != REFERENCE} or dev_bss, n_features)
    lines = [HEADER.format(final=" final" if final else "", boot=N_BOOT,
                           scope="Фінальна оцінка з тестом." if final else "Лише розробка: тест відкриває `final`, один раз."),
             f"Фіналіст за правилом: ★ `{star}`.", "", "## Моделі", ""]
    lines += [f"- `{m}`{' ★' if m == star else ''}: {about[m]}" for m in models] + [""]
    lines += part_table("Розробка, walk-forward", dev, y, clim, models, thr, n_features)
    if final:
        lines += part_table("Тест", test, y, clim, models, thr, n_features)
    return lines


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd in ([], ["final"]):
        lines = report(final=cmd == ["final"])
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines).rstrip() + "\n")
        print("\n".join(lines))
        print(f"written {REPORT}")
    elif len(cmd) == 2 and cmd[0] == "check":
        print("\n".join(report(only={REFERENCE, cmd[1]})))
    else:
        sys.exit("usage: python -I -m airalerts.modeling.nights [final | check NAME]")


if __name__ == "__main__":
    main()
