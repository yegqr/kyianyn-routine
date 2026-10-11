"""Tests of the live features (src/airalerts/live/features.py) on the research data: every shared column equals gold
kyiv_quiet, no column known at t changes when the silver rows known after t are removed or perturbed, the alert columns
equal a plain loop over the kyiv_alerts intervals, and the import loads no gold module, no other silver builder and not
the Jev client.

Run from the project root with either of (python -I does not put the project root on sys.path, so
`-m unittest tests.test_live_features` cannot import the tests folder):
    choom -n 500 -- .venv/bin/python -I -m unittest discover -s tests -p test_live_features.py -v
    choom -n 500 -- .venv/bin/python -I tests/test_live_features.py
"""
import random
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from airalerts import paths
from airalerts.live import features as live
from airalerts.silver.alerts import END, RANK, START, head, ts

SEED = 2026
HOUR = timedelta(hours=1)
KNOWN_AT_T = live.INPUTS + ("quiet_now", "alert_active", "alert_level_now")
FORBIDDEN = ("airalerts.jev",) + tuple(f"airalerts.silver.{n}" for n in ("weather", "political_events", "calendar_dates",
                                                                        "rf_strikes", "astro"))


def cut(base, t):
    """The silver tables as known at t. Removed: hours and their posts that end after t (an hour is known at its end),
    alerts, S4 events and tg_posts known at or after t. Perturbed: what is not known at t yet, the end and the final
    level of an alert still open at t, the direction of an S4 wave whose last post is not before t."""
    at = pa.scalar(t, pa.timestamp("us"))
    out = {n: base[n].filter(pc.less_equal(base[n]["available_at"], at)) for n in ("kyiv_threat_hourly", "kyiv_threat_posts")}
    out.update({n: base[n].filter(pc.less(base[n]["available_at"], at)) for n in ("kyiv_alerts", "prep_signal_events", "tg_posts")})
    rows = out["kyiv_alerts"].to_pylist()
    for r in rows:
        if r["end_utc"] is None or r["end_utc"] >= t:
            r.update(end_utc=None, duration_min=None, end_post_id=None, max_level="alert" if r["max_level"] == "red" else "red")
    schema = base["kyiv_alerts"].schema
    out["kyiv_alerts"] = pa.Table.from_pylist(rows, schema=schema).replace_schema_metadata(schema.metadata)
    e = out["prep_signal_events"]
    flip = pc.if_else(pc.greater_equal(e["last_post_at"], at), pc.invert(e["toward_kyiv"]), e["toward_kyiv"])
    out["prep_signal_events"] = e.set_column(e.schema.get_field_index("toward_kyiv"), "toward_kyiv", flip)
    return out


class LiveFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.silver = Path(cls.tmp.name)
        for p in live.tables().values():  # only the live tables: no other silver table is reachable
            (cls.silver / p.name).symlink_to(p)
        cls.rows = live.build(silver=cls.silver).to_pylist()
        cls.gold = pq.read_table(live.REFERENCE)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_equals_gold(self):
        shared = [c for c in live.COLUMNS if c in self.gold.column_names and c != "t_utc"]
        self.assertEqual(sorted(set(live.COLUMNS) - set(shared)), ["alert_level_now", "t_utc", "y_alert_3h"])
        self.assertEqual(self.gold.num_rows, 3909)
        hours = [r["t_utc"] for r in self.rows]
        self.assertEqual(hours[0], ts(paths.T0))
        self.assertTrue(all(b - a == HOUR for a, b in zip(hours, hours[1:])))
        rows = {r["t_utc"]: r for r in self.rows}
        bad = dict.fromkeys(shared, 0)
        for g in self.gold.select(["t_utc"] + shared).to_pylist():
            r = rows[g["t_utc"]]
            for c in shared:
                a, b = r[c], g[c]
                if (a is None) != (b is None) or a is not None and (abs(a - b) > 1e-12 if isinstance(b, float) else a != b):
                    bad[c] += 1
        self.assertEqual(bad, dict.fromkeys(shared, 0))
        self.assertTrue(all((r["alert_level_now"] is not None) == r["alert_active"] for r in self.rows))

    def test_no_leak(self):
        src = live.tables()
        base = {n: pq.read_table(p) for n, p in src.items() if n != "tg_posts"}
        base["tg_posts"] = pq.read_table(src["tg_posts"], filters=[("channel", "in", ["VA_Kyiv", "UkraineAlarmSignal"])])
        rng = random.Random(SEED)
        on = [r for r in self.rows if r["alert_active"]]
        off = [r for r in self.rows if not r["alert_active"]]
        for full in rng.sample(on, 10) + rng.sample(off, 10):
            t = full["t_utc"]
            with tempfile.TemporaryDirectory() as d:
                for n, table in cut(base, t).items():
                    pq.write_table(table, Path(d) / f"{n}.parquet")
                row = live.build(end=t, silver=Path(d)).to_pylist()[-1]
            self.assertEqual(row["t_utc"], t)
            for c in KNOWN_AT_T:
                self.assertEqual(row[c], full[c], f"{c} at {t}")

    def test_alert_columns_plain_loop(self):
        src = live.tables()
        al = pq.read_table(src["kyiv_alerts"]).to_pylist()
        until = live.meta(src["kyiv_alerts"], "data_until")
        posts = pq.read_table(src["tg_posts"], columns=["channel", "available_at", "text"],
                              filters=[("channel", "==", "VA_Kyiv")]).to_pylist()
        rng = random.Random(SEED + 1)
        for r in rng.sample([r for r in self.rows if r["alert_active"]], 10) + rng.sample(self.rows, 10):
            t = r["t_utc"]
            ahead = None if t + 3 * HOUR > until else any(
                a["start_utc"] < t + 3 * HOUR and (a["end_utc"] is None or a["end_utc"] >= t) for a in al)
            level = None
            for a in al:  # the alert active at t: started before t, not ended before t
                if not (a["available_at"] < t and (a["end_utc"] is None or a["end_utc"] >= t)):
                    continue
                if a["start_source"] != "VA_Kyiv":
                    level = a["max_level"]  # eTryvoga: one start post, the level never rises
                    continue
                seen = []
                for p in posts:  # the VA_Kyiv start posts of this alert published before t
                    h = head(p["text"] or "")
                    if a["start_utc"] <= p["available_at"] < t and START.match(h) and not END.match(h):
                        seen.append("red" if "Червоний" in h else "yellow" if "Жовтий" in h else "alert")
                level = max(seen, key=RANK.get)
            self.assertEqual((r["alert_level_now"], r["y_alert_3h"]), (level, ahead), t)
        # at the end of an alert its whole level is known: it equals max_level of silver for every alert
        al.sort(key=lambda a: a["available_at"])
        done = [a for a in al if a["end_utc"] is not None]
        got = live.levels([a["end_utc"] for a in done], al, *live.read_starts(src["tg_posts"]))
        self.assertEqual(got, [a["max_level"] for a in done])

    def test_imports(self):
        code = "import sys, airalerts.live.features; print(*sorted(m for m in sys.modules if m.startswith('airalerts')))"
        loaded = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True).stdout.split()
        self.assertIn("airalerts.live.features", loaded)
        self.assertEqual([m for m in loaded if m.startswith("airalerts.gold") or m in FORBIDDEN], [])


if __name__ == "__main__":
    unittest.main()
