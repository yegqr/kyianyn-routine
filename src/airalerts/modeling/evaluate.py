"""One scorer for every model. Each model writes its probability for the same evaluation hours to
data/predictions/<name>.parquet; this module takes labels and subsets from gold, scores every model the same way and writes
reports/leaderboard.md, which explains how to read it. The test is scored only with `final`, once, at the end
(docs/adr/0008-time-split.md).

Evaluation hours: the evaluation weeks of the development folds and of the test folds (split.py, docs/adr/0008-time-split.md).

    .venv/bin/python -I -m airalerts.modeling.evaluate          score the development folds of every model
    .venv/bin/python -I -m airalerts.modeling.evaluate final    also score the test: the final evaluation
"""
import random
import sys
from datetime import timedelta
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from ..gold.kyiv_hourly import LABEL
from ..paths import DATA, ROOT
from . import split

PREDICTIONS = DATA / "predictions"
REPORT = ROOT / "reports" / "leaderboard.md"
REFERENCE = "naive_7d"  # every model is compared with it on the same resampled days
BETA = 2                # provisional threshold rule: the best F2 on the development predictions
N_BOOT = 1000
SEED = 20261011
BINS = (0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1)
UTC, KYIV = ZoneInfo("UTC"), ZoneInfo("Europe/Kyiv")


def hours(t):
    """Evaluation hours: the evaluation weeks of the development and test folds, in time order."""
    return [x for fs in (split.dev_folds(t), split.test_folds(t)) for _, _, ev in fs for x in ev["t_utc"].to_pylist()]


def save(name, description, at, p):
    """Write data/predictions/<name>.parquet after checking that it covers exactly the evaluation hours."""
    if list(at) != hours(split.load()):
        raise ValueError(f"{name}: predictions must cover exactly the evaluation hours, in time order")
    if any(v is None or not 0 <= v <= 1 for v in p):
        raise ValueError(f"{name}: every p must be in [0, 1]")
    PREDICTIONS.mkdir(parents=True, exist_ok=True)
    table = pa.table({"t_utc": pa.array(at, pa.timestamp("us")), "p": pa.array(p, pa.float64())})
    pq.write_table(table.replace_schema_metadata({"description": description}), PREDICTIONS / f"{name}.parquet")
    print(f"{name}: {len(p)} hours written to {PREDICTIONS / f'{name}.parquet'}")


# metrics: y is a list of 0 and 1, p a list of probabilities

def brier(y, p):
    return sum((a - b) ** 2 for a, b in zip(p, y)) / len(y)


def tie_groups(y, p):
    """(p, true, false) per distinct p, highest p first."""
    out = []
    for v, a in sorted(zip(p, y), reverse=True):
        if out and out[-1][0] == v:
            out[-1][1] += a
            out[-1][2] += 1 - a
        else:
            out.append([v, a, 1 - a])
    return out


def roc_auc(y, p):
    """Chance that a true hour gets a higher p than a false one, ties count half; None without both classes."""
    pos, neg = sum(y), len(y) - sum(y)
    if not pos or not neg:
        return None
    above, s = 0, 0.0  # false hours with a lower p, lowest p first
    for _, tp, fp in reversed(tie_groups(y, p)):
        s += tp * (above + fp / 2)
        above += fp
    return s / (pos * neg)


def pr_auc(y, p):
    """Average precision: the precision at each distinct threshold weighted by the recall it adds; None without a true."""
    pos = sum(y)
    if not pos:
        return None
    tp = fp = 0
    ap = 0.0
    for _, a, b in tie_groups(y, p):
        tp, fp = tp + a, fp + b
        ap += a / pos * tp / (tp + fp)
    return ap


def best_threshold(y, p, beta=BETA):
    """The threshold (alarm when p >= it) with the best F-beta; on a tie the higher one, which raises fewer alarms."""
    pos, b2 = sum(y), beta * beta
    tp = fp = 0
    best = (-1.0, 1.0)
    for v, a, b in tie_groups(y, p):
        tp, fp = tp + a, fp + b
        f = (1 + b2) * tp / ((1 + b2) * tp + b2 * (pos - tp) + fp)
        if f > best[0]:
            best = (f, v)
    return best[1]


