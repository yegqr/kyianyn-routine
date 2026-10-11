#!/usr/bin/env python3
"""Bronze fetcher for dronestrikemap.com: strikes on Russia and Ukraine from its open JSON API (stdlib only).

Run: python3 -I scripts/bronze/dronestrikemap_fetch.py

Every run is one snapshot: data/bronze/strikes_rf/dronestrikemap/<fetched_at YYYYMMDDTHHMMSSZ>/ with the raw answers
  meta.json      /api/meta: every day the site has, first and last day
  strikes.json   /api/strikes: the whole strike record, one point per (day, place) with summary, confidence, sources count
  timeline.json  /api/timeline: per day and country (RU, UA): launched min/max and intercepted, by weapon, with the basis
  events.json    /api/events: truces and similar periods
  sources.json   /api/sources: the feeds the site reads
  days/<d>.json  /api/day/<d> for every day from FETCH_FROM: strikes with weapons and the articles behind them
and fetch_log.jsonl (url, status, bytes, sha256, fetched_at per request). Nothing is ever overwritten: the site has no
revision history, so the snapshots are how we know what it said at a given time. The answers carry dates only, no time
of day and no publication time (silver has to set available_at with a lag).
Polite: one request at a time, 1 s pause, browser User-Agent, retry with backoff on 429, 5xx and network errors.
"""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "bronze" / "strikes_rf" / "dronestrikemap"
FETCH_FROM = "2026-04-16"  # Kyiv day of FETCH_FROM in src/airalerts/paths.py (2026-04-16T21:00:00Z): 14-day windows full at T0
BASE = "https://dronestrikemap.com/api/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
           "Accept": "application/json"}
PAUSE = 1.0


def now():
    return datetime.now(timezone.utc)


def get(path, log, tries=6):
    url = BASE + path
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                body, status = r.read(), r.status
        except urllib.error.HTTPError as e:
            body, status = b"", e.code
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            body, status = b"", f"net: {e}"
        log.write(json.dumps({"url": url, "status": status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                              "fetched_at": now().strftime("%Y-%m-%dT%H:%M:%SZ")}) + "\n")
        log.flush()
        time.sleep(PAUSE)
        if status == 200:
            json.loads(body)  # a broken answer must stop the run, not land in bronze
            return body
        if status in (429,) or not isinstance(status, int) or status >= 500:
            time.sleep(min(60, 2 ** (i + 1)))
            continue
        raise SystemExit(f"{url}: HTTP {status}")
    raise SystemExit(f"{url}: gave up after {tries} tries")


def main():
    snap = OUT / now().strftime("%Y%m%dT%H%M%SZ")
    (snap / "days").mkdir(parents=True)
    with open(snap / "fetch_log.jsonl", "w") as log:
        meta = get("meta", log)
        (snap / "meta.json").write_bytes(meta)
        for name in ("strikes", "timeline", "events", "sources"):
            (snap / f"{name}.json").write_bytes(get(name, log))
        days = [d for d in json.loads(meta)["days"] if d >= FETCH_FROM]
        for i, d in enumerate(days, 1):
            (snap / "days" / f"{d}.json").write_bytes(get(f"day/{d}", log))
            if i % 20 == 0:
                print(f"days {i}/{len(days)}", flush=True)
    m = json.loads(meta)
    n = len(json.loads((snap / "strikes.json").read_bytes())["strikes"])
    print(f"{snap}: meta {m['min']}..{m['max']} ({len(m['days'])} days); strikes {n}; day files {len(days)} ({days[0]}..{days[-1]})")


if __name__ == "__main__":
    sys.exit(main())
