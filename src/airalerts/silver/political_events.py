"""Silver political_events: visits, summits, forums and talks in Kyiv and of the Russian leadership; class and importance level from Jev facts.

Bronze: Telegram OP_UA and V_Zelenskiy_official, Kremlin news and trips, Wikipedia lists with all revisions (docs/PARSING.md section 6).
Candidates are cut out by code (regex rules, wikitext tables) from FETCH_FROM on. Jev answers 21 yes/no facts per candidate (noul: 18 in FACT_QUESTIONS, press_remarks in its own request PRESS_QUESTION, five facts read a second time with CHECK_QUESTIONS and averaged, two caps in GATE_QUESTIONS); the code turns the facts into the class (kyiv, russia, world, none: class_of) and into the importance level 0..5
(level_of). Class world is scored (it decides the abroad twins) and then dropped like class none (user 2026-10-11). Class none is dropped (except a Wikipedia version that replaces a version of another class: keep_candidates; also a Kyiv-by-default candidate whose same-day twin names a foreign place: mark_abroad_twins), the rest is deduplicated by (class, main participant, event_date); a later candidate of the same
key stays as its own row only if its level is higher than the level of the key at its announcement (it is known only from its own announcement).
A Wikipedia event key has one candidate and one row per version of its row (title, text, country, dates): a version starts in the revision where the
row changes, is scored on the text of that revision and is known from the timestamp of that revision (wiki_events, dedup; columns version_of, revid, text).
Gold: features(con, t_table) uses, for every event key, only its latest version known before t. Documentation: docs/data/silver/political_events.md

Run (from the project root):
  .venv/bin/python -I -m airalerts.silver.political_events                          build data/silver/political_events.parquet
  .venv/bin/python -I -m airalerts.silver.political_events build --dump FILE        also write every scored candidate (JSON lines)
  .venv/bin/python -I -m airalerts.silver.political_events candidates               candidate counts, no Jev
  .venv/bin/python -I -m airalerts.silver.political_events strip-demo               the date stripper on 3 titles
  .venv/bin/python -I -m airalerts.silver.political_events place-check              where the president is: place words, kinds, hints
  .venv/bin/python -I -m airalerts.silver.political_events report --dump FILE --out DIR   anchors, levels per class and month, checks, samples
  .venv/bin/python -I -m airalerts.silver.political_events features-check           hourly features, nulls, ASOF test
  .venv/bin/python -I -m airalerts.silver.political_events features-check --old FILE   also the hours that differ from an older table (without version_of and revid)
  .venv/bin/python -I -m airalerts.silver.political_events wiki-check               leak check of the Wikipedia versions against the revision files
"""
import argparse
import hashlib
import inspect
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html import unescape
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect, register_layers
from ..jev import MODEL, ask_many
from ..paths import BRONZE, FETCH_FROM, SILVER
from ..telegram import load as load_posts

TABLE = "political_events"
PATH = SILVER / f"{TABLE}.parquet"
PROMPT_VERSION = "pol-v9"  # questions as in pol-v8; class world dropped (user 2026-10-11)
D_TO = date(2026, 10, 31)  # events after it are not kept; D_FROM (first Kyiv day of FETCH_FROM) is set below
CAP_DAYS = 14                                          # {c}_days_to_imp4 is capped here
IMP_HIGH = 4                                           # importance that counts for {c}_days_to_imp4
SURE = 0.8                                             # a gate fact caps another fact only when its p is at least this sure
CLASSES = ("kyiv", "russia")                          # class world is scored but dropped (score_all): user 2026-10-11, war-related world events are too hard to tell apart
TG_SRC = ("tg_op", "tg_zel")                           # free-form posts of the office and of the president of Ukraine
GENERIC = {"RU", "EU", "NATO", "UN", "EUCO", "G7", "UDCG", "CIS", "BRICS", "SCO", "EAEU", "CE", "EPC"}  # codes that do not identify one meeting
WORKERS = 8                                            # Jev workers (the limit is 8)
PLACE_HOURS = {"kyiv": 30, "abroad": 30, "ukraine": 8}  # how long the place named by the office holds for the posts after it
KYIV = ZoneInfo("Europe/Kyiv")
CAL = BRONZE / "calendar"
ASOF = {TABLE: f"SELECT * FROM {TABLE} WHERE available_at < {{t}}"}

IMP_FACTS = ["in_person", "us_president", "us_russia_presidents", "leaders5", "head_major", "head_any", "minister"]
CLASS_FACTS = ["remote_call", "statement", "ceremony", "damage_report", "recap", "inspection", "in_kyiv", "ukraine_elsewhere",
               "abroad", "place_written", "russian_leadership", "press_remarks"]
NONE_REASONS = ("remote_call", "statement", "press_remarks", "ceremony", "damage_report", "recap", "inspection")  # any of them true: class none
GATE_FACTS = ["bilateral", "titled"]                   # caps on leaders5 and head_any (score_all)
FACTS = IMP_FACTS + CLASS_FACTS + GATE_FACTS

SCHEMA = pa.schema([
    ("event_id", pa.string()), ("version_of", pa.string()), ("revid", pa.int64()), ("event_date", pa.date32()), ("end_date", pa.date32()), ("class", pa.string()),
    ("type", pa.string()), ("title", pa.string()), ("text", pa.string()), ("participants", pa.list_(pa.string())),
    ("importance", pa.int32()), ("importance_confidence", pa.float64()), ("class_confidence", pa.float64()),
    ("scheduled", pa.bool_()), ("announced_at", pa.timestamp("us")), ("available_at", pa.timestamp("us")),
    ("sources", pa.list_(pa.string())), ("jev_model", pa.string()), ("prompt_version", pa.string()),
] + [(f"p_{f}", pa.float64()) for f in FACTS])

# ---------------------------------------------------------------------------------------------------------- time


