"""Quiet hours: will [t, t + 3 h) be quiet in Kyiv, drones counted (docs/adr/0011-quiet-hours.md).

The same time split and weekly walk-forward folds as the hourly models (split.py); the test stays closed until `final`.
A model module in airalerts.modeling.quiet_models defines
MODELS = {name: {"fit": f, "predict": g, "description": str, "n_features": int}} with top-level functions
f(rows) -> model and g(model, rows) -> [p of busy]: fit gets labelled hours, predict gets hours without the target.

Rules fixed before any quiet model was scored:
- the main evaluation is on the hours that are quiet now (quiet_now: no alert at t, no flag in [t - 1 h, t));
- "quiet" is called when p <= threshold; the threshold is the highest one whose development hours called quiet are
  quiet in at least 95% of cases (on quiet-now hours);
- finalist: the best development BSS on quiet-now hours; a model with fewer features wins when it is within 0.01;
- the test is scored once, with `final`, after the finalist is known.

    .venv/bin/python -I -m airalerts.modeling.quiet               write naive_7d, score the development folds
    .venv/bin/python -I -m airalerts.modeling.quiet final         also score the test: once, at the end
    .venv/bin/python -I -m airalerts.modeling.quiet check NAME    NAME against naive_7d on development; writes only naive_7d
"""
import sys
from bisect import bisect_left, bisect_right
from datetime import timedelta
from zoneinfo import ZoneInfo

from ..gold import kyiv_quiet as quiet_table
from ..paths import DATA, ROOT
from . import split, tasks

LABEL, H = quiet_table.LABEL, quiet_table.H
SPEC = tasks.Spec(quiet_table.PATH, LABEL, H, DATA / "predictions" / "quiet", "hours")
REPORT = ROOT / "reports" / "quiet_leaderboard.md"
REFERENCE = "naive_7d"
NPV = 0.95
UTC, KYIV = ZoneInfo("UTC"), ZoneInfo("Europe/Kyiv")


def load():
    return tasks.load(SPEC)


def features_only(rows):
    return tasks.features_only(SPEC, rows)


def dev_folds(t):
    return tasks.dev_folds(SPEC, t)


def test_folds(t):
    return tasks.test_folds(SPEC, t)


def run(mod):
    tasks.run(SPEC, mod)


def naive_7d(t, at):
    """Share of busy windows among the hours of the last 7 days whose target is known at t (t' <= t - 3 h)."""
    ts, prefix = t["t_utc"].to_pylist(), [0]
    for y in t[LABEL].to_pylist():
        prefix.append(prefix[-1] + y)
    out = []
    for x in at:
        i, j = bisect_left(ts, x - timedelta(days=7)), bisect_right(ts, x - timedelta(hours=H))
        out.append((prefix[j] - prefix[i]) / (j - i))
    return out


def quiet_threshold(y, p, npv=NPV):
    """The highest threshold whose hours called quiet (p <= it) are quiet in at least `npv` of cases; -1 calls none."""
    best, called, quiet = -1.0, 0, 0
    pairs = sorted(zip(p, y))
    for k, (v, b) in enumerate(pairs):
        called, quiet = called + 1, quiet + (not b)
        if (k + 1 == len(pairs) or pairs[k + 1][0] != v) and quiet / called >= npv:
            best = v
    return best


def decisions(y, p, thr):
    """Hours called quiet, of them really quiet, busy windows called quiet (missed)."""
    called = [b for v, b in zip(p, y) if v <= thr]
    return len(called), len(called) - sum(called), sum(called)


def dev_scores(fit, predict, t=None):
    """Development folds, quiet-now hours: BSS, Brier, ROC AUC, PR AUC, BSS per fold, mean p, share busy, and the
    hours called quiet at the 95% threshold (chosen on the same hours, so optimistic). All-hours BSS too."""
    t = load() if t is None else t
    folds = dev_folds(t)
    p = tasks.fold_predictions(SPEC, fit, predict, folds)
    rows = [r for _, _, ev in folds for r in ev.select([LABEL, "quiet_now"]).to_pylist()]
    y = [int(r[LABEL]) for r in rows]
    clim = tasks.climatology(SPEC, folds)
    q = [i for i, r in enumerate(rows) if r["quiet_now"]]
    out = tasks.scores([y[i] for i in q], [p[i] for i in q], [clim[i] for i in q])
    per_fold, start = [], 0
    for _, _, ev in folds:
        idx = [i for i in q if start <= i < start + ev.num_rows]
        yy, cc = [y[i] for i in idx], [clim[i] for i in idx]
        per_fold.append(round(1 - tasks.evaluate.brier(yy, [p[i] for i in idx]) / tasks.evaluate.brier(yy, cc), 3))
        start += ev.num_rows
    thr = quiet_threshold([y[i] for i in q], [p[i] for i in q])
    called, right, missed = decisions([y[i] for i in q], [p[i] for i in q], thr)
    return {**out, "bss_all_hours": tasks.scores(y, p, clim)["bss"], "bss_per_fold": per_fold,
            "mean_p": sum(p[i] for i in q) / len(q), "share_busy": sum(y[i] for i in q) / len(q),
            "threshold": thr, "called_quiet": f"{called}/{len(q)}", "really_quiet": f"{right}/{called}", "missed": missed}


def days(idx, at):
    """Index lists of the given rows, one per noon-to-noon Kyiv day (a night is never cut)."""
    out = {}
    for i in idx:
        out.setdefault((at[i].replace(tzinfo=UTC).astimezone(KYIV) - timedelta(hours=12)).date(), []).append(i)
    return list(out.values())


