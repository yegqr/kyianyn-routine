"""No-leakage test of the gold table kyiv_hourly (docs/data/gold/kyiv_hourly.md, section "Тест на витік").

Under -I the project root is not on sys.path, so `-m unittest tests/test_gold_hourly.py` cannot import the package `tests`.
Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -v
    .venv/bin/python -I tests/test_gold_hourly.py
"""
import ast
import inspect
import random
import textwrap
import unittest
from datetime import timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq

from airalerts.db import connect, register_layers
from airalerts.gold import kyiv_hourly as gold
from airalerts.paths import SILVER
from airalerts.silver import threat_hourly

N_RANDOM = 50    # random hours t checked against the ASOF views
SEED = 20261011  # fixed: the same 50 hours on every run
HOUR = timedelta(hours=1)
KYIV = ZoneInfo("Europe/Kyiv")


def sql_ts(t):
    return f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'"


def arrow(con, sql):
    r = con.execute(sql)
    return (r.to_arrow_table if hasattr(r, "to_arrow_table") else r.fetch_arrow_table)()


def same(a, b):
    """Identical values, no tolerance; null equals only null; NaN equals NaN."""
    if a is None or b is None:
        return a is None and b is None
    return a == b or (a != a and b != b)


def names_in(fn):
    """Every name and attribute that the source of the function mentions."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def reaches(mod, fn, target, seen):
    """True when fn, or a function of the same module that fn mentions (and so on), mentions the name target."""
    seen.add(fn)
    found = names_in(fn)
    if target in found:
        return True
    for name in found:
        g = vars(mod).get(name)
        if inspect.isfunction(g) and g.__module__ == mod.__name__ and g not in seen and reaches(mod, g, target, seen):
            return True
    return False


class NoLeakage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = pq.read_table(gold.PATH)
        cls.meta = {k.decode(): v.decode() for k, v in pq.read_metadata(gold.PATH).metadata.items()}
        cls.rows = {r["t_utc"]: r for r in cls.table.to_pylist()}
        cls.hours = sorted(cls.rows)
        cls.sample = sorted(random.Random(SEED).sample(cls.hours, N_RANDOM))
        cls.full = register_layers(connect())  # every silver table as it is now
        cls.full.execute(f"CREATE TABLE one AS SELECT {sql_ts(cls.hours[0])} AS t_utc")
        cls.full_rows = {t: cls.full.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for _, m in gold.MODULES for t in m.ASOF}

    @classmethod
    def tearDownClass(cls):
        cls.full.close()

    def asof_connection(self, t):
        """A fresh DuckDB where each table of every module's ASOF is the table as it was known before t, and nothing else."""
        con, keep, hidden = connect(), [], 0
        for _, mod in gold.MODULES:
            for table, sql in mod.ASOF.items():
                known = arrow(self.full, sql.format(t=sql_ts(t)))
                keep.append(known)  # the connection reads these tables later
                hidden += self.full_rows[table] - known.num_rows
                con.register(f"known_{table}", known)
                con.execute(f"CREATE VIEW {table} AS SELECT * FROM known_{table}")
        con.execute(f"CREATE TABLE one AS SELECT {sql_ts(t)} AS t_utc")
        return con, keep, hidden

    def test_01_shape_and_columns(self):
        cols = self.table.column_names
        self.assertEqual(cols[:3], ["t_utc", "hour_kyiv", "dow_kyiv"])
        self.assertEqual(cols[-1], gold.LABEL)
        self.assertEqual(len(set(cols)), len(cols))
        expected = []
        for name, mod in gold.MODULES:
            f = mod.features(self.full, "one")
            self.assertEqual(f.column_names[0], "t_utc", name)
            self.assertEqual(f.num_rows, 1, name)
            expected += f.column_names[1:]
        self.assertEqual(cols[3:-1], expected, "gold columns are the features() columns of the modules, in module order")
        t0, cut = gold.parse_utc(self.meta["t0_utc"]), gold.parse_utc(self.meta["cutoff_utc"])
        self.assertEqual(self.table["t_utc"].to_pylist(), [t0 + i * HOUR for i in range(int((cut - t0) / HOUR) + 1)],
                         "one row per hour from T0 to the cutoff: unique and continuous")
        print(f"\nshape: {self.table.num_rows} rows, {len(cols)} columns, T0 {self.meta['t0_utc']}, cutoff {self.meta['cutoff_utc']}")

    def test_02_gold_is_not_older_than_silver(self):
        built = gold.PATH.stat().st_mtime
        newer = [t for _, mod in gold.MODULES for t in mod.ASOF if (SILVER / f"{t}.parquet").stat().st_mtime > built]
        self.assertEqual(newer, [], "silver tables rebuilt after gold: run python -I -m airalerts.gold.kyiv_hourly again")

    def test_03_features_on_asof_views_equal_gold(self):
        compared, hidden, mismatches = 0, 0, []
        for t in self.sample:
            con, keep, h = self.asof_connection(t)
            hidden += h
            for name, mod in gold.MODULES:
                f = mod.features(con, "one")
                self.assertEqual(f.num_rows, 1, name)
                got = f.to_pylist()[0]
                self.assertEqual(got.pop("t_utc"), t, name)
                for c, v in got.items():
                    compared += 1
                    if not same(v, self.rows[t][c]):
                        mismatches.append((gold.iso(t), name, c, v, self.rows[t][c]))
            con.close()
        print(f"\nASOF: {len(self.sample)} random t (seed {SEED}) from {gold.iso(self.sample[0])} to {gold.iso(self.sample[-1])}, "
              f"{len(gold.MODULES)} modules, {compared} feature values compared with the gold rows, differences {len(mismatches)}; "
              f"rows hidden by the ASOF views in total {hidden}")
        self.assertGreater(hidden, 0, "the ASOF views hid nothing: the test would be empty")
        self.assertEqual(mismatches, [], "(t, module, column, value on ASOF views, value in gold)")

    def test_04_hour_and_dow_in_kyiv_time(self):
        bad = []
        for t, r in self.rows.items():
            local = t.replace(tzinfo=timezone.utc).astimezone(KYIV)
            if (r["hour_kyiv"], r["dow_kyiv"]) != (local.hour, local.weekday()):
                bad.append((gold.iso(t), r["hour_kyiv"], r["dow_kyiv"], local.hour, local.weekday()))
        self.assertEqual(bad, [])

    def test_05_label_is_a_strike_in_the_next_3_hours(self):
        strikes = {h for (h,) in self.full.execute("SELECT hour_utc FROM kyiv_threat_hourly WHERE missile_strike").fetchall()}
        first = self.full.execute("SELECT min(hour_utc) FROM kyiv_threat_hourly").fetchone()[0]
        end = gold.parse_utc(pq.read_metadata(SILVER / "kyiv_threat_hourly.parquet").metadata[b"label_end"].decode())
        bad = []
        for t, r in self.rows.items():
            want = None if (t + 3 * HOUR > end or t < first) else any(t + k * HOUR in strikes for k in range(3))
            if r[gold.LABEL] != want:
                bad.append((gold.iso(t), r[gold.LABEL], want))
        self.assertEqual(bad, [], "(t, gold, recomputed from kyiv_threat_hourly)")
        self.full.register("all_t", self.table.select(["t_utc"]))
        lab = {r["t_utc"]: r[gold.LABEL] for r in threat_hourly.labels(self.full, "all_t").to_pylist()}
        self.assertEqual(lab, {t: r[gold.LABEL] for t, r in self.rows.items()}, "gold label is the output of labels()")

    def test_06_no_feature_column_is_the_label(self):
        labelled = [r for r in self.rows.values() if r[gold.LABEL] is not None]
        copies = []
        for c in self.table.column_names[1:-1]:
            pairs = [(r[c], int(r[gold.LABEL])) for r in labelled if r[c] is not None]
            if pairs and (all(v == y for v, y in pairs) or all(v == 1 - y for v, y in pairs)):
                copies.append(c)
        self.assertEqual(copies, [], "feature columns equal to the label or its negation")

    def test_07_labels_is_not_called_by_any_features(self):
        for name, mod in gold.MODULES:
            self.assertFalse(reaches(mod, mod.features, "labels", set()), f"{name}.features mentions labels")
        boom = mock.Mock(side_effect=AssertionError("labels() was called by a features()"))
        with mock.patch.object(threat_hourly, "labels", boom):
            for name, mod in gold.MODULES:
                mod.features(self.full, "one")
        boom.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