def utc(ts):
    """'2026-10-10T12:42:56Z' to a naive UTC datetime."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


def kyiv_day(dt):
    """Kyiv calendar date of a naive UTC datetime."""
    return dt.replace(tzinfo=timezone.utc).astimezone(KYIV).date()


def kyiv_midnight(d):
    """00:00 Kyiv of date d as a naive UTC datetime."""
    return datetime(d.year, d.month, d.day, tzinfo=KYIV).astimezone(timezone.utc).replace(tzinfo=None)


D_FROM = kyiv_day(utc(FETCH_FROM))  # events before it are not kept


# ------------------------------------------------------------------------------------------- leakage guard (Jev state)

_UA_M = (r"січ(?:ня|ень|ні)|лют(?:ого|ий|ому)|берез(?:ня|ень|ні)|квіт(?:ня|ень|ні)|трав(?:ня|ень|ні)|черв(?:ня|ень|ні)|"
         r"лип(?:ня|ень|ні)|серп(?:ня|ень|ні)|верес(?:ня|ень|ні)|жовт(?:ня|ень|ні)|листопад(?:а|і)?|груд(?:ня|ень|ні)")
_RU_M = (r"январ[яье]|феврал[яье]|март[аеу]?|апрел[яье]|ма[яйе]|июн[яье]|июл[яье]|август[аеу]?|сентябр[яье]|"
         r"октябр[яье]|ноябр[яье]|декабр[яье]")
_EN_M = "January|February|March|April|May|June|July|August|September|October|November|December|Sept"
_EN_AB = "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_UA_AB = "січ|лют|берез|квіт|трав|черв|лип|серп|вер|жовт|лист|груд"
_RANGE = r"\d{1,2}(?:\s*[\u2013\u2014-]\s*\d{1,2})?"
_YEAR = r"(?<!\d)(?:19|20)\d{2}(?!\d)"
_AFTER_YEAR = r"(?:\s*(?:року|рік|р\.|г\.|года))?"
_DDMM = r"(?<![\d.,/])(?:0?[1-9]|[12]\d|3[01])\.(?:0[1-9]|1[0-2])(?!\d)"
RX_URL = re.compile(r"https?://\S+")
RX_ISO = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?")
RX_NUM = re.compile(rf"(?<!\d)\d{{1,2}}[./]\d{{1,2}}[./]\d{{2,4}}(?!\d)|{_DDMM}")
RX_DAY_MONTH = re.compile(rf"\b{_RANGE}(?:-(?:го|й|е))?\s+(?:{_UA_M}|{_RU_M})\b(?:\s+{_YEAR}){{0,1}}{_AFTER_YEAR}", re.I)
RX_DAY_MONTH_AB = re.compile(rf"\b{_RANGE}\s+(?:{_UA_AB})\.", re.I)
RX_MONTH = re.compile(rf"\b(?:{_UA_M}|{_RU_M})\b", re.I)
RX_MONTH_DAY_EN = re.compile(rf"\b(?:{_EN_M}|{_EN_AB})\b\.?\s+{_RANGE}(?:st|nd|rd|th)?\b(?:,?\s+{_YEAR})?")
RX_DAY_MONTH_EN = re.compile(rf"\b{_RANGE}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{_EN_M}|{_EN_AB})\b\.?(?:,?\s+{_YEAR})?")
RX_MONTH_EN = re.compile(rf"\b(?:{_EN_M})\b\.?|\b(?:{_EN_AB})\.(?=[\s,;)]|$)")
RX_YEAR = re.compile(rf"{_YEAR}(?:-го)?{_AFTER_YEAR}")
_LEAK = [re.compile(_YEAR), re.compile(r"(?<!\d)\d{4}-\d{2}"), re.compile(r"(?<!\d)\d{1,2}[./]\d{1,2}[./]\d{2,4}"), re.compile(_DDMM),
         re.compile(rf"\b(?:{_UA_M}|{_RU_M})\b", re.I), re.compile(rf"\b(?:{_EN_M})\b"),
         re.compile(rf"\b(?:{_EN_AB})\b\.?\s+\d{{1,2}}\b"), re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{_EN_M}|{_EN_AB})\b"),
         re.compile(r"https?://")]


def strip_dates(s):
    """Text for Jev with every date and year removed (docs/JEV.md, leakage): URLs are deleted; ISO dates and date-times,
    dd.mm.yyyy and dd.mm, day plus month name (Ukrainian, Russian, English, also abbreviated: Aug. 8, Sep 11-13, 15 черв.)
    and month names alone become the marker [date] (it keeps the sentence readable and carries no date); four-digit years
    1900..2099 are deleted (also inside FY2026)."""
    s = RX_URL.sub(" ", s or "")
    for rx in (RX_ISO, RX_NUM, RX_DAY_MONTH, RX_DAY_MONTH_AB, RX_MONTH_DAY_EN, RX_DAY_MONTH_EN, RX_MONTH, RX_MONTH_EN):
        s = rx.sub(" [date] ", s)
    s = RX_YEAR.sub(" ", s)
    s = re.sub(r"(?:\[date\][\s,;-]*){2,}", "[date] ", s)
    s = re.sub(r"\(\s*[,;]?\s*\)", " ", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def leak_scan(s):
    """What is left of a date, a year or a URL in a text after strip_dates (an empty list means clean)."""
    return [m.group(0) for rx in _LEAK for m in rx.finditer(s)]



# -------------------------------------------------------------------------------------------- participants lexicon

_ENT = r"""
US|США|Сполучен\w+ Штат|американ|Трамп|Trump|United States|America|(?-i:\bUSA?\b)|Rubio|Рубіо|Witkoff|Віткофф|Уіткофф|Vance|Венс|Вашингтон|Washington
RU|Росі[яїйює]|російськ|Russia|Путін|Putin|Кремл|Kremlin|Ушаков|Ushakov|Лавров|Lavrov
GB|Британ|Великої Британії|Об'єднан\w+ Королівств|United Kingdom|Britain|British|(?-i:\bUK\b)|Стармер|Starmer|Лондон|London
FR|Франц|France|French|Макрон|Macron|Париж|Paris
DE|Німеч|Germany|German|Мерц|Merz|Берлін|Berlin|Шольц|Scholz
PL|Польщ|Польськ|Poland|Polish|Навроцьк|Nawrocki|Туск|Tusk|Варшав|Warsaw
IT|Італі|Italy|Italian|Мелоні|Meloni
ES|Іспані|Spain|Spanish|Санчес|Sánchez
NL|Нідерланд|Netherlands|Dutch
BE|Бельгі|Belgium
SE|Швеці|Sweden|Swedish
NO|Норвег|Norway|Norwegian|Осло|Oslo
DK|Данії|Данія|Данію|Denmark|Danish
FI|Фінлянд|Finland|Finnish|Стубб|Stubb
IS|Ісланд|Iceland
IE|Ірланд|Ireland|Irish
EE|Естон|Estonia
LV|Латв|Latvia
LT|Литв|Lithuania|Науседа|Nausėda
CZ|Чехі|Чеськ|Czech
SK|Словаччин|Slovakia|Slovak
HU|Угорщин|Hungary|Hungarian|Орбан|Orb[aá]n
RO|Румуні|Romania
BG|Болгарі|Bulgaria
GR|Греці|Greece|Greek
HR|Хорват|Croatia
SI|Словені|Slovenia
RS|Серб|Serbia
BA|Боснії|Bosnia
ME|Чорногор|Montenegro
MK|Північн\w+ Македон|North Macedonia
AL|Албані|Albania
XK|Косов|Kosovo
MD|Молдов|Moldova
GE|Грузі|(?-i:\bGeorgia\b)
AM|Вірмені|Armenia
AZ|Азербайджан|Azerbaijan
PT|Португал|Portugal
AT|Австрі|Austria
CH|Швейцар|Switzerland|Swiss
LU|Люксембург|Luxembourg
MT|Мальт|(?-i:\bMalta\b)
CY|Кіпр|Cyprus
TR|Туреч|Turkey|Türkiye|Turkish|Ердоган|Erdo[gğ]an|Анкар|Ankara
JP|Япон|Japan
KR|Кореї|Південн\w+ Корe|South Korea
CN|Китай|China|Chinese|Сі Цзіньпін|Xi Jinping|Пекін|Beijing
IN|Індії|Індія|Індію|India|Моді|Modi
AU|Австрал|Australia
NZ|Нової Зеландії|New Zealand
CA|Канад|Canada|Canadian
SA|Саудів|Saudi
AE|ОАЕ|Емірат|Emirates|(?-i:\bUAE\b)
QA|Катар|Qatar
IL|Ізраїл|Israel
IR|Іран|Iran
EG|Єгипет|Єгипт|Egypt
KZ|Казахстан|Kazakhstan
UZ|Узбекистан|Uzbekistan
BY|Білорус|Belarus|Лукашенк|Lukashenko
KG|Киргиз|Кыргыз|Kyrgyz|Бішкек|Bishkek
TJ|Таджикистан|Tajikistan|Rahmon
TM|Туркмен|Turkmen
MN|Монголі|Mongolia
VN|В'єтнам|Vietnam
ID|Індонез|Indonesia
BR|Бразил|Brazil
ZA|Південн\w+ Афри|South Africa
PH|Філіппін|Philippines
EU|ЄС\b|Євросоюз|Європейськ\w+ Союз|European Union|(?-i:\bEU\b)|Єврокомісі|European Commission|фон дер Ляєн|von der Leyen|Брюссел|Brussels
NATO|НАТО|NATO|Рютте|Rutte
EUCO|Європейськ\w+ [Рр]ад|European Council|Євророад
G7|G7|Г7|Групи семи|Group of Seven
UN|ООН|Об'єднаних Націй|United Nations|Гутерріш|Guterres
UDCG|Рамштайн|Ramstein|UDCG|Contact Group
CIS|СНД|(?-i:\bCIS\b)|Commonwealth of Independent States
BRICS|БРІКС|BRICS
SCO|ШОС|(?-i:\bSCO\b)
EAEU|ЄАЕС|ЕАЭС|Eurasian Economic Union
CE|Рада Європи|Council of Europe
EPC|Європейськ\w+ політичн\w+ спільнот|European Political Community
"""
ENTITIES = [(ln.split("|", 1)[0], re.compile(ln.split("|", 1)[1], re.I)) for ln in _ENT.strip().split("\n")]


def participants_of(text, limit=6):
    """Entity codes found in the text, in order of first mention."""
    hits = []
    for code, rx in ENTITIES:
        m = rx.search(text)
        if m:
            hits.append((m.start(), code))
    return [c for _, c in sorted(hits)][:limit]


def main_participant(parts, typ):
    """The main participant of the dedup key: the first one that is not Russia; Russia if alone; else the event type."""
    for p in parts:
        if p != "RU":
            return p
    return parts[0] if parts else typ


# -------------------------------------------------------------------------------------- candidates: Telegram, Kremlin

SRC_LABEL = {
    "tg_op": "Telegram channel of the Office of the President of Ukraine",
    "tg_zel": "Telegram channel of the President of Ukraine Volodymyr Zelensky",
    "kremlin_news": "News of the President of Russia on the official Kremlin website",
    "kremlin_trips": "Trips of the President of Russia on the official Kremlin website",
}
SRC_RANK = {"tg_op": 0, "tg_zel": 1, "kremlin_news": 2, "kremlin_trips": 3, "wiki": 4}
TG_RULES = [  # docs/PARSING.md section 6, plus summits and forums; the first rule that matches gives the type
    ("ramstein", r"Рамштайн|Ramstein|UDCG"), ("sanctions", r"пакет\w* санкц"),
    ("ua_visit", r"візит|прибув|приїха|у Києві|до Києва"), ("ua_talks", r"переговор"),
    ("ua_call", r"розмов"), ("ua_meeting", r"зустр[іi]"), ("ua_summit", r"саміт|форум|конференці"),
]
KR_SKIP = re.compile(r"^(Greetings|Congratulations|Condolences|Message|Telegram|Address|Statements?\b|Birthday greetings to (?!Vladimir Putin))", re.I)
KR_RULES = [  # docs/PARSING.md section 6 plus the forms seen in the titles; the first rule that matches gives the type
    ("putin_birthday", r"^Birthday greetings to Vladimir Putin"),
    ("foreign_meeting", r"^(Meeting|Talks) with (President|Prime Minister|King|Emir|Crown Prince|Chancellor|Sultan|Chairman|"
                        r"Supreme Leader|Secretary|Foreign Minister)|Russian-\w+ talks"),
    ("putin_trip_abroad", r"^(State|Official|Working) visit to|\barrived in\b|\bwill (make|pay) a\b"),
    ("putin_trip_domestic", r"^(Trip|Visit) to"),
    ("forum_ru", r"Plenary session|Forum|Valdai"),
    ("summit", r"[Ss]ummit|Council of Heads of State"),
]
PUTIN = re.compile(r"Путін|Путіна|Путіну|Putin|Кремл|Ушаков", re.I)
EXCLUDED = []  # Telegram posts left out as recaps by RECAP_RX (written next to the dump for the report)
RECAP_RX = re.compile(  # digests and recaps are not events (code rule; Jev checks the rest with the question `recap`)
    r"Головне зі звернення|Зовнішньополітична робота|^\W*(?:Цього|Минулого) тижня|"
    rf"^\W*(?:Протягом|За|У|В)\s+(?:(?:цього|минулого)\s+)?(?:тижня|місяця|{_UA_M})\s+Президент", re.I)

# Where the president is. The office names the place in its template ("В Анкарі Президент України ..."); the posts that name
# none inherit the latest named place of the two channels (only earlier posts, so no look-ahead). Jev says what kind of place a
# word is (Kyiv, other Ukraine, abroad); the code carries it forward.
_W = r"[А-ЯІЇЄҐ][\w'’-]*"
_PLACE = rf"({_W}(?:[ -]{_W})?)"
PLACE_CUES = [  # (cue, loose): the group is the place word; the first cue that fits wins; a loose cue is no proof of Kyiv
    (re.compile(rf"(?:^|\s)(?:[УуВв]|[Нн]а)\s+{_PLACE}(?:,\s[^.]{{0,80}}?,)?\s+Президент\w*\s+України"), False),                # "У Києві Президент України ..."
    (re.compile(rf"Президент\w*\s+України\s+Володимир\w*\s+Зеленськ\w*\s+(?:[УуВв]|[Нн]а)\s+{_PLACE}\s+[а-яіїєґ]"), False),  # "... Зеленський в Анкарі провів ..."
    (re.compile(rf"^\W*(?:[^.]{{0,40}}?\s)?[Пп]рибу(?:в|ла|ли)\w*[^.]{{0,80}}?\s(?:до|в|у|на)\s+{_PLACE}"), False),     # Zelensky: "Прибув до Єревана", "Прибули ... до Нью-Йорка"
    (re.compile(rf"^\W*Розпоч\w+\s+(?:\w+\s+)?візит\w*\s+(?:до|в|у)\s+{_PLACE}"), False),  # Zelensky: "Розпочав візит до Нью-Йорка"
    (re.compile(rf"^\W*Сьогодні\s+[ув]\s+{_PLACE}"), True),                                   # Zelensky: "Сьогодні в Британії"
]
PLACE_SKIP = {"Україні", "Україну", "Україна", "Україною"}
# a post whose first sentence says the event is in Kyiv or in Ukraine ignores a place inherited from earlier posts (a later sentence may
# name Kyiv for another reason, for example a strike there)
KYIV_MENTION = re.compile(r"[УуВв]\s+Києві|до Києва|візит\w*\s+(?:в|до)\s+Україн|(?:прибув|приїхав|прибули|приїхали)\w*\s+(?:в|до)\s+(?:Київ|Україн)|вітат\w*[^.]{0,40}\sв\s+Україні")


def own_place_ex(text):
    """(place word, loose) that the post itself names as the place of the president ('Анкарі' in 'В Анкарі Президент
    України ...'), else (None, False)."""
    head = text[:400]
    for rx, loose in PLACE_CUES:
        m = rx.search(head)
        if m and m[1] not in PLACE_SKIP:
            return m[1], loose
    return None, False


def own_place(text):
    return own_place_ex(text)[0]


def post_stream():
    """All posts of the two channels of the president (no reposts), oldest first: (published_at, url, text)."""
    out = []
    for ch in ("OP_UA", "V_Zelenskiy_official"):
        for r in load_posts(ch):
            if not r["forwarded_from"] and r["text"].strip():
                out.append((utc(r["published_at"]), r["url"], r["text"].strip()))
    out.sort(key=lambda p: (p[0], p[1]))
    return out


def place_hints(stream, kinds):
    """url -> (kind, place word) for every post that names a place or follows one within PLACE_HOURS[kind]."""
    out, cur = {}, None
    for at, url, text in stream:
        tok, loose = own_place_ex(text)
        if tok in kinds and not (loose and kinds[tok] == "kyiv"):
            cur = (kinds[tok], tok, at)
            out[url] = (kinds[tok], tok)
        elif cur and at - cur[2] <= timedelta(hours=PLACE_HOURS[cur[0]]):
            out[url] = (cur[0], cur[1])
    return out


def first_line(text, n=160):
    return re.sub(r"\s+", " ", text.strip().split("\n")[0])[:n]


def first_sentence(text, n=220):
    """First sentence of a post (up to the first sentence mark or line break), at most n characters."""
    return re.split(r"(?<=[.!?\u2026])\s|\n", text.strip(), maxsplit=1)[0][:n]


def mk(src, url, ann, d1, d2, typ, title, text, allowed, label=None, country=""):
    return {"src": src, "url": url, "announced_at": ann, "event_date": d1, "end_date": d2 or d1, "type": typ,
            "title": title, "text": text, "allowed": tuple(allowed), "label": label or SRC_LABEL[src], "country": country}


def tg_candidates():
    EXCLUDED.clear()
    out = []
    for ch, src in (("OP_UA", "tg_op"), ("V_Zelenskiy_official", "tg_zel")):
        for r in load_posts(ch):
            if r["forwarded_from"] or not r["text"].strip():
                continue
            at = utc(r["published_at"])
            d = kyiv_day(at)
            typ = next((t for t, rx in TG_RULES if re.search(rx, r["text"], re.I)), None)
            if typ and D_FROM <= d <= D_TO:
                if RECAP_RX.search(r["text"]):
                    EXCLUDED.append({"src": src, "url": r["url"], "event_date": d.isoformat(), "type": typ, "title": first_line(r["text"])})
                    continue
                allowed = ("kyiv", "world", "none") + (("russia",) if PUTIN.search(r["text"]) else ())
                c = mk(src, r["url"], at, d, d, typ, first_line(r["text"]), r["text"].strip(), allowed)
                c["own_place"] = own_place(r["text"])
                out.append(c)
    return out


def kremlin_type(title):
    if re.search(r"[Tt]elephone conversation|^Conversation with", title):
        return "call_trump" if "Trump" in title else "call"
    return next((t for t, rx in KR_RULES if re.search(rx, title)), None)


def kremlin_candidates():
    out = []
    for fn, src in (("kremlin_news.jsonl", "kremlin_news"), ("kremlin_trips.jsonl", "kremlin_trips")):
        with open(CAL / fn, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f]
        for r in rows:
            title = r["title"]
            if src == "kremlin_news" and (KR_SKIP.search(title) or not (typ := kremlin_type(title))):
                continue
            if src == "kremlin_trips":
                typ = ("putin_trip_abroad" if re.match(r"(State|Official|Working) visit to", title)
                       else "putin_trip_domestic" if re.match(r"(Trip|Visit) to", title) else "putin_trip")
            pub = utc(r["published_at"])
            d1 = d2 = kyiv_day(pub)
            ann = pub + timedelta(hours=24)  # the page time is the event time, the record appears later (PARSING 6)
            if re.search(r"\bwill\b", title) and (dd := parse_dates(title, pub.year)) and dd[0] >= d1:
                d1, d2 = dd  # an announcement of a future event is public at the page time
                ann = pub
            country = ""
            if m := re.match(r"(?:State|Official|Working) visit to (?:the )?([A-Z][\w' -]+?)(?:[.,]|$| and )", title):
                country = m[1]
            if D_FROM <= d1 <= D_TO:
                allowed = ("russia", "none")  # the class facts decide: calls, statements and award ceremonies are none
                out.append(mk(src, r["url"], ann, d1, d2, typ, title, "", allowed, country=country))
    return out


# ---------------------------------------------------------------------------------------------- Wikipedia (wikitext)

MONTHS = {m: i for i, m in enumerate("January February March April May June July August September October November December".split(), 1)}
_MN = "|".join(MONTHS)
_DASH = r"\s*[\u2013\u2014-]\s*"
_ISO = r"\d{4}-\d\d-\d\d(?:" + _DASH + r"\d{4}-\d\d-\d\d)?"


def parse_dates(s, year=None):
    """(start, end) of the date forms the Wikipedia tables use, else None. Forms: 2026-07-15, 2026-08-23-2026-08-24,
    19-20 May, 31 August - 1 September, 15 April 2026, 7-8 July 2026, September 1-4, September 1."""
    s = s.strip()

    def d(day, mon, y):
        return date(int(y or year), MONTHS[mon], int(day))
    try:
        if m := re.search(r"(\d{4})-(\d\d)-(\d\d)(?:" + _DASH + r"(\d{4})-(\d\d)-(\d\d))?", s):
            a = date(int(m[1]), int(m[2]), int(m[3]))
            return a, (date(int(m[4]), int(m[5]), int(m[6])) if m[4] else a)
        if m := re.search(rf"(\d{{1,2}})\s+({_MN})(?:\s+(\d{{4}}))?{_DASH}(\d{{1,2}})\s+({_MN})(?:\s+(\d{{4}}))?", s):
            y = m[3] or m[6]
            return d(m[1], m[2], y), d(m[4], m[5], m[6])
        if m := re.search(rf"(\d{{1,2}}){_DASH}(\d{{1,2}})\s+({_MN})(?:\s+(\d{{4}}))?", s):
            return d(m[1], m[3], m[4]), d(m[2], m[3], m[4])
        if m := re.search(rf"(\d{{1,2}})\s+({_MN})(?:\s+(\d{{4}}))?", s):
            a = d(m[1], m[2], m[3])
            return a, a
        if m := re.search(rf"({_MN})\s+(\d{{1,2}})(?:(?:{_DASH}|\s+to\s+)(\d{{1,2}}))?", s):
            return d(m[2], m[1], None), d(m[3] or m[2], m[1], None)
    except (ValueError, TypeError):
        return None
    return None


def _tpl(m):
    parts = m.group(1).split("|")
    name = parts[0].strip().lower()
    if name == "sort" and len(parts) > 2:
        return parts[2]
    if name in ("flag", "flagu", "flag icon", "flagicon", "flagcountry", "nowrap") and len(parts) > 1:
        return parts[1]
    return ""


def clean(s):
    """Wikitext cell to plain text: no refs, templates, links or markup."""
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{\{([^{}]*)\}\}", _tpl, s)
    s = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", s, flags=re.I)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\]", "", s)
    s = re.sub(r"<[^>]+>", "", s).replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", unescape(s)).strip()


