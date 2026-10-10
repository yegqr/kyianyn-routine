"""Silver rf_strikes: Ukrainian strikes on Russia. Three tables from one module.

rf_mod_reports    one row per air-defence report of the Russian MoD (@mod_russia): drones shot down, regions, Moscow.
rf_strike_events  one row per candidate post (General Staff hits, Moscow mayor, Rosaviatsia, big MoD reports) with an
                  importance 0..5 scored by Jev; the Jev state is the post text with every date and year removed.
rf_energy_hits    rows of the ukwiki table of attacks on Russian targets, with the time each row first appeared.
Gold: features(con, t_table). Documentation: docs/data/silver/rf_strikes.md

Run (from the project root):
  .venv/bin/python -I -m airalerts.silver.rf_strikes                      build the three tables (Jev answers are cached)
  .venv/bin/python -I -m airalerts.silver.rf_strikes checks               first and last post per channel, counts straight from bronze, no Jev
  .venv/bin/python -I -m airalerts.silver.rf_strikes score-sample --n 60  anchors and a sample scored by Jev, no tables written
  .venv/bin/python -I -m airalerts.silver.rf_strikes report --out DIR     anchors, top 20 and 10 low events from the table
  .venv/bin/python -I -m airalerts.silver.rf_strikes features-check       hourly features, nulls, direct computation, ASOF test
  .venv/bin/python -I -m airalerts.silver.rf_strikes states-check         strip_dates cases and dates left in the Jev states, no Jev
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect, register_layers
from ..jev import MODEL, ask_many
from ..paths import BRONZE, FETCH_FROM, SILVER, T0
from ..telegram import load

MOD, EVENTS, HITS = "rf_mod_reports", "rf_strike_events", "rf_energy_hits"
PROMPT_VERSION = "rf-imp-v5"                # v5 = the v4 levels, state without numeric dates (see strip_dates)
WORKERS = 6                       # Jev workers (the limit is 8)
CAP_HOURS = 336.0                 # hours_since_rf_imp4 is capped here (14 days)
IMP_HIGH = 4                      # importance that counts for hours_since_rf_imp4
BIG_WAVE = 100                    # a MoD report with at least this many drones is a candidate event
MSK = timedelta(hours=3)          # the MoD writes windows in Moscow time (UTC+3)
WIKI = BRONZE / "strikes_rf" / "ukwiki_list_2026"
ASOF = {t: f"SELECT * FROM {t} WHERE available_at < {{t}}" for t in (MOD, EVENTS, HITS)}

TS = pa.timestamp("us")
SCHEMAS = {
    MOD: pa.schema([("post_id", pa.int64()), ("published_at", TS), ("window_start_utc", TS), ("window_end_utc", TS),
                    ("window_kind", pa.string()), ("drones_n", pa.int64()), ("regions_n", pa.int64()),
                    ("regions", pa.list_(pa.string())), ("moscow", pa.bool_()), ("edited", pa.bool_()),
                    ("available_at", TS)]),
    EVENTS: pa.schema([("source", pa.string()), ("post_id", pa.int64()), ("published_at", TS), ("kind", pa.string()),
                       ("text", pa.string()), ("importance", pa.float64()), ("importance_confidence", pa.float64()),
                       ("importance_probs", pa.list_(pa.float64())), ("edited", pa.bool_()), ("jev_model", pa.string()),
                       ("prompt_version", pa.string()), ("available_at", TS)]),
    HITS: pa.schema([("event_date", pa.date32()), ("region", pa.string()), ("object", pa.string()),
                     ("description", pa.string()), ("is_energy", pa.bool_()), ("moscow", pa.bool_()),
                     ("source_url", pa.string()), ("first_revid", pa.int64()), ("key_n", pa.int32()),
                     ("available_at", TS)]),
}


def utc(ts):
    """'2026-10-10T12:42:56Z' to a naive UTC datetime."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------------------- leakage guard (Jev state)

_UA_M = (r"січ(?:ня|ень|ні)|лют(?:ого|ий|ому)|берез(?:ня|ень|ні)|квіт(?:ня|ень|ні)|трав(?:ня|ень|ні)|черв(?:ня|ень|ні)|"
         r"лип(?:ня|ень|ні)|серп(?:ня|ень|ні)|верес(?:ня|ень|ні)|жовт(?:ня|ень|ні)|листопад(?:а|і)?|груд(?:ня|ень|ні)")
_RU_M = (r"январ[яье]|феврал[яье]|март[аеу]?|апрел[яье]|ма[яйе]|июн[яье]|июл[яье]|август[аеу]?|сентябр[яье]|"
         r"октябр[яье]|ноябр[яье]|декабр[яье]")
_RANGE = r"\d{1,2}(?:\s*[–-]\s*\d{1,2}|\s+(?:по|до|і|та|и|на)\s+\d{1,2})?"   # 7-13, 7 по 13, 6 на 7
_YEAR = r"(?:19|20)\d{2}"
_AFTER_YEAR = r"(?:\s*(?:року|рік|р\.|г\.|года))?"
RX_DAY_MONTH = re.compile(rf"\b{_RANGE}(?:-(?:го|й|е))?\s+(?:{_UA_M}|{_RU_M})\b(?:\s+{_YEAR}){{0,1}}{_AFTER_YEAR}", re.I)
RX_MONTH = re.compile(rf"\b(?:{_UA_M}|{_RU_M})\b", re.I)
RX_YEAR = re.compile(rf"\b{_YEAR}(?:-го)?\b{_AFTER_YEAR}")


_EN_M = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
         r"nov(?:ember)?|dec(?:ember)?")
_EN_FULL = r"january|february|march|april|june|july|august|september|october|november|december"
_EN_ORD = r"(?:st|nd|rd|th)?"
RX_EN_DATE = re.compile(rf"\b\d{{1,2}}{_EN_ORD}\s+(?:of\s+)?(?:{_EN_M})\b\.?(?:,?\s+{_YEAR}\b)?|"
                        rf"\b(?:{_EN_M})\b\.?\s+\d{{1,2}}{_EN_ORD}\b(?:,?\s+{_YEAR}\b)?|"
                        rf"\b(?:{_EN_M})\b\.?,?\s+{_YEAR}\b|\b(?:{_EN_FULL})\b", re.I)