def score(y, p, clim, thr):
    alarm = [v >= thr for v in p]
    tp = sum(a and b for a, b in zip(alarm, y))
    return {"bss": 1 - brier(y, p) / brier(y, clim), "brier": brier(y, p), "pr_auc": pr_auc(y, p),
            "roc_auc": roc_auc(y, p), "recall": tp / sum(y) if sum(y) else None,
            "precision": tp / sum(alarm) if sum(alarm) else None, "alarm_week": 168 * sum(alarm) / len(y)}


class Hours:
    """Labels, climatology, subsets and noon-to-noon Kyiv days of the evaluation hours."""

    def __init__(self, t):
        self.at = hours(t)
        row = {x: r for x, r in zip(t["t_utc"].to_pylist(), t.select([LABEL, "hours_since_strike", "alert_active"]).to_pylist())}
        clim = {}  # the share of true labels known at the origin of the fold of each hour
        for fs in (split.dev_folds(t), split.test_folds(t)):
            for _, fit, ev in fs:
                ys = fit[LABEL].to_pylist()
                clim.update(dict.fromkeys(ev["t_utc"].to_pylist(), sum(ys) / len(ys)))
        self.y = [int(row[x][LABEL]) for x in self.at]
        self.clim = [clim[x] for x in self.at]
        self.onset = [row[x]["hours_since_strike"] >= 3 for x in self.at]
        self.no_alert = [not row[x]["alert_active"] for x in self.at]
        self.test = [x >= split.TEST_START for x in self.at]
        self.day = [(x.replace(tzinfo=UTC).astimezone(KYIV) - timedelta(hours=12)).date() for x in self.at]
        self.first_rows = attack_first_rows(t)  # an attack is caught when p >= threshold in one of these hours

    def groups(self, keep):
        """Index lists of the kept hours, one per day."""
        out = {}
        for i, (d, k) in enumerate(zip(self.day, keep)):
            if k:
                out.setdefault(d, []).append(i)
        return list(out.values())


def attack_first_rows(t):
    """For every attack (run of true labels) its first 3 hours: the strike is in the window, its first hour has not begun."""
    out, prev = [], None
    for x, y in zip(t["t_utc"].to_pylist(), t[LABEL].to_pylist()):
        if y and not (prev and prev[1] and x - prev[0] == split.HOUR):
            out.append([])
        if y and len(out[-1]) < 3:
            out[-1].append(x)
        prev = (x, y)
    return out


def bootstrap(h, models, groups, thr, metrics):
    """{(model, metric): (low, high)} 95% intervals over resampled days, plus (model, 'd_bss'): BSS minus REFERENCE's.
    Every model sees the same resampled days."""
    rnd = random.Random(SEED)
    vals = {}
    for _ in range(N_BOOT):
        idx = [i for g in rnd.choices(groups, k=len(groups)) for i in g]
        y, clim = [h.y[i] for i in idx], [h.clim[i] for i in idx]
        got = {m: score(y, [p[i] for i in idx], clim, thr[m]) for m, p in models.items()}
        for m, s in got.items():
            for k in metrics:
                if s[k] is not None:
                    vals.setdefault((m, k), []).append(s[k])
            if REFERENCE in got:
                vals.setdefault((m, "d_bss"), []).append(s["bss"] - got[REFERENCE]["bss"])
    return {k: (sorted(v)[int(0.025 * len(v))], sorted(v)[int(0.975 * len(v)) - 1]) for k, v in vals.items()}


def load_models(at):
    models, about = {}, {}
    for f in sorted(PREDICTIONS.glob("*.parquet")):
        t = pq.read_table(f)
        if t["t_utc"].to_pylist() != at:
            raise ValueError(f"{f.name}: not the evaluation hours; rewrite it with evaluate.save()")
        models[f.stem], about[f.stem] = t["p"].to_pylist(), t.schema.metadata[b"description"].decode()
    if REFERENCE not in models:
        raise ValueError(f"no {REFERENCE}: run .venv/bin/python -I -m airalerts.modeling.naive first")
    return models, about