def flag_country(cell):
    m = re.search(r"\{\{\s*(?:flag|flagu|flagicon|flag icon|flagcountry)\s*\|\s*([^|}]+)", cell, re.I)
    return m[1].strip() if m else None


_ATTR = re.compile(r"""^\s*(?:(?:rowspan|colspan|style|class|valign|align|width|height|scope|data-sort-value|bgcolor)\s*=\s*"""
                   r"""(?:"[^"]*"|'[^']*'|[^\s|]+)\s*)+\|(?!\|)""")


def split_cells(s):
    cells = []
    for c in s.split("||"):
        c = _ATTR.sub("", c, count=1)
        cells.append((c[1:] if c.startswith("|") else c).strip())
    return cells


def wiki_rows(text):
    """Rows of every wikitable as (nearest heading, [raw cells])."""
    head, row = "", None
    for line in text.split("\n"):
        s = line.strip()
        if m := re.match(r"^(=+)\s*(.*?)\s*\1$", s):
            head = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        elif s.startswith("{|"):
            row = None
        elif s.startswith("|-") or s.startswith("|}"):
            if row:
                yield head, row
            row = [] if s.startswith("|-") else None
        elif row is not None and s.startswith("|") and not s.startswith("|+"):
            row.extend(split_cells(s[1:]))
        elif row is not None and s.startswith("!"):
            continue
        elif row and s:
            row[-1] += " " + s


def wiki_revisions(path):
    """All revisions of a bronze wiki file, oldest first: (timestamp, revid, wikitext)."""
    d = json.load(open(path, encoding="utf-8"))
    revs = {}

    def add(resp):
        for pg in resp.get("query", {}).get("pages", []):
            for r in pg.get("revisions") or []:
                c = ((r.get("slots") or {}).get("main") or {}).get("content", r.get("content"))
                if c is not None:
                    revs[r["revid"]] = (r["timestamp"], c)
    add(d["base"]["response"])
    for x in d["revisions"] + d["snapshots"]:
        add(x["response"])
    return [(ts, rid, c) for rid, (ts, c) in sorted(revs.items(), key=lambda kv: (kv[1][0], kv[0]))]


def _wiki_row(info):
    """What a revision says about one event: the fields of the candidate. A change in any of them starts a new version."""
    return (info["title"], info["text"], info["country"], info["event_date"], info["end_date"])


def wiki_events(path, parse):
    """Versions of the events that the newest revision lists (the set of keys is that of the newest revision). A key has one version for
    each distinct row (title, text, country, dates) in the revisions where it appears: a new version starts in the revision where the row
    differs from the previous version of the key (a key that is missing from some revisions and returns unchanged keeps its version).
    announced_at and url are those of the revision where the version starts (the base revision before 2026-04-01 for a row that was
    already there), so a version knows nothing that was added to the page later. latest marks the version of the newest revision."""
    versions, last = {}, {}
    for ts, rid, text in wiki_revisions(path):
        last = parse(text)
        for k, info in last.items():
            vs = versions.setdefault(k, [])
            if not vs or _wiki_row(vs[-1]) != _wiki_row(info):
                vs.append(dict(info, key=k, revid=rid, announced_at=utc(ts), url=f"https://en.wikipedia.org/w/index.php?oldid={rid}"))
    return [dict(v, latest=i == len(versions[k]) - 1) for k in last for i, v in enumerate(versions[k])]


def _infobox(text, typ, title, text2, parts):
    m = re.search(r"^\|\s*date\s*=\s*(.+)$", text, re.M)
    dd = parse_dates(clean(m[1]), 2026) if m else None
    if not dd:
        return {}
    return {(typ, dd[0].isoformat()): {"event_date": dd[0], "end_date": dd[1], "title": title, "text": text2, "country": parts}}


def p_g7(text):
    return _infobox(text, "g7", "G7 summit in Evian-les-Bains, France", "Summit of the leaders of the G7 states.", "G7 FR")


def p_nato(text):
    return _infobox(text, "nato", "NATO summit in Ankara, Turkey",
                    "Summit of the heads of state and government of the NATO member states.", "NATO TR")


def p_eef(text):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.fullmatch(r"\|\s*2026\s*", ln.strip()):
            for nxt in lines[i + 1:i + 4]:
                if nxt.strip().startswith("|") and (dd := parse_dates(clean(nxt.strip()[1:]), 2026)):
                    return {("eef", dd[0].isoformat()): {"event_date": dd[0], "end_date": dd[1], "country": "RU",
                                                          "title": "Eastern Economic Forum in Vladivostok, Russia",
                                                          "text": "Annual international economic forum, usually attended by Vladimir Putin."}}
    return {}


def p_euco(text):
    out = {}
    for m in re.finditer(r"european-council/2026/(\d\d)/(\d\d)(?:-(\d\d))?/", text):
        a, b = date(2026, int(m[1]), int(m[2])), date(2026, int(m[1]), int(m[3] or m[2]))
        out[("euco", a.isoformat())] = {"event_date": a, "end_date": b, "country": "EUCO",
                                        "title": "European Council meeting", "text": "Meeting of the heads of state or government of the EU."}
    return out


def p_udcg(text):
    out = {}
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("|") and "<ref" not in s[:40] and (m := re.match(rf"^\|[^<\d]{{0,25}}(\d{{1,2}})\s+({_MN})\s+2026\b", s)):
            a = date(2026, MONTHS[m[2]], int(m[1]))
            num = re.search(r"'''(\d+)'''", s)
            out[("udcg", a.isoformat())] = {"event_date": a, "end_date": a, "country": "UDCG",
                                            "title": "Ukraine Defense Contact Group meeting (Ramstein format)" + (f" no. {num[1]}" if num else ""),
                                            "text": "Meeting of the defence ministers of the countries that support Ukraine."}
    return out


def p_trips(kind, heads):
    def parse(text):
        out = {}
        for head, cells in wiki_rows(text):
            if head.lower() not in heads:
                continue
            ci = next((i for i, c in enumerate(cells) if flag_country(c)), None)
            if ci is None:
                continue
            country, di, dt = flag_country(cells[ci]), None, None
            for i, c in enumerate(cells):
                cc = clean(c)
                if i != ci and 0 < len(cc) <= 45 and (r := parse_dates(cc, 2026)):
                    di, dt = i, r
                    break
            if dt is None:
                continue
            areas = ", ".join(x for x in (clean(c) for c in cells[ci + 1:di]) if x)
            details = next((x for x in (clean(c) for c in cells[di + 1:]) if x), "")
            out[(kind, country, dt[0].isoformat())] = {"event_date": dt[0], "end_date": dt[1], "country": country,
                                                       "title": "", "text": (areas + ". " if areas else "") + details}
        return out
    return parse


def p_visits(text):
    out, country, leader = {}, "", ""
    for _, cells in wiki_rows(text):
        di = next((i for i, c in enumerate(cells) if re.fullmatch(_ISO, clean(c))), None)
        if di is None:
            continue
        for c in cells[:di]:
            if fc := flag_country(c):
                country = fc
            elif "[[" in c:
                leader = clean(c)
        a, b = parse_dates(clean(cells[di]))
        if not (D_FROM <= a <= D_TO):
            continue
        details = clean(cells[di + 1]) if di + 1 < len(cells) else ""
        refs = re.findall(r"\|\s*title\s*=\s*([^|}\n]+)", " ".join(cells[di + 1:]))[:2]
        out[("visit_ua", country, leader, a.isoformat())] = {
            "event_date": a, "end_date": b, "country": country, "title": f"Visit to Ukraine of the head of state or government {leader or 'an unnamed leader'} ({country})",
            "text": details + (" Reports: " + "; ".join(r.strip() for r in refs) if refs else "")}
    return out


WIKI_PAGES = [  # (file prefix, parser, event type, allowed classes, label of the source, title template)
    ("52nd_G7_summit", p_g7, "g7", ("world",), "Wikipedia article about the G7 summit", None),
    ("2026_Ankara_NATO_summit", p_nato, "nato", ("world",), "Wikipedia article about the NATO summit", None),
    ("Eastern_Economic_Forum", p_eef, "eef", ("russia",), "Wikipedia article about the Eastern Economic Forum", None),
    ("List_of_European_Council_meetings", p_euco, "euco", ("world",), "Wikipedia list of European Council meetings", None),
    ("Ukraine_Defense_Contact_Group", p_udcg, "udcg", ("world",), "Wikipedia article about the Ukraine Defense Contact Group", None),
    ("List_of_international_presidential_trips_made_by_Vladimir_Putin", p_trips("putin_trip", {"2026"}), "putin_trip",
     ("russia",), "Wikipedia list of foreign trips of Vladimir Putin", "Trip of Putin to {country}"),
    ("List_of_international_presidential_trips_made_by_Volodymyr_Zelenskyy", p_trips("zelensky_trip", {"2026", "future trips"}),
     "zelensky_trip_abroad", ("world",), "Wikipedia list of foreign trips of Volodymyr Zelensky", "Trip of Zelensky to {country}"),
    ("List_of_heads_of_state_and_government_who_have_visited_Ukraine", p_visits, "visit_to_ukraine", ("kyiv", "none"),
     "Wikipedia list of heads of state and government who visited Ukraine", None),
]


def wiki_candidates():
    out = []
    for prefix, parse, typ, allowed, label, tpl in WIKI_PAGES:
        path = next(CAL.glob(f"wiki/{prefix}*.json"))
        for e in wiki_events(path, parse):
            if not (D_FROM <= e["event_date"] <= D_TO):
                continue
            title = e["title"] or tpl.format(country=e["country"])
            c = mk("wiki", e["url"], e["announced_at"], e["event_date"], e["end_date"], typ, title, e["text"], allowed, label, e["country"])
            c.update(wkey="|".join(str(x) for x in e["key"]), revid=e["revid"], latest=e["latest"])
            out.append(c)
    return out


def collect():
    cands = tg_candidates() + kremlin_candidates() + wiki_candidates()
    for c in cands:
        txt = " ".join((c["country"], c["title"], c["text"]))
        if c.get("own_place"):  # the city of a meeting is not a participant
            txt = re.sub(rf"\b{re.escape(c['own_place'])}\b", " ", txt)
        c["participants"] = participants_of(txt)
        if c["src"].startswith("kremlin") and all(p == "RU" for p in c["participants"]):  # country not in the lexicon
            m = re.search(r"\b(?:President|Prime Minister|King|Emir|Crown Prince|Chancellor|Sultan|Chairman|Leader|Minister|Sheikh)"
                          r" of (?:the )?([A-Z][A-Za-z']+)", c["title"])
            if m and m[1] != "Russia":
                c["participants"] = [m[1].upper()] + c["participants"]
        c["main"] = main_participant(c["participants"], c["type"])
        c["cid"] = hashlib.sha1(f"{c['src']}|{c['url']}|{c['type']}|{c['event_date']}|{c['main']}".encode()).hexdigest()[:16]
    return cands


# ------------------------------------------------------------------------------------------------------------- Jev

PRE = ("The state describes one candidate political event: `source` says where the description comes from, `title` and `text` "
       "describe the event (Ukrainian, Russian or English; the text may be empty; dates and years were removed on purpose). ")
PLACE_NOTE = ("The optional field `place` was found by code in the announcements of the office of the president of Ukraine: it says "
              "whether the president of Ukraine is in Kyiv, elsewhere in Ukraine or abroad. ")


def noul(question, true, false, place=False):
    return {"type": "noul", "instructions": PRE + (PLACE_NOTE if place else "") + question,
            "criteria": {"true": true, "false": false}}