# ISO date, also with a time and zone: 2026-10-10, 2026-10-10T05:00:00Z
RX_ISO = re.compile(r"\b\d{4}[-/.]\d{2}[-/.]\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}(?::?\d{2})?)?)?")
RX_NUM_FULL = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|\b\d{1,2}-\d{1,2}-(?:19|20)\d{2}\b")
# dd.mm without a year: day 1..31 and a two-digit month 01..12 (clock times 20.00 and 8.30, 24/7, 2.1б, 2.5 are not dates)
RX_NUM_DM = re.compile(r"(?<![\w.,/:])(?:0?[1-9]|[12]\d|3[01])[./](?:0[1-9]|1[0-2])(?!\w|[./,:]\d)(?!\s*(?:тис|млн|млрд|%))", re.I)
# "16-го та в ніч на [date]": the day of the month in front of the marker; "7 числа"
RX_DAY_ORD = re.compile(r"\b\d{1,2}-(?:го|й|е)(?=\s+(?:та|і|и)\s+(?:в|у)\s+ніч\s+на\s*\[date\])", re.I)
RX_DAY_WORD = re.compile(r"\b\d{1,2}(?:-(?:го|й|е))?\s+числа\b", re.I)


def strip_dates(s):
    """Text for Jev with every date and year removed (docs/JEV.md, leakage). The marker [date] replaces URLs, ISO dates
    and datetimes, dd.mm.yyyy and dd.mm dates, day plus month name (Ukrainian, Russian, English) with day ranges
    (7-13, 7 по 13, 6 на 7), month names alone, 'N-го та в ніч на [date]' and 'N числа'. Four-digit years are
    deleted. Clock times such as 20.00 and 8.30 stay."""
    s = re.sub(r"https?://\S+", " ", s or "")
    for rx in (RX_ISO, RX_NUM_FULL, RX_DAY_MONTH, RX_EN_DATE, RX_MONTH, RX_DAY_ORD, RX_DAY_WORD, RX_NUM_DM):
        s = rx.sub(" [date] ", s)
    s = RX_YEAR.sub(" ", s)
    s = re.sub(r"(?:\[date\][\s,;-]*){2,}", "[date] ", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


STRIP_CASES = [  # (text, what strip_dates must return); run by the states-check command
    ("(с 21.00 мск 6.05 до 7.00 мск 7.05) дежурными", "(с 21.00 мск [date] до 7.00 мск [date] ) дежурными"),
    ("Станом на 09.10 ситуація", "Станом на [date] ситуація"),
    ("Станом на 09.10.", "Станом на [date]."),
    ("2026-10-10T05:00:00Z", "[date]"),
    ("На 2026-10-10 12:00 було", "На [date] було"),
    ("10 Oct 2026", "[date]"), ("Oct 10, 2026", "[date]"), ("10th of October 2026", "[date]"), ("September", "[date]"),
    ("MARQUISE and MARCH5X", "MARQUISE and MARCH5X"), ("March 5", "[date]"),
    ("Працює 24/7 з 20.00-08.00, 8.30, 14.00 мск", "Працює 24/7 з 20.00-08.00, 8.30, 14.00 мск"),
    ("Союз-2.1б, 2.5 тис. дронів, 1.05 млн т, версія 1.12.3", "Союз-2.1б, 2.5 тис. дронів, 1.05 млн т, версія 1.12.3"),
    ("в ніч с 6 на 7 мая", "в ніч с [date]"), ("З 7 по 13 жовтня підрозділи", "З [date] підрозділи"),
    ("16-го та в ніч на 17 червня 2026 року", "[date] та в ніч на [date]"), ("7 числа", "[date]"),
    ("в ніч на 6 мая 2026 года", "в ніч на [date]"), ("06.05-07.05", "[date]"),
    ("09.10.2026 09.10.26 09-10-2026", "[date]"), ("1-го Окремого центру", "1-го Окремого центру"),
    ("13.13 і 32.05 і 31.12", "13.13 і 32.05 і [date]"),
]


# ------------------------------------------------------------------------------- rf_mod_reports (PARSING 8)

WORDS = {"один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7,
         "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
         "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
         "девятнадцать": 19, "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
         "семьдесят": 70, "восемьдесят": 80, "девяносто": 90, "сто": 100, "двести": 200, "триста": 300}
MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7, "августа": 8,
          "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
# the three regexes of PARSING 8 plus a fourth: a report says drones were intercepted or destroyed
RX_LOOSE = [re.compile(x, re.I) for x in (r"беспилотн|БПЛА", r"ПВО", r"над\s+(?:территори|акватори)")]
RX_VERB = re.compile(r"перехвачен|уничтожен", re.I)
RX_N = re.compile(r"(?:перехвачен[аоы]?\s+и\s+уничтожен[аоы]?|уничтожен[аоы]?\s+и\s+перехвачен[аоы]?|уничтожен[аоы]?)\s+"
                  r"(?P<n>\d[\d\s]*?|[а-яё]+(?:\s+(?!украинск)[а-яё]+)?)\s+(?:украинск\w+\s+)?(?:беспилотн\w+|БПЛА)", re.I)
RX_W = re.compile(r"с\s+(?P<h1>\d{1,2})[.:](?P<m1>\d{2})(?:\s*мск)?(?:\s+(?P<d1>\d{1,2})\s+(?P<mo1>[а-я]+))?"
                  r"\s+до\s+(?P<h2>\d{1,2})[.:](?P<m2>\d{2})(?:\s+(?P<d2>\d{1,2})\s+(?P<mo2>[а-я]+))?", re.I)
RX_REG = re.compile(r"над\s+(?:территори(?:ей|ями|и)|акватори(?:ей|ями|и))\s+(?P<lst>[^.]+)", re.I)
RX_REG_SPLIT = re.compile(r",\s*|\s+и\s+|\s+а\s+также\s+")
RX_REG_SKIP = re.compile(r"мор[ея]|акватор|водохранилищ|залив", re.I)
RX_MOSCOW = re.compile(r"Москв|Московск")
RX_MOSCOW_UA = re.compile(r"Москв|Московськ")  # the ukwiki table is Ukrainian: Московська область


def words_to_int(s):
    s = s.strip()
    if not s:
        return None
    if s[0].isdigit():
        return int(re.sub(r"\s", "", s))
    ws = s.lower().split()
    return sum(WORDS[w] for w in ws) if all(w in WORDS for w in ws) else None


def regions_of(text):
    m = RX_REG.search(text)
    if not m:
        return []
    parts = [x.strip() for x in RX_REG_SPLIT.split(m.group("lst"))]
    return [x for x in parts if x and not RX_REG_SKIP.search(x)]


def _msk_day(d, mo, pub_msk):
    month = MONTHS.get((mo or "").lower())
    if not d or not month:
        return None
    day = date(pub_msk.year, month, int(d))
    return day if day <= pub_msk.date() + timedelta(days=1) else date(pub_msk.year - 1, month, int(d))


def window_of(text, pub):
    """(start, end) of the reported window as naive UTC datetimes, or (None, None) when the report has no hours.
    Dates in the text win; otherwise the end is the last such clock time (Moscow) not after the publication."""
    m = RX_W.search(text)
    if not m:
        return None, None
    pm = pub + MSK

    def at(day, h, mi):
        return datetime(day.year, day.month, day.day) + timedelta(hours=int(h), minutes=int(mi))

    d1, d2 = _msk_day(m["d1"], m["mo1"], pm), _msk_day(m["d2"], m["mo2"], pm)
    if d1 and d2:
        s, e = at(d1, m["h1"], m["m1"]), at(d2, m["h2"], m["m2"])
    elif d1:
        s, e = at(d1, m["h1"], m["m1"]), at(d1, m["h2"], m["m2"])
        if e <= s:
            e += timedelta(days=1)
    elif d2:
        e = at(d2, m["h2"], m["m2"])
        s = at(d2, m["h1"], m["m1"])
        if s >= e:
            s -= timedelta(days=1)
    else:
        e = at(pm.date(), m["h2"], m["m2"])
        if e > pm:
            e -= timedelta(days=1)
        s = at(e.date(), m["h1"], m["m1"])
        if s >= e:
            s -= timedelta(days=1)
    return s - MSK, e - MSK


def parse_report(p):
    """None when the post is not an air-defence report; otherwise a row (drones_n is None when the count is not parsed)."""
    t = p["text"]
    if not (all(rx.search(t) for rx in RX_LOOSE) and RX_VERB.search(t)):
        return None
    m = RX_N.search(t)
    pub = utc(p["published_at"])
    regs = regions_of(t)
    ws, we = window_of(t, pub)
    head = t[:90]
    kind = "night" if re.search("ноч", head, re.I) else "day" if re.search("дня|день", head, re.I) else "other"
    return {"post_id": p["post_id"], "published_at": pub, "window_start_utc": ws, "window_end_utc": we,
            "window_kind": kind, "drones_n": words_to_int(m.group("n")) if m else None, "regions_n": len(regs),
            "regions": regs, "moscow": any(RX_MOSCOW.search(x) for x in regs), "edited": bool(p["edited"]),
            "available_at": pub}


def build_mod():
    """(rows, info, posts by id). info: loose-only post ids (no verb), unparsed post ids."""
    posts = {p["post_id"]: p for p in load("mod_russia") if p["published_at"] >= FETCH_FROM}
    rows, unparsed, loose_only = [], [], []
    for p in posts.values():
        t = p["text"]
        if all(rx.search(t) for rx in RX_LOOSE) and not RX_VERB.search(t):
            loose_only.append(p["post_id"])
        r = parse_report(p)
        if r is None:
            continue
        (rows if r["drones_n"] is not None else unparsed).append(r if r["drones_n"] is not None else p["post_id"])
    rows.sort(key=lambda r: r["post_id"])
    return rows, {"loose_only": sorted(loose_only), "unparsed": sorted(unparsed)}, posts


# ------------------------------------------------------------------------------- rf_strike_events: candidates

RX_GS_OBJ = re.compile(r"НПЗ|нафтопереробн\w*|ЛВДС|нафтобаз\w*|нафтоперекачувальн\w*|нафтов\w+\s+термінал\w*|\bТЕЦ\b|\bТЕС\b|"
                       r"\bГРЕС\b|підстанці\w*|газопереробн\w*|нафтохімічн\w*", re.I)
RX_GS_ACT = re.compile(r"уражен|влучан|удар", re.I)
RX_GS_TITLE = re.compile(r"^\W*(?:Повторно\s+)?(?:уражен|уразил|знищен|вразил)", re.I)  # the post starts with a hit announcement
RX_RU = re.compile(r"\bрф\b|росі[їяю]|російськ\w+\s+(?:територ|федерац)|Ростов|Бєлгород|Курськ|Брянськ|Воронез|Краснодар|"
                   r"Волгоград|Саратов|Самарськ|Липецьк|Тульськ|Рязанськ|Московськ|Смоленськ|Псковськ|Орловськ|Калузьк|"
                   r"Нижегородськ|Татарстан|Башкортостан|Оренбурзьк|Пермськ|Ленінградськ|Новгородськ|Тверськ|Ставропольськ|"
                   r"Астраханськ|Адигей|Кримськ|Криму|Крим\b|Севастопол", re.I)
RX_MOS = re.compile(r"летевш\w*\s+(?:на|в\s+сторону)\s+Москв|летящ\w*\s+(?:на|в\s+сторону)\s+Москв", re.I)
RX_AP = re.compile(r"\b(Шереметьево|Внуково|Домодедово|Жуковский)\b", re.I)
RX_CLOSED = re.compile(r"введены\s+(?:\S+\s+)?(?:временные\s+)?ограничени", re.I)
RX_PARTIAL = re.compile(r"по\s+согласованию", re.I)
KINDS = ("energy_hit", "military_hit", "moscow_attack", "airport_closure", "mass_drone_report")


def candidates(mod_rows, mod_posts):
    out = []

    def add(source, p, kind):
        out.append({"source": source, "post_id": p["post_id"], "published_at": utc(p["published_at"]), "kind": kind,
                    "text": p["text"], "edited": bool(p["edited"])})

    for p in load("GeneralStaffZSU"):
        t = p["text"]
        if p["published_at"] < FETCH_FROM:
            continue
        if RX_GS_OBJ.search(t) and RX_GS_ACT.search(t):
            add("GeneralStaffZSU", p, "energy_hit")
        elif RX_GS_TITLE.search(t) and RX_RU.search(t):
            add("GeneralStaffZSU", p, "military_hit")
    for p in load("mos_sobyanin"):
        if p["published_at"] >= FETCH_FROM and RX_MOS.search(p["text"]):
            add("mos_sobyanin", p, "moscow_attack")
    for p in load("favt_info"):
        if p["published_at"] >= FETCH_FROM and RX_AP.search(p["text"]) and (RX_CLOSED.search(p["text"]) or RX_PARTIAL.search(p["text"])):
            add("favt_info", p, "airport_closure")
    for r in mod_rows:
        if r["drones_n"] >= BIG_WAVE or r["moscow"]:
            add("mod_russia", mod_posts[r["post_id"]], "mass_drone_report")
    out.sort(key=lambda c: (c["published_at"], c["source"], c["post_id"]))
    return out


# ------------------------------------------------------------------------------- Jev importance

INSTRUCTIONS = (
    "The state is one post from an official channel: the Ukrainian General Staff, the mayor of Moscow, the Russian aviation "
    "authority or the Russian Ministry of Defence. It reports a Ukrainian strike on Russia, a drone attack on Moscow, "
    "restrictions at Moscow airports or the number of drones shot down over Russia (dates and years were removed on "
    "purpose). Rate how important this strike or attack is, judged by the strategic weight of the target and the size of "
    "the attack. Rate what the post says, not what may follow. Choose the description that fits best."
)
LEVELS = [  # index = score on the 0..5 scale; described by situations, never by number or by neighbour
    "Not a strike: the post does not report a strike or an attack, for example a statement, a message that restrictions "
    "were lifted, a weekly or monthly recap of earlier strikes, or an unrelated notice.",
    "A routine report: a few drones flying at Moscow, or a few tens of drones shot down over border regions or over "
    "several regions; or a post that lists one Moscow airport under introduced restrictions or working only with limits; no damage reported.",
    "A smaller hit or a moderate drone wave: a hit on a minor military object, a depot, a radar, a vessel or a small "
    "facility; or about ten to twenty drones flying at Moscow in one wave; or up to about a hundred drones shot down "
    "over Russian regions; or a post that lists two Moscow airports under introduced restrictions.",
    "A confirmed hit on an important military or energy object: an airfield, an air-defence system, a defence-industry "
    "plant, an oil depot, a pumping station, a power plant or a substation, reported as hit by the General Staff; or a "
    "large drone wave of about one hundred to three hundred drones shot down; or a post that lists three Moscow airports under introduced restrictions.",
    "A large refinery or an energy hub hit, or Moscow under a large wave: a major refinery or an oil terminal hit and "
    "burning, several energy objects hit in one night, or dozens of drones flying at Moscow in one wave, or several "
    "hundred drones, up to more than a thousand, shot down over Russia in one night.",
    "A strike of strategic weight: strategic bombers destroyed on airfields, a major refinery deep in Russia burning for "
    "days, or a mass attack on Moscow that closes all its airports (a post that lists all four Moscow airports, Sheremetyevo, Vnukovo, Domodedovo and Zhukovsky, under introduced restrictions).",
]
QUESTION = {"importance": {"type": "score", "instructions": INSTRUCTIONS, "criteria": LEVELS}}


def state_of(text):
    return strip_dates(text)[:3000]


def probs_of(ans):
    p = ans.get("probabilities")
    if isinstance(p, dict):
        return [float(p[k]) for k in sorted(p, key=lambda k: (not str(k).isdigit(), int(k) if str(k).isdigit() else 0, str(k)))]
    return [float(x) for x in p] if p else []


def score(cands, workers=WORKERS):
    """Adds importance, importance_confidence and importance_probs to every candidate. Identical states are asked once."""
    for c in cands:
        c["state"] = state_of(c["text"])
    distinct = sorted({c["state"] for c in cands})
    got = {}
    for i in range(0, len(distinct), 100):
        chunk = distinct[i:i + 100]
        for st, ans in zip(chunk, ask_many([(st, QUESTION) for st in chunk], tag=EVENTS, workers=workers)):
            got[st] = ans["importance"]
        print(f"jev {len(got)}/{len(distinct)} distinct states", flush=True)
    for c in cands:
        a = got[c["state"]]
        c.update(importance=float(a["score"]), importance_confidence=float(a["confidence"]), importance_probs=probs_of(a))
    return cands


# ------------------------------------------------------------------------------- rf_energy_hits (ukwiki)

RX_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
RX_ENERGY = re.compile(r"НПЗ|нафтопереробн|нафтобаз|ЛВДС|нафтоперекачувальн|термінал|ТЕЦ|ТЕС|ГРЕС|підстанці|енерг|газопереробн|"
                       r"нафтохім|паливн|резервуар|нафтов", re.I)
RX_ATTR = re.compile(r"^\s*(?:\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|\S+)\s*)+$")


def _split_top(s, sep):
    """Split s on sep outside [[ ]] and {{ }}."""
    if sep not in s:
        return [s]
    out, cur, depth, i = [], [], 0, 0
    while i < len(s):
        two = s[i:i + 2]
        if two in ("[[", "{{"):
            depth += 1
            cur.append(two)
            i += 2
        elif two in ("]]", "}}") and depth > 0:
            depth -= 1
            cur.append(two)
            i += 2
        elif depth == 0 and s.startswith(sep, i):
            out.append("".join(cur))
            cur = []
            i += len(sep)
        else:
            cur.append(s[i])
            i += 1
    out.append("".join(cur))
    return out


def _cell(piece):
    parts = _split_top(piece, "|")
    attrs, text = ("", piece)
    if len(parts) >= 2 and RX_ATTR.match(parts[0]):
        attrs, text = parts[0], "|".join(parts[1:])
    m = re.search(r"rowspan\s*=\s*\"?(\d+)", attrs)
    return {"text": text.strip(), "rowspan": int(m.group(1)) if m else 1}


def wiki_rows(wt):
    """Rows [date, region, object, description] (raw wikitext cells) of the data tables, rowspan expanded."""
    out = []
    for tm in re.finditer(r"\{\|.*?\n\|\}", wt, re.S):
        t = tm.group(0)
        if "!дата" not in t[:400]:      # the first table is the legend
            continue
        rows, cur, cell = [], None, None
        for line in t.split("\n"):
            s = line.rstrip()
            if s.startswith(("{|", "|}", "|+", "!")):
                continue
            if s.startswith("|-"):
                cur, cell = [], None
                rows.append(cur)
            elif s.startswith("|"):
                if cur is None:
                    continue
                for piece in _split_top(s[1:], "||"):
                    cell = _cell(piece)
                    cur.append(cell)
            elif cell is not None:
                cell["text"] += "\n" + s
        pend = {}
        for r in rows:
            full, ci, col = [], 0, 0
            while col < 4:
                if pend.get(col, [None, 0])[1] > 0:
                    full.append(pend[col][0])
                    pend[col][1] -= 1
                elif ci < len(r):
                    c = r[ci]
                    ci += 1
                    full.append(c["text"])
                    if c["rowspan"] > 1:
                        pend[col] = [c["text"], c["rowspan"] - 1]
                else:
                    break
                col += 1
            if len(full) != 4 or ci != len(r):
                raise ValueError(f"ukwiki row with {len(full)} cells and {len(r) - ci} left over: {[c['text'][:40] for c in r]}")
            out.append(full)
    return out


def wiki_clean(s):
    s = re.sub(r"<ref[^>/]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\{\{нп\|([^|}]*)[^}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'{2,}", "", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def wiki_revisions():
    revs = [json.loads(line) for line in open(WIKI / "revisions.jsonl", encoding="utf-8") if line.strip()]
    return sorted(revs, key=lambda r: (r["timestamp"], r["revid"]))


def wiki_content(revid):
    d = json.load(open(WIKI / f"rev_{revid}.json", encoding="utf-8"))
    return d["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]


def _row_key(r):
    m = RX_DATE.search(r[0])
    return (f"{m[3]}-{m[2]}-{m[1]}" if m else r[0].strip(), wiki_clean(r[1]), wiki_clean(r[2]))


def build_hits():
    """(rows, info). One row per row of the last revision; available_at is the first revision that has the n-th row
    with the same (date, region, object) key."""
    revs = wiki_revisions()
    first, last_rows, last_wt = {}, None, None
    for rev in revs:
        wt = wiki_content(rev["revid"])
        rows = wiki_rows(wt)
        seen = Counter()
        for r in rows:
            k = _row_key(r)
            seen[k] += 1
            first.setdefault((k, seen[k]), (rev["revid"], rev["timestamp"]))
        last_rows, last_wt = rows, wt
    urls = {}
    for m in re.finditer(r"<ref\s+name=\"([^\"]+)\"[^>/]*>(.*?)</ref>", last_wt, re.S):
        u = re.search(r"url\s*=\s*(https?://[^\s|}]+)", m.group(2))
        if u:
            urls.setdefault(m.group(1), u.group(1))
    out, seen = [], Counter()
    for r in last_rows:
        k = _row_key(r)
        seen[k] += 1
        revid, ts = first[(k, seen[k])]
        m = RX_DATE.search(r[0])
        url = None
        for ref in re.finditer(r"<ref\b([^>]*?)(?:/>|>(.*?)</ref>)", r[3], re.S):
            u = re.search(r"url\s*=\s*(https?://[^\s|}]+)", ref.group(2) or "")
            nm = re.search(r"name\s*=\s*\"([^\"]+)\"", ref.group(1))
            url = u.group(1) if u else (urls.get(nm.group(1)) if nm else None)
            if url:
                break
        region, obj, desc = wiki_clean(r[1]), wiki_clean(r[2]), wiki_clean(r[3])
        out.append({"event_date": date(int(m[3]), int(m[2]), int(m[1])), "region": region, "object": obj,
                    "description": desc, "is_energy": bool(RX_ENERGY.search(obj + " " + desc)),
                    "moscow": bool(RX_MOSCOW_UA.search(region)), "source_url": url, "first_revid": revid,
                    "key_n": seen[k], "available_at": utc(ts)})
    return out, {"revisions": len(revs), "first_ts": revs[0]["timestamp"], "last_ts": revs[-1]["timestamp"],
                 "last_revid": revs[-1]["revid"], "distinct_keys": len(seen)}


# ------------------------------------------------------------------------------- build

def write(name, rows):
    tbl = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
    tmp = SILVER / f"{name}.parquet.tmp"
    pq.write_table(tbl, tmp)
    os.replace(tmp, SILVER / f"{name}.parquet")
    return tbl.num_rows


def main():
    mod_rows, info, posts = build_mod()
    if info["unparsed"]:
        sys.exit(f"MoD reports with an unparsed count (fix the regex): {info['unparsed']}")
    cands = score(candidates(mod_rows, posts))
    ev = [dict(c, jev_model=MODEL, prompt_version=PROMPT_VERSION, available_at=c["published_at"]) for c in cands]
    hits, _ = build_hits()
    SILVER.mkdir(parents=True, exist_ok=True)
    print({MOD: write(MOD, mod_rows), EVENTS: write(EVENTS, ev), HITS: write(HITS, hits)})


# ------------------------------------------------------------------------------- features for gold

def _arrow(res):
    t = res.to_arrow_table() if hasattr(res, "to_arrow_table") else res.fetch_arrow_table()
    return t.read_all() if hasattr(t, "read_all") else t


def features(con, t_table):
    """Columns for gold, one row per t_utc, only rows with available_at < t_utc.
    rf_imp_max_24h, rf_imp_max_72h: max importance of rf_strike_events with available_at in [t-24h, t) and [t-72h, t), 0 if none.
    rf_drones_downed_24h: sum of drones_n of rf_mod_reports with available_at in [t-24h, t).
    hours_since_rf_imp4: hours from the last event with importance >= 4 to t, capped at 336 (also when there is none)."""
    sql = f"""
    WITH t AS (SELECT DISTINCT t_utc FROM {t_table})
    SELECT t.t_utc,
      COALESCE((SELECT max(importance) FROM rf_strike_events e
                WHERE e.available_at >= t.t_utc - INTERVAL 24 HOUR AND e.available_at < t.t_utc), 0)::DOUBLE AS rf_imp_max_24h,
      COALESCE((SELECT max(importance) FROM rf_strike_events e
                WHERE e.available_at >= t.t_utc - INTERVAL 72 HOUR AND e.available_at < t.t_utc), 0)::DOUBLE AS rf_imp_max_72h,
      COALESCE((SELECT sum(drones_n) FROM rf_mod_reports r
                WHERE r.available_at >= t.t_utc - INTERVAL 24 HOUR AND r.available_at < t.t_utc), 0)::BIGINT AS rf_drones_downed_24h,
      LEAST({CAP_HOURS}, COALESCE((SELECT date_diff('second', max(e.available_at), t.t_utc) / 3600.0
                                   FROM rf_strike_events e
                                   WHERE e.importance >= {IMP_HIGH} AND e.available_at < t.t_utc), {CAP_HOURS}))::DOUBLE AS hours_since_rf_imp4
    FROM t ORDER BY t.t_utc"""
    return _arrow(con.execute(sql))


# ------------------------------------------------------------------------------- commands

def last_full_hour():
    """Floor to the hour of the earliest 'last post' among the four channels: every channel is complete up to it."""
    last = min(max(p["published_at"] for p in load(c)) for c in ("mod_russia", "GeneralStaffZSU", "mos_sobyanin", "favt_info"))
    return utc(last).replace(minute=0, second=0)


def month_table(rows, key="published_at"):
    agg = {}
    for r in rows:
        m = r[key].strftime("%Y-%m")
        a = agg.setdefault(m, [0, 0, 0])
        a[0] += 1
        a[1] += r["drones_n"]
        a[2] += int(r["moscow"])
    return agg


def cmd_checks():
    for ch in ("mod_russia", "GeneralStaffZSU", "mos_sobyanin", "favt_info"):
        ps = sorted((p for p in load(ch) if p["published_at"] >= FETCH_FROM), key=lambda p: p["published_at"])
        gap = max((utc(b["published_at"]) - utc(a["published_at"]), a["published_at"]) for a, b in zip(ps, ps[1:]))
        print(f"bronze {ch}: posts from FETCH_FROM {len(ps)}, first {ps[0]['published_at']} (id {ps[0]['post_id']}), "
              f"last {ps[-1]['published_at']} (id {ps[-1]['post_id']}), longest silence {gap[0].total_seconds() / 3600:.1f} h after {gap[1]}")
    rows, info, posts = build_mod()
    print(f"MoD: posts {len(posts)}, reports {len(rows)}, unparsed {len(info['unparsed'])} {info['unparsed']}, "
          f"loose regexes without a verb {info['loose_only']}")
    nohrs = [r["post_id"] for r in rows if r["window_start_utc"] is None]
    clock = [i for i in nohrs if re.search(r"\d{1,2}[.:]\d{2}\s*мск", posts[i]["text"], re.I)]
    print("MoD no hours:", len(nohrs), "of them with a clock time in the text:", clock, "no regions:", sum(1 for r in rows if r["regions_n"] == 0),
          "edited:", sum(r["edited"] for r in rows))
    print("MoD windows odd (end after publication, or longer than 24 h):",
          [r["post_id"] for r in rows if r["window_end_utc"] and (r["window_end_utc"] > r["published_at"] or r["window_end_utc"] - r["window_start_utc"] > timedelta(hours=24))])
    print("month, reports, drones, with Moscow")
    for m, a in sorted(month_table(rows).items()):
        print(" ", m, *a)
    by = {r["post_id"]: r for r in rows}
    print("regions_n 68079:", by[68079]["regions_n"], "67489:", by[67489]["regions_n"], "67073:", by[67073]["drones_n"], "67751:", by[67751]["drones_n"])
    print("windows from 2026-06-18T10:21Z, (kind, Moscow hours): reports")
    cnt = Counter()
    for r in rows:
        if r["published_at"] >= datetime(2026, 6, 18, 10, 21):
            w = "nohours" if r["window_start_utc"] is None else (r["window_start_utc"] + MSK).strftime("%H:%M") + "-" + (r["window_end_utc"] + MSK).strftime("%H:%M")
            cnt[(r["window_kind"], w)] += 1
    for k, n in sorted(cnt.items()):
        print(" ", *k, n)
    cands = candidates(rows, posts)
    print("candidates:", len(cands), dict(Counter(c["kind"] for c in cands)), "edited", sum(c["edited"] for c in cands))
    for k in KINDS:
        print(" ", k, sorted(Counter(c["published_at"].strftime("%Y-%m") for c in cands if c["kind"] == k).items()))
    hits, hi = build_hits()
    print("ukwiki:", hi, "rows", len(hits), "from 2026-05-01", sum(h["event_date"] >= date(2026, 5, 1) for h in hits))
    for flag in ("is_energy", "moscow"):
        c = Counter(h["event_date"].month for h in hits if h[flag] and h["event_date"] >= date(2026, 5, 1))
        print(" ", flag, "per month 05..10:", [c.get(m, 0) for m in range(5, 11)])
    first = hi["first_ts"]
    print("  rows already in the first revision:", sum(h["available_at"] == utc(first) for h in hits), "first_revid min/max:",
          min(h["first_revid"] for h in hits), max(h["first_revid"] for h in hits), "with source_url:", sum(h["source_url"] is not None for h in hits))
    print("  available_at from", min(h["available_at"] for h in hits).strftime("%Y-%m-%dT%H:%M:%SZ"), "to",
          max(h["available_at"] for h in hits).strftime("%Y-%m-%dT%H:%M:%SZ"))
    p = SILVER / f"{MOD}.parquet"
    if p.exists():
        con = register_layers(connect())
        q = con.execute("SELECT strftime(published_at, '%Y-%m'), count(*), sum(drones_n), count(*) FILTER (WHERE moscow) FROM rf_mod_reports GROUP BY 1 ORDER BY 1").fetchall()
        print("parquet monthly equals fresh parse:", {r[0]: list(r[1:]) for r in q} == {m: a for m, a in month_table(rows).items()})


def pick_sample(cands, n, rng):
    anchors = [("GeneralStaffZSU", 42522), ("mos_sobyanin", 22067), ("mod_russia", 68079), ("mod_russia", 67489),
               ("favt_info", 8579), ("GeneralStaffZSU", 42444), ("GeneralStaffZSU", 37994), ("mos_sobyanin", 22009)]
    want = [c for c in cands if (c["source"], c["post_id"]) in anchors]
    rest = [c for c in cands if c not in want]
    return want + rng.sample(rest, min(n, len(rest)))


def cmd_score_sample(n):
    rows, info, posts = build_mod()
    sample = score(pick_sample(candidates(rows, posts), n, random.Random(7)))
    print("prompt_version", PROMPT_VERSION, "probabilities of the first:", sample[0]["importance_probs"])
    by = {}
    for c in sample:
        by.setdefault(c["kind"], []).append(c["importance"])
    for k, v in by.items():
        print(f"{k}: n={len(v)} mean={sum(v) / len(v):.2f} min={min(v):.2f} max={max(v):.2f}")
    for c in sorted(sample, key=lambda c: (c["kind"], -c["importance"])):
        print(f"{c['importance']:.2f} conf={c['importance_confidence']:.2f} {c['kind']:<17} {c['source']}/{c['post_id']} "
              f"{c['published_at']:%m-%d} | {c['state'][:150]!r}")


def cmd_report(out):
    os.makedirs(out, exist_ok=True)
    ev = pq.read_table(SILVER / f"{EVENTS}.parquet").to_pylist()
    by = {(r["source"], r["post_id"]): r for r in ev}
    for key in (("GeneralStaffZSU", 42522), ("mos_sobyanin", 22067)):
        r = by[key]
        print("anchor", key, "importance", round(r["importance"], 3), "confidence", round(r["importance_confidence"], 3), r["kind"])

    def dump(path, rows):
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"source": r["source"], "post_id": r["post_id"], "published_at": f"{r['published_at']:%Y-%m-%dT%H:%M:%SZ}",
                                    "kind": r["kind"], "importance": r["importance"], "confidence": r["importance_confidence"],
                                    "text": r["text"][:500]}, ensure_ascii=False) + "\n")
    top = sorted(ev, key=lambda r: (-r["importance"], r["published_at"]))[:20]
    low = [r for r in ev if r["importance"] <= 1]
    low = random.Random().sample(low, min(10, len(low)))
    dump(os.path.join(out, "top20.jsonl"), top)
    dump(os.path.join(out, "low10.jsonl"), low)
    print("events", len(ev), "kinds", dict(Counter(r["kind"] for r in ev)), "importance<=1:", sum(r["importance"] <= 1 for r in ev),
          "importance>=4:", sum(r["importance"] >= 4 for r in ev), "prompt", {r["prompt_version"] for r in ev}, {r["jev_model"] for r in ev})
    b = Counter(min(int(r["importance"]), 4) for r in ev)
    print("importance buckets <1, [1,2), [2,3), [3,4), >=4:", [b[i] for i in range(5)])
    print("by source:", dict(sorted(Counter(r["source"] for r in ev).items())), "available_at = published_at:",
          sum(r["available_at"] == r["published_at"] for r in ev), "edited:", sum(r["edited"] for r in ev))
    rec = [r["importance"] for r in ev if re.search("ТИЖДЕНЬ|Підсумки уражень", r["text"], re.I)]
    print(f"recap posts (ТИЖДЕНЬ or Підсумки уражень): n {len(rec)}, mean {sum(rec) / len(rec):.2f}, max {max(rec):.2f}")
    print("top 20:")
    for r in top:
        print(f"  {r['importance']:.2f} {r['kind']:<17} {r['source']}/{r['post_id']} {r['published_at']:%Y-%m-%d} {r['text'][:90]!r}")
    print("10 events scored 0..1:")
    for r in low:
        print(f"  {r['importance']:.2f} {r['kind']:<17} {r['source']}/{r['post_id']} {r['published_at']:%Y-%m-%d} {r['text'][:90]!r}")


