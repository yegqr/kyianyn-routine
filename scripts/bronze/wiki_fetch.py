#!/usr/bin/env python3
"""Bronze fetcher for Wikipedia (MediaWiki API, stdlib only): the English event pages of the political calendar.

Run: python3 -I scripts/bronze/wiki_fetch.py

en -> data/bronze/calendar/wiki/<title with _>.json, one file per page (en dash in the name written as -):
      {"title", "lang", "base": last revision before 2026-04-01, "revisions": [API pages with every revision since
      2026-04-01, with wikitext], "snapshots": [current page, redirects resolved]}. Each part keeps request URL,
      fetched_at and the API response. A rerun asks for the current revision id of all pages in one request; a page
      with nothing new is left untouched, a page with new revisions gets them appended to "revisions" plus a new
      snapshot appended to "snapshots".
Files are written whole through a temporary file and a rename; the middle dot and the em dash are written as JSON
escapes. Polite: own User-Agent, one request at a time, 1.5 s pause, Retry-After respected on 429.
"""
import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "data" / "bronze" / "calendar" / "wiki"
EN_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "airalers-parser/0.1 (non-commercial research on public pages; one request at a time)",
           "Accept": "application/json"}
SINCE, BEFORE = "2026-04-01T00:00:00Z", "2026-03-31T23:59:59Z"
PAUSE = 1.5
Z = "%Y-%m-%dT%H:%M:%SZ"
TITLES = [
    "List of international presidential trips made by Vladimir Putin",
    "List of international presidential trips made by Volodymyr Zelenskyy",
    "List of heads of state and government who have visited Ukraine during the Russo-Ukrainian war (2022\u2013present)",
    "List of European Council meetings",
    "Ukraine Defense Contact Group",
    "52nd G7 summit",
    "2026 Ankara NATO summit",
    "Eastern Economic Forum",
]


def now():
    return datetime.now(timezone.utc).strftime(Z)


def dumps(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            .replace("\u2014", "\\u2014").replace("\u00b7", "\\u00b7"))


def get(url, tries=6):
    delay = 5
    for attempt in range(1, tries + 1):
        wait = delay
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            ra = e.headers.get("Retry-After", "")
            wait = min(int(ra) + 1, 300) if ra.isdigit() else delay
            why = f"HTTP {e.code}"
        except (OSError, http.client.HTTPException) as e:
            why = repr(e)
        print(f"  retry {attempt}/{tries}: {why}; sleep {wait}s", file=sys.stderr, flush=True)
        time.sleep(wait)
        delay = min(delay * 2, 120)
    raise RuntimeError(f"giving up: {url}")


def call(api, params):
    url = api + "?" + urllib.parse.urlencode(params)
    data = json.loads(get(url))
    fetched = now()
    time.sleep(PAUSE)
    if "error" in data:
        raise RuntimeError(f"API error {data['error']} for {url}")
    return url, data, fetched


def write_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def revisions_of(response):
    return [rv for p in response.get("query", {}).get("pages", []) for rv in p.get("revisions", [])]


def one_query(api, title, **extra):
    params = dict(action="query", prop="revisions", titles=title, rvprop="ids|timestamp|content", rvslots="main",
                  format="json", formatversion=2)
    params.update(extra)
    url, data, fetched = call(api, params)
    return {"request": url, "fetched_at": fetched, "response": data}


def all_pages(api, title, **extra):
    params = dict(action="query", prop="revisions", titles=title, rvprop="ids|timestamp|content", rvslots="main",
                  format="json", formatversion=2)
    params.update(extra)
    out, cont = [], {}
    while True:
        url, data, fetched = call(api, {**params, **cont})
        out.append({"request": url, "fetched_at": fetched, "response": data})
        if "continue" not in data:
            return out
        cont = data["continue"]


def known_revisions(doc):
    out = {}
    for entry in ([doc["base"]] if doc.get("base") else []) + doc["revisions"]:
        for rv in revisions_of(entry["response"]):
            out[rv["revid"]] = rv["timestamp"]
    return out


def run_en():
    WIKI.mkdir(parents=True, exist_ok=True)
    paths = {t: WIKI / (t.replace(" ", "_").replace("\u2013", "-") + ".json") for t in TITLES}
    heads = {}
    if any(p.exists() for p in paths.values()):
        _, info, _ = call(EN_API, dict(action="query", titles="|".join(TITLES), prop="info", format="json", formatversion=2))
        heads = {p["title"]: p.get("lastrevid") for p in info["query"]["pages"]}
    for title in TITLES:
        path = paths[title]
        if path.exists():
            doc = json.loads(path.read_text(encoding="utf-8"))
            seen = known_revisions(doc)
            if heads.get(title) in seen:
                print(f"{title}: up to date (head {heads.get(title)})", flush=True)
                continue
            doc["revisions"] += all_pages(EN_API, title, rvdir="newer", rvlimit=50, rvstart=max(seen.values()))
        else:
            doc = {"title": title, "lang": "en",
                   "base": one_query(EN_API, title, rvdir="older", rvlimit=1, rvstart=BEFORE),
                   "revisions": all_pages(EN_API, title, rvdir="newer", rvlimit=50, rvstart=SINCE),
                   "snapshots": []}
        doc["snapshots"].append(one_query(EN_API, title, redirects=1))
        write_atomic(path, dumps(doc))
        since = {rv["revid"] for e in doc["revisions"] for rv in revisions_of(e["response"])}
        base = revisions_of(doc["base"]["response"])
        snap = revisions_of(doc["snapshots"][-1]["response"])
        print(f"{title}: {len(since)} revisions since {SINCE[:10]}, base {base[0]['revid'] if base else None}, "
              f"snapshot {snap[0]['revid'] if snap else None}, file {path.stat().st_size} bytes", flush=True)


if __name__ == "__main__":
    run_en()
