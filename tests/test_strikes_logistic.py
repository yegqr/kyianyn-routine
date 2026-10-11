"""Small checks of the logistic model on toy data: the Newton solver reaches the optimum, the intercept is free, the step
limit survives separable data, recent rows weigh more, and predict does not need the label.

    .venv/bin/python -I -m unittest tests.test_logistic -v     (from the project root, or: discover -s tests)
"""
import math
import random
import unittest
from datetime import datetime, timedelta

import pyarrow as pa

from airalerts.gold.kyiv_hourly import LABEL
from airalerts.strikes import logistic as L

SEED = 20261011
T0 = datetime(2026, 6, 1)


def toy(n, label, alert=None, since=None, start=T0):
    rnd = random.Random(SEED)
    hours = [(start + timedelta(hours=i)).hour for i in range(n)]
    cols = {"t_utc": [start + timedelta(hours=i) for i in range(n)], "hour_kyiv": hours,
            "alert_active": alert or [rnd.random() < 0.2 for _ in range(n)],
            "hours_since_strike": since or [rnd.choice((0.0, 1.0, 5.0, 30.0, 336.0)) for _ in range(n)]}
    cols[LABEL] = [label(i, cols) for i in range(n)]
    return pa.table(cols)


class LogisticTest(unittest.TestCase):
    def test_newton_reaches_the_optimum(self):
        rnd = random.Random(SEED)
        z = [[rnd.gauss(0, 1), rnd.gauss(0, 1)] for _ in range(300)]
        y = [int(rnd.random() < L.sigmoid(-1 + 1.5 * a - 0.7 * b)) for a, b in z]
        wt = [rnd.uniform(0.2, 1) for _ in y]
        w = L.newton(z, y, wt, 2.0)
        g = [0.0, 0.0, 0.0]
        for x, v, q in zip(z, y, wt):
            p = L.sigmoid(w[0] + w[1] * x[0] + w[2] * x[1])
            for i, xi in enumerate([1.0] + x):
                g[i] += q * (p - v) * xi
        g = [g[0], g[1] + 2.0 * w[1], g[2] + 2.0 * w[2]]  # the intercept has no penalty term
        self.assertLess(max(abs(v) for v in g), 1e-7)

    def test_intercept_is_not_penalized(self):
        t = toy(240, lambda i, c: i % 10 == 0, alert=[False] * 240, since=[336.0] * 240)
        m = L.fit(t, harmonics=0, lam=1e6, half_life=None)
        self.assertAlmostEqual(L.predict(m, t.drop_columns([LABEL]))[0], 0.1, places=6)

    def test_separable_data_stays_finite(self):
        t = toy(200, lambda i, c: c["alert_active"][i])  # alert decides the label exactly
        m = L.fit(t, lam=1e-6)
        p = L.predict(m, t.drop_columns([LABEL]))
        self.assertTrue(all(0 <= v <= 1 and math.isfinite(v) for v in p))
        self.assertGreater(min(v for v, a in zip(p, t["alert_active"].to_pylist()) if a), 0.9)

    def test_recent_rows_weigh_more(self):
        n = 24 * 120  # true only in the last 30 days
        t = toy(n, lambda i, c: i >= n - 24 * 30 and i % 5 == 0, alert=[False] * n, since=[336.0] * n)
        x = t.drop_columns([LABEL])
        flat = L.predict(L.fit(t, harmonics=0, half_life=None), x)[0]
        recent = L.predict(L.fit(t, harmonics=0, half_life=28.0), x)[0]
        self.assertAlmostEqual(flat, 0.05, places=3)
        self.assertGreater(recent, 0.09)

    def test_start_drops_early_rows(self):
        t = toy(24 * 20, lambda i, c: i >= 24 * 10 and i % 4 == 0, alert=[False] * 480, since=[336.0] * 480)
        cut = (T0 + timedelta(days=10)).isoformat()
        m = L.fit(t, harmonics=0, half_life=None, start=cut)
        self.assertAlmostEqual(L.predict(m, t.drop_columns([LABEL]))[0], 0.25, places=4)

    def test_attack_and_pause_flags(self):
        t = toy(10, lambda i, c: False, since=[0.0, 2.9, 3.0, 23.9, 24.0, 336.0, None, 1.0, 5.0, 50.0])
        names, x = L.raw_features(t, 1, ())
        a, s = names.index("attack_on"), names.index("pause_3_24h")
        self.assertEqual([r[a] for r in x], [1, 1, 0, 0, 0, 0, 0, 1, 0, 0])
        self.assertEqual([r[s] for r in x], [0, 0, 1, 1, 0, 0, 0, 0, 1, 0])

    def test_odds_multiplier_of_a_flag(self):
        t = toy(400, lambda i, c: c["alert_active"][i] and i % 2 == 0 or i % 25 == 0)
        m = L.fit(t, harmonics=0, lam=1e-9, half_life=None)
        x = t.drop_columns([LABEL])
        on = pa.table({"hour_kyiv": [0], "alert_active": [True], "hours_since_strike": [336.0]})
        off = pa.table({"hour_kyiv": [0], "alert_active": [False], "hours_since_strike": [336.0]})
        p1, p0 = L.predict(m, on)[0], L.predict(m, off)[0]
        self.assertAlmostEqual(p1 / (1 - p1) / (p0 / (1 - p0)), L.odds_multipliers(m)["alert_active"], places=9)
        self.assertEqual(len(L.predict(m, x)), x.num_rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
