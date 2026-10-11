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
    .venv/bin/python -I -m airalerts.modeling.nights check NAME    NAME against naive_7n on development, write nothing
"""
import importlib
import pkgutil
import random
import sys
from datetime import timedelta

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..gold import kyiv_nightly as nightly
from ..paths import DATA, ROOT
from . import evaluate, split

LABEL, H = nightly.LABEL, nightly.H
PREDICTIONS = DATA / "predictions" / "nights"
REPORT = ROOT / "reports" / "nights_leaderboard.md"
REFERENCE = "naive_7n"
RECALL = 0.8
N_BOOT = 1000
SEED = 20261011


def load():
    """Nights with a known target, in time order."""
    t = pq.read_table(nightly.PATH).sort_by("t_utc")
    return t.filter(pc.is_valid(t[LABEL]))


def features_only(rows):
    return rows.drop_columns([LABEL])


def dev_folds(t):
    return split.dev_folds(t, H)


def test_folds(t):
    return split.test_folds(t, H)


def nights_scored(t):
    return [x for fs in (dev_folds(t), test_folds(t)) for _, _, ev in fs for x in ev["t_utc"].to_pylist()]


def fold_predictions(fit, predict, folds):
    out = []
    for _, rows, ev in folds:
        p = [float(v) for v in predict(fit(rows), features_only(ev))]
        if len(p) != ev.num_rows or any(not 0 <= v <= 1 for v in p):
            raise ValueError(f"predict must return {ev.num_rows} probabilities in [0, 1]")
        out += p
    return out


def climatology(folds):
    """The share of attack nights known at each fold origin, for every night it scores."""
    return [sum(rows[LABEL].to_pylist()) / rows.num_rows for _, rows, ev in folds for _ in range(ev.num_rows)]


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


def scores(y, p, clim):
    return {"bss": 1 - evaluate.brier(y, p) / evaluate.brier(y, clim), "brier": evaluate.brier(y, p),
            "roc_auc": evaluate.roc_auc(y, p), "pr_auc": evaluate.pr_auc(y, p)}


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


def save(name, description, at, p):
    if list(at) != nights_scored(load()):
        raise ValueError(f"{name}: predictions must cover exactly the scored nights, in time order")
    if any(v is None or not 0 <= v <= 1 for v in p):
        raise ValueError(f"{name}: every p must be in [0, 1]")
    PREDICTIONS.mkdir(parents=True, exist_ok=True)
    table = pa.table({"t_utc": pa.array(at, pa.timestamp("us")), "p": pa.array(p, pa.float64())})
    tmp = PREDICTIONS / f".{name}.parquet.tmp"  # write then rename: a reader never sees half a file
    pq.write_table(table.replace_schema_metadata({"description": description}), tmp)
    tmp.replace(PREDICTIONS / f"{name}.parquet")
    print(f"{name}: {len(p)} nights written")


def run(mod):
    """Fit and predict every development and test fold for each model of a night model module, then save."""
    t = load()
    for name, m in mod.MODELS.items():
        save(name, m["description"], nights_scored(t), fold_predictions(m["fit"], m["predict"], dev_folds(t) + test_folds(t)))


def night_modules():
    from . import night_models
    return [importlib.import_module(f"{night_models.__name__}.{m.name}") for m in pkgutil.iter_modules(night_models.__path__)]


def load_predictions(at, only=None):
    models, about = {}, {}
    for f in sorted(PREDICTIONS.glob("*.parquet")):
        if only and f.stem not in only:
            continue
        t = pq.read_table(f)
        if t["t_utc"].to_pylist() != at:
            raise ValueError(f"{f.name}: not the scored nights; rerun its module")
        models[f.stem], about[f.stem] = t["p"].to_pylist(), t.schema.metadata[b"description"].decode()
    return models, about


def ci(v, box, fmt=".3f"):
    return "n/a" if v is None else f"{v:{fmt}} [{box[0]:{fmt}}, {box[1]:{fmt}}]"


def part_table(title, idx, y, clim, models, thr, n_features):
    """Markdown rows for one part: point scores, 95% bootstrap intervals over nights, alarms at the threshold."""
    rnd = random.Random(SEED)
    vals = {}
    for _ in range(N_BOOT):
        b = [rnd.choice(idx) for _ in idx]
        yy, cc = [y[i] for i in b], [clim[i] for i in b]
        got = {m: scores(yy, [p[i] for i in b], cc) for m, p in models.items()}
        for m, s in got.items():
            for k, v in s.items():
                if v is not None:
                    vals.setdefault((m, k), []).append(v)
            vals.setdefault((m, "d"), []).append(s["bss"] - got[REFERENCE]["bss"])
    box = {k: (sorted(v)[int(0.025 * len(v))], sorted(v)[int(0.975 * len(v)) - 1]) for k, v in vals.items()}
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
            d = ci(s["bss"] - point[REFERENCE]["bss"], (lo, hi))
            verdict = "краще" if lo > 0 else "гірше" if hi < 0 else "не розрізнити"
        out.append(f"| `{m}` | {n_features.get(m, '')} | {ci(s['bss'], box.get((m, 'bss'), (0, 0)))} | "
                   f"{ci(s['roc_auc'], box.get((m, 'roc_auc'), (0, 0)))} | {ci(s['pr_auc'], box.get((m, 'pr_auc'), (0, 0)))} | "
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


def finalist(point, n_features):
    best = max(point, key=lambda m: point[m])
    near = [m for m in point if point[best] - point[m] < 0.01]
    return min(near, key=lambda m: (n_features.get(m, 99), -point[m]))


def report(final=False, only=None):
    t = load()
    at = nights_scored(t)
    save(REFERENCE, "share of attack nights among the 7 nights before", at, naive_7n(t, at))
    models, about = load_predictions(at, only)
    n_features = {}
    from . import night_models
    for info in pkgutil.iter_modules(night_models.__path__):
        try:  # another builder's module may be half written; its own tests and check will say so
            mod = importlib.import_module(f"{night_models.__name__}.{info.name}")
        except Exception as e:
            print(f"skipped night_models.{info.name}: {e!r}", file=sys.stderr)
            continue
        for name, m in getattr(mod, "MODELS", {}).items():
            n_features[name] = m.get("n_features", "")
    n_features[REFERENCE] = 1
    folds = dev_folds(t) + test_folds(t)
    y = [int(v) for _, _, ev in folds for v in ev[LABEL].to_pylist()]
    clim = climatology(folds)
    dev = [i for i, x in enumerate(at) if x < split.TEST_START]
    test = [i for i, x in enumerate(at) if x >= split.TEST_START]
    thr = {m: threshold([y[i] for i in dev], [p[i] for i in dev]) for m, p in models.items()}
    dev_bss = {m: scores([y[i] for i in dev], [p[i] for i in dev], [clim[i] for i in dev])["bss"] for m, p in models.items()}
    star = finalist({m: v for m, v in dev_bss.items() if m != REFERENCE} or dev_bss, n_features)
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
