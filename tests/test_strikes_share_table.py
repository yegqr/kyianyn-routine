"""Checks of the share table on toy rows: the smoothing equals a hand count, unseen cells fall back to their parent,
recency weights and the first fit hour work as documented, predict needs no label and no time.

    .venv/bin/python -I -m unittest discover -s tests -p test_share_table.py -v
"""
import unittest
from datetime import datetime, timedelta

import pyarrow as pa

from airalerts.gold.kyiv_hourly import LABEL
from airalerts.strikes import share_table as st

T0 = datetime(2026, 6, 1)


def table(rows):
    """rows: (hours after T0, hour_kyiv, alert_active, hours_since_strike, label)."""
    cols = list(zip(*rows))
    return pa.table({"t_utc": [T0 + timedelta(hours=h) for h in cols[0]], "hour_kyiv": list(cols[1]),
                     "alert_active": list(cols[2]), "hours_since_strike": list(cols[3]), LABEL: list(cols[4])})


TOY = table([(0, 1, True, 100.0, True), (1, 1, True, 5.0, False), (2, 1, False, 100.0, False),
             (3, 2, False, 100.0, False), (4, 2, False, 100.0, True), (5, 2, True, 10.0, False)])


class ShareTableTest(unittest.TestCase):
    def test_smoothing_equals_a_hand_count(self):
        m = 2
        c = st.fit(TOY, m=m)
        root = 2 / 6
        h1 = (1 + m * root) / (3 + m)
        h1a = (1 + m * h1) / (2 + m)
        h1a_calm = (1 + m * h1a) / (1 + m)  # hour 1, alert, no pause: one row, true
        h1a_pause = (0 + m * h1a) / (1 + m)  # hour 1, alert, pause (5 h after a strike): one row, false
        self.assertAlmostEqual(c[()][2], root, places=12)
        self.assertAlmostEqual(c[(1,)][2], h1, places=12)
        x = TOY.drop_columns([LABEL])
        p = st.predict(c, x)
        self.assertAlmostEqual(p[0], h1a_calm, places=12)
        self.assertAlmostEqual(p[1], h1a_pause, places=12)
        self.assertGreater(p[0], p[1])

    def test_unseen_cells_take_the_parent_p(self):
        c = st.fit(TOY, m=24)
        new = pa.table({"hour_kyiv": [1, 7], "alert_active": [None, True], "hours_since_strike": [None, 4.0]})
        self.assertEqual(st.predict(c, new), [c[(1,)][2], c[()][2]])

    def test_pause_bounds(self):
        self.assertFalse(st.cell_keys(0, False, 2.99)[-1][-1])
        self.assertTrue(st.cell_keys(0, False, 3.0)[-1][-1])
        self.assertTrue(st.cell_keys(0, False, 23.5)[-1][-1])
        self.assertFalse(st.cell_keys(0, False, 24.0)[-1][-1])
        self.assertFalse(st.cell_keys(0, False, None)[-1][-1])

    def test_recency_weights_halve_per_half_life(self):
        two = table([(0, 1, False, 100.0, True), (48, 1, False, 100.0, False)])  # the true row is 2 days older
        c = st.fit(two, half_life_days=2)
        self.assertAlmostEqual(c[()][0], 0.5, places=12)
        self.assertAlmostEqual(c[()][1], 1.5, places=12)
        self.assertAlmostEqual(c[()][2], 1 / 3, places=12)

    def test_start_drops_earlier_rows(self):
        c = st.fit(TOY, start=T0 + timedelta(hours=3))
        self.assertEqual(c[()][1], 3)
        self.assertNotIn((1,), c)

    def test_predict_needs_only_three_columns_and_is_repeatable(self):
        c = st.fit(TOY)
        x = TOY.select(list(st.COLUMNS))
        p = st.predict(c, x)
        self.assertEqual(p, st.predict(st.fit(TOY), x))
        self.assertTrue(all(isinstance(v, float) and 0 <= v <= 1 for v in p))


if __name__ == "__main__":
    unittest.main(verbosity=2)
