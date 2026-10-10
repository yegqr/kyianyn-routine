#!/usr/bin/env python3
"""Bronze fetcher for en.kremlin.ru: president news and the trips Atom feed (stdlib only).

Run: python3 -I scripts/bronze/kremlin_fetch.py [news] [trips]      (no argument = both)

news  -> data/bronze/calendar/kremlin_news.jsonl
         Walks /events/president/news, /page/2, ... (newest first) and appends every item whose item_id is not in
         the file yet, until a page holds an item older than FETCH_FROM (that whole page is kept). A rerun starts at
         page 1 and stops at the first page with nothing new once the file reaches back to FETCH_FROM, so it adds
         only what is missing; an interrupted run continues where the file ends.
trips -> data/bronze/calendar/kremlin_trips.jsonl
         First page of the Atom feed (the 20 newest trips). A row is added when (item_id, updated_at) is new.

Times: the site and the feed give Moscow wall time (UTC+3, no daylight saving). The +04:00 offset in the Atom feed
is wrong. published_at and updated_at are UTC = wall time minus 3 h; published_local_msk keeps the wall time.
Titles: tags removed, entities decoded, whitespace (also no-break spaces) collapsed to one space.
Polite: one request at a time, 1.5 s pause, browser User-Agent, retry with backoff on 429, 5xx and network errors.
"""
import html
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "bronze" / "calendar"
FETCH_FROM = "2026-04-23T21:00:00Z"  # T0 minus 7 days: political features look forward, so the 14-day FETCH_FROM of src/airalerts/paths.py is not needed here
BASE = "http://en.kremlin.ru"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
PAUSE = 1.5
MAX_PAGES = 150
Z = "%Y-%m-%dT%H:%M:%SZ"
MSK = timedelta(hours=3)
MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}
ITEM = re.compile(
    r'<a href="/events/president/news/(\d+)" rel="bookmark" itemprop="url">'
    r'<span class="entry-title p-name"[^>]*>(.*?)</span>\s*'
    r'<span class="hentry__meta">\s*'
    r'<time class="published dt-published" datetime="(\d{4}-\d{2}-\d{2})"[^>]*>([^<]*)</time>', re.S)


def now():
    return datetime.now(timezone.utc).strftime(Z)


def dumps(obj):
    # one JSON line; the middle dot and the em dash are written as escapes (this repo keeps them out of files)
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            .replace("\u2014", "\\u2014").replace("\u00b7", "\\u00b7"))


def get(url, tries=6):
    delay = 5
    for attempt in range(1, tries + 1):
        wait = delay
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            ra = e.headers.get("Retry-After", "")
            wait = min(int(ra) + 1, 300) if ra.isdigit() else delay
            why = f"HTTP {e.code}"
        except (OSError, http.client.HTTPException) as e:
            why = repr(e)
        print(f"  retry {attempt}/{tries} {url}: {why}; sleep {wait}s", file=sys.stderr, flush=True)
        time.sleep(wait)
        delay = min(delay * 2, 120)
    raise RuntimeError(f"giving up: {url}")


def read_jsonl(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path, rows):
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write("".join(dumps(r) + "\n" for r in rows))


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def parse_news(page_html, fetched):
    rows = []
    for item_id, title, day, label in ITEM.findall(page_html):
        m = re.search(r"([A-Z][a-z]+) (\d{1,2}), (\d{4}), (\d{1,2}):(\d{2})", label)
        if not m or m.group(1) not in MONTHS:
            raise ValueError(f"item {item_id}: cannot read the time from {label!r}")
        wall = datetime(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)), int(m.group(4)), int(m.group(5)))
        if wall.date().isoformat() != day:
            print(f"  warning: item {item_id}: date attribute {day} differs from text {label!r}", file=sys.stderr)
        rows.append({
            "source": "kremlin_news", "item_id": int(item_id), "url": f"{BASE}/events/president/news/{item_id}",
            "title": clean(title), "published_local_msk": wall.isoformat(),
            "published_at": (wall - MSK).strftime(Z), "fetched_at": fetched})
    return rows


def run_news():
    path = OUT / "kremlin_news.jsonl"
    have = read_jsonl(path)
    known = {r["item_id"] for r in have}
    complete = any(r["published_at"] < FETCH_FROM for r in have)
    added = pages = 0
    for page in range(1, MAX_PAGES + 1):
        url = BASE + "/events/president/news" + (f"/page/{page}" if page > 1 else "")
        text = get(url).decode("utf-8", "replace")
        rows = parse_news(text, now())
        pages += 1
        if not rows:
            if page == 1:
                raise RuntimeError("page 1 has no items: markup changed?")
            print(f"  page {page}: no items, stop", flush=True)
            break
        new = [r for r in rows if r["item_id"] not in known]
        append_jsonl(path, new)
        known.update(r["item_id"] for r in new)
        added += len(new)
        oldest = min(r["published_at"] for r in rows)
        hrefs = len(set(re.findall(r'href="/events/president/news/(\d+)"', text)))
        print(f"  page {page}: {len(rows)} items ({hrefs} hrefs), {len(new)} new, oldest {oldest}", flush=True)
        if oldest < FETCH_FROM or (complete and not new):
            break
        time.sleep(PAUSE)
    else:
        raise RuntimeError(f"no stop after {MAX_PAGES} pages")
    rows = read_jsonl(path)
    print(f"news: {pages} pages, {added} added, file has {len(rows)} rows, "
          f"{min(r['published_at'] for r in rows)} .. {max(r['published_at'] for r in rows)}", flush=True)


def wall_pair(stamp):
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", stamp or "")
    if not m:
        raise ValueError(f"bad feed time {stamp!r}")
    wall = datetime.fromisoformat(m.group(1))
    return wall.isoformat(), (wall - MSK).strftime(Z)


def run_trips():
    path = OUT / "kremlin_trips.jsonl"
    seen = {(r["item_id"], r["updated_at"]) for r in read_jsonl(path)}
    body = get(BASE + "/events/president/trips/feed")
    fetched = now()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = ET.fromstring(body).findall("a:entry", ns)
    new = []
    for e in entries:
        eid = e.findtext("a:id", "", ns)
        pub, upd = e.findtext("a:published", "", ns), e.findtext("a:updated", "", ns)
        (pub_local, pub_utc), (upd_local, upd_utc) = wall_pair(pub), wall_pair(upd)
        item_id = int(eid.rstrip("/").rsplit("/", 1)[-1])
        if (item_id, upd_utc) in seen:
            continue
        url = next((l.get("href") for l in e.findall("a:link", ns) if l.get("rel", "alternate") == "alternate"), eid)
        new.append({
            "source": "kremlin_trips", "item_id": item_id, "url": url, "title": clean(e.findtext("a:title", "", ns)),
            "published_local_msk": pub_local, "published_at": pub_utc,
            "updated_local_msk": upd_local, "updated_at": upd_utc,
            "published_raw": pub, "updated_raw": upd, "fetched_at": fetched})
    append_jsonl(path, new)
    rows = read_jsonl(path)
    print(f"trips: feed has {len(entries)} entries, {len(new)} added, file has {len(rows)} rows, "
          f"{min(r['published_at'] for r in rows)} .. {max(r['published_at'] for r in rows)}", flush=True)


if __name__ == "__main__":
    which = sys.argv[1:] or ["trips", "news"]
    if "trips" in which:
        run_trips()
        time.sleep(PAUSE)
    if "news" in which:
        run_news()
