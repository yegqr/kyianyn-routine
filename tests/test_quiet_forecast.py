"""Tests of the person's forecast (src/airalerts/quiet/forecast.py): its scale comes from development, and a forecast
for hour t does not change when anything after t changes.

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_quiet_forecast.py
"""
import random
import unittest
from datetime import timedelta

import pyarrow as pa
import pyarrow.compute as pc

from airalerts.evaluation import split
from airalerts.quiet import forecast, score as quiet

SEED = 20261011
HOUR = timedelta(hours=1)


class ForecastTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.both = forecast.tables()
        hours = cls.both[0]["t_utc"].to_pylist()
        cls.at = random.Random(SEED).sample([x for x in hours if x >= split.TEST_START - 8 * 7 * 24 * HOUR], 8)

    def test_scale_still_comes_from_development(self):
        busy_at, high_at = forecast.rules(self.both[0])
        self.assertAlmostEqual(busy_at, forecast.BUSY_AT, places=3)
        self.assertAlmostEqual(high_at, forecast.HIGH_AT, places=3)

    def test_levels(self):
        self.assertEqual(forecast.level(forecast.BUSY_AT - 0.001)[0], "тихо")
        self.assertEqual(forecast.level(forecast.BUSY_AT), ("неспокійно", "середній ризик"))
        self.assertEqual(forecast.level(forecast.HIGH_AT), ("неспокійно", "високий ризик"))

    def test_nothing_after_t_changes_the_forecast(self):
        """Drop every labelled hour whose target is not known at t, or flip all their targets: the same forecast."""
        labelled, every = self.both
        for t in self.at:
            want = forecast.forecast(t, self.both)
            known = labelled.filter(pc.less_equal(labelled["t_utc"], pa.scalar(t - 3 * HOUR, pa.timestamp("us"))))
            self.assertEqual(forecast.forecast(t, (known, every))["p"], want["p"])
            later = [x > t - 3 * HOUR for x in labelled["t_utc"].to_pylist()]
            flipped = labelled
            for c in (quiet.LABEL, "y_drone_3h", "y_missile_3h"):
                ys = [(not y) if f else y for y, f in zip(flipped[c].to_pylist(), later)]
                flipped = flipped.set_column(flipped.schema.get_field_index(c), c, pa.array(ys, pa.bool_()))
            self.assertEqual(forecast.forecast(t, (flipped, every))["p"], want["p"])

    def test_text(self):
        f = forecast.forecast(self.at[0], self.both)
        lines = forecast.text(f).splitlines()
        self.assertTrue(lines[1].startswith("  Зараз: "))
        self.assertTrue(lines[2].startswith("  Наступні 3 години: "))
        self.assertIn("Ймовірність", lines[3])
        self.assertTrue(lines[4].startswith("  Чому: "))


if __name__ == "__main__":
    unittest.main(verbosity=2)
