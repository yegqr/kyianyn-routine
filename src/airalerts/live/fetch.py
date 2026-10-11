"""Live Telegram fetch: append the new posts of the live channels to $AIRALERTS_DATA/bronze/telegram/<channel>.jsonl.
Usage: AIRALERTS_DATA=data/live .venv/bin/python -I -m airalerts.live.fetch [--once]
  --once: one pass, then exit; without it a pass every 5 minutes. The dir is made by airalerts.live.datadir init.
CHANNELS come from the code: the 7 Kyiv channels of silver/threat_hourly.py, the 6 of silver/signals.py and VA_Kyiv of
silver/alerts.py (10 different channels), plus UkraineAlarmSignal (eTryvoga): silver/alerts.py takes from it the start of a
VA_Kyiv alert end without a start. That feed is read back only to 3 h before the newest VA_Kyiv post known before the pass,
as scripts/bronze/etryvoga_patch.py does for an end, never back to FETCH_FROM.
Pages come from get() and parse() of scripts/bronze/tg_fetch.py, one request at a time, 1.5 s apart. Only posts newer than
the newest post_id of the file are appended, so no post_id is written twice. DATA/live.lock (flock) keeps two passes apart:
a second run exits at once with code 0. Each pass adds one JSON line to DATA/fetch_log.jsonl (not data/bronze/MANIFEST.md).
A channel fetched without error gets its check time, the UTC time just before its first page request of the pass, in
DATA/bronze/telegram/_checked.json ({channel: ISO UTC}, read by telegram.checks); a failed channel keeps its old entry.
label_end of silver/threat_hourly.py and data_until of silver/alerts.py take it, so a channel without new posts does not
hold the data end back."""
import argparse
import fcntl
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from .. import telegram
from ..paths import DATA, FETCH_FROM, ROOT
from ..silver import signals, threat_hourly

_spec = importlib.util.spec_from_file_location("tg_fetch", ROOT / "scripts" / "bronze" / "tg_fetch.py")
tg_fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tg_fetch)

FEED = "UkraineAlarmSignal"
CHANNELS = tuple(sorted({*threat_hourly.CHANNELS, *signals.CHANNELS, "VA_Kyiv", FEED}))
FEED_BACK = timedelta(hours=3)
PAUSE = 1.5  # seconds between two requests
EVERY = 300  # seconds between passes without --once
TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


def tg_page(channel, before=None):
    """The posts of one t.me/s page in bronze format: the newest page, or the one before post_id `before`."""
    return list(tg_fetch.parse(tg_fetch.get(channel, before)))


def known(path):
    """post_id -> published_at of a channel file; a cut last line is skipped."""
    have = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                have.setdefault(r["post_id"], r["published_at"])
    return have


def newer(channel, top, since, page=tg_page, pause=PAUSE):
    """Posts with post_id > top and published_at >= since, sorted by post_id: pages back from the newest one until a page
    reaches `top` or `since`. Returns (posts, pages)."""
    found, before, pages = {}, None, 0
    while True:
        if pages:
            time.sleep(pause)
        posts = page(channel, before)
        pages += 1
        if not posts:
            if before is None:
                raise RuntimeError("0 posts on the newest page (no such public channel or the markup changed)")
            break
        for p in posts:
            if p["post_id"] > top and p["published_at"] >= since:
                found.setdefault(p["post_id"], p)
        low = min(p["post_id"] for p in posts)
        if low <= top or min(p["published_at"] for p in posts) < since or (before and low >= before):
            break
        before = low
    return [found[k] for k in sorted(found)], pages


def lock(data):
    """DATA/live.lock taken without waiting: the open file (closing it frees the lock), or None if another pass has it."""
    f = open(data / "live.lock", "a")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def record_check(tg, channel, at):
    """Set the check time of `channel` in tg/_checked.json, keeping the other entries, atomically (a temporary file, then
    os.replace): a reader sees the old file or the new one, never a part."""
    checks = telegram.checks(tg)
    checks[channel] = at
    tmp = tg / f"{telegram.CHECKED}.tmp"
    tmp.write_text(json.dumps(checks, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, tg / telegram.CHECKED)


def run_once(data=DATA, channels=CHANNELS, page=tg_page, pause=PAUSE):
    """One pass: a line per channel (new posts, newest published_at, seconds). Returns the exit code."""
    held = lock(data)
    if held is None:
        print(f"another fetch is running ({data / 'live.lock'} is locked): nothing fetched")
        return 0
    with held:
        tg, t0 = data / "bronze" / "telegram", time.time()
        have = {ch: known(tg / f"{ch}.jsonl") for ch in channels}
        va = max(have.get("VA_Kyiv", {}).values(), default=None)
        log = {"at": datetime.now(timezone.utc).strftime(TIME_FMT), "new": {}, "newest": {}, "errors": {}}
        for i, ch in enumerate(channels):
            start = time.time()
            if not have[ch]:
                log["errors"][ch] = f"no posts in {tg / ch}.jsonl: run python -m airalerts.live.datadir init first"
                print(f"{ch:20} ERROR {log['errors'][ch]}")
                continue
            since = FETCH_FROM
            if ch == FEED and va:
                since = (datetime.strptime(va, TIME_FMT) - FEED_BACK).strftime(TIME_FMT)
            if i:
                time.sleep(pause)
            checked = datetime.now(timezone.utc).strftime(TIME_FMT)  # just before the first page request of the channel
            try:
                rows, _ = newer(ch, max(have[ch]), since, page, pause)
            except (Exception, SystemExit) as e:  # tg_fetch.get() exits after 5 failed tries; the other channels go on
                log["errors"][ch] = str(e)[:300]
                print(f"{ch:20} ERROR {log['errors'][ch]}")
                continue
            if rows:
                with open(tg / f"{ch}.jsonl", "a", encoding="utf-8") as f:
                    f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            record_check(tg, ch, checked)  # after the append, so the file is complete up to `checked`
            newest = max([*have[ch].values(), *(r["published_at"] for r in rows)])
            log["new"][ch], log["newest"][ch] = len(rows), newest
            print(f"{ch:20} new {len(rows):4}  newest {newest}  {time.time() - start:5.1f} s", flush=True)
        log["seconds"] = round(time.time() - t0, 1)
        with open(data / "fetch_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
        print(f"{sum(log['new'].values())} new posts in {log['seconds']} s"
              + (f", {len(log['errors'])} channels failed" if log["errors"] else ""), flush=True)
    return 1 if log["errors"] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m airalerts.live.fetch", description="Append the new posts of the live channels.")
    ap.add_argument("--once", action="store_true", help="one pass, then exit (default: a pass every 5 minutes)")
    a = ap.parse_args(argv)
    if DATA.resolve() == (ROOT / "data").resolve():
        sys.exit("AIRALERTS_DATA is not set and the research data is frozen: run with AIRALERTS_DATA=data/live "
                 "(made by python -m airalerts.live.datadir init data/live)")
    if not (DATA / "bronze" / "telegram").is_dir():
        sys.exit(f"no {DATA / 'bronze' / 'telegram'}: run python -m airalerts.live.datadir init first")
    while True:
        code = run_once()
        if a.once:
            return code
        time.sleep(EVERY - time.time() % EVERY)


if __name__ == "__main__":
    sys.exit(main())