FACT_QUESTIONS = {  # one judgement per question (docs/JEV.md); the code combines the answers into the class and the level
    # what the event is: any of the first six makes the candidate class none
    "remote_call": noul(
        "Is the event a telephone call, a video call or another remote conversation?",
        "The event is a telephone call, a video call, a videoconference or an online meeting: the participants are not in the same place; "
        "or the text says only that the speaker spoke with a person or had a conversation with a person (for example 'spoke with', "
        "'had a conversation with') and names no meeting, no visit, no talks and no arrival, and does not say that the participants "
        "were in the same place.",
        "The participants are in the same place (a meeting, a visit, talks, a summit, a forum), or the text names a meeting, a visit, "
        "talks or an arrival, or the event is not a conversation."),
    "statement": noul(
        "Is the text only the remarks of a speaker (a statement, an address, a comment, thanks, remarks to journalists) or an "
        "announcement of a visit that has not begun, with no meeting, visit, talks, summit or forum that has taken place or is "
        "taking place as the subject of the text?",
        "An address (for example a daily video address), a speech to the nation, a statement, a comment, an interview, a message, a "
        "greeting, condolences; thanks, gratitude or congratulations of the speaker when no meeting is reported; an address or a "
        "message sent to the participants and guests of an event (a forum, a festival, a conference, a tournament) by a speaker who "
        "is not there (a video or written address), also when the title names the participants and guests; remarks made to "
        "journalists or the press (a press conference, a briefing, a comment to the media, a communication with journalists), "
        "before, during or after a meeting: the text is then the remarks and the meeting is only the occasion; an announcement or "
        "a discussion of a visit, a meeting or talks that are still to come and have not begun, including a preparatory "
        "consultation of the officials of one country.",
        "A meeting, a visit, talks, negotiations, a summit, a forum or a conference takes place and the text reports it: who met "
        "whom, who took part, what was discussed or agreed, also when the text begins or ends with thanks; the arrival of the "
        "speaker at the place of a visit or a summit (the visit has begun), also when the text lists the meetings planned there; a "
        "speech given in person to the participants at a session of a summit, a forum or a conference is part of that event, also "
        "when the post only quotes the speech and names the summit where it was given; it is not a remark to the press."),
    "ceremony": noul(
        "Is the event a ceremony of awarding state decorations, titles, ranks or prizes?",
        "A ceremony of awarding or presenting state decorations, honorary titles, military ranks or prizes.",
        "Any other event; a meeting in which a decoration is mentioned in passing is not an award ceremony."),
    "damage_report": noul(
        "Is the event a report about an enemy attack, its damage or casualties, or about the situation at the front?",
        "The text mainly reports an enemy strike or shelling, destroyed or damaged buildings or infrastructure, casualties, or the "
        "situation on the front line.",
        "A meeting, a visit, talks or a summit takes place, even when attacks or the front are discussed there."),
    "recap": noul(
        "Is the post a recap: does it mainly sum up what happened over a period of time or in earlier events, instead of reporting "
        "one event of the day it was posted?",
        "A summary of a week, a month, a season or a year; a count of the meetings or calls of a period; a digest of the main points "
        "of an address; a look back at a summit or a trip that has already ended.",
        "A report or an announcement of one event of the day: a meeting, a visit, a telephone call, a speech at a forum, a signed "
        "agreement, a summit that is going on."),
    "inspection": noul(
        "Is the event a domestic working trip or inspection of Ukrainian officials inside Ukraine?",
        "The president of Ukraine or another Ukrainian official visits a region, a front-line unit, a military or industrial site, a "
        "hospital, a damaged place or a construction site in Ukraine, meets soldiers, local officials or residents, or checks the "
        "progress of work.",
        "A meeting, talks, a visit or a summit with foreign leaders, foreign officials or foreign delegations (also when it is held in "
        "Ukraine), or an event abroad or in Russia."),
    # where the event is and who acts in it
    "in_kyiv": noul(
        "Does the event take place in the city of Kyiv?",
        "The text or `place` says that the event takes place in Kyiv or in the capital of Ukraine, or in an institution seated in Kyiv "
        "(the Office of the President, the Verkhovna Rada, the Mariinskyi Palace), or says that foreign guests come to Kyiv; or the text "
        "names no place at all and is a meeting, talks or a visit that the president of Ukraine holds with guests who came to him.",
        "The text names another place for the event: another city, town, village or region of Ukraine, a foreign country or city, Russia, "
        "or the front; or `place` says that the president is outside Kyiv and the text does not say that the event is in Kyiv.",
        place=True),
    "ukraine_elsewhere": noul(
        "Does the event take place in Ukraine, outside the city of Kyiv?",
        "The text or `place` names a place in Ukraine other than the city of Kyiv as the place of the event: another city, town, village "
        "or region (for example Lviv, Odesa, Kharkiv, Dnipro, Zaporizhzhia), or the front.",
        "The event is in Kyiv, abroad or in Russia, or the text names no place in Ukraine other than Kyiv.",
        place=True),
    "abroad": noul(
        "Does the event take place outside Ukraine?",
        "A foreign country or city, or an international organization seated abroad, is written in the text or in `place` as the place of "
        "the event (for example 'in Ankara', 'arrived in Norway'), or `place` says that the president of Ukraine is outside Ukraine and "
        "the event is a meeting, talks or a summit of the president.",
        "The event is in Ukraine, or no foreign place is written for the event. Do not infer the place from the guests, from the name of "
        "a summit or from what you know about the event: the nationality of a guest or the country of a delegation does not make the "
        "place foreign.",
        place=True),
    "place_written": noul(
        "Is a geographic place written in the text or in `place` as the place where the event takes place?",
        "The name of a city, town, village, region or country is written as the place of the event (for example 'in Ankara', 'in Norway', "
        "'in Kyiv', 'in a village of the region'), or `place` gives such a name.",
        "No geographic name is given as the place of the event. A summit, a forum, a format or an initiative with a name is not a "
        "place; the nationality of a guest is not a place.",
        place=True),
    "russian_leadership": noul(
        "Is Vladimir Putin, the president of Russia, physically present at the event, or does he hold it himself (a meeting, talks, "
        "a trip, a forum, a summit), or is the event held by the Kremlin (the office of the president of Russia)?",
        "The description says that Putin meets someone, holds talks, travels, attends, speaks at or hosts a forum or a summit, or "
        "that the Kremlin holds the event; or the source is the website of the president of Russia and the item reports an event of "
        "the president.",
        "Putin is not present. He is only named, quoted, criticized or addressed in the words of a speaker, or the speaker says what "
        "Putin plans, decides or does next, or speaks about Russian aggression, sanctions or negotiations, at an event held by Ukraine, "
        "by other countries or by international bodies (for example the president of Ukraine at a summit says what Putin will decide "
        "next: Putin is not at the summit). A post of the Telegram channel of the president of Ukraine or of his office reports an "
        "event of Ukraine and its partners, and Putin or the Kremlin is there only when the text says so. Also false when the "
        "description does not mention Putin or the Kremlin."),
    # who takes part: the importance facts, all about the people present in person; what the description does not say is false
    "in_person": noul(
        "Does the event include people meeting face to face?",
        "An in-person meeting, visit, talks, negotiations, a summit, a forum or a conference where the participants are in the same place.",
        "A telephone or video call, an online meeting, an address, a statement, a message, a report, or an award ceremony with no meeting; "
        "or the description does not say that people met."),
    "us_president": noul(
        "Does the description say that the President of the United States (Donald Trump) takes part in the event in person?",
        "The description names the President of the United States or Donald Trump among the participants who are physically present: he "
        "meets, visits, hosts or attends, and the description itself says so.",
        "The description does not say that he is present: he is only mentioned, or he takes part by telephone or video, or a meeting "
        "with him is only planned for the future, or the description speaks of the team, the representatives, the envoys, the "
        "administration or the office of the President of the United States. A summit, a session or a general assembly does not make "
        "him present unless the description says that he attends. Other Americans are not the President: a member of the US Congress "
        "or a delegation of Congress, a senator, a congressman, the Vice President, the Secretary of State or another secretary, a "
        "special envoy, an ambassador."),
    "us_russia_presidents": noul(
        "Does the description say that the President of the United States and the President of Russia meet in person?",
        "The description says that Donald Trump and Vladimir Putin are both physically present and meet face to face: a summit or a "
        "meeting of the two presidents.",
        "Only one of them is mentioned, or neither is mentioned, or they speak by telephone or video, or the description does not say "
        "that they meet."),
    "leaders5": noul(
        "Do heads of state or government of at least five countries themselves take part in person in the event that the state "
        "describes (not in another event that the text only mentions)?",
        "The description says that presidents, prime ministers, chancellors, monarchs or other heads of state or government of five or "
        "more countries are physically present at this event, or names five or more such leaders as present, or says that the summit "
        "brought together five or more countries; or the event is a multilateral summit of leaders held in person (a summit of the G7, "
        "NATO, the European Council, the European Political Community, BRICS, the SCO, the Crimea Platform, NB8, the Bucharest Nine "
        "or a similar group of countries); the plenary session, a working session and a speech given there belong to the summit.",
        "Fewer than five such leaders, or none; or the leaders take part only online; or the description does not say that several "
        "leaders are present. Not a summit of leaders: a bilateral meeting or a meeting of a few leaders, also when it is held on the "
        "sidelines of a summit (unless the description says that five or more leaders take part in it); an economic forum, a "
        "conference, an exhibition, a ceremony or a presentation where the description names no leaders; an event of the spouses of "
        "leaders, of ministers or of delegations on the sidelines of a summit; thanks, congratulations or praise addressed to leaders; "
        "a summit, an alliance or a group of states only mentioned: as an earlier or a coming event, as the topic of the talks, as the "
        "reason for thanks or as a list of countries, while the event itself is a meeting, a visit, a conversation or a statement of "
        "one person or of a small group (for example a meeting with a member of the US Congress, with a minister or with the Secretary "
        "General of NATO)."),
    "head_major": noul(
        "Is a head of state or head of government of one of the listed countries physically present at the event? The list: the "
        "United States, China, India, Brazil, the United Kingdom, France, Germany, Italy, Japan, Canada, Turkey, Poland; and the "
        "President of the European Commission and the President of the European Council.",
        "The description names the president, the prime minister, the chancellor or the monarch of one of these twelve countries, or "
        "the President of the European Commission or of the European Council, as physically present (a meeting, a visit, talks, a "
        "trip to or from that leader); this includes a summit of the leaders of a group that includes these countries, such as the G7, "
        "NATO or the European Council, when the description says that the summit takes place or that its leaders are present.",
        "The head of any other country (for example Norway, the Netherlands, Sweden, Finland, Denmark, Ireland, Spain, Belgium, the "
        "Czech Republic, Lithuania, Latvia, Estonia, Moldova, Azerbaijan), however friendly to Ukraine; or a person who is not a head "
        "of state or government, even when the person comes from one of the listed countries: a member of a parliament, a congress or "
        "a diet and a delegation of legislators (for example of the House of Representatives of Japan), a speaker of a chamber, a "
        "minister, an ambassador, a general, an envoy, the spouse of a leader; or the leader takes part only by telephone or video, or "
        "only a coming meeting is announced, or the description does not mention such a leader."),
    "head_any": noul(
        "Is a foreign head of state or head of government physically present at the event?",
        "A president, prime minister, chancellor, monarch or other head of state or government of a country other than Ukraine and "
        "Russia, in office now, is physically present at the event: a meeting, a visit, talks, a summit. The President of the "
        "European Commission and the President of the European Council count as well.",
        "No such leader is present: only ministers, officials or delegations take part; or the person is not a head of state or "
        "government: a member of a parliament, a congress or a diet, a delegation of legislators, a speaker of a chamber, an "
        "ambassador or a permanent representative (the North Atlantic Council of NATO is a council of ambassadors), the Secretary "
        "General of NATO, a general, an envoy, a former leader, an adviser, the spouse of a leader; or the leader takes part only by "
        "telephone or video, or only a coming visit is announced, or the description does not mention such a leader."),
    "minister": noul(
        "Does a minister of a foreign government, the Secretary General of NATO or a special envoy of a head of state take part in "
        "the event in person?",
        "A minister of a country other than Ukraine and Russia (for example of foreign affairs or of defence), the Secretary General of "
        "NATO, or a special envoy or special representative of a head of state is physically present at the event that has taken "
        "place or is taking place.",
        "No such person is present, or the person takes part only by telephone or video, or the person is only expected to come in "
        "the future (a coming visit is announced), or the description does not mention such a person; a member of a parliament or a "
        "congress, an ambassador and a permanent representative are not ministers."),
}

PRESS_QUESTION = {  # one judgement in its own request: the wording of the closing line decides, a long list of other questions dilutes it
    "press_remarks": noul(
        "Is the text the speaker's remarks to journalists on a topic (a situation, sanctions, support, plans, thanks), not a report of a meeting?",
        "The text itself says (for example in its closing line) that it is from the speaker's communication with journalists, from a press conference, a briefing, a comment to the media or an interview, or that the speaker said it to journalists or to the press; and its first sentences are about a topic and do not report that a meeting, talks or a visit took place.",
        "The first sentence reports that a meeting, talks or a visit took place or is taking place (who met whom, what was agreed or decided at it), also when the text is taken from answers to journalists; or the text does not say that it is from communication with journalists; or it is a speech given to the participants of a summit, a forum or a conference."),
}
CHECK_QUESTIONS = {  # a second reading of five facts, worded as a search for the named person; p is the mean of the two readings
    "us_president": noul(
        "Does the text say that Donald Trump, the President of the United States, is present at the event, in the same place as the speaker?",
        "The text says that he meets the speaker, visits, hosts or attends in person: a meeting with him, talks with him, a visit of the speaker to him, or his name among those who take part in the session or the summit.",
        "The text does not say that he is present: he is only mentioned; or the text says only that the speaker spoke with him (a conversation, a call, communication) and does not say that they met in person; or a meeting with him is only planned or only mentioned; or the text names only his team, representatives, envoys or administration, or another American official, or a member of Congress."),
    "leaders5": noul(
        "Does the text show that the event is a summit or a meeting where the leaders (heads of state or government) of at least five countries are present in person?",
        "The text names five or more leaders as present, or says that the summit brought together five or more countries, or the event is a summit of a group of leaders (the G7, NATO, the European Council, the European Political Community, BRICS, the SCO, the CIS Council of Heads of State, the Eurasian Economic Union, ASEAN, the Coalition of the Willing, the Crimea Platform, NB8, the Bucharest Nine, a regional summit of several states) that takes place in person, including its sessions and the speeches given there.",
        "The text names fewer than five leaders, or none; or the text reports a meeting or talks of the speaker with one or two named persons, also when it says that this meeting took place within the framework of, on the sidelines of or during a summit and names that summit; or it reports a conversation; or it is a ceremony, a forum, a conference, thanks to leaders, an event of spouses or ministers; or a summit is only mentioned as an earlier or a coming event."),
    "head_major": noul(
        "Does the text name, as present at the event, the president, the prime minister, the chancellor or the monarch of the United States, China, India, Brazil, the United Kingdom, France, Germany, Italy, Japan, Canada, Turkey or Poland, or the President of the European Commission or of the European Council?",
        "The text names such a person as present: a meeting, a visit, talks, a trip, a summit.",
        "The text names no such person as present; the leader is from any other country (for example Norway, the Netherlands, Sweden, Finland, Denmark, Ireland, Spain, Lithuania, Moldova); or the person is a minister, a legislator, an ambassador, an envoy, a former leader or the spouse of a leader; or the text only thanks or lists countries; or the contact is only by telephone or video or only planned."),
    "head_any": noul(
        "Does the text name, as present at the event, a president, prime minister, chancellor or monarch of a foreign country, in office now?",
        "The text names such a person as present: a meeting, a visit, talks, a summit; the President of the European Commission and the President of the European Council count.",
        "The text names no such person as present; the person is a minister, a legislator, an ambassador, a permanent representative, the Secretary General of NATO, an envoy, a former leader or the spouse of a leader; or the text only thanks or lists countries; or the contact is only by telephone or video or only planned."),
    "remote_call": noul(
        "Does the text itself call the contact of the speaker with named persons a conversation, a talk or a call, without saying that they met in person?",
        "The text itself calls the contact a conversation, a talk or a call, or says that the speaker 'just spoke with' the named persons, and does not say that they met face to face, visited each other or were in the same place; a summit, a meeting or talks that the text names as an earlier event, which the conversation sums up or follows, do not make the conversation an in-person event.",
        "The text reports a meeting, a visit, an arrival or talks held in person ('met with', 'a meeting with', 'held a meeting', 'arrived'), a session or a speech; or the text says only that the speaker discussed something with a person, without calling it a conversation, a talk or a call; or the text is not about a contact with named persons."),
}
GATE_QUESTIONS = {  # single readings used as caps on free-form posts in score_all: leaders5 <= 1 - bilateral (if bilateral >= SURE); head_any <= max(titled, bilateral)
    "bilateral": noul(
        "Does the text report a meeting or talks of the speaker with one named person or with two named persons, and not a session, a summit or a meeting of a larger group?",
        "The text reports that the speaker met or held talks with one named person, or with two named persons, also when the text says that the meeting took place within the framework of, on the sidelines of or during a summit, a forum or a conference and names that event.",
        "The text reports a session, a plenary, a summit, a joint meeting of a group of states or of three or more named leaders, or a speech to a group; or the text is not about a meeting or talks."),
    "titled": noul(
        "Does the text itself give a person the title of president, prime minister, chancellor, head of government or monarch of a foreign country (not Ukraine, not Russia), and say that this person takes part in the event?",
        "The text names a person together with such a title and says that the person meets the speaker, visits, hosts, attends or takes part: for example 'the President of Poland', 'the Prime Minister of Italy', 'the head of the Council of Ministers of Italy', 'the Chancellor of Germany', 'the King of Norway', 'the President of the European Commission', 'the President of the European Council'; or the text calls the participants the leaders of states or the heads of state or government.",
        "The text names a person only by name, without such a title; or gives only the title of a minister, an ambassador, a permanent representative, a Secretary General, an envoy, a commissioner, a member of a parliament or a congress, a speaker of a chamber, the head of an organization, an adviser or a former leader; or the title is that of Ukraine or Russia; or the text only thanks countries or lists countries; or the person takes part only by telephone or video, or a visit is only announced."),
}
assert set(FACT_QUESTIONS) | set(PRESS_QUESTION) | set(GATE_QUESTIONS) == set(FACTS) and len(FACTS) == len(set(FACTS)) \
    and not set(FACT_QUESTIONS) & set(PRESS_QUESTION) and not set(FACT_QUESTIONS) & set(GATE_QUESTIONS) and set(CHECK_QUESTIONS) <= set(FACT_QUESTIONS)

