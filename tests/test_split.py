"""No-leakage test of the time split of gold into development and test (docs/adr/0008-time-split.md).

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_split.py
"""
import unittest
from datetime import timedelta
from zoneinfo import ZoneInfo

from airalerts.gold.kyiv_hourly import LABEL
from airalerts.modeling import split

HOUR = timedelta(hours=1)
KYIV = ZoneInfo("Europe/Kyiv")
UTC = ZoneInfo("UTC")


def times(part):
    return part["t_utc"].to_pylist()


class SplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = split.load()

    def test_parts_do_not_overlap_and_cover_every_row(self):
        for h in (1, split.H, 24):
            dev, test = set(times(split.dev(self.t, h))), set(times(split.test(self.t)))
            purged = set(times(split.between(self.t, split.TEST_START - (h - 1) * HOUR, split.TEST_START)))
            self.assertEqual(len(purged), h - 1)
            self.assertFalse(dev & test or dev & purged or test & purged)
            self.assertEqual(dev | test | purged, set(times(self.t)))

    def test_no_development_label_reaches_test(self):
        for h in (1, split.H, 24):
            self.assertLessEqual(max(times(split.dev(self.t, h))) + h * HOUR, split.TEST_START)
        self.assertGreaterEqual(min(times(split.test(self.t))), split.TEST_START)

    def test_cut_is_saturday_noon_kyiv_and_not_inside_an_attack(self):
        k = split.TEST_START.replace(tzinfo=UTC).astimezone(KYIV)
        self.assertEqual((k.weekday(), k.hour, k.minute), (5, 12, 0))
        # no strike hour in [cut - 24 h, cut + 24 h): every label from cut - 24 h to cut + 21 h is false
        near = split.between(self.t, split.TEST_START - 24 * HOUR, split.TEST_START + (24 - split.H + 1) * HOUR)
        self.assertEqual(near.num_rows, 48 - split.H + 1)
        self.assertFalse(any(near[LABEL].to_pylist()))

    def test_test_is_the_last_six_full_weeks(self):
        last = max(times(self.t))
        self.assertLessEqual(split.TEST_START + 6 * split.WEEK, last)
        self.assertGreater(split.TEST_START + 6 * split.WEEK + 24 * HOUR, last)

    def check_folds(self, fs, rows, h):
        evaluated = []
        for o, fit, ev in fs:
            self.assertLessEqual(max(times(fit)) + h * HOUR, o)  # every fitted label is known at the origin
            self.assertGreaterEqual(min(times(ev)), o)
            evaluated += times(ev)
        self.assertEqual(evaluated, sorted(set(evaluated)))     # evaluation weeks never overlap
        self.assertEqual(set(evaluated), set(rows))

    def test_development_folds(self):
        for h in (1, split.H, 24):
            fs = split.dev_folds(self.t, h)
            self.assertEqual(len(fs), split.DEV_FOLDS)
            self.assertEqual(fs[-1][0] + split.WEEK, split.TEST_START)
            dev = split.dev(self.t, h)
            self.check_folds(fs, [ts for ts in times(dev) if ts >= fs[0][0]], h)
            self.assertLessEqual(max(max(times(fit)) for _, fit, _ in fs) + h * HOUR, split.TEST_START)

    def test_test_folds(self):
        fs = split.test_folds(self.t)
        self.assertEqual(fs[0][0], split.TEST_START)
        self.assertTrue(all(b[0] - a[0] == split.WEEK for a, b in zip(fs, fs[1:])))
        self.check_folds(fs, times(split.test(self.t)), split.H)


if __name__ == "__main__":
    unittest.main(verbosity=2)
