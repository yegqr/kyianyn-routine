"""Walk-forward scoring shared by the questions that have their own gold table (nights.py, quiet.py). A Spec names the
table, its target, the hours after t_utc when the target becomes known, and where predictions go. The folds are the
weekly folds of split.py (docs/adr/0008-time-split.md): each fold fits on the rows whose target is known at its origin
and predicts its evaluation week from features only.
"""
import importlib
import pkgutil
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import evaluate, split

N_BOOT = 1000
SEED = 20261011


@dataclass(frozen=True)
class Spec:
    path: Path          # the gold table
    label: str          # its target column
    h: int              # the target of row t is known at t_utc + h hours
    predictions: Path   # folder of <model>.parquet
    unit: str = "rows"  # what a row is, for messages
    extra_targets: tuple = ()  # more columns that look ahead (auxiliary targets): kept from predict like the label


def load(spec):
    """Rows with a known target, in time order."""
    t = pq.read_table(spec.path).sort_by("t_utc")
    return t.filter(pc.is_valid(t[spec.label]))


def features_only(spec, rows):
    return rows.drop_columns([spec.label, *spec.extra_targets])


def dev_folds(spec, t):
    return split.dev_folds(t, spec.h)


def test_folds(spec, t):
    return split.test_folds(t, spec.h)


def scored(spec, t):
    """t_utc of every row a fold scores: the development weeks, then the test weeks."""
    return [x for fs in (dev_folds(spec, t), test_folds(spec, t)) for _, _, ev in fs for x in ev["t_utc"].to_pylist()]


def fold_predictions(spec, fit, predict, folds):
    out = []
    for _, rows, ev in folds:
        p = [float(v) for v in predict(fit(rows), features_only(spec, ev))]
        if len(p) != ev.num_rows or any(not 0 <= v <= 1 for v in p):
            raise ValueError(f"predict must return {ev.num_rows} probabilities in [0, 1]")
        out += p
    return out


def climatology(spec, folds):
    """The share of true targets known at each fold origin, for every row it scores."""
    return [sum(rows[spec.label].to_pylist()) / rows.num_rows for _, rows, ev in folds for _ in range(ev.num_rows)]


def scores(y, p, clim):
    return {"bss": 1 - evaluate.brier(y, p) / evaluate.brier(y, clim), "brier": evaluate.brier(y, p),
            "roc_auc": evaluate.roc_auc(y, p), "pr_auc": evaluate.pr_auc(y, p)}


def save(spec, name, description, at, p, t=None):
    if list(at) != scored(spec, load(spec) if t is None else t):
        raise ValueError(f"{name}: predictions must cover exactly the scored rows, in time order")
    if any(v is None or not 0 <= v <= 1 for v in p):
        raise ValueError(f"{name}: every p must be in [0, 1]")
    spec.predictions.mkdir(parents=True, exist_ok=True)
    table = pa.table({"t_utc": pa.array(at, pa.timestamp("us")), "p": pa.array(p, pa.float64())})
    tmp = spec.predictions / f".{name}.parquet.tmp"  # write then rename: a reader never sees half a file
    pq.write_table(table.replace_schema_metadata({"description": description}), tmp)
    tmp.replace(spec.predictions / f"{name}.parquet")
    print(f"{name}: {len(p)} {spec.unit} written")


def run(spec, mod):
    """Fit and predict every development and test fold for each model of a module, then save."""
    t = load(spec)
    folds = dev_folds(spec, t) + test_folds(spec, t)
    for name, m in mod.MODELS.items():
        save(spec, name, m["description"], scored(spec, t), fold_predictions(spec, m["fit"], m["predict"], folds), t)


def load_predictions(spec, at, only=None):
    models, about = {}, {}
    for f in sorted(spec.predictions.glob("*.parquet")):
        if only and f.stem not in only:
            continue
        t = pq.read_table(f)
        if t["t_utc"].to_pylist() != at:
            raise ValueError(f"{f.name}: not the scored rows; rerun its module")
        models[f.stem], about[f.stem] = t["p"].to_pylist(), t.schema.metadata[b"description"].decode()
    return models, about


def n_features(package):
    """{model: n_features} of every module of a model package; a module that fails to import is skipped with a note
    (another builder may be writing it; its own tests say why)."""
    out = {}
    for info in pkgutil.iter_modules(package.__path__):
        try:
            mod = importlib.import_module(f"{package.__name__}.{info.name}")
        except Exception as e:
            print(f"skipped {package.__name__}.{info.name}: {e!r}", file=sys.stderr)
            continue
        for name, m in getattr(mod, "MODELS", {}).items():
            out[name] = m.get("n_features", "")
    return out


def bootstrap(groups, y, clim, models, reference):
    """{(model, metric): (low, high)} 95% intervals over resampled groups of rows (a night, or a day of hours), and
    (model, "d"): BSS minus the reference's BSS on the same resample."""
    rnd = random.Random(SEED)
    vals = {}
    for _ in range(N_BOOT):
        b = [i for g in [rnd.choice(groups) for _ in groups] for i in g]
        yy, cc = [y[i] for i in b], [clim[i] for i in b]
        got = {m: scores(yy, [p[i] for i in b], cc) for m, p in models.items()}
        for m, s in got.items():
            for k, v in s.items():
                if v is not None:
                    vals.setdefault((m, k), []).append(v)
            vals.setdefault((m, "d"), []).append(s["bss"] - got[reference]["bss"])
    return {k: (sorted(v)[int(0.025 * len(v))], sorted(v)[int(0.975 * len(v)) - 1]) for k, v in vals.items()}


def ci(v, box, fmt=".3f"):
    return "n/a" if v is None else f"{v:{fmt}} [{box[0]:{fmt}}, {box[1]:{fmt}}]"


def recall_threshold(y, p, recall):
    """The highest threshold whose alarms (p >= it) still catch at least `recall` of the true rows: missing an event
    is worse than a false warning (docs/METHODOLOGY.md 4.4)."""
    need = recall * sum(y)
    for v in sorted(set(p), reverse=True):
        if sum(1 for a, b in zip(p, y) if b and a >= v) >= need:
            return v
    return min(p)


def finalist(point, n_features):
    """The best development BSS; a model with fewer features wins when it is within 0.01."""
    best = max(point, key=lambda m: point[m])
    near = [m for m in point if point[best] - point[m] < 0.01]
    return min(near, key=lambda m: (n_features.get(m, 99), -point[m]))
