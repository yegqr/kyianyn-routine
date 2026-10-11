"""No-leakage tests of the gold table kyiv_quiet and of every quiet model (docs/adr/0011-quiet-hours.md).

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_quiet.py
"""
import importlib
import pkgutil
import random
import sys
import unittest
from datetime import timedelta
from pathlib import Path

import pyarrow.parquet as pq

from airalerts.gold import kyiv_hourly as hourly, kyiv_quiet
from airalerts import quiet as quiet_models
from airalerts.evaluation import split
from airalerts.quiet import score as quiet

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the tests folder off the path
from test_strikes import FORBIDDEN  # noqa: E402
from test_nights import check_model  # noqa: E402

SEED = 20261011
HOUR = timedelta(hours=1)
QUIET_FORBIDDEN = FORBIDDEN + ("quiet", "kyiv_quiet", "read_flags", "read_drone_max", "read_s4", "THREAT", "POSTS", "EVENTS")


class QuietTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = pq.read_table(hourly.PATH).sort_by("t_utc")
        cls.flags = kyiv_quiet.read_flags()
        cls.drone_max = kyiv_quiet.read_drone_max()
        cls.s4 = kyiv_quiet.read_s4()
        cls.q = pq.read_table(kyiv_quiet.PATH)

    def test_file_equals_a_fresh_build(self):
        self.assertTrue(kyiv_quiet.build_table(self.h, self.flags, self.drone_max, self.s4).equals(self.q))

    def test_features_use_only_hours_ended_by_t(self):
        """For random hours t, rebuild row t from what is known at t: flags and post answers of hours that ended by t
        (h + 1 h <= t), S4 events with available_at < t whose direction is hidden until their last post: every feature
        is the same."""
        rows = self.h.to_pylist()
        for i in random.Random(SEED).sample(range(len(rows)), 60):
            t = rows[i]["t_utc"]
            flags = {k: v for k, v in self.flags.items() if k + HOUR <= t}
            drone_max = {k: v for k, v in self.drone_max.items() if k + HOUR <= t}
            s4 = [(a, last, kyiv) if last < t else (a, None, None) for a, last, kyiv in self.s4 if a < t]
            again = kyiv_quiet.build_table(self.h.slice(i, 1), flags, drone_max, s4).to_pylist()[0]
            want = self.q.slice(i, 1).to_pylist()[0]
            self.assertEqual({k: v for k, v in again.items() if k not in kyiv_quiet.TARGETS},
                             {k: v for k, v in want.items() if k not in kyiv_quiet.TARGETS})

    def test_targets_are_flags_in_the_next_3_hours(self):
        for r in self.q.to_pylist():
            ahead = [self.flags.get(r["t_utc"] + k * HOUR) for k in range(3)]
            known = None not in ahead
            self.assertEqual(r[kyiv_quiet.LABEL], any(any(f[:3]) for f in ahead) if known else None, r["t_utc"])
            self.assertEqual(r["y_drone_3h"], any(f[0] for f in ahead) if known else None)
            self.assertEqual(r["y_missile_3h"], any(f[1] or f[2] for f in ahead) if known else None)

    def test_quiet_now_and_no_feature_is_the_target(self):
        for r in self.q.to_pylist():
            self.assertEqual(r["quiet_now"], not r["alert_active"] and not r["busy_prev_1h"])
        for target in kyiv_quiet.TARGETS:
            y = self.q[target].to_pylist()
            for c in self.q.column_names:
                if c not in kyiv_quiet.TARGETS:
                    v = self.q[c].to_pylist()
                    self.assertFalse(v == y or v == [None if x is None else not x for x in y], (target, c))

    def test_predict_never_sees_a_target(self):
        t = quiet.load()
        self.assertEqual([c for c in kyiv_quiet.TARGETS if c in quiet.features_only(t).column_names], [])

    def test_naive_7d_uses_only_known_targets(self):
        t = quiet.load()
        at = random.Random(SEED).sample(t["t_utc"].to_pylist()[200:], 30)
        rows = list(zip(t["t_utc"].to_pylist(), t[kyiv_quiet.LABEL].to_pylist()))
        for x, p in zip(at, quiet.naive_7d(t, at)):
            ys = [y for u, y in rows if x - timedelta(days=7) <= u <= x - 3 * HOUR]
            self.assertAlmostEqual(p, sum(ys) / len(ys), places=12)


class QuietModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t = quiet.load()
        dev, test = quiet.dev_folds(t), quiet.test_folds(t)
        cls.folds = [dev[0], dev[-1], test[-2]]

    def test_every_quiet_model(self):
        """Each module of airalerts.quiet in its own subtest, then each of its models."""
        for info in pkgutil.iter_modules(quiet_models.__path__):
            with self.subTest(module=info.name):
                mod = importlib.import_module(f"{quiet_models.__name__}.{info.name}")
                for name, m in getattr(mod, "MODELS", {}).items():
                    with self.subTest(model=name):
                        self.assertTrue({"fit", "predict", "description", "n_features"} <= set(m))
                        check_model(self, mod, m["fit"], m["predict"], self.folds, quiet.SPEC, QUIET_FORBIDDEN)

    def test_dev_scores_runs(self):
        from airalerts.quiet import baselines
        m = baselines.MODELS["clim_hour"]
        self.assertIn("bss", quiet.dev_scores(m["fit"], m["predict"]))

    def test_development_never_reaches_the_test(self):
        t = quiet.load()
        for _, rows, ev in quiet.dev_folds(t):
            self.assertLessEqual(max(ev["t_utc"].to_pylist()) + 3 * HOUR, split.TEST_START)


if __name__ == "__main__":
    unittest.main(verbosity=2)