def part_table(title, idx, at, y, clim, models, thr, n_features):
    box = tasks.bootstrap(days(idx, at), y, clim, models, REFERENCE)
    yy, cc = [y[i] for i in idx], [clim[i] for i in idx]
    point = {m: tasks.scores(yy, [p[i] for i in idx], cc) for m, p in models.items()}
    out = [f"## {title}: {len(idx)} годин, неспокійних 3-годинних вікон {sum(yy)} ({sum(yy) / len(yy):.0%})", "",
           "| модель | ознак | BSS | ROC AUC | PR AUC | поріг «тихо» | годин названо тихими | з них справді тихі | пропущено неспокійних | ΔBSS з naive_7d | вердикт |",
           "|" + "---|" * 11]
    for m in sorted(models, key=lambda m: -point[m]["bss"]):
        s = point[m]
        called, right, missed = decisions(yy, [models[m][i] for i in idx], thr[m])
        share = f"{called}/{len(idx)} ({called / len(idx):.0%})"
        npv = f"{right / called:.3f}" if called else "n/a"
        if m == REFERENCE:
            d, verdict = "", "опорна"
        else:
            lo, hi = box[(m, "d")]
            d = tasks.ci(s["bss"] - point[REFERENCE]["bss"], (lo, hi))
            verdict = "краще" if lo > 0 else "гірше" if hi < 0 else "не розрізнити"
        out.append(f"| `{m}` | {n_features.get(m, '')} | {tasks.ci(s['bss'], box.get((m, 'bss'), (0, 0)))} | "
                   f"{tasks.ci(s['roc_auc'], box.get((m, 'roc_auc'), (0, 0)))} | {tasks.ci(s['pr_auc'], box.get((m, 'pr_auc'), (0, 0)))} | "
                   f"{thr[m]:.3f} | {share} | {npv} | {missed} | {d} | {verdict} |")
    return out + [""]


HEADER = """# Спокійні 3 години: чи буде тихо в Києві

Згенеровано `.venv/bin/python -I -m airalerts.modeling.quiet{final}`, не редагувати вручну. Ціль: у наступні 3 години дрони летять на Київ або вибухають у ньому, ракетна загроза Києву чи ракетний удар ([ADR-0011](../docs/adr/0011-quiet-hours.md)). Модель дає ймовірність, що буде неспокійно. Поділ як у погодинних моделей ([ADR-0008](../docs/adr/0008-time-split.md)). {scope}

Як читати:

- **Головна таблиця: години «зараз тихо»** (тривоги немає, атаки в минулу годину не було). Питання: чи протримається тиша 3 години.
- **BSS**: на скільки прогноз кращий за «завжди частка неспокійних вікон, відома на початок тижня». 0 той самий рівень, більше 0 краще.
- **ROC AUC**: шанс, що неспокійне вікно отримає вищий прогноз за тихе; 0.5 це монетка.
- **Поріг «тихо»** (задано до запуску моделей): найвищий, за якого серед годин розробки, названих тихими, справді тихих щонайменше 95%. Від нього: скільки годин модель називає тихими, скільки з них справді тихі, скільки неспокійних вікон вона пропустила.
- **Вердикт**: різниця BSS з `naive_7d` (частка неспокійних вікон за 7 днів) на тих самих добах, 95% інтервал bootstrap по добах від полудня до полудня, {boot} повторів.
- **Фіналіст** (★, правило задано до запуску): найкращий BSS на розробці на годинах «зараз тихо»; модель з меншою кількістю ознак, якщо вона гірша менш ніж на 0.01.
"""


def report(final=False, only=None):
    from . import quiet_models
    t = load()
    at = tasks.scored(SPEC, t)
    tasks.save(SPEC, REFERENCE, "share of busy 3 h windows among the hours of the last 7 days known at t", at,
               naive_7d(t, at), t)
    models, about = tasks.load_predictions(SPEC, at, only)
    n_features = tasks.n_features(quiet_models)
    n_features[REFERENCE] = 1
    folds = dev_folds(t) + test_folds(t)
    rows = [r for _, _, ev in folds for r in ev.select([LABEL, "quiet_now"]).to_pylist()]
    y = [int(r[LABEL]) for r in rows]
    clim = tasks.climatology(SPEC, folds)
    dev_q = [i for i, x in enumerate(at) if x < split.TEST_START and rows[i]["quiet_now"]]
    thr = {m: quiet_threshold([y[i] for i in dev_q], [p[i] for i in dev_q]) for m, p in models.items()}
    dev_bss = {m: tasks.scores([y[i] for i in dev_q], [p[i] for i in dev_q], [clim[i] for i in dev_q])["bss"]
               for m, p in models.items()}
    star = tasks.finalist({m: v for m, v in dev_bss.items() if m != REFERENCE} or dev_bss, n_features)
    lines = [HEADER.format(final=" final" if final else "", boot=tasks.N_BOOT,
                           scope="Фінальна оцінка з тестом." if final else "Лише розробка: тест відкриває `final`, один раз."),
             f"Фіналіст за правилом: ★ `{star}`.", "", "## Моделі", ""]
    lines += [f"- `{m}`{' ★' if m == star else ''}: {about[m]}" for m in models] + [""]
    parts = [("Розробка, години «зараз тихо»", lambda i, x: x < split.TEST_START and rows[i]["quiet_now"]),
             ("Розробка, усі години", lambda i, x: x < split.TEST_START)]
    if final:
        parts += [("Тест, години «зараз тихо»", lambda i, x: x >= split.TEST_START and rows[i]["quiet_now"]),
                  ("Тест, усі години", lambda i, x: x >= split.TEST_START)]
    for title, keep in parts:
        lines += part_table(title, [i for i, x in enumerate(at) if keep(i, x)], at, y, clim, models, thr, n_features)
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
        sys.exit("usage: python -I -m airalerts.modeling.quiet [final | check NAME]")


if __name__ == "__main__":
    main()
