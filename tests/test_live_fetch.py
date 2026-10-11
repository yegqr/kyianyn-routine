"""Live fetch offline: the incremental append, the lock, the channels, AIRALERTS_DATA in paths, the Jev key mode and the
check times of bronze/telegram/_checked.json with the data ends they move (label_end, data_until of the alerts).
No network.

Under -I the project root is not on sys.path, so `-m unittest tests.test_live_fetch` cannot import the package `tests`.
Run from the project root with either of:
    .venv/bin/python -I -m unittest discover -s tests -p test_live_fetch.py -v
    .venv/bin/python -I tests/test_live_fetch.py
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from airalerts import jev, paths, telegram
from airalerts.live import fetch
from airalerts.silver import threat_hourly


def post(i, text="x"):
    return {"channel": "chan", "post_id": i, "published_at": f"2026-10-11T{i // 60:02d}:{i % 60:02d}:00Z", "text": text,
            "edited": False, "views": None, "forwarded_from": None, "url": f"https://t.me/chan/{i}",
            "fetched_at": "2026-10-11T12:00:00Z"}


class Site:
    """Stand-in for t.me/s: a page is the 20 newest posts before `before`; every request is recorded."""

    def __init__(self, ids, dup=None):
        self.ids, self.dup, self.calls = sorted(ids), dup, []

    def __call__(self, channel, before=None):
        self.calls.append(before)
        page = [post(i) for i in self.ids if before is None or i < before][-20:]
        if self.dup in {p["post_id"] for p in page}:
            page.append(post(self.dup, "edited"))  # the same post_id twice on one page
        return page


def run(env_data, code):
    env = {k: v for k, v in os.environ.items() if k != "AIRALERTS_DATA"}
    if env_data is not None:
        env["AIRALERTS_DATA"] = env_data
    return subprocess.run([sys.executable, "-I", *code], env=env, capture_output=True, text=True)


class LiveFetch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.file = self.data / "bronze" / "telegram" / "chan.jsonl"
        self.file.parent.mkdir(parents=True)
        self.file.write_text("".join(json.dumps(post(i)) + "\n" for i in range(81, 106)), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def pass_(self, site):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = fetch.run_once(self.data, ("chan",), site, pause=0)
        return code, out.getvalue()

    def ids(self):
        return [json.loads(line)["post_id"] for line in self.file.read_text(encoding="utf-8").splitlines()]

    def test_append_only_newer_without_duplicates(self):
        site = Site(range(81, 121), dup=110)
        code, out = self.pass_(site)
        self.assertEqual((code, site.calls), (0, [None]))  # the newest page already reaches 105, the newest known id
        self.assertEqual(self.ids(), list(range(81, 121)))
        self.assertIn("new   15  newest 2026-10-11T02:00:00Z", out)
        site.ids += [121, 122]
        site.calls.clear()
        self.pass_(site)
        self.assertEqual((self.ids(), site.calls), (list(range(81, 123)), [None]))

    def test_walks_back_to_the_newest_known_id(self):
        site = Site(range(81, 131))
        rows, pages = fetch.newer("chan", 90, paths.FETCH_FROM, site, pause=0)
        self.assertEqual(([r["post_id"] for r in rows], pages, site.calls), (list(range(91, 131)), 3, [None, 111, 91]))

    def test_lock_makes_a_second_run_exit_without_fetching(self):
        held = fetch.lock(self.data)
        try:
            site = Site(range(81, 121))
            code, out = self.pass_(site)
        finally:
            held.close()
        self.assertEqual((code, site.calls, self.ids()), (0, [], list(range(81, 106))))
        self.assertIn("another fetch is running", out)

    def test_channels_from_the_silver_code(self):
        self.assertEqual(set(fetch.CHANNELS), {"VA_Kyiv", "vitaliy_klitschko", "truexakyiv", "war_monitor", "AerisRimor",
                                               "kyiv_nebo", "kyiv_airdef", "kpszsu", "StrategicaviationT", "monitorwarr",
                                               "UkraineAlarmSignal"})

    def test_paths_honour_airalerts_data(self):
        code = ["-c", "from airalerts import paths; print(paths.DATA); print(paths.SILVER)"]
        self.assertEqual(run(None, code).stdout.split(), [str(paths.ROOT / "data"), str(paths.ROOT / "data" / "silver")])
        self.assertEqual(run("data/live", code).stdout.split()[0], str(paths.ROOT / "data" / "live"))
        self.assertEqual(run(self.tmp.name, code).stdout.split(), [self.tmp.name, str(self.data / "silver")])

    def test_fetch_refuses_the_research_data(self):
        r = run(None, ["-m", "airalerts.live.fetch", "--once"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("research data is frozen", r.stderr)

    def test_jev_key_mode_never_puts_the_key_in_an_error(self):
        sent = []

        def urlopen(req, timeout):  # stands in for the API: records the header, then the network is down
            sent.append(req.get_header("Authorization"))
            raise OSError("no network in tests")

        with (mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": "sk-secret-1\n"}),
              mock.patch.object(jev.urllib.request, "urlopen", urlopen)):
            self.assertEqual(jev._post({"q": 1}), (599, "OSError"))  # the line end is cut, the request goes out
            os.environ["TYPESAFE_API_KEY"] = "sk-secret\n1"  # http.client would refuse it and quote the key
            with self.assertRaises(jev.JevError) as e:
                jev._post({"q": 1})
        self.assertEqual(sent, ["Bearer sk-secret-1"])
        self.assertNotIn("sk-secret", str(e.exception))

    def test_check_times_only_for_channels_without_error(self):
        tg = self.file.parent
        (tg / "bad.jsonl").write_text(self.file.read_text(encoding="utf-8"), encoding="utf-8")
        old = {"bad": "2026-10-11T00:00:00Z", "other": "2026-10-11T01:00:00Z"}
        (tg / telegram.CHECKED).write_text(json.dumps(old), encoding="utf-8")
        site, first = Site(range(81, 121)), {}

        def page(channel, before=None):  # notes the time of the first request of each channel; "bad" does not answer
            first.setdefault(channel, datetime.now(timezone.utc).strftime(fetch.TIME_FMT))
            if channel == "bad":
                raise RuntimeError("t.me is down")
            return site(channel, before)

        start = datetime.now(timezone.utc).strftime(fetch.TIME_FMT)
        with contextlib.redirect_stdout(io.StringIO()):
            code = fetch.run_once(self.data, ("bad", "chan", "gone"), page, pause=0)  # "gone" has no file: an error too
        checks = telegram.checks(tg)
        self.assertEqual(code, 1)
        self.assertEqual({k: v for k, v in checks.items() if k != "chan"}, old)  # failed channels keep their old entry
        self.assertTrue(start <= checks["chan"] <= first["chan"], (start, checks, first))  # just before the first request
        self.assertEqual(self.ids(), list(range(81, 121)))
        self.assertEqual(sorted(p.name for p in tg.iterdir()), ["_checked.json", "bad.jsonl", "chan.jsonl"])  # no temp file

    def test_check_times_move_label_end_and_data_until(self):
        tg = self.file.parent
        fetched = dict.fromkeys(threat_hourly.CHANNELS, "2026-10-11T20:15:00Z")  # fetched_at of the newest post
        fetched.update(war_monitor="2026-10-11T10:05:00Z", AerisRimor="2026-10-11T20:17:00Z", kyiv_nebo="2026-10-11T20:16:00Z")
        for c, at in fetched.items():
            row = dict(post(1), channel=c, published_at="2026-10-11T09:50:00Z", fetched_at=at)
            (tg / f"{c}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
        code = ["-c", "from airalerts.silver import alerts, threat_hourly as t; print(t.label_end(), alerts.build()[1])"]

        def ends(checks=None):  # label_end and the alerts data_until in a fresh process on this data dir
            if checks is not None:
                (tg / telegram.CHECKED).write_text(json.dumps(checks), encoding="utf-8")
            r = run(self.tmp.name, code)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.split()

        # no check file, as in the research bronze: the quiet war_monitor holds label_end, the last VA_Kyiv post ends the data
        self.assertEqual(ends(), ["2026-10-11T10:05:00Z", "2026-10-11T09:50:00Z"])
        checks = dict.fromkeys(threat_hourly.CHANNELS, "2026-10-11T20:18:00Z")
        checks["AerisRimor"] = "2026-10-11T20:10:00Z"  # older than the fetched_at of its newest post, which stays
        del checks["kyiv_nebo"]  # no entry: its fetched_at stays and is now the earliest
        self.assertEqual(ends(checks), ["2026-10-11T20:16:00Z", "2026-10-11T20:18:00Z"])
        checks["VA_Kyiv"] = "2026-10-11T09:00:00Z"  # older than the last VA_Kyiv post, which stays the end of the data
        self.assertEqual(ends(checks), ["2026-10-11T20:15:00Z", "2026-10-11T09:50:00Z"])


if __name__ == "__main__":
    unittest.main()
