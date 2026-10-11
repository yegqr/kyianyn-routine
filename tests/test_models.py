"""Tests of the models and the scorer: no model sees a label that is unknown at t, and the metrics equal brute force.

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_models.py
"""
import importlib
import pkgutil
import random
import sys
import unittest
from pathlib import Path

import pyarrow as pa

from airalerts import modeling
from airalerts.gold.kyiv_hourly import LABEL
from airalerts.modeling import evaluate, naive, runner, split

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the tests folder off the path
from test_no_leakage import reaches  # noqa: E402

SEED = 20261011
# fit and predict see only the rows they are given: neither they nor a function of their module that they reach may
# mention a way to read data on their own
FORBIDDEN = ("read_table", "ParquetFile", "dataset", "duckdb", "connect", "load", "PATH", "GOLD", "open", "split",
             "evaluate", "runner")


class NaiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = split.load()
        cls.at = random.Random(SEED).sample(evaluate.hours(cls.t), 30)

    def with_labels(self, change):
        """gold with the label of every row t' replaced by change(t', label)."""
        ys = [change(x, y) for x, y in zip(self.t["t_utc"].to_pylist(), self.t[LABEL].to_pylist())]
        return self.t.set_column(self.t.schema.get_field_index(LABEL), LABEL, pa.array(ys))

    def test_unknown_labels_do_not_change_p(self):
        rnd = random.Random(SEED)
        for x in self.at:
            noisy = self.with_labels(lambda u, y: rnd.random() < 0.5 if u > x - split.H * split.HOUR else y)
            self.assertEqual(naive.predict(noisy, [x]), naive.predict(self.t, [x]))

    def test_the_last_known_label_changes_p(self):
        for x in self.at:  # the check above must be able to fail: the label known last at t does move p
            last = x - split.H * split.HOUR
            flipped = self.with_labels(lambda u, y: (not y) if u == last else y)
            self.assertNotEqual(naive.predict(flipped, [x]), naive.predict(self.t, [x]))

    def test_equals_a_plain_loop(self):
        rows = list(zip(self.t["t_utc"].to_pylist(), self.t[LABEL].to_pylist()))
        for x in self.at:
            ys = [y for u, y in rows if x - naive.DAYS * 24 * split.HOUR <= u <= x - split.H * split.HOUR]
            self.assertEqual(len(ys), naive.DAYS * 24 - split.H + 1)
            self.assertAlmostEqual(naive.predict(self.t, [x])[0], sum(ys) / len(ys), places=12)

    def test_save_rejects_other_hours(self):
        at = evaluate.hours(self.t)
        with self.assertRaises(ValueError):
            evaluate.save("bad", "", at[1:], [0.0] * (len(at) - 1))


def fitted_models():
    """Every module of airalerts.modeling with NAME, fit and predict: the models that runner.py runs."""
    mods = (importlib.import_module(f"airalerts.modeling.{m.name}") for m in pkgutil.iter_modules(modeling.__path__))
    return [m for m in mods if all(hasattr(m, a) for a in ("NAME", "fit", "predict"))]


def reads_outside(mod, fns):
    return [n for n in FORBIDDEN if any(reaches(mod, f, n, set()) for f in fns)]


def _share_fit(rows):
    ys = rows[LABEL].to_pylist()
    return sum(ys) / len(ys)


def _share_predict(model, rows):
    return [model] * rows.num_rows


def _leaky_predict(model, rows):
    split.load()
    return [model] * rows.num_rows


class FittedModelsTest(unittest.TestCase):
    """Every fitted model: fit sees only labels known at the fold origin, predict sees no label, neither reads data on its
    own, and the output is reproducible probabilities."""

    @classmethod
    def setUpClass(cls):
        t = split.load()
        dev, test = split.dev_folds(t), split.test_folds(t)
        cls.folds = [dev[0], dev[-1], test[-2]]

    def check(self, mod, fit, predict):
        self.assertEqual(reads_outside(mod, (fit, predict)), [])
        for o, rows, ev in self.folds:
            self.assertLessEqual(max(rows["t_utc"].to_pylist()) + split.H * split.HOUR, o)
            x = runner.features_only(ev)
            self.assertNotIn(LABEL, x.column_names)
            p = list(predict(fit(rows), x))
            self.assertEqual(len(p), ev.num_rows)
            self.assertTrue(all(0 <= v <= 1 for v in p))
            self.assertEqual(p, list(predict(fit(rows), x)))

    def test_the_check_passes_a_clean_model_and_catches_a_file_read(self):
        here = sys.modules[__name__]
        self.check(here, _share_fit, _share_predict)
        self.assertEqual(reads_outside(here, (_share_fit, _leaky_predict)), ["load", "split"])

    def test_every_fitted_model(self):
        for mod in fitted_models():
            with self.subTest(model=mod.NAME):
                self.check(mod, mod.fit, mod.predict)


class MetricsTest(unittest.TestCase):
    def test_roc_auc_equals_counting_pairs(self):
        rnd = random.Random(SEED)
        for _ in range(20):
            y = [int(rnd.random() < 0.2) for _ in range(60)]
            p = [rnd.choice((0, 0.1, 0.2, 0.5)) for _ in y]  # many ties
            pos, neg = [a for a, b in zip(p, y) if b], [a for a, b in zip(p, y) if not b]
            pairs = sum((a > b) + (a == b) / 2 for a in pos for b in neg) / (len(pos) * len(neg))
            self.assertAlmostEqual(evaluate.roc_auc(y, p), pairs, places=12)

    def test_pr_auc(self):
        self.assertEqual(evaluate.pr_auc([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]), 1.0)
        self.assertAlmostEqual(evaluate.pr_auc([0, 1, 0, 1], [0.9, 0.8, 0.2, 0.1]), (1 / 2 + 2 / 4) / 2)
        self.assertAlmostEqual(evaluate.pr_auc([1, 0, 1, 0], [0.5] * 4), 0.5)  # one tie group: the share of true

    def test_brier_and_threshold(self):
        self.assertAlmostEqual(evaluate.brier([1, 0], [0.5, 0.5]), 0.25)
        self.assertEqual(evaluate.best_threshold([1, 0, 0, 1], [0.9, 0.8, 0.1, 0.7]), 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