def kyiv(x):
    return f"{x.replace(tzinfo=UTC).astimezone(KYIV):%Y-%m-%d %H:%M}"


def ci(v, lo_hi, fmt=".3f"):
    return "n/a" if v is None else f"{v:{fmt}} [{lo_hi[0]:{fmt}}, {lo_hi[1]:{fmt}}]"


def main_table(h, models, thr, keep, title):
    idx = [i for i, k in enumerate(keep) if k]
    y, clim = [h.y[i] for i in idx], [h.clim[i] for i in idx]
    kept = {h.at[i] for i in idx}
    attacks = [a for a in h.first_rows if a[0] in kept]
    pos = {x: i for i, x in enumerate(h.at)}
    point = {m: score(y, [p[i] for i in idx], clim, thr[m]) for m, p in models.items()}
    keys = ("bss", "brier", "pr_auc", "roc_auc", "recall", "precision", "alarm_week")
    box = bootstrap(h, models, h.groups(keep), thr, keys)
    out = [f"## {title}: {kyiv(h.at[idx[0]])} .. {kyiv(h.at[idx[-1]])} за Києвом, {len(idx)} годин, {sum(y)} true, "
           f"{len(attacks)} атак, частка true {sum(y) / len(y):.3f}", "",
           "| модель | BSS | Brier | PR AUC | ROC AUC | поріг | recall | precision | атак спіймано | попереджень, год/тиждень "
           "| ΔBSS з naive_7d | вердикт |", "|" + "---|" * 12]
    for m in sorted(models, key=lambda m: -point[m]["bss"]):
        s, p = point[m], models[m]
        caught = sum(any(p[pos[x]] >= thr[m] for x in a) for a in attacks)
        if m == REFERENCE:
            d, verdict = "", "опорна"
        else:
            lo, hi = box[(m, "d_bss")]
            d = ci(s["bss"] - point[REFERENCE]["bss"], (lo, hi))
            verdict = "краще" if lo > 0 else "гірше" if hi < 0 else "не розрізнити"
        cells = [ci(s[k], box.get((m, k), (0, 0)), ".1f" if k == "alarm_week" else ".3f") for k in keys]
        out.append(f"| `{m}` | {' | '.join(cells[:4])} | {thr[m]:.3f} | {cells[4]} | {cells[5]} | {caught}/{len(attacks)} "
                   f"| {cells[6]} | {d} | {verdict} |")
    return out + [""]


def subsets_table(h, models, thr, keep, title):
    out = [f"## Підмножини, {title}: BSS; PR AUC", "",
           "| модель | усі години | початок атаки: удару не було 3 год | без тривоги на момент t |", "|---|---|---|---|"]
    cells = {m: [] for m in models}
    for sub in (keep, [a and b for a, b in zip(keep, h.onset)], [a and b for a, b in zip(keep, h.no_alert)]):
        idx = [i for i, k in enumerate(sub) if k]
        y, clim = [h.y[i] for i in idx], [h.clim[i] for i in idx]
        box = bootstrap(h, models, h.groups(sub), thr, ("bss", "pr_auc"))
        for m, p in models.items():
            s = score(y, [p[i] for i in idx], clim, thr[m])
            cells[m].append(f"{ci(s['bss'], box[(m, 'bss')])}; {ci(s['pr_auc'], box[(m, 'pr_auc')])} ({len(idx)} год, {sum(y)} true)")
    return out + [f"| `{m}` | {' | '.join(c)} |" for m, c in cells.items()] + [""]


