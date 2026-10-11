"""Checks of the night ML module on toy nights: the fit window, the cap of nights_since_attack, the output.

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_nights_ml.py
"""
import random
import unittest
from datetime import datetime, timedelta

import pyarrow as pa

from airalerts.nights import ml


def toy(n=60, start=datetime(2026, 5, 1, 19), seed=0):
    rnd = random.Random(seed)
    cols = {"t_utc": [start + timedelta(days=i) for i in range(n)], ml.TARGET: [rnd.random() < 0.3 for _ in range(n)]}
    for c in ml.FEATURES:
        cols[c] = [rnd.random() < 0.3 for _ in range(n)] if c in ("attack_last_night", "alert_active") else [rnd.randint(0, 30) for _ in range(n)]
    return pa.table(cols)


class NightMlTest(unittest.TestCase):
    def test_fit_window_starts_2026_05_13(self):
        rows = toy()
        x, y = ml.training(rows)
        self.assertEqual(len(y), sum(1 for t in rows["t_utc"].to_pylist() if t >= datetime(2026, 5, 13, 19)))
        self.assertEqual(len(y), 60 - 12)

    def test_nights_since_attack_is_capped_at_14(self):
        rows = toy()
        x = ml.features(rows)
        self.assertEqual(x[:, 0].tolist(), [float(min(v, 14)) for v in rows[ml.SINCE].to_pylist()])

    def test_every_model_gives_probabilities_in_order(self):
        rows = toy()
        ev = toy(7, datetime(2026, 7, 1, 19), seed=1).drop_columns([ml.TARGET])
        for name, m in ml.MODELS.items():
            with self.subTest(model=name):
                p = m["predict"](m["fit"](rows), ev)
                self.assertEqual(len(p), 7)
                self.assertTrue(all(isinstance(v, float) and 0 <= v <= 1 for v in p))
                self.assertEqual(p, m["predict"](m["fit"](rows), ev))


if __name__ == "__main__":
    unittest.main(verbosity=2)