NOT_DATES = {"24/7": "round the clock", "10-12": "10-12 million tonnes", "2.1": "Союз-2.1б", "22-4": "22-4М5, a product code"}


def cmd_states_check():
    """The strip_dates cases and the dates left in the Jev states of all candidates. Bronze only: no Jev, no tables."""
    bad = [(a, strip_dates(a), want) for a, want in STRIP_CASES if strip_dates(a) != want]
    print(f"strip_dates cases {len(STRIP_CASES)}, failed {len(bad)} {bad}")
    rows, _, posts = build_mod()
    states = {f"{c['source']}/{c['post_id']}": state_of(c["text"]) for c in candidates(rows, posts)}
    print(f"states {len(states)}, distinct {len(set(states.values()))}, with the [date] marker {sum('[date]' in s for s in states.values())}")
    kinds = {
        "year of four digits": re.compile(r"\b(?:19|20)\d{2}\b"),
        "ISO date": re.compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"),
        "month name (uk, ru)": re.compile(rf"\b(?:{_UA_M}|{_RU_M})\b", re.I),
        "month name or weekday (en)": re.compile(rf"\b(?:{_EN_M}|(?:mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat(?:ur)?|sun)(?:day)?)\b", re.I),
    }
    for name, rx in kinds.items():
        hits = [(k, mt.group(0)) for k, s in states.items() for mt in rx.finditer(s)]
        print(f"left in states, {name}: {len(hits)} {hits[:5]}")
    tok = Counter()
    for s in states.values():
        for mt in re.finditer(r"(?<![\d.,:])(\d{1,2})[./-](\d{1,2})(?!\d)", s):
            if 1 <= int(mt.group(1)) <= 31 and 1 <= int(mt.group(2)) <= 12:
                tok[mt.group(0)] += 1
    print("left in states, day.month-like tokens:", dict(tok), "not on the list of known non-dates:", [t for t in tok if t not in NOT_DATES])


