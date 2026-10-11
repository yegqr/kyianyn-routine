"""Tests of the models and the scorer: no model sees a label that is unknown at t, and the metrics equal brute force.

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_models.py
"""
import random
import unittest

import pyarrow as pa

from airalerts.gold.kyiv_hourly import LABEL
from airalerts.modeling import evaluate, naive, split

SEED = 20261011


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