def calibration_table(h, models, keep, title):
    out = [f"## Калібрування, {title}", "",
           "| модель | прогноз | годин | середній прогноз | частка ударів |", "|---|---|---|---|---|"]
    for m, p in models.items():
        for lo, hi in zip(BINS, BINS[1:]):
            idx = [i for i, v in enumerate(p) if keep[i] and (lo <= v < hi or (hi == 1 and v == 1))]
            if idx:
                out.append(f"| `{m}` | {lo:.2f}..{hi:.2f} | {len(idx)} | {sum(p[i] for i in idx) / len(idx):.3f} "
                           f"| {sum(h.y[i] for i in idx) / len(idx):.3f} |")
    return out + [""]


HEADER = """# Порівняння моделей

Згенеровано `.venv/bin/python -I -m airalerts.modeling.evaluate{final}`, не редагувати вручну. Поділ: [ADR-0008](../docs/adr/0008-time-split.md), горизонт 3 год. Кожна модель дає ймовірність для тих самих годин оцінки (тижні фолдів розробки і тесту); мітки й підмножини оцінювач бере з gold. {scope}

Як читати:

- **BSS**, головна мірка: на скільки Brier моделі кращий за кліматологію, тобто сталу частку ударів серед міток, відомих на початок тижня. 0 це рівень кліматології, 1 ідеал, менше 0 гірше за неї.
- **Brier**: середній квадрат помилки ймовірності, менше краще.
- **PR AUC**: наскільки високо в списку годин модель ставить години удару; прогноз навмання дає частку true.
- **ROC AUC**: шанс, що година удару отримає вищий прогноз за годину без удару; 0.5 це навмання.
- **Поріг** (тимчасове правило, чекає рішення): найкращий F2 на прогнозах фолдів розробки, F2 цінує recall удвічі більше за precision. Від порогу залежать recall і precision по годинах, атаки спіймані (прогноз вище порогу хоч в одну з трьох перших годин серії true, тобто до початку першої години удару) і години попереджень на тиждень.
- **Вердикт**: різниця BSS з `naive_7d` на тих самих добах; «краще», коли весь 95% інтервал вище 0, «гірше», коли нижче 0, інакше «не розрізнити».
- Інтервали: 95%, bootstrap по добах від полудня до полудня за Києвом, {boot} повторів, ті самі доби для всіх моделей.
"""
DEV_ONLY = ("Лише розробка: тест відкривається один раз, командою `final`. Розробка обирає модель і поріг, тож її числа "
            "трохи оптимістичні.")
WITH_TEST = ("Фінальна оцінка з тестом. Тест чистий, але має мало атак; walk-forward з розробкою і тестом має більше атак, "
             "але трохи оптимістичний, бо розробка обирала модель і поріг.")


def main(argv=None):
    cmd = sys.argv[1:] if argv is None else list(argv)
    if cmd not in ([], ["final"]):
        sys.exit("usage: python -I -m airalerts.modeling.evaluate [final]    (final opens the test: once, at the end)")
    final = cmd == ["final"]
    h = Hours(split.load())
    models, about = load_models(h.at)
    dev = [not k for k in h.test]
    thr = {m: best_threshold([h.y[i] for i, k in enumerate(dev) if k], [p[i] for i, k in enumerate(dev) if k])
           for m, p in models.items()}
    lines = [HEADER.format(final=" final" if final else "", scope=WITH_TEST if final else DEV_ONLY, boot=N_BOOT),
             "## Моделі", ""] + [f"- `{m}`: {about[m]}" for m in models] + [""]
    lines += main_table(h, models, thr, dev, "Розробка, walk-forward")
    if final:
        lines += main_table(h, models, thr, h.test, "Тест")
        lines += main_table(h, models, thr, [True] * len(h.at), "Walk-forward, розробка і тест")
        lines += subsets_table(h, models, thr, h.test, "тест") + calibration_table(h, models, [True] * len(h.at), "розробка і тест")
    else:
        lines += subsets_table(h, models, thr, dev, "розробка") + calibration_table(h, models, dev, "розробка")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines).rstrip() + "\n")
    print("\n".join(lines))
    print(f"written {REPORT}")


if __name__ == "__main__":
    main()
