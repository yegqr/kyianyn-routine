#!/usr/bin/env python3
"""Bronze fetcher for the Office of the President of Ukraine site (president.gov.ua): news (stdlib only).

Run: python3 -I scripts/bronze/president_fetch.py        exit 0 never; 3 = blocked, 4 = reachable (see below)

Status 2026-10-10: the site answers HTTP 403 "Access Denied" (CDN edge) to this host. The script asks for /news and
/en/news with a browser User-Agent and Accept-Language, twice each with a pause, and prints status, response
headers and the start of the body as evidence. If no answer is 200 it stops and writes nothing to bronze (exit 3).
There is no way around a block here: no proxies, no other hosts. The official Telegram channel OP_UA is downloaded
by tg_backfill.sh instead.
If a page does answer 200, its raw HTML is saved under data/bronze/calendar/president/ (name and UTC time in the
file name) and the script exits with 4: the item parser (item_id, url, title, published_at into president_news.jsonl,
paging back to FETCH_FROM) is not written, because the real markup has never been seen from this host.
"""
import http.client
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "bronze" / "calendar" / "president"
PAGES = {"news_uk": "https://www.president.gov.ua/news", "news_en": "https://www.president.gov.ua/en/news"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
}


def ask(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()
    except (OSError, http.client.HTTPException) as e:
        return 0, {}, repr(e).encode()


def main():
    saved = 0
    for name, url in PAGES.items():
        for attempt in (1, 2):
            status, headers, body = ask(url)
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"{stamp} {url} attempt {attempt}: HTTP {status}", flush=True)
            if status == 200:
                OUT.mkdir(parents=True, exist_ok=True)
                (OUT / f"{name}_{stamp.replace(':', '')}.html").write_bytes(body)
                saved += 1
                break
            for k, v in headers.items():
                print(f"  {k}: {v}")
            print("  body:", body[:300].decode("utf-8", "replace").replace("\n", " "), flush=True)
            if attempt == 1:
                time.sleep(8)
        time.sleep(2)
    if saved:
        print(f"REACHABLE: {saved} raw page(s) saved; no item parser yet (markup unknown), nothing written to president_news.jsonl")
        return 4
    print("BLOCKED: no page answered 200; nothing written to bronze")
    return 3


if __name__ == "__main__":
    sys.exit(main())
