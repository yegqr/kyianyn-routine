"""Small checks of the linear quiet models on toy hours (docs/quiet/linear.md)."""
import math
import unittest
from datetime import datetime, timedelta

import pyarrow as pa

from airalerts.quiet import linear


def toy(n=48):
    hours = [datetime(2026, 6, 1) + timedelta(hours=i) for i in range(n)]
    busy = [i % 3 == 0 for i in range(n)]
    return pa.table({
        "t_utc": pa.array(hours, pa.timestamp("us")),
        "hour_kyiv": [(i + 3) % 24 for i in range(n)],
        "ua_missiles_launched_1d": [None if i % 4 == 0 else i for i in range(n)],
        "hours_since_busy": [float(i % 5) for i in range(n)],
        "quiet_now": [i % 2 == 0 for i in range(n)],
        "y_busy_3h": busy, "y_drone_3h": busy, "y_missile_3h": [i % 6 == 0 for i in range(n)],
    })


class LinearTest(unittest.TestCase):
    def test_wide_skips_time_and_targets_and_marks_unknown(self):
        t = toy()
        names = linear.wide_columns(t)
        self.assertEqual(names, ("hour_kyiv", "ua_missiles_launched_1d", "hours_since_busy", "quiet_now"))
        x = linear.wide(t, names)
        self.assertEqual(x.shape, (48, 5))
        self.assertEqual(list(x[:2, 1]), [-1.0, 1.0])
        self.assertEqual(list(x[:2, 2]), [1.0, 0.0])

    def test_hour_features(self):
        x = linear.design(toy(), linear.SMALL)
        self.assertAlmostEqual(x[0, 0], math.sin(2 * math.pi * 3 / 24))
        self.assertEqual([x[i, 2] for i in (14, 15, 20, 21)], [0.0, 1.0, 1.0, 0.0])  # 17, 18, 23 and 0 Kyiv
        self.assertAlmostEqual(x[1, 3], math.log1p(1))

    def test_quiet_now_subset(self):
        self.assertEqual(linear.training(toy(), "quiet_now").num_rows, 24)
        with self.assertRaises(ValueError):
            linear.training(toy(), "other")

    def test_wide_model_predicts_without_targets(self):
        t = toy()
        p = linear.predict_wide(linear.fit_wide(t), t.drop_columns(["y_busy_3h", "y_drone_3h", "y_missile_3h"]))
        self.assertEqual(len(p), 48)
        self.assertTrue(all(0 <= v <= 1 for v in p))


if __name__ == "__main__":
    unittest.main(verbosity=2)
