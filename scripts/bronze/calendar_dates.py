#!/usr/bin/env python3
"""Bronze: symbolic dates of Russia and Ukraine (docs/PARSING.md section 5).

Writes, under data/bronze/calendar/:
  dates.csv        the 100 rows of the PARSING.md table, columns date,name,group,type,source_url,hypothesis
  dates_added.csv  high-symbolism dates that the 100 miss; every one is confirmed on a Wikipedia page fetched here
                   (the columns of dates.csv plus verified_from)
  sources/         one JSON per fetched page (plain-text extract, revid, timestamps) and manifest.jsonl

Run: python3 -I scripts/bronze/calendar_dates.py
Stdlib only. One request at a time, 2 s pause, retry on 429 and 5xx. A rerun adds only what is missing; rows that are
already in a CSV and files that are already in sources/ are never changed or deleted.
A candidate is written to dates_added.csv only if its date string stands next to the event keywords on the fetched page.
The em dash and the middle dot are kept out of every file (inside the JSON sources they are written as JSON escapes).
"""
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARSING = ROOT / "docs" / "PARSING.md"
OUT = ROOT / "data" / "bronze" / "calendar"
SRC = OUT / "sources"
COLS = ["date", "name", "group", "type", "source_url", "hypothesis"]
ADDED_COLS = COLS + ["verified_from"]
UA = "Mozilla/5.0 (X11; Linux x86_64) airalerts-research/0.1"  # browser-like, plus a project token for Wikimedia
PAUSE = 2.0  # seconds before every request: one request at a time
EM_DASH, MIDDLE_DOT = chr(0x2014), chr(0xB7)

MONTHS = {  # month number: (uk, ru, en) as written in a date
    1: ("січня", "января", "January"), 2: ("лютого", "февраля", "February"), 3: ("березня", "марта", "March"),
    4: ("квітня", "апреля", "April"), 5: ("травня", "мая", "May"), 6: ("червня", "июня", "June"),
    7: ("липня", "июля", "July"), 8: ("серпня", "августа", "August"), 9: ("вересня", "сентября", "September"),
    10: ("жовтня", "октября", "October"), 11: ("листопада", "ноября", "November"), 12: ("грудня", "декабря", "December"),
}