WHERE_Q = {"where": {"type": "choice",
                     "instructions": "The state is the name of a place, in Ukrainian (usually in the locative or genitive case), taken from "
                                     "an official announcement of a meeting or a visit of the president of Ukraine. Say where this place is.",
                     "criteria": {"kyiv": "The city of Kyiv, or an institution that sits in Kyiv, such as the Verkhovna Rada, the Office of "
                                          "the President or the Mariinskyi Palace.",
                                  "ukraine": "Any other place in Ukraine: another city, town, village or region, or Ukraine as a whole.",
                                  "abroad": "A place outside Ukraine: a foreign city, region or country, or an international organization "
                                            "that sits abroad, such as the United Nations."}}}
PLACE_TEXT = {"kyiv": "the president of Ukraine is in the city of Kyiv",
              "ukraine": "the president of Ukraine is in Ukraine, outside the city of Kyiv",
              "abroad": "the president of Ukraine is outside Ukraine"}


def place_kinds(tokens):
    """Jev says what each place word is: kyiv, ukraine (other) or abroad. A few dozen words, answers are cached."""
    toks = sorted(tokens)
    ans = ask_many([({"place": t}, WHERE_Q) for t in toks], tag=TABLE, workers=WORKERS)
    return {t: a["where"]["choice"] for t, a in zip(toks, ans)}


def attach_places(cands):
    """Sets c['place'] = (kind, word) on Telegram candidates; where the president is not in Kyiv the class kyiv
    is not allowed (and outside Ukraine's capital but inside Ukraine the class world too)."""
    stream = post_stream()
    kinds = place_kinds({t for _, _, x in stream if (t := own_place(x))})
    hints = place_hints(stream, kinds)
    for c in cands:
        h = hints.get(c["url"]) if c["src"] in ("tg_op", "tg_zel") else None
        if h and h[1] != c.get("own_place") and KYIV_MENTION.search(first_sentence(c["text"] or c["title"])):
            h = None  # the hint is inherited and the first sentence of the post itself says Kyiv or Ukraine
        c["place"] = h
        if h and h[0] == "abroad":
            c["allowed"] = tuple(a for a in c["allowed"] if a != "kyiv")
        elif h and h[0] == "ukraine":
            c["allowed"] = tuple(a for a in c["allowed"] if a not in ("kyiv", "world"))
    return kinds, hints


def questions():
    return FACT_QUESTIONS


def state(c):
    st = {"source": c["label"], "title": strip_dates(c["title"]), "text": strip_dates(c["text"])[:1500]}
    if c.get("place"):
        st["place"] = f"{PLACE_TEXT[c['place'][0]]} (the announcements name the place: {c['place'][1]})"
    return st


def fact(p):
    """(truth, margin) of a Jev probability: true at p >= 0.5, margin |2p - 1| (0 is a coin toss, 1 is certain)."""
    return p >= 0.5, abs(2 * p - 1)


def f_and(*xs):
    """AND of facts: true with the smallest margin of the operands; false with the margin of the most certain false operand."""
    if all(t for t, _ in xs):
        return True, min(m for _, m in xs)
    return False, max(m for t, m in xs if not t)


def f_or(*xs):
    """OR of facts: true with the margin of the most certain true operand; false with the smallest margin of the operands."""
    if any(t for t, _ in xs):
        return True, max(m for t, m in xs if t)
    return False, min(m for _, m in xs)


def first_true(rules):
    """rules: [(value, (truth, margin))] in order. Returns (value of the first true rule, confidence): the confidence is the smallest
    margin among that rule and the rules before it, that is the facts that decided (why it holds and why the earlier ones do not)."""
    conf = 1.0
    for value, (t, m) in rules:
        conf = min(conf, m)
        if t:
            return value, conf
    return None, conf


def class_of(p, allowed):
    """(class, confidence) from the class facts p (fact -> probability). The first rule that holds wins:
    none (a call, a statement, an award ceremony, a damage report, a recap or a domestic inspection), kyiv (in Kyiv), none (in Ukraine
    outside Kyiv), russia (Putin or the Kremlin, anywhere outside Kyiv), world (outside Ukraine, without the Russian leadership: the place must be abroad and written in the text or in `place`).
    Only the classes in `allowed` take part: the source and the place of the president restrict them (a table of Wikipedia gives one
    class). If no rule holds the class is none, or the first allowed one."""
    F = {k: fact(p[k]) for k in CLASS_FACTS}
    rules = []
    if "none" in allowed:
        rules.append(("none", f_or(*(F[k] for k in NONE_REASONS))))
    if "kyiv" in allowed:
        rules.append(("kyiv", F["in_kyiv"]))
    if "none" in allowed:
        rules.append(("none", F["ukraine_elsewhere"]))
    if "russia" in allowed:
        rules.append(("russia", F["russian_leadership"]))
    if "world" in allowed:
        rules.append(("world", f_and(F["abroad"], F["place_written"])))
    cls, conf = first_true(rules)
    return (cls if cls is not None else ("none" if "none" in allowed else allowed[0])), conf


def level_of(p, cls, cls_conf):
    """(level 0..5, confidence) from the importance facts p and the class (table of the user, 2026-10-10, one scale for every class;
    docs/data/silver/political_events.md): 5 (us_president and kyiv) or us_russia_presidents; 4 leaders5 or us_president; 3 head_major
    or (head_any and kyiv); 2 head_any or minister; 1 in_person; 0 otherwise. A fact is true at p >= 0.5."""
    F = {k: fact(p[k]) for k in IMP_FACTS}
    ky = (cls == "kyiv", cls_conf)
    return first_true([
        (5, f_or(f_and(F["us_president"], ky), F["us_russia_presidents"])),
        (4, f_or(F["leaders5"], F["us_president"])),
        (3, f_or(F["head_major"], f_and(F["head_any"], ky))),
        (2, f_or(F["head_any"], F["minister"])),
        (1, F["in_person"]),
        (0, (True, 1.0)),
    ])


def jev_p(a, name):
    v = a[name]
    return float(v["noul"] if isinstance(v, dict) else v)


def ask_states(states, qs):
    """Jev answers to the questions qs for every state, in the order of the states; identical states are asked once (parallel twins
    could get different answers)."""
    keys = [json.dumps(st, sort_keys=True, ensure_ascii=False) for st in states]
    todo = list(dict(zip(keys, states)).items())
    got = {}
    for i in range(0, len(todo), 120):
        chunk = todo[i:i + 120]
        for (key, _), ans in zip(chunk, ask_many([(st, qs) for _, st in chunk], tag=TABLE, workers=WORKERS)):
            got[key] = ans
        print(f"jev {len(got)}/{len(todo)} distinct states, questions {sorted(qs)[:2]}.. ({len(qs)})", flush=True)
    return [got[k] for k in keys]


def mark_abroad_twins(scored):
    """The default puts a meeting of the president with foreign guests in Kyiv when no place is written. If another candidate (Telegram of the
    office or of the president, or a Wikipedia trip of the president abroad) covers the same day, names a foreign place and names the same
    participant, it is the same meeting held abroad: the default candidate gets class none and s['twin'] = cid of the twin. A row only
    disappears; nothing of the twin enters another row, and the twin keeps its own announcement time."""
    abroad = [t for t in scored if t["class"] in ("world", "russia") and t["p"]["abroad"] >= 0.5 and t["p"]["place_written"] >= 0.5
              and (t["src"] in TG_SRC or (t["type"] == "zelensky_trip_abroad" and t["latest"]))]
    for s in scored:
        s["twin"] = None
        if s["class"] == "kyiv" and s["src"] in TG_SRC and s["p"]["place_written"] < 0.5:
            mine = set(s["participants"]) - GENERIC
            t = next((t for t in abroad if mine & (set(t["participants"]) - GENERIC) and t["event_date"] <= s["event_date"] <= t["end_date"]), None)
            if t:
                s["twin"], s["class"] = t["cid"], "none"


def score_all(cands):
    attach_places(cands)
    states = [state(c) for c in cands]
    bad = [(c["url"], leak_scan(" ".join(str(v) for v in st.values()))) for c, st in zip(cands, states)]
    bad = [b for b in bad if b[1]]
    if bad:
        raise SystemExit(f"a date is left in the Jev state of {len(bad)} candidates, first: {bad[:3]}")
    main, press, check, gate = (ask_states(states, qs) for qs in (questions(), PRESS_QUESTION, CHECK_QUESTIONS, GATE_QUESTIONS))
    out = []
    for c, st, a, b, d, g in zip(cands, states, main, press, check, gate):
        p = {f: jev_p(a, f) for f in FACT_QUESTIONS}
        p.update({f: jev_p(b, f) for f in PRESS_QUESTION})
        p.update({f: jev_p(g, f) for f in GATE_QUESTIONS})
        for f in CHECK_QUESTIONS:
            q = jev_p(d, f)
            p[f] = max(p[f], q) if f == "remote_call" else (p[f] + q) / 2  # two readings: the mean settles a coin toss; for a call either reading is enough
        if c["src"] in TG_SRC:  # free-form posts only (the tables of Wikipedia and the titles of Kremlin are structured)
            if p["bilateral"] >= SURE:
                p["leaders5"] = min(p["leaders5"], 1 - p["bilateral"])  # a bilateral meeting on the sidelines of a summit is not the summit
            p["head_any"] = min(p["head_any"], max(p["titled"], p["bilateral"]))  # a bare name makes a head of state only as the counterpart of a bilateral meeting
        p["head_major"] = min(p["head_major"], p["head_any"])  # a head of a major country is a head: legislators of a major country are neither
        cls, ccf = class_of(p, c["allowed"])
        lvl, conf = level_of(p, cls, ccf)
        out.append(dict(c, state=st, p=p, **{"class": cls}, class_confidence=ccf, importance=lvl, importance_confidence=conf))
    mark_abroad_twins(out)
    for s in out:  # after the twins: a meeting abroad still removes its kyiv-by-default twin, then the world event itself goes
        if s["class"] == "world":
            s["class"], s["was_world"] = "none", True
    return out


# --------------------------------------------------------------------------------------------------------- silver


def dedup(scored):
    """Rows of the table from the candidates that keep_candidates returns. The key of a row is (class, main participant, event_date).
    Telegram and Kremlin: the earliest announcement gives the first row of the key; a later candidate of the key gets its own
    row only if its level is higher than the level of the key at its announcement (it is known only from its own announcement, so nothing
    leaks backwards). Wikipedia: every version of an event key (wiki_events) is its own row and is never dropped: version_of is the event
    key, revid the revision where the version starts, text the row text of that revision, available_at the time of that revision. In the
    level of a key a Wikipedia event counts with its latest version known at that time, so a later version with a lower level lowers it.
    `sources` lists the URLs of the key announced up to that row (other revisions of the same Wikipedia event left out), the first is the
    announcement that gives the row."""
    groups = defaultdict(list)
    for s in scored:
        groups[(s["class"], s["main"], s["event_date"])].append(s)
    level, home, rows = defaultdict(dict), {}, []  # level: key -> {Wikipedia event or cid: level now}; home: Wikipedia event -> key of its latest version
    for p in sorted(scored, key=lambda s: (s["announced_at"], SRC_RANK[s["src"]], -s["importance"], s["cid"])):
        g = (p["class"], p["main"], p["event_date"])
        cls, main, d = g
        wk = p.get("wkey")
        if wk:
            if home.get(wk, g) != g:
                level[home[wk]].pop(wk, None)  # this version moved the event to another key
            home[wk] = g
            level[g][wk] = p["importance"]
        elif p["importance"] <= max(level[g].values(), default=-1):
            continue
        else:
            level[g][p["cid"]] = p["importance"]
        urls = [p["url"]] + sorted({s["url"] for s in groups[g] if s["announced_at"] <= p["announced_at"]
                                    and not (wk and s.get("wkey") == wk)} - {p["url"]})
        eid = f"{cls}|{main}|{d}|{p['importance']}" + (f"|{wk}|{p['revid']}" if wk else "")
        rows.append({
            "event_id": hashlib.sha1(eid.encode()).hexdigest()[:12], "version_of": wk, "revid": p["revid"] if wk else None, "event_date": d,
            "end_date": p["end_date"], "class": cls, "type": p["type"], "title": p["title"][:200], "text": p["text"] if wk else None,
            "participants": p["participants"], "importance": p["importance"], "importance_confidence": p["importance_confidence"],
            "class_confidence": p["class_confidence"], "scheduled": p["announced_at"] < kyiv_midnight(d),
            "announced_at": p["announced_at"], "available_at": p["announced_at"], "sources": urls,
            "jev_model": MODEL, "prompt_version": PROMPT_VERSION, **{f"p_{f}": p["p"][f] for f in FACTS}})
    rows.sort(key=lambda r: (r["event_date"], r["class"], r["event_id"]))
    return rows


