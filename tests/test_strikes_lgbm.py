"""Small checks of the LightGBM model on toy data: the feature list, nulls and booleans, the since filter, a plain signal
is learned, and the output is reproducible."""
import math
import random
import unittest
from datetime import datetime, timedelta

import pyarrow as pa

from airalerts.gold.kyiv_hourly import LABEL
from airalerts.strikes import lgbm


def toy(n=800, seed=1):
    """Random features; the label is mostly true when an alert is active."""
    rnd = random.Random(seed)
    cols = {"t_utc": [datetime(2026, 5, 1) + timedelta(hours=i) for i in range(n)]}
    for c in lgbm.FEATURES + lgbm.WEATHER:
        cols[c] = [rnd.random() for _ in range(n)]
    cols["alert_active"] = [rnd.random() < 0.2 for _ in range(n)]
    cols[LABEL] = [rnd.random() < (0.6 if a else 0.03) for a in cols["alert_active"]]
    return pa.table(cols)


class LgbmTest(unittest.TestCase):
    def test_feature_list(self):
        self.assertTrue(10 <= len(lgbm.FEATURES) <= 20)
        every = lgbm.FEATURES + lgbm.WEATHER
        self.assertEqual(len(set(every)), len(every))
        self.assertNotIn("t_utc", every)
        self.assertNotIn(LABEL, every)
        self.assertNotIn("ua_missiles_launched_1d", every)

    def test_rejects_time_as_a_feature(self):
        with self.assertRaises(ValueError):
            lgbm.fit(toy(), features=("t_utc", "hour_kyiv"))

    def test_nulls_become_nan_and_booleans_numbers(self):
        t = pa.table({"a": pa.array([True, None, False]), "b": pa.array([1.5, None, 3.0])})
        m = lgbm.matrix(t, ("b", "a"))
        self.assertEqual(m.shape, (3, 2))
        self.assertEqual((m[0, 0], m[0, 1], m[2, 1]), (1.5, 1.0, 0.0))
        self.assertTrue(math.isnan(m[1, 0]) and math.isnan(m[1, 1]))

    def test_since_drops_only_earlier_rows(self):
        t = toy()
        since = datetime(2026, 5, 10)
        kept = lgbm.fit_rows(t, since)["t_utc"].to_pylist()
        self.assertEqual(kept, [x for x in t["t_utc"].to_pylist() if x >= since])
        self.assertIs(lgbm.fit_rows(t, None), t)

    def test_learns_a_plain_signal_reproducibly(self):
        t = toy()
        x = t.drop_columns([LABEL])
        p = lgbm.predict(lgbm.fit(t), x)
        self.assertTrue(all(0 <= v <= 1 for v in p))
        alert = x["alert_active"].to_pylist()
        on = [v for v, a in zip(p, alert) if a]
        off = [v for v, a in zip(p, alert) if not a]
        self.assertGreater(sum(on) / len(on), 3 * sum(off) / len(off))
        self.assertEqual(p, lgbm.predict(lgbm.fit(t), x))


if __name__ == "__main__":
    unittest.main(verbosity=2)