# Dates missing from the 100. `dates` are (month, day, year of the event) tried in order; the row gets 2026-MM-DD.
# A candidate counts only if its date string and every `near` pattern stand within 300 characters on a fetched page.
CANDIDATES = [
    dict(name="День народження Зеленського (1978)", group="UA", type="personal",
         hypothesis="День народження президента України: символічна дата, можлива демонстрація сили; не перевірено на даних",
         pages=[("uk", "Володимир Зеленський"), ("en", "Volodymyr Zelenskyy")],
         dates=[(1, 25, 1978)], near=[r"Зеленськ|Zelensk"]),
    dict(name="Визнання Росією ДНР і ЛНР (2022)", group="RF", type="anniversary",
         hypothesis="Передодень вторгнення: символічна дата для РФ, можлива демонстрація сили; не перевірено на даних",
         pages=[("en", "Russian recognition of the Donetsk People's Republic and the Luhansk People's Republic"),
                ("uk", "Визнання Росією ДНР і ЛНР")],
         search=[("en", "Russia recognition Donetsk Luhansk People's Republics 21 February 2022"),
                 ("ru", "признание ДНР и ЛНР Россией 21 февраля 2022")],
         dates=[(2, 21, 2022)],
         near=[r"recogni|визнан|признан", r"Donetsk|Luhansk|Донецьк|Луганськ|ДНР|ЛНР|Донецк|Луганск"]),
    dict(name="Звільнення Київщини від російських військ (2022)", group="UA", type="anniversary",
         hypothesis="Перемога під Києвом: символічна дата для України, можлива відповідь РФ; не перевірено на даних",
         pages=[("uk", "Битва за Київ (2022)"), ("en", "Battle of Kyiv (2022)")],
         search=[("uk", "звільнення Київщини квітень 2022"), ("en", "Kyiv offensive 2022 withdrawal Kyiv Oblast liberated")],
         dates=[(4, 2, 2022), (3, 31, 2022)], no_year=True,
         near=[r"Київськ\w* област|Київщин|Kyiv Oblast|Kyiv region|Kyiv direction|Київськ\w* напрям",
               r"звільн|liberat|withdr|відступ|вийшл|вивел|вивід"]),
    dict(name="Виявлення масових убивств у Бучі (2022)", group="UA", type="anniversary",
         hypothesis="Символ воєнних злочинів РФ: пам'ятна дата для України, можлива інформаційна реакція; не перевірено на даних",
         pages=[("en", "Bucha massacre"), ("uk", "Різанина в Бучі")],
         search=[("uk", "Бучанська різанина квітень 2022")],
         dates=[(4, 2, 2022), (4, 3, 2022), (4, 1, 2022)],
         near=[r"Буч|Bucha", r"тіл|вбив|убив|massacre|bodies|corpses|killing|civilian"]),
    dict(name="Затоплення крейсера «Москва» (2022)", group="UA", type="anniversary",
         hypothesis="Втрата флагмана Чорноморського флоту: символічна дата для РФ і України; не перевірено на даних",
         pages=[("en", "Russian cruiser Moskva"), ("uk", "Москва (крейсер)")],
         search=[("uk", "крейсер Москва затоплення 14 квітня 2022")],
         dates=[(4, 14, 2022)], near=[r"Moskva|Москва", r"sank|sunk|sinking|затон|потон|затоп|sink"]),
    dict(name="Інавгурація Зеленського (2019)", group="UA", type="anniversary",
         hypothesis="Початок президентства Зеленського: символічна дата для України; не перевірено на даних",
         pages=[("uk", "Інавгурація Володимира Зеленського"), ("en", "Inauguration of Volodymyr Zelenskyy")],
         search=[("uk", "інавгурація Зеленського 20 травня 2019")],
         dates=[(5, 20, 2019)], near=[r"inaugurat|інавгурац|sworn|oath|присяг"]),
    dict(name="Початок Другої світової війни (1939)", group="RF", type="anniversary",
         hypothesis="Початок світової війни: символічна дата в історичній політиці РФ і України; не перевірено на даних",
         pages=[("uk", "Друга світова війна"), ("en", "World War II")],
         dates=[(9, 1, 1939)], near=[r"світов|World War|війн"]),
    dict(name="Оголошення часткової мобілізації в РФ (2022)", group="RF", type="anniversary",
         hypothesis="Звернення Путіна про мобілізацію: символічна дата для РФ; не перевірено на даних",
         pages=[("ru", "Частичная мобилизация в России (2022)"), ("en", "2022 Russian mobilization"),
                ("uk", "Часткова мобілізація в Росії")],
         search=[("en", "partial mobilization Russia 21 September 2022")],
         dates=[(9, 21, 2022)], near=[r"мобилиз|мобіліз|mobili[sz]"]),
    dict(name="Звільнення Херсона (2022)", group="UA", type="anniversary",
         hypothesis="Звільнення єдиного обласного центру, захопленого РФ: символічна дата для України; не перевірено на даних",
         pages=[("en", "Kherson counteroffensive"), ("uk", "Звільнення Херсона")],
         search=[("en", "Kherson liberation 11 November 2022"), ("uk", "звільнення Херсона 11 листопада 2022")],
         dates=[(11, 11, 2022)],
         near=[r"Kherson|Херсон", r"liberat|entered|withdr|retreat|звільн|відступ|вихід|ввійш|увійш|вступ"]),
]


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_table():
    """The 100 rows of the table inside <details> of PARSING.md section 5."""
    lines = PARSING.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("<details><summary>Таблиця дат"))
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("</details>"))
    rows = []
    for line in lines[start:end]:
        if not line.startswith("| 2026-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            raise SystemExit(f"table row with {len(cells)} cells: {line[:80]}")
        rows.append(dict(zip(COLS, cells)))
    if len(rows) != 100:
        raise SystemExit(f"expected 100 rows in PARSING.md section 5, found {len(rows)}")
    return rows


def read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sync_csv(path, cols, rows):
    """Append the rows whose key (date, group, name) is not in the file yet. Existing rows are never changed."""
    exists = path.exists() and path.stat().st_size > 0
    have = {(x["date"], x["group"], x["name"]) for x in read_csv(path)}
    new = [x for x in rows if (x["date"], x["group"], x["name"]) not in have]
    if new or not exists:
        with path.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            if not exists:
                w.writeheader()
            w.writerows(new)
    return len(new)


def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        time.sleep(PAUSE)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                ra = e.headers.get("Retry-After", "")
                time.sleep(int(ra) if ra.isdigit() else min(60, 2 ** (attempt + 1)))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(min(60, 2 ** (attempt + 1)))
    raise SystemExit(f"gave up on {url}")


def safe_json(obj):
    """JSON text in which the em dash and the middle dot are written as JSON escapes; json.loads gives the original back."""
    bs = chr(92)
    return json.dumps(obj, ensure_ascii=False).replace(EM_DASH, bs + "u2014").replace(MIDDLE_DOT, bs + "u00b7")


def fetch_page(lang, title):
    """Plain-text extract and revision of one article, saved once under sources/. None if the article does not exist."""
    slug = re.sub(r"[^\w()-]+", "_", title).strip("_")
    path = SRC / f"{lang}.wikipedia.org__{slug}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    d = api_get(lang, {"action": "query", "prop": "extracts|revisions", "explaintext": 1, "exsectionformat": "plain",
                       "rvprop": "ids|timestamp", "titles": title, "redirects": 1, "format": "json", "formatversion": 2})
    p = d["query"]["pages"][0]
    if p.get("missing") or p.get("invalid") or "revisions" not in p:
        print(f"  no page {lang}:{title}")
        return None
    rec = {"key": path.stem, "file": path.name, "lang": lang, "requested_title": title, "title": p["title"],
           "url": f"https://{lang}.wikipedia.org/wiki/" + p["title"].replace(" ", "_"),
           "revid": p["revisions"][0]["revid"], "rev_timestamp": p["revisions"][0]["timestamp"],
           "fetched_at": now_utc(), "bytes": len(p.get("extract", "").encode("utf-8")), "extract": p.get("extract", "")}
    SRC.mkdir(parents=True, exist_ok=True)
    path.write_text(safe_json(rec), encoding="utf-8")
    meta = {k: rec[k] for k in ("key", "url", "revid", "rev_timestamp", "fetched_at", "bytes")}
    with (SRC / "manifest.jsonl").open("a", encoding="utf-8") as f:
        f.write(safe_json(meta) + "\n")
    return rec