def keep_candidates(scored):
    """The candidates that become rows: every candidate whose class is not none, and a Wikipedia version of class none that comes right after a
    version of another class (from that revision on the event is no longer an event, and a row of class none lets the latest version win in
    features()). A Wikipedia version of class none after a version of class none, or the first version, is dropped as before."""
    prev = {}
    for s in sorted((s for s in scored if s.get("wkey")), key=lambda s: (s["announced_at"], s["revid"])):
        s["replaces"] = s["class"] == "none" and prev.get(s["wkey"], "none") != "none"
        prev[s["wkey"]] = s["class"]
    return [s for s in scored if s["class"] != "none" or s.get("replaces")]


def final_rows(rows):
    """The events of a list of rows: every row that is not a Wikipedia version, and the latest version (by available_at, then revid) of
    each Wikipedia event key."""
    last = {}
    for r in rows:
        k = r["version_of"]
        if k and (k not in last or (r["available_at"], r["revid"]) > (last[k]["available_at"], last[k]["revid"])):
            last[k] = r
    return [r for r in rows if not r["version_of"] or last[r["version_of"]] is r]


def build(dump=None):
    cands = collect()
    print(f"candidates {len(cands)}: {dict(Counter(c['src'] for c in cands))}; from {D_FROM}; recap posts left out by the code rule {len(EXCLUDED)}", flush=True)
    scored = score_all(cands)
    if dump:
        with open(dump, "w", encoding="utf-8") as f:
            for s in scored:
                f.write(json.dumps({k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in s.items()},
                                   ensure_ascii=False) + "\n")
        with open(str(dump) + ".excluded.jsonl", "w", encoding="utf-8") as f:
            for e in EXCLUDED:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    kept = keep_candidates(scored)
    rows = dedup(kept)
    SILVER.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), tmp)
    tmp.replace(PATH)
    print(f"{PATH}: {len(rows)} events from {len(kept)} candidates of {len(scored)} (none dropped {len(scored) - len(kept)}); "
          f"class {dict(Counter(r['class'] for r in rows))}; Wikipedia version rows {sum(bool(r['version_of']) for r in rows)} (class none: {sum(r['class'] == 'none' for r in rows)}); model {MODEL}, prompt {PROMPT_VERSION}")


