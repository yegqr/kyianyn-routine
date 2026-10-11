"""No-leakage tests of the nightly gold table and of every night model (docs/adr/0010-night-question.md).

Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_nights.py
"""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from airalerts.gold import kyiv_hourly as hourly, kyiv_nightly as nightly
from airalerts.modeling import nights, split

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the tests folder off the path
from test_models import FORBIDDEN, data_globals, reaches  # noqa: E402

HOUR = timedelta(hours=1)
NIGHT_FORBIDDEN = FORBIDDEN + ("nights", "nightly", "kyiv_nightly")


class NightlyTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = pq.read_table(hourly.PATH).sort_by("t_utc")
        cls.n = pq.read_table(nightly.PATH)

    def test_file_equals_a_fresh_build(self):
        self.assertTrue(nightly.build_table(self.h).equals(self.n))

    def test_features_use_only_what_is_known_at_22(self):
        """For every night, rebuild from the hourly rows up to 22:00 D, with every hourly label that is not known by
        22:00 D (t + 3 h > 22:00 D) erased: every feature of night D stays the same."""
        for r in self.n.to_pylist():
            t = r["t_utc"]
            cut = self.h.filter(pc.less_equal(self.h["t_utc"], t))
            known = [y if x + 3 * HOUR <= t else None for x, y in zip(cut["t_utc"].to_pylist(), cut[hourly.LABEL].to_pylist())]
            cut = cut.set_column(cut.schema.get_field_index(hourly.LABEL), hourly.LABEL, pa.array(known, pa.bool_()))
            again = [x for x in nightly.build_table(cut).to_pylist() if x["t_utc"] == t]
            self.assertEqual(len(again), 1)
            self.assertEqual({k: v for k, v in again[0].items() if k != nightly.LABEL},
                             {k: v for k, v in r.items() if k != nightly.LABEL})

    def test_target_is_a_strike_hour_from_22_to_08(self):
        strikes = {x[0] for x in duckdb.sql("SELECT hour_utc FROM 'data/silver/kyiv_threat_hourly.parquet' WHERE missile_strike").fetchall()}
        for r in self.n.to_pylist():
            want = any(r["t_utc"] + k * HOUR in strikes for k in range(10))
            self.assertEqual(r[nightly.LABEL], want, r["night_date"])

    def test_decision_row_is_22_kyiv_and_no_feature_is_the_target(self):
        for r in self.n.to_pylist():
            self.assertEqual(nightly.kyiv(r["t_utc"]).hour, 22)
            self.assertEqual(nightly.kyiv(r["t_utc"]).date(), r["night_date"])
        y = self.n[nightly.LABEL].to_pylist()
        for c in self.n.column_names:
            if c != nightly.LABEL:
                v = self.n[c].to_pylist()
                self.assertFalse(v == y or v == [not x for x in y], c)

    def test_naive_7n_is_the_share_of_the_7_nights_before(self):
        t = nights.load()
        at = t["t_utc"].to_pylist()
        self.assertEqual(nights.naive_7n(t, at), [v / 7 for v in t["attack_nights_7"].to_pylist()])


class NightModelsTest(unittest.TestCase):
    """Every model of every module in airalerts.modeling.night_models: fit sees only nights whose target is known at
    the fold origin, predict sees no target, neither reads data on its own, the output is reproducible probabilities."""

    @classmethod
    def setUpClass(cls):
        t = nights.load()
        dev, test = nights.dev_folds(t), nights.test_folds(t)
        cls.folds = [dev[0], dev[-1], test[-2]]

    def check(self, mod, fit, predict):
        self.assertEqual([n for n in NIGHT_FORBIDDEN if any(reaches(mod, f, n, set()) for f in (fit, predict))], [])
        self.assertEqual(data_globals(mod, (fit, predict)), [])
        for o, rows, ev in self.folds:
            self.assertLessEqual(max(rows["t_utc"].to_pylist()) + nights.H * HOUR, o)
            x = nights.features_only(ev)
            self.assertNotIn(nights.LABEL, x.column_names)
            p = [float(v) for v in predict(fit(rows), x)]
            self.assertEqual(len(p), ev.num_rows)
            self.assertTrue(all(0 <= v <= 1 for v in p))
            self.assertEqual(p, [float(v) for v in predict(fit(rows), x)])

    def test_every_night_model(self):
        for mod in nights.night_modules():
            for name, m in mod.MODELS.items():
                with self.subTest(model=name):
                    self.assertTrue({"fit", "predict", "description", "n_features"} <= set(m))
                    self.check(mod, m["fit"], m["predict"])

    def test_the_split_keeps_test_nights_out_of_development(self):
        t = nights.load()
        for _, rows, ev in nights.dev_folds(t):
            self.assertLess(max(ev["t_utc"].to_pylist()), split.TEST_START)
        self.assertEqual(min(x for _, _, ev in nights.test_folds(t) for x in ev["t_utc"].to_pylist()) >= split.TEST_START, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