def search_titles(lang, query):
    d = api_get(lang, {"action": "query", "list": "search", "srsearch": query, "srlimit": 3,
                       "format": "json", "formatversion": 2})
    return [x["title"] for x in d["query"]["search"]]


def date_re(month, day, year=None):
    """Day and month name (uk, ru or en), then the year unless it is None (narrative pages that leave the year out)."""
    return rf"(?<!\d){day} (?:{'|'.join(MONTHS[month])})" + (rf" {year}" if year else "")


def find(text, rx, near):
    """First place where date regex rx has every `near` pattern within 300 characters; returns a short quote."""
    for m in re.finditer(rx, text):
        win = text[max(0, m.start() - 300):m.end() + 300]
        if all(re.search(p, win, re.I) for p in near):
            quote = " ".join(text[max(0, m.start() - 80):m.end() + 100].split())
            return quote.replace(EM_DASH, "-").replace(MIDDLE_DOT, ".").replace('"', "'")
    return None


def confirm(c):
    """Fetch the candidate's pages in order; return (record, (month, day), quote) of the first that confirms a date."""
    tried = set()

    def pages():
        yield from c["pages"]
        for lang, q in c.get("search", []):
            yield from ((lang, t) for t in search_titles(lang, q))

    for lang, title in pages():
        if (lang, title) in tried:
            continue
        tried.add((lang, title))
        rec = fetch_page(lang, title)
        if rec is None:
            continue
        for month, day, year in c["dates"]:
            quote = find(rec["extract"], date_re(month, day, None if c.get("no_year") else year), c["near"])
            print(f"  {lang}:{rec['title']} rev {rec['revid']} {year}-{month:02d}-{day:02d}: {'CONFIRMED' if quote else 'not found'}")
            if quote:
                return rec, (month, day), quote
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    run = now_utc()
    table = parse_table()
    n = sync_csv(OUT / "dates.csv", COLS, table)
    print(f"dates.csv: {len(table)} rows from PARSING.md, {n} new")

    have = {(x["group"], x["name"]) for x in read_csv(OUT / "dates_added.csv")}
    added, unverified = [], []
    for c in CANDIDATES:
        if (c["group"], c["name"]) in have:
            print(f"already in dates_added.csv: {c['name']}")
            continue
        print(f"candidate: {c['name']}")
        hit = confirm(c)
        if hit is None:
            unverified.append(c["name"])
            continue
        rec, (month, day), quote = hit
        added.append({"date": f"2026-{month:02d}-{day:02d}", "name": c["name"], "group": c["group"], "type": c["type"],
                      "source_url": rec["url"], "hypothesis": c["hypothesis"],
                      "verified_from": f'sources/{rec["file"]} rev {rec["revid"]} {rec["rev_timestamp"]}: "{quote}"'})
    n_added = sync_csv(OUT / "dates_added.csv", ADDED_COLS, added)

    all_added = read_csv(OUT / "dates_added.csv")
    metas = [json.loads(l) for l in (SRC / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l]
    print(f"dates_added.csv: {len(all_added)} rows, {n_added} new this run; unverified: {unverified or 'none'}")
    print(f"MANIFEST calendar/dates.csv | {run} | {len(table)} | {min(r['date'] for r in table)} | {max(r['date'] for r in table)}")
    if all_added:
        print(f"MANIFEST calendar/dates_added.csv | {run} | {len(all_added)} | {min(r['date'] for r in all_added)} | {max(r['date'] for r in all_added)}")
    if metas:
        print(f"MANIFEST calendar/sources (Wikipedia pages) | {run} | {len(metas)} | {min(m['fetched_at'] for m in metas)} | {max(m['fetched_at'] for m in metas)}")
    sys.exit(1 if unverified else 0)


if __name__ == "__main__":
    main()