def direct_features(ev, mod, t):
    """The four gold columns for one t in plain Python from the table rows (a check of features(), not used by gold)."""
    def within(r, hours):
        return t - timedelta(hours=hours) <= r["available_at"] < t
    hi = [e["available_at"] for e in ev if e["importance"] >= IMP_HIGH and e["available_at"] < t]
    return {"rf_imp_max_24h": max([e["importance"] for e in ev if within(e, 24)], default=0.0),
            "rf_imp_max_72h": max([e["importance"] for e in ev if within(e, 72)], default=0.0),
            "rf_drones_downed_24h": sum(r["drones_n"] for r in mod if within(r, 24)),
            "hours_since_rf_imp4": min(CAP_HOURS, (t - max(hi)).total_seconds() / 3600.0) if hi else CAP_HOURS}


def cmd_features_check():
    con = register_layers(connect())
    last = last_full_hour()
    t0 = utc(T0)
    n = int((last - t0) / timedelta(hours=1)) + 1
    con.execute(f"CREATE TABLE tt AS SELECT unnest(generate_series(TIMESTAMP '{t0:%Y-%m-%d %H:%M:%S}', TIMESTAMP '{last:%Y-%m-%d %H:%M:%S}', INTERVAL 1 HOUR)) AS t_utc")
    ft = features(con, "tt")
    nulls = {c: ft[c].null_count for c in ft.column_names}
    print(f"hours {t0:%Y-%m-%dT%H}Z..{last:%Y-%m-%dT%H}Z = {n}; rows {ft.num_rows}; first column {ft.column_names[0]}; unique t_utc "
          f"{len(set(ft['t_utc'].to_pylist())) == ft.num_rows}; columns {ft.column_names}; nulls {nulls}")
    for c in ft.column_names[1:]:
        v = ft[c].to_pylist()
        print(f"  {c}: min {min(v):.2f} max {max(v):.2f} mean {sum(v) / len(v):.2f}")
    rows = ft.to_pylist()
    ev = pq.read_table(SILVER / f"{EVENTS}.parquet").to_pylist()
    mod = pq.read_table(SILVER / f"{MOD}.parquet").to_pylist()
    pre = [e for e in ev if e["available_at"] < t0]
    hi0 = sorted((e["available_at"], e["source"], e["post_id"], e["importance"]) for e in pre if e["importance"] >= IMP_HIGH)
    last_hi = f"{hi0[-1][1]}/{hi0[-1][2]} at {hi0[-1][0]:%Y-%m-%dT%H:%M:%SZ}, importance {hi0[-1][3]:.2f}" if hi0 else "none"
    print(f"events before {t0:%Y-%m-%dT%H}Z: {len(pre)}, the earliest at {min(e['available_at'] for e in pre):%Y-%m-%dT%H:%M:%SZ} "
          f"(FETCH_FROM {FETCH_FROM}); with importance >= {IMP_HIGH}: {len(hi0)}, the last one {last_hi}")
    d0 = direct_features(ev, mod, t0)
    print(f"hours_since_rf_imp4 at {t0:%Y-%m-%dT%H}Z: features {rows[0]['hours_since_rf_imp4']:.4f}, direct {d0['hours_since_rf_imp4']:.4f}, "
          f"row 0 is that hour {rows[0]['t_utc'] == t0}, equal {abs(rows[0]['hours_since_rf_imp4'] - d0['hours_since_rf_imp4']) < 1e-9}")
    bad = [i for i in range(n) if any(abs(rows[i][k] - v) > 1e-9 for k, v in direct_features(ev, mod, t0 + timedelta(hours=i)).items())]
    print(f"all four features equal a direct computation from the tables, hours {n}, different {len(bad)} {bad[:5]}")
    early = int((datetime(2026, 5, 7, 21) - t0) / timedelta(hours=1))  # 2026-05-07T21:00Z = 2026-04-23T21:00Z, the old data start, plus 14 days
    rng = random.Random()
    for i in [rng.randrange(early)] + sorted(rng.sample(range(early, n), 2)):
        t = t0 + timedelta(hours=i)
        lit = f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'"
        c2 = connect()
        for name, sql in ASOF.items():
            c2.register(name, _arrow(con.execute(sql.format(t=lit))))
        c2.execute(f"CREATE TABLE t1 AS SELECT {lit} AS t_utc")
        got = features(c2, "t1").to_pylist()
        print(f"ASOF t={t:%Y-%m-%dT%H}Z ({'before 2026-05-07T21Z' if i < early else 'later'}) identical to the full computation: {got == [rows[i]]} {got[0]}")


def cli():
    ap = argparse.ArgumentParser(prog="airalerts.silver.rf_strikes")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("build")
    sub.add_parser("checks")
    sub.add_parser("features-check")
    sub.add_parser("states-check")
    sp = sub.add_parser("score-sample")
    sp.add_argument("--n", type=int, default=60)
    sp = sub.add_parser("report")
    sp.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd in (None, "build"):
        main()
    elif a.cmd == "checks":
        cmd_checks()
    elif a.cmd == "score-sample":
        cmd_score_sample(a.n)
    elif a.cmd == "report":
        cmd_report(a.out)
    elif a.cmd == "features-check":
        cmd_features_check()
    elif a.cmd == "states-check":
        cmd_states_check()


if __name__ == "__main__":
    cli()