def load_dump(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def bronze_stats():
    for ch in ("OP_UA", "V_Zelenskiy_official"):
        rows = load_posts(ch)
        own = [r for r in rows if not r["forwarded_from"] and r["text"].strip()]
        print(f"bronze {ch}: posts {len(rows)} ({min(r['published_at'] for r in rows)}..{max(r['published_at'] for r in rows)}), own (no repost, not empty) {len(own)}")
    for fn in ("kremlin_news.jsonl", "kremlin_trips.jsonl"):
        with open(CAL / fn, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f]
        print(f"bronze {fn}: rows {len(rows)} ({min(r['published_at'] for r in rows)}..{max(r['published_at'] for r in rows)})")
    print("bronze wiki files:", len(list(CAL.glob("wiki/*.json"))))


def candidates_cmd():
    bronze_stats()
    cands = collect()
    print("candidates", len(cands))
    for key, n in sorted(Counter((c["src"], c["type"]) for c in cands).items()):
        print(f"  {key[0]:14s} {key[1]:22s} {n}")
    print("by month", sorted(Counter(c["event_date"].strftime("%Y-%m") for c in cands).items()))
    rnd = random.Random(3)
    for c in rnd.sample(cands, 6):
        print(f"- {c['src']} {c['type']} {c['event_date']}..{c['end_date']} ann {c['announced_at']} main {c['main']} parts {c['participants']}\n"
              f"  {c['title'][:110]}")
    wk = [c for c in cands if c["src"] == "wiki"]
    print(f"wiki candidates: {len(wk)} versions of {len({c['wkey'] for c in wk})} keys, keys with more than one version "
          f"{sum(v > 1 for v in Counter(c['wkey'] for c in wk).values())}")
    for c in sorted(wk, key=lambda c: (c["type"], c["event_date"], c["announced_at"])):
        print(f"  {c['type']:18s} {c['event_date']}..{c['end_date']} ann {c['announced_at']:%Y-%m-%dT%H:%MZ} {c['title'][:60]}")


def strip_demo():
    print(inspect.getsource(strip_dates))
    titles = [
        "Зустріч з Прем'єр-міністром Великої Британії 15 червня 2026 року у Києві, 24.04.2026 https://bit.ly/4cu47zX",
        "Trip of Putin to China: 19-20 May 2026, State visit; talks with Xi Jinping in Beijing on May 19",
        "On October 8-9, Vladimir Putin will make a working visit to Turkmenistan. Meeting 2026-10-08 of the CIS Council of Heads of State",
    ]
    for t in titles:
        print("IN :", t)
        print("OUT:", strip_dates(t))
    print("more cases (abbreviated months, dd.mm, date-time, FY2026); LEFT is what leak_scan still finds:")
    for t in ["a visit to Serbia on Aug. 8", "Summit Sep 11-13 in Kyiv", "meeting on Oct 8", "15.06 and 1.07 and 3.5 bn", "FY2026 budget",
              "2026-06-15T12:00:00Z start", "15 черв. зустріч", "Mar-a-Lago talks", "the 20th package of sanctions"]:
        o = strip_dates(t)
        print(f"IN : {t}\nOUT: {o}\nLEFT: {leak_scan(o)}")


ANCHORS = [  # (name, class, first day, last day, participant code, type, expected level, expected scheduled, regex on the title): the anchors of the user
    ("summit of 24 countries in Kyiv", "kyiv", date(2026, 5, 26), date(2026, 5, 26), None, None, 4, None, None),
    ("NB8 summit in Kyiv", "kyiv", date(2026, 8, 23), date(2026, 8, 23), None, None, 4, None, None),
    ("visit of the UK Prime Minister to Kyiv", "kyiv", date(2026, 8, 24), date(2026, 8, 25), "GB", None, 3, None, None),
    ("BRICS summit", "russia", date(2026, 9, 12), date(2026, 9, 12), None, None, 4, None, r"BRICS"),
    ("SCO summit", "russia", date(2026, 8, 31), date(2026, 9, 1), None, None, 4, None, r"SCO|Kyrgyz"),
    ("Putin and Xi Jinping", "russia", date(2026, 8, 31), date(2026, 8, 31), "CN", None, 3, None, None),
]
MISREAD = [  # (name, day, regex on the title and text of the post named in the review of pol-v4, what must hold, test on a scored candidate)
    ("meeting with US Congressman McCaul (kyiv level 4 in pol-v4)", "2026-07-10", r"Маккол", "class none or below level 4",
     lambda s: s["class"] == "none" or s["importance"] < 4),
    ("post 'Щодо ситуації у Чорному морі' (kyiv level 4 in pol-v4)", "2026-08-24", r"^\W*Щодо ситуації у Чорному морі", "class none (a statement)",
     lambda s: s["class"] == "none"),
    ("speech at the European Political Community summit that names Putin (russia level 3 in pol-v4)", "2026-05-04",
     r"^\W*Це літо буде часом, коли Путін", "class world before the world drop", lambda s: s.get("was_world")),
    ("post 'Балістика – це останній російський аргумент' (kyiv level 4 in pol-v4; the day of the NATO Council in Kyiv with Rutte)", "2026-06-03",
     r"^\W*Балістика", "class kyiv or none and below level 4", lambda s: s["class"] in ("kyiv", "none") and s["importance"] < 4),
    ("meeting with members of the House of Representatives of Japan (kyiv level 3 in pol-v5: legislators are not heads of state)", "2026-10-01",
     r"Палати представників Національного парламенту Японії", "class none or below level 3", lambda s: s["class"] == "none" or s["importance"] < 3),
    ("visit of the North Atlantic Council of NATO to Kyiv (kyiv level 3 in pol-v5: ambassadors are not heads of state)", "2026-06-03",
     r"Північноатлантичн\w+ ради", "class none or below level 3", lambda s: s["class"] == "none" or s["importance"] < 3),
    ("meeting with the Prime Minister of Norway abroad (world level 3 in pol-v5: Norway is not in the list of major countries)", "2026-09-09",
     r"Норвегії", "not class world with level 3 or more", lambda s: s["class"] != "world" or s["importance"] < 3),
    ("thanks to the leaders in the excerpt of the speech at the opening of the Irish presidency (world level 4 in pol-v5)", "2026-07-01",
     r"^\W*Я дякую всім європейським лідерам", "class none or below level 4", lambda s: s["class"] == "none" or s["importance"] < 4),
    ("remarks to journalists before the meeting with Starmer at the EPC summit (world level 4 in pol-v5)", "2026-05-03",
     r"^\W*Зараз ми знаходимо свої формати санкцій", "class none", lambda s: s["class"] == "none"),
    ("roundtable of the First Lady during the NATO summit (world level 4 in pol-v5: spouses are not leaders)", "2026-07-08",
     r"круглому столі", "class none or below level 4", lambda s: s["class"] == "none" or s["importance"] < 4),
    ("meeting with the President of Lithuania, held abroad (kyiv level 3 in pol-v6: no place written)", "2026-04-23", r"Наусєд", "not class kyiv",
     lambda s: s["class"] != "kyiv"),
    ("meeting with the Prime Minister of Denmark, held abroad (kyiv level 3 in pol-v6: no place written)", "2026-04-23", r"Фредеріксен", "not class kyiv",
     lambda s: s["class"] != "kyiv"),
    ("meeting with the Prime Minister of Italy, held abroad (kyiv level 3 in pol-v6: the post names a strike in Kyiv)", "2026-07-08", r"Мелоні", "not class kyiv",
     lambda s: s["class"] != "kyiv"),
    ("meeting with the Prime Minister of Norway, held abroad (kyiv level 3 in pol-v6: no place written)", "2026-09-09", r"Прем.єр-міністр\w* Норвегії", "not class kyiv",
     lambda s: s["class"] != "kyiv"),
    ("bilateral meeting with the President of Poland on the sidelines of a summit (world 4 in pol-v6)", "2026-05-13", r"Навроцьк", "class none or below level 4",
     lambda s: s["class"] == "none" or s["importance"] < 4),
    ("bilateral meeting with the President of Brazil on the sidelines of the G7 summit (world 4 in pol-v6)", "2026-06-17", r"Лул[аиіуо]", "class none or below level 4",
     lambda s: s["class"] == "none" or s["importance"] < 4),
    ("conversation with Trump and Macron after the G7 summit (world 4 in pol-v6)", "2026-06-17", r"^\W*Щойно говорили з Президентом США", "class none",
     lambda s: s["class"] == "none"),
    ("post about the visit of the NATO ambassadors with Rutte, no head of state named (kyiv 3 in pol-v6)", "2026-06-03", r"^\W*Сьогодні в Україні був Марк Рютте",
     "class none or below level 3", lambda s: s["class"] == "none" or s["importance"] < 3),
    ("meeting of the advisory group with a former prime minister among its members (kyiv 3 in pol-v6)", "2026-05-19", r"^\W*Вдячний, що Міжнародна консультативна група",
     "class none or below level 3", lambda s: s["class"] == "none" or s["importance"] < 3),
]


def fmt_row(r):
    facts = " ".join(f"{f}={r['p_' + f]:.2f}" for f in IMP_FACTS)
    return (f"{r['event_date']}..{r['end_date']} {r['class']} level {r['importance']} (confidence {r['importance_confidence']:.2f}) "
            f"scheduled {int(r['scheduled'])} {r['type']} [{facts}] {r['title'][:80]}"
            + (f" (version of {r['version_of']} from {r['available_at']:%Y-%m-%dT%H:%MZ})" if r.get("version_of") else ""))


def fmt_cand(s):
    facts = " ".join(f"{f}={s['p'][f]:.2f}" for f in FACTS)
    return f"{s['event_date']} {s['src']} {s['class']} level {s['importance']} [{facts}] {s['title'][:80]}"


def report(dump, out):
    from pathlib import Path
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    allrows = pq.read_table(PATH).to_pylist()
    rows = [r for r in final_rows(allrows) if r["class"] != "none"]  # the events: a Wikipedia key counts with its latest version (section 3 switches to all rows)
    scored = load_dump(dump)
    L, ok = [], True

    L.append("1. ANCHORS (event, class, facts, level)")
    for name, cls, d1, d2, part, typ, want, sched, rx_t in ANCHORS:
        hit = sorted((r for r in rows if r["class"] == cls and d1 <= r["event_date"] <= d2 and (part is None or main_participant(r["participants"], r["type"]) == part)
                      and (typ is None or r["type"] == typ) and (rx_t is None or re.search(rx_t, r["title"]))),
                     key=lambda r: (-r["importance"], r["event_date"], r["event_id"]))
        good = bool(hit) and hit[0]["importance"] == want and (sched is None or hit[0]["scheduled"] == sched)
        ok &= good
        L.append(("PASS " if good else "FAIL ") + f"{name}: expected {cls} {want}" + ("" if sched is None else f", scheduled {sched}") + f"; rows {len(hit)}")
        L += ["    " + fmt_row(r) for r in hit[:3]]
    L.append("1b. MISREADINGS of pol-v4 (fixed by the facts and the level table, no rule for a single post)")
    for name, day, rx_m, need, test in MISREAD:
        hit = [s for s in scored if s["event_date"] == day and re.search(rx_m, s["title"] + " " + s["text"], re.I)]
        good = bool(hit) and all(test(s) for s in hit)
        ok &= good
        L.append(("PASS " if good else "FAIL ") + f"{name}: must be {need}; candidates {len(hit)}")
        L += ["    " + fmt_cand(s) for s in hit[:4]]
    rx = re.compile(r"Гут[аиіу]\b|Huta|Карпат|Carpath", re.I)
    huta = [s for s in scored if date(2026, 9, 17) <= date.fromisoformat(s["event_date"]) <= date(2026, 9, 19) and rx.search(s["title"] + " " + s["text"])]
    kept = [s for s in huta if s["class"] != "none" and s.get("latest", True)]  # an event: not a Wikipedia version that a later version replaced
    t, cur_hours = datetime(2026, 4, 30, 21), 0
    while t <= max(r["available_at"] for r in allrows) + timedelta(hours=1):  # hours t at which a row that names the summit is a current event
        cur_hours += any(r["class"] != "none" and date(2026, 9, 17) <= r["event_date"] <= date(2026, 9, 19) and rx.search(r["title"] + " " + (r["text"] or ""))
                         for r in final_rows([r for r in allrows if r["available_at"] < t]))
        t += timedelta(hours=1)
    ok &= not kept and not cur_hours
    L.append(("PASS " if not (kept or cur_hours) else "FAIL ") + f"Carpathian summit in Huta is not in the table: candidates found {len(huta)}, kept as an event "
             f"(a Wikipedia key with its latest version) {len(kept)}; hours t from 2026-04-30T21:00Z at which a row of the table that names it is a current event {cur_hours}")
    L += ["    " + fmt_cand(s) for s in huta[:4]]
    rxd = re.compile(r"^\W*Заступни\w+ Керівника Офісу", re.I)
    dep = sorted((s for s in scored if rxd.search(s["title"]) and s["class"] != "none"), key=lambda s: -s["importance"])
    good = all(s["importance"] <= 2 for s in dep)
    ok &= good
    L.append(("PASS " if good else "FAIL ") + f"a deputy head of the Office (post starts with his title) is at most 2: kept candidates {len(dep)}, "
             f"highest level {dep[0]['importance'] if dep else None}")
    L += ["    " + fmt_cand(s) for s in dep[:3]]
    k4 = [r for r in rows if r["class"] == "kyiv" and r["importance"] >= 4]
    ok &= bool(k4)
    L.append(("PASS " if k4 else "FAIL ") + f"at least one kyiv event with level >= 4: {len(k4)}")
    L += ["    " + fmt_row(r) for r in sorted(k4, key=lambda r: (r["event_date"], r["event_id"]))]

    ab = [s for s in scored if (s["class"] == "russia" or s.get("was_world")) and s["p"]["abroad"] >= 0.5 and s["p"]["place_written"] >= 0.5
          and (s["src"] in TG_SRC or (s["type"] == "zelensky_trip_abroad" and s["latest"]))]
    twins = []
    for r in rows:
        if r["class"] == "kyiv":
            mine = set(r["participants"]) - GENERIC
            hit = next((s for s in ab if mine & (set(s["participants"]) - GENERIC)
                        and date.fromisoformat(s["event_date"]) <= r["event_date"] <= date.fromisoformat(s["end_date"])), None)
            if hit:
                twins.append((r, hit))
    ok &= not twins
    L.append(("PASS " if not twins else "FAIL ") + f"no kyiv row is a meeting abroad (a same-day candidate with a foreign place written and a common participant): {len(twins)}")
    L += [f"    {fmt_row(r)} | twin {s['src']} {s['url'].split('/')[-1]} {s['class']}" for r, s in twins]
    dropped = [s for s in scored if s.get("twin")]
    L.append(f"kyiv-by-default candidates dropped as the twin of a meeting abroad: {len(dropped)}")
    L += ["    " + fmt_cand(s) for s in dropped]
    trips = [s for s in scored if s["type"] == "zelensky_trip_abroad" and s["latest"]]
    on_trip = [r for r in rows if r["class"] == "kyiv" and any(date.fromisoformat(t["event_date"]) <= r["event_date"] <= date.fromisoformat(t["end_date"]) for t in trips)]
    L.append(f"kyiv rows on a day of a Wikipedia trip of the president abroad (for review, not a check): {len(on_trip)}")
    L += ["    " + fmt_row(r) for r in on_trip]

    L.append("2. LEVELS per class and month (number of events per level 0..5)")
    by = Counter((r["class"], f"{r['event_date']:%Y-%m}", r["importance"]) for r in rows)
    for c in CLASSES:
        for mo in sorted({k[1] for k in by if k[0] == c}):
            cnt = [by[(c, mo, lv)] for lv in range(6)]
            L.append(f"  {c:6s} {mo} {cnt} total {sum(cnt)}")
        cnt = [sum(v for k, v in by.items() if k[0] == c and k[2] == lv) for lv in range(6)]
        L.append(f"  {c:6s} all     {cnt} total {sum(cnt)}")

    L.append("3. TABLE CHECKS")
    events, rows = rows, allrows  # from here rows are all rows of the table (every Wikipedia version), events the final ones
    bad_range = [r for r in rows if not (D_FROM <= r["event_date"] <= D_TO)]
    nulls = {k: sum(r[k] is None for r in rows) for k in ("class", "importance", "importance_confidence", "announced_at", "available_at")}
    ids = Counter(r["event_id"] for r in rows)
    keys = Counter((r["class"], main_participant(r["participants"], r["type"]), r["event_date"], r["importance"]) for r in rows if r["version_of"] is None)
    wrows = [r for r in rows if r["version_of"]]
    wkeys = Counter(r["version_of"] for r in wrows)
    vdup = sum(v > 1 for v in Counter((r["version_of"], r["revid"]) for r in wrows).values())
    p_bad = sum(not (0.0 <= r["p_" + f] <= 1.0) for r in rows for f in FACTS)
    lv_bad = sum(not (isinstance(r["importance"], int) and 0 <= r["importance"] <= 5) for r in rows)
    redo = sum(level_of({f: r["p_" + f] for f in FACTS}, r["class"], r["class_confidence"]) == (r["importance"], r["importance_confidence"]) for r in rows)
    grp = Counter((r["class"], main_participant(r["participants"], r["type"]), r["event_date"]) for r in rows if r["version_of"] is None)
    L.append(f"rows {len(rows)}; event_date from {min(r['event_date'] for r in rows)} to {max(r['event_date'] for r in rows)}; out of range {len(bad_range)} "
             f"(range {D_FROM}..{D_TO}); nulls {nulls}; duplicate event_id {sum(v > 1 for v in ids.values())}; "
             f"duplicate key (class, main participant, event_date, level) among the rows that are not Wikipedia versions {sum(v > 1 for v in keys.values())}; "
             f"end_date < event_date {sum(r['end_date'] < r['event_date'] for r in rows)}")
    L.append(f"p outside 0..1: {p_bad}; level not an integer 0..5: {lv_bad}; level and confidence recomputed from the stored p_* and class: {redo} of {len(rows)}")
    L.append(f"events (a Wikipedia key counted once, with its latest version) {len(events)}; Wikipedia version rows {len(wrows)} of {len(wkeys)} keys (class none, replacing a version of another class: {sum(r['class'] == 'none' for r in wrows)}), "
             f"keys with more than one version {sum(v > 1 for v in wkeys.values())}, duplicate (version_of, revid) {vdup}; rows of the other sources {len(rows) - len(wrows)}")
    L.append(f"keys (class, main participant, event_date) of the rows of the other sources {len(grp)}; with more than one row (a later announcement with a higher level) "
             f"{sum(v > 1 for v in grp.values())}; scheduled rows {sum(r['scheduled'] for r in rows)}, scheduled events {sum(r['scheduled'] for r in events)}")
    L.append("by class (events) " + str(dict(Counter(r["class"] for r in events))) + "; by type (events) " + str(dict(Counter(r["type"] for r in events))))
    L.append("level >= 4 per class (events): " + str(dict(Counter(r["class"] for r in events if r["importance"] >= 4))))
    ok &= not bad_range and not any(nulls.values()) and not p_bad and not lv_bad and redo == len(rows) and not any(v > 1 for v in ids.values()) \
        and not any(v > 1 for v in keys.values()) and not vdup

    L.append("4. CANDIDATES")
    L.append(f"candidates {len(scored)}; by (source, class): {dict(sorted(Counter((s['src'], s['class']) for s in scored).items()))}")
    tg = [s for s in scored if s["src"] in ("tg_op", "tg_zel")]
    L.append("Telegram candidates by (place hint, class): " + str(dict(sorted(Counter((s["place"][0] if s.get("place") else "none", s["class"]) for s in tg).items()))))
    tgr = [s for s in tg if s["class"] == "russia"]
    L.append(f"Telegram candidates of class russia: {len(tgr)}")
    L += ["    " + fmt_cand(s) for s in tgr[:6]]

    def reason(s):
        if s.get("twin"):
            return "abroad_twin"
        if s.get("was_world"):
            return "world_dropped"
        for k in NONE_REASONS + ("ukraine_elsewhere",):
            if s["p"][k] >= 0.5:
                return k
        return "no rule holds"
    L.append("dropped as none, by the first reason that holds: " + str(dict(Counter(reason(s) for s in scored if s["class"] == "none"))))
    texts = [" ".join(str(v) for v in s["state"].values()) for s in scored]
    L.append(f"Jev states {len(scored)}; with a date, a year or a URL left {sum(bool(leak_scan(t)) for t in texts)}; with the marker [date] {sum('[date]' in t for t in texts)}")
    fr = Counter()
    for s in scored:
        for f in FACTS:
            fr[f] += s["p"][f] >= 0.5
    L.append("candidates with the fact true (p >= 0.5): " + str(dict(fr)))

    rows = [r for r in allrows if r["class"] != "none"]
    L.append("5. LEVEL >= 3 ROWS DECIDED BY A FACT NEAR THE THRESHOLD, LEGISLATORS, KREMLIN ADDRESSES")
    hi = [r for r in rows if r["importance"] >= 3]
    bd = sorted((r for r in hi if r["importance_confidence"] <= 0.10), key=lambda r: (r["event_date"], r["event_id"]))
    L.append(f"rows with level >= 3: {len(hi)} (level 4: {sum(r['importance'] == 4 for r in hi)}, level 3: {sum(r['importance'] == 3 for r in hi)}); "
             f"with importance_confidence <= 0.10: {len(bd)} (level 4: {sum(r['importance'] == 4 for r in bd)}, level 3: {sum(r['importance'] == 3 for r in bd)})")
    L += ["    " + fmt_row(r) for r in bd]
    rxl = re.compile(r"Палат\w+ представників|Конгрес|Сенат|сенатор|парламент|Бундестаг|Congress|Senate|senator|parliament|Bundestag|Riksdag|Sejm|Сейм", re.I)
    lg = sorted((s for s in scored if s["class"] != "none" and s["importance"] >= 3 and rxl.search(s["title"] + " " + s["text"])),
                key=lambda s: (s["event_date"], s["url"]))
    L.append(f"kept candidates with level >= 3 whose text names a parliament, a congress or a senator: {len(lg)}")
    L += ["    " + fmt_cand(s) for s in lg]
    kad = [r for r in rows if re.match(r"(Address|Statements?\b)", r["title"])]
    ok &= not kad
    L.append(("PASS " if not kad else "FAIL ") + f"no row of the table is a Kremlin address or statement: {len(kad)}")

    rows = events
    cols = ["class", "level", "confidence", "event_date", "end_date", "type"] + [f"p_{f}" for f in FACTS] + ["title"]
    top = sorted(rows, key=lambda r: (-r["importance"], r["event_date"], r["event_id"]))[:15]
    rnd = random.Random(42).sample(rows, 15)
    for name, sel in (("top15", top), ("random15", rnd)):
        with open(out / f"{name}.tsv", "w", encoding="utf-8") as f:
            f.write("\t".join(cols) + "\n")
            for r in sel:
                f.write("\t".join([r["class"], str(r["importance"]), f"{r['importance_confidence']:.2f}", str(r["event_date"]), str(r["end_date"]), r["type"]]
                                  + [f"{r['p_' + x]:.2f}" for x in FACTS] + [r["title"][:140]]) + "\n")
    L.append(f"files in {out}: top15.tsv, random15.tsv, checks.txt")
    L.append("REPORT " + ("PASS" if ok else "FAIL"))
    (out / "checks.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return ok


# --------------------------------------------------------------------------------------------------------- gold


def _arrow(con, sql):
    res = con.execute(sql)
    for name in ("to_arrow_table", "fetch_arrow_table"):
        if hasattr(res, name):
            return getattr(res, name)()
    raise RuntimeError("no arrow export on this DuckDB result")


def features(con, t_table):
    """One row per t_utc of t_table: for c in CLASSES (kyiv, russia): {c}_imp_today and {c}_days_to_imp4 (INTEGER).

    The day is the Kyiv calendar day d of t_utc. {c}_imp_today is the largest level (0..5) of class-c events with
    event_date <= d <= end_date that were announced before t_utc (0 if none). {c}_days_to_imp4 is the number of days
    from d to the nearest class-c event with level >= 4 announced before t_utc: 0 if it is on or under way on d,
    at most 14 (14 also when there is none). Events announced at or after t_utc are invisible. An event key (version_of of a Wikipedia
    row, else the row itself) counts with its latest version available before t_utc: later versions are invisible and earlier ones are replaced
    (a latest version of class none counts for no class)."""
    typ = con.execute(f"SELECT typeof(t_utc) FROM {t_table} LIMIT 1").fetchone()
    cols = [f"{c}_imp_today" for c in CLASSES] + [f"{c}_days_to_imp4" for c in CLASSES]
    if typ is None:
        return pa.table({"t_utc": pa.array([], pa.timestamp("us")), **{c: pa.array([], pa.int32()) for c in cols}})
    tz = "WITH TIME ZONE" in typ[0].upper()
    tn = "timezone('UTC', t_utc)" if tz else "t_utc"       # naive UTC, comparable with available_at
    tk = "t_utc" if tz else "timezone('UTC', t_utc)"       # timestamptz, for the Kyiv day
    sel = []
    for c in CLASSES:
        sel.append(f"""CAST(COALESCE(max(v.imp) FILTER (WHERE v.cls = '{c}' AND v.event_date <= k.d AND k.d <= v.end_date), 0) AS INTEGER) AS {c}_imp_today""")
    for c in CLASSES:
        sel.append(f"""CAST(LEAST({CAP_DAYS}, COALESCE(min(GREATEST(0, v.event_date - k.d)) FILTER (WHERE v.cls = '{c}' AND v.imp >= {IMP_HIGH}
            AND v.end_date >= k.d), {CAP_DAYS})) AS INTEGER) AS {c}_days_to_imp4""")
    return _arrow(con, f"""
        WITH k AS (SELECT t_utc, {tn} AS tn, CAST(timezone('Europe/Kyiv', {tk}) AS DATE) AS d
                   FROM (SELECT DISTINCT t_utc FROM {t_table})),
             vis AS (SELECT k.t_utc, e."class" AS cls, e.importance AS imp, e.event_date, e.end_date
                     FROM k JOIN {TABLE} e ON e.available_at < k.tn
                     QUALIFY row_number() OVER (PARTITION BY k.t_utc, COALESCE(e.version_of, e.event_id)
                                                ORDER BY e.available_at DESC, e.revid DESC NULLS LAST, e.event_id DESC) = 1)
        SELECT k.t_utc, {", ".join(sel)} FROM k LEFT JOIN vis v ON v.t_utc = k.t_utc GROUP BY k.t_utc, k.d ORDER BY k.t_utc""")


def _py_features(rows, t):
    """The same six features in plain Python, as an independent check of the SQL."""
    d = kyiv_day(t)
    rows = final_rows([r for r in rows if r["available_at"] < t])  # the latest version of each key known before t
    res = []
    for c in CLASSES:
        res.append(max([r["importance"] for r in rows if r["class"] == c and r["event_date"] <= d <= r["end_date"]
                        and r["available_at"] < t], default=0))
    for c in CLASSES:
        ahead = [max(0, (r["event_date"] - d).days) for r in rows if r["class"] == c and r["importance"] >= IMP_HIGH
                 and r["end_date"] >= d and r["available_at"] < t]
        res.append(min(CAP_DAYS, min(ahead)) if ahead else CAP_DAYS)
    return res


def data_end():
    """Last full hour for which every bronze source is fetched: the earliest of the fetch times of the newest item of each source
    (the newest by publication time, so a later back-fill of older items does not move it), rounded down to the hour."""
    ends = [max(load_posts(ch), key=lambda r: r["published_at"])["fetched_at"] for ch in ("OP_UA", "V_Zelenskiy_official")]
    for fn in ("kremlin_news.jsonl", "kremlin_trips.jsonl"):
        with open(CAL / fn, encoding="utf-8") as f:
            ends.append(max((json.loads(line) for line in f), key=lambda r: r["published_at"])["fetched_at"])
    for p in CAL.glob("wiki/*.json"):
        ends.append(json.load(open(p, encoding="utf-8"))["snapshots"][0]["fetched_at"])
    return min(utc(x) for x in ends).replace(minute=0, second=0, microsecond=0)


def _hours(con, name, first, last):
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '{first}', "
                f"TIMESTAMP '{last}', INTERVAL 1 HOUR) AS g(t)")


def _asof_connection(t):
    """DuckDB where view political_events is the table as it was known before t (the ASOF rule)."""
    con = connect()
    con.execute(f"CREATE TABLE _all AS SELECT * FROM read_parquet('{PATH}')")
    sql = ASOF[TABLE].format(t=f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'").replace(f"FROM {TABLE}", "FROM _all")
    con.execute(f"CREATE VIEW {TABLE} AS {sql}")
    return con


def features_check(first="2026-04-30 21:00:00", seed=7, old=None):
    last = f"{data_end():%Y-%m-%d %H:%M:%S}"
    rows = pq.read_table(PATH).to_pylist()
    con = register_layers(connect())
    _hours(con, "t_hours", first, last)
    res = features(con, "t_hours")
    n_t = con.execute("SELECT count(*) FROM t_hours").fetchone()[0]
    nulls = {c: res[c].null_count for c in res.column_names}
    exp = [_py_features(rows, t) for t in res["t_utc"].to_pylist()]
    got = [[res[c][i].as_py() for c in res.column_names[1:]] for i in range(res.num_rows)]
    same = all(a == b for x, y in zip(got, exp) for a, b in zip(x, y))
    const = [c for c in res.column_names[1:] if "days" in c and len(set(res[c].to_pylist())) == 1]
    ok = res.num_rows == n_t and res.column_names[0] == "t_utc" and not any(nulls.values()) and same and not const
    print(f"t {first}Z..{last}Z: rows {res.num_rows} of {n_t} hours, columns {res.column_names}")
    print(f"nulls {nulls}")
    print(f"equals plain-Python recomputation: {same} -> {'PASS' if same else 'FAIL'}")
    full = {r["t_utc"]: r for r in res.to_pylist()}
    for c in res.column_names[1:]:
        vals = res[c].to_pylist()
        print(f"  {c}: min {min(vals)}, max {max(vals)}, distinct {len(set(vals))}, hours different from {14 if 'days' in c else 0}: "
              f"{sum(v != (14 if 'days' in c else 0) for v in vals)}")
    print(f"days_to_imp4 columns that are constant over the hours: {const or 'none'} -> {'PASS' if not const else 'FAIL'}")
    if old:  # features of an older table without version_of and revid (every row its own key): the hours where the two differ
        from pathlib import Path
        co = connect()
        co.execute(f"CREATE VIEW {TABLE} AS SELECT *, CAST(NULL AS VARCHAR) AS version_of, CAST(NULL AS BIGINT) AS revid FROM read_parquet('{old}')")
        _hours(co, "t_hours", first, last)
        prev = features(co, "t_hours")
        ts = res["t_utc"].to_pylist()
        hrs = {c: [t for t, a, b in zip(ts, res[c].to_pylist(), prev[c].to_pylist()) if a != b] for c in res.column_names[1:]}
        print(f"hours that differ from the features of the older table {Path(old).name} ({prev.num_rows} hours): {({c: len(h) for c, h in hrs.items()})}")
        for c, h in hrs.items():
            if h:
                print(f"  {c}: {len(h)} hours, first {h[0]:%Y-%m-%dT%H:%MZ}, last {h[-1]:%Y-%m-%dT%H:%MZ}")
    for s in ("2026-05-25 21:00:00", "2026-05-26 21:00:00", "2026-06-14 20:00:00", "2026-07-07 03:00:00", "2026-09-25 09:00:00"):
        if datetime.fromisoformat(s) in full:
            print("  sample", s, {k: v for k, v in full[datetime.fromisoformat(s)].items() if k != "t_utc"})
    con.execute("CREATE OR REPLACE TABLE t_tz AS SELECT CAST(t_utc AS TIMESTAMPTZ) AS t_utc FROM t_hours")
    same_tz = [list(x.values())[1:] for x in features(con, "t_tz").to_pylist()] == [list(x.values())[1:] for x in res.to_pylist()]
    ok &= same_tz
    print(f"TIMESTAMPTZ t_table gives the same features: {same_tz}")
    active = [t for t, r in full.items() if any(r[f"{c}_imp_today"] > 0 for c in CLASSES)]
    rnd = random.Random(seed)
    for label, picks in (("random", rnd.sample(sorted(full), 3)), ("active", rnd.sample(active, min(2, len(active))))):
        for t in picks:
            c2 = _asof_connection(t)
            c2.execute(f"CREATE TABLE t1 AS SELECT TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}' AS t_utc")
            g = features(c2, "t1").to_pylist()
            same_asof = g == [full[t]]
            ok &= same_asof
            print(f"ASOF {label} t={t:%Y-%m-%dT%H:%M}Z rows {len(g)} identical to the full computation: {same_asof}; {({k: v for k, v in g[0].items() if k != 't_utc'})}")
    print("FEATURES CHECK", "PASS" if ok else "FAIL")
    return ok


def wiki_check():
    """Leak check of the Wikipedia version rows against the revision files, independent of the build: the files are reloaded and every event is
    parsed again. (1) The revision of each version row exists and starts a version of its key (the row of the key differs from its row in the
    previous revision where it appears); the timestamp of the revision is the available_at and the announced_at of the version row; the row of
    the key in that revision has the text, the dates and the title stored in the version row. (2) What the revisions have as versions and the table
    has not is the versions of class none. Prints the number of versions and of keys with more than one version, then the two cases of the verifier."""
    rows = [r for r in pq.read_table(PATH).to_pylist() if r["version_of"]]
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    bad, n_exp, n_exp_multi, absent, n_gone, n_gap = [], 0, 0, 0, 0, 0
    for prefix, parse, typ, allowed, label, tpl in WIKI_PAGES:
        hist, newest = defaultdict(list), {}
        for i, (ts, rid, text) in enumerate(wiki_revisions(next(CAL.glob(f"wiki/{prefix}*.json")))):
            newest = parse(text)
            for k, info in newest.items():
                hist["|".join(str(x) for x in k)].append((utc(ts), rid, info, i))
        newest_keys = {"|".join(str(x) for x in k) for k in newest}
        exp = {}
        for kn, h in hist.items():
            if kn in newest_keys and D_FROM <= h[-1][2]["event_date"] <= D_TO:
                vs = []
                for at, rid, info, _ in h:
                    if not vs or _wiki_row(vs[-1][2]) != _wiki_row(info):
                        vs.append((at, rid, info))
                exp[kn] = vs
        n_exp += sum(len(v) for v in exp.values())
        n_gone += sum(1 for kn, h in hist.items() if kn not in newest_keys and D_FROM <= h[-1][2]["event_date"] <= D_TO)
        n_gap += sum(1 for kn in exp if hist[kn][-1][3] - hist[kn][0][3] + 1 != len(hist[kn]))
        n_exp_multi += sum(len(v) > 1 for v in exp.values())
        stored = {(r["version_of"], r["revid"]): r for r in by_type.get(typ, [])}
        for (kn, rid), r in stored.items():
            hit = next(((at, info) for at, i, info in exp.get(kn, []) if i == rid), None)
            if hit is None:
                bad.append(("no such version in the revisions", kn, rid))
                continue
            at, info = hit
            title = (info["title"] or tpl.format(country=info["country"]))[:200]
            if not (r["available_at"] == at == r["announced_at"] and r["text"] == info["text"] and r["title"] == title
                    and (r["event_date"], r["end_date"]) == (info["event_date"], info["end_date"])):
                bad.append(("row differs from its revision", kn, rid))
        absent += sum(1 for kn, vs in exp.items() for _, rid, _ in vs if (kn, rid) not in stored)
    keys = Counter(r["version_of"] for r in rows)
    print(f"Wikipedia version rows in the table {len(rows)}; keys {len(keys)}; keys with more than one version {sum(v > 1 for v in keys.values())}")
    chain = {kn: sorted((r for r in rows if r["version_of"] == kn), key=lambda r: (r["available_at"], r["revid"])) for kn in keys}
    print(f"keys whose (class, level) differs between versions {sum(len(v) > 1 and len({(r['class'], r['importance']) for r in v}) > 1 for v in chain.values())}; "
          f"whose first and latest version differ in (class, level) {sum(len(v) > 1 and (v[0]['class'], v[0]['importance']) != (v[-1]['class'], v[-1]['importance']) for v in chain.values())}; "
          f"version rows of class none {sum(r['class'] == 'none' for r in rows)}")
    print(f"versions found in the revision files for the keys of the newest revisions in range: {n_exp} (keys with more than one: {n_exp_multi}); "
          f"not in the table (class none, no version of another class right before): {absent}")
    print(f"events in range that were on a page in some revision but are not in the newest one (not in the table): {n_gone}; "
          f"keys of the table that are missing from some revision between their first and their last (the version continues when the row returns unchanged): {n_gap}")
    print(f"version rows whose revision, time, text, dates or title do not match the revision file: {len(bad)} -> {'PASS' if not bad else 'FAIL'} {bad[:5]}")

    def versions(kn):
        return sorted((r for r in rows if r["version_of"] == kn), key=lambda r: (r["available_at"], r["revid"]))

    def show(vs):
        for r in vs:
            print(f"  {r['available_at']:%Y-%m-%dT%H:%M:%SZ} rev {r['revid']} {r['class']} level {r['importance']} us_president {r['p_us_president']:.2f} "
                  f"leaders5 {r['p_leaders5']:.2f} head_major {r['p_head_major']:.2f} head_any {r['p_head_any']:.2f} minister {r['p_minister']:.2f} "
                  f"in_person {r['p_in_person']:.2f} | {r['text'][:110]}")
    un, pb = versions("zelensky_trip|United States|2026-09-22"), versions("putin_trip|China|2026-05-19")
    print("trip of Zelensky to the UN General Assembly, event_date 2026-09-22 (versions):")
    show(un)
    ok_un = not un  # pol-v9: class world is dropped, so the trip (world in pol-v8) has no row
    print(f"{'PASS' if ok_un else 'FAIL'} no row of the trip: class world is dropped (pol-v9)")
    print("trip of Putin to China, event_date 2026-05-19 (versions):")
    show(pb)
    ok_pb = (bool(pb) and f"{pb[0]['available_at']:%Y-%m-%dT%H:%M:%S}" == "2026-05-16T11:29:33" and "Met with" not in pb[0]["text"]
             and level_of({f: pb[0]["p_" + f] for f in FACTS}, pb[0]["class"], pb[0]["class_confidence"])[0] == pb[0]["importance"])
    print(f"{'PASS' if ok_pb else 'FAIL'} the version from 2026-05-16 has the text public then (no 'Met with') and the level {pb[0]['importance'] if pb else None} of that text")
    ok = not bad and ok_un and ok_pb
    print("WIKI CHECK", "PASS" if ok else "FAIL")
    return ok


def place_check(old=None):
    cands = collect()
    kinds, hints = attach_places(cands)
    print("place words", len(kinds), dict(Counter(kinds.values())))
    for k in ("abroad", "ukraine", "kyiv"):
        print(f"  {k}: {', '.join(sorted(t for t, v in kinds.items() if v == k))}")
    tg = [c for c in cands if c["src"] in ("tg_op", "tg_zel")]
    print("telegram candidates", len(tg), "with place", dict(Counter(c["place"][0] for c in tg if c["place"])),
          "own cue", sum(bool(c.get("own_place")) for c in tg))
    if old:
        prev = [r for r in load_dump(old) if r["src"] in ("tg_op", "tg_zel") and r["class"] == "kyiv"]
        moved = [r for r in prev if hints.get(r["url"]) and hints[r["url"]][0] != "kyiv"]
        print(f"previous kyiv-class Telegram candidates {len(prev)}; now with a place outside Kyiv {len(moved)}:")
        for r in sorted(moved, key=lambda r: r["announced_at"]):
            print(f"  {r['announced_at'][:16]} {hints[r['url']][0]}:{hints[r['url']][1]} imp {r['importance']:.2f} {r['title'][:80]}")


def main():
    build()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="build",
                    choices=["build", "candidates", "strip-demo", "report", "features-check", "place-check", "wiki-check"])
    ap.add_argument("--dump")
    ap.add_argument("--out")
    ap.add_argument("--old")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.dump)
    elif a.cmd == "candidates":
        candidates_cmd()
    elif a.cmd == "strip-demo":
        strip_demo()
    elif a.cmd == "report":
        sys.exit(0 if report(a.dump, a.out) else 1)
    elif a.cmd == "place-check":
        place_check(a.dump)
    elif a.cmd == "wiki-check":
        sys.exit(0 if wiki_check() else 1)
    else:
        sys.exit(0 if features_check(old=a.old) else 1)
