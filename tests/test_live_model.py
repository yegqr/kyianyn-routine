"""Tests of the live model service (src/airalerts/live/model.py and publish.py): the JSON model gives what sklearn gives,
a fit at `at` sees only what is known at `at`, the replay retrains at its cadence (daily, every 6 hours) without looking ahead, the person's
forecast gets the same p, and the publisher writes every key of the site's four files.

Run from the project root with either of:
    choom -n 500 -- .venv/bin/python -I -m unittest discover -s tests -p test_live_model.py
    .venv/bin/python -I tests/test_live_model.py
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from airalerts import paths
from airalerts.evaluation import split
from airalerts.gold import kyiv_quiet as quiet_table
from airalerts.live import model, publish
from airalerts.quiet import forecast, linear

HOUR = timedelta(hours=1)
UTC, KYIV = ZoneInfo("UTC"), ZoneInfo("Europe/Kyiv")
AT = datetime(2026, 9, 18, 14)  # naive UTC, an hour of the test period
KEYS = {  # every key of the contract, by where it sits
    "now": {"schema", "generated_at", "data_until", "stale", "stale_reason", "hour", "window_end", "now", "forecast",
            "model", "waves"},
    "now.now": {"alert", "level", "alert_since", "quiet_now"},
    "forecast": {"p", "tier", "label", "busy_at", "high_at", "reasons", "kind"},
    "reason": {"key", "text", "value", "logit"},
    "kind": {"n", "busy_share", "missile_share", "drone_only_share", "alert_share", "period"},
    "now.model": {"name", "trained_at", "rows"},
    "wave": {"at", "kyiv", "count", "text"},
    "history": {"schema", "generated_at", "hours", "tiers", "tiers_since_test", "calibration"},
    "hour": {"t", "p", "tier", "source", "quiet_now", "alert", "busy_3h", "drone_3h", "missile_3h", "alert_3h"},
    "tier": {"hours", "busy_share", "alert_share", "missile_share"},
    "bin": {"from", "to", "n", "p_mean", "busy_share"},
    "model": {"schema", "name", "trained_at", "rows", "busy_share", "intercept", "C", "busy_at", "high_at", "evening",
              "features"},
    "feature": {"column", "how", "mean", "scale", "coef", "text"},
    "meta": {"schema", "generated_at", "quality", "channels", "pipeline", "jev"},
    "quality": {"source", "dev", "test"},
    "channel": {"name", "last_post", "posts_24h"},
    "jev": {"calls", "usd"},
}


def exported(table, at):
    return model.export(model.train(table, at), at, 0, 0.0)


def flipped(table, after):
    """The table with every target of an hour later than `after` flipped."""
    late = pc.greater(table["t_utc"], pa.scalar(after, pa.timestamp("us"))).to_pylist()
    y = [None if v is None else (v != f) for v, f in zip(table[linear.TARGET].to_pylist(), late)]
    i = table.schema.get_field_index(linear.TARGET)
    return table.set_column(i, linear.TARGET, pa.array(y, table.schema.field(i).type))


class LiveModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = model.prepare(pq.read_table(quiet_table.PATH))
        cls.rows = {r["t_utc"]: r for r in cls.table.to_pylist()}
        cls.fit = model.train(cls.table, AT)
        cls.json = model.export(cls.fit, AT, 0, 0.0)
        cls.some = cls.table.take(list(range(0, 3800, 19)))  # 200 hours over the whole table

    def test_json_predict_equals_sklearn(self):
        spec, pipe = self.fit
        want = pipe.predict_proba(linear.design(self.some, spec))[:, 1]
        self.assertEqual(len(want), 200)
        for r, w in zip(self.some.to_pylist(), want):
            self.assertAlmostEqual(model.predict(self.json, r)[0], w, delta=1e-12)

    def test_contributions_add_up_to_the_logit(self):
        spec, pipe = self.fit
        z = pipe.decision_function(linear.design(self.some, spec))
        for r, want in zip(self.some.to_pylist(), z):
            parts = model.predict(self.json, r)[1]
            self.assertEqual(list(parts), list(model.INPUTS))  # the three hour features are one reason
            self.assertAlmostEqual(self.json["intercept"] + sum(parts.values()), want, delta=1e-12)

    def test_train_ignores_what_is_not_known_at(self):
        """Flip every target not known at AT (t + 3 h > AT): the same model; flipped later, the model changes."""
        other = flipped(self.table, AT - 3 * HOUR)
        self.assertEqual(exported(other, AT), self.json)
        self.assertNotEqual(exported(other, AT + 48 * HOUR), exported(self.table, AT + 48 * HOUR))

    def test_replay_uses_the_model_of_that_days_retrain(self):
        """Each replay hour equals a model trained at the last 04:00 Kyiv before it; flipping what that retrain could
        not know changes nothing before the next retrain."""
        end = datetime(2026, 9, 12, 9)
        part = self.table.filter(pc.less(self.table["t_utc"], pa.scalar(end, pa.timestamp("us"))))
        rep = model.replay(part, "2026-09-10T09:00:00Z", "daily")
        self.assertEqual([x["t"] for x in rep], [datetime(2026, 9, 10, 9) + k * HOUR for k in range(48)])
        models = {}
        for x in rep:
            k = x["t"].replace(tzinfo=UTC).astimezone(KYIV)
            day = k.date() if k.hour >= 4 else k.date() - timedelta(days=1)
            r = datetime.combine(day, time(4), KYIV).astimezone(UTC).replace(tzinfo=None)
            if r not in models:
                models[r] = exported(self.table, r)
            self.assertAlmostEqual(x["p"], model.predict(models[r], self.rows[x["t"]])[0], delta=1e-12)
            self.assertEqual(x["tier"], model.tier(x["p"]))
        first, second = sorted(models)[:2]
        self.assertEqual((first, len(models)), (datetime(2026, 9, 10, 1), 3))
        again = model.replay(flipped(part, first - 3 * HOUR), "2026-09-10T09:00:00Z", "daily")
        self.assertEqual([x["p"] for x in again if x["t"] < second], [x["p"] for x in rep if x["t"] < second])
        self.assertNotEqual([x["p"] for x in again], [x["p"] for x in rep])

    def test_replay_at_a_non_daily_cadence(self):
        """Every 6 hours (04, 10, 16, 22 Kyiv): each replay hour equals a model trained at its last retrain moment r,
        and flipping every target r could not know (t + 3 h > r) leaves the hours of r as they were. The weekly
        moments are the fold origins of split.py."""
        start, end = datetime(2026, 9, 10, 9), datetime(2026, 9, 11, 9)
        part = self.table.filter(pc.less(self.table["t_utc"], pa.scalar(end, pa.timestamp("us"))))
        rep = model.replay(part, start, "6h")
        self.assertEqual([x["t"] for x in rep], [start + k * HOUR for k in range(24)])
        moment = {x["t"]: x["t"] - (x["t"].replace(tzinfo=UTC).astimezone(KYIV).hour - 4) % 6 * HOUR for x in rep}
        models = {r: exported(self.table, r) for r in set(moment.values())}
        self.assertEqual(len(models), 5)
        for x in rep:
            self.assertAlmostEqual(x["p"], model.predict(models[moment[x["t"]]], self.rows[x["t"]])[0], delta=1e-12)
        for r in sorted(models):
            again = model.replay(flipped(part, r - 3 * HOUR), start, "6h")
            mine = [k for k, x in enumerate(rep) if moment[x["t"]] == r]
            self.assertEqual([again[k]["p"] for k in mine], [rep[k]["p"] for k in mine])
            if r == min(models):  # the flips do reach the later retrains
                self.assertNotEqual([x["p"] for x in again], [x["p"] for x in rep])
        origins = [split.TEST_START - k * split.WEEK for k in range(split.DEV_FOLDS, -1, -1)]
        self.assertEqual(model.retrains(origins[0], origins[-1], "weekly"), origins)

    def test_same_p_as_the_person_forecast(self):
        both = forecast.tables()
        for t in (datetime(2026, 8, 15, 10), AT, datetime(2026, 10, 5, 20)):
            p = model.predict(exported(self.table, t), self.rows[t])[0]
            self.assertAlmostEqual(p, forecast.forecast(t, both)["p"], delta=1e-9)

    def test_publish_writes_every_contract_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            data = tmp / "data"
            data.mkdir()
            for part in ("bronze", "silver"):  # read only: the publisher writes nothing there
                if (paths.DATA / part).exists():
                    (data / part).symlink_to(paths.DATA / part)
            now = datetime(2026, 10, 10, 20)
            publish.publish(tmp / "site", self.table, data, now)
            api = tmp / "site" / "api"
            self.assertEqual(sorted(os.listdir(api)), ["history.json", "meta.json", "model.json", "now.json"])
            f = {n: json.loads((api / f"{n}.json").read_text(encoding="utf-8")) for n in ("now", "history", "model", "meta")}

            def has(key, d):
                self.assertLessEqual(KEYS[key], set(d), key)

            has("now", f["now"])
            has("now.now", f["now"]["now"])
            has("forecast", f["now"]["forecast"])
            has("kind", f["now"]["forecast"]["kind"])
            has("now.model", f["now"]["model"])
            self.assertEqual(len(f["now"]["forecast"]["reasons"]), 3)
            for r in f["now"]["forecast"]["reasons"]:
                has("reason", r)
            for w in f["now"]["waves"]:
                has("wave", w)
            has("history", f["history"])
            for h in f["history"]["hours"]:
                has("hour", h)
            for name in ("tiers", "tiers_since_test"):
                self.assertEqual(set(f["history"][name]), {"low", "medium", "high"})
                for v in f["history"][name].values():
                    has("tier", v)
            self.assertEqual(len(f["history"]["calibration"]), 10)
            for b in f["history"]["calibration"]:
                has("bin", b)
            has("model", f["model"])
            for x in f["model"]["features"]:
                has("feature", x)
            has("meta", f["meta"])
            has("quality", f["meta"]["quality"])
            has("jev", f["meta"]["jev"])
            for c in f["meta"]["channels"]:
                has("channel", c)

            hours = f["history"]["hours"]
            self.assertEqual(hours[0]["t"], model.START)
            self.assertEqual((hours[-1]["t"], hours[-1]["source"]), (f["now"]["hour"], "live"))
            self.assertEqual(f["now"]["hour"], "2026-10-10T17:00:00Z")
            self.assertTrue(f["now"]["stale"])
            self.assertEqual(f["model"]["trained_at"], "2026-10-10T20:00:00Z")
            self.assertTrue((data / "live_model" / "logit_signals-2026-10-10.json").exists())
            log = (data / publish.LOG).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(log), 1)
            self.assertFalse(publish.log(data, json.loads(log[0])))  # once per hour


if __name__ == "__main__":
    unittest.main()
