"""Silver table prep_signal_events: events of strike preparation found in the monitoring channels: strategic aviation
(S1), MiG-31K (S2) and waves of attack drones (S4). Jev confirms that a post reports an actual event now.

Input: data/silver/tg_posts.parquet. A candidate is a post of one of CHANNELS whose rx_signals has S1, S2 or S4
(S3 and S5 are dropped and vanek_nikolaev is excluded: docs/HISTORY.md). Jev answers yes/no questions about every candidate
(many posts per request, dates removed from the text); code turns the confirmed posts into events: posts of one signal
and subtype within GAP of the first post of the event are one event, the event time is the earliest post.
Docs: docs/data/silver/prep_signal_events.md.

    .venv/bin/python -I -m airalerts.silver.signals                 # judge (Jev, cached) and build the table
    .venv/bin/python -I -m airalerts.silver.signals check <outdir>  # DONE checks, samples and the features test
"""
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect
from ..jev import MODEL, JevError, ask_many, usage
from ..paths import FETCH_FROM, SILVER
from .telegram_rx import S1_COUNT, S4_COUNT

TABLE = "prep_signal_events"
PATH = SILVER / f"{TABLE}.parquet"
SRC = SILVER / "tg_posts.parquet"
PROMPT_VERSION = "sig-v2"
CHANNELS = ("war_monitor", "kpszsu", "AerisRimor", "StrategicaviationT", "monitorwarr", "kyiv_airdef")
KEPT = ("S1", "S2", "S4")
THRESHOLD = 0.5            # noul threshold (docs/JEV.md rule 8); the table keeps the probabilities
GAP = timedelta(minutes=15)  # a post joins the event when it is at most GAP after the first post of the event
CAP_HOURS = 336.0          # hours_since_s1 cap: 14 days
WORKERS = 8                # Jev workers (the limit is 8)
MAX_POSTS, MAX_CHARS, MAX_TEXT = 8, 3000, 3500   # S4 requests: posts and characters of text; characters per post

ASOF = {TABLE: """SELECT event_id, signal, subtype, first_post_at,
       CASE WHEN last_post_at < {t} THEN last_post_at END AS last_post_at,
       CASE WHEN last_post_at < {t} THEN n_channels END AS n_channels,
       CASE WHEN last_post_at < {t} THEN n_posts END AS n_posts,
       CASE WHEN last_post_at < {t} THEN aircraft_n END AS aircraft_n,
       CASE WHEN last_post_at < {t} THEN toward_kyiv END AS toward_kyiv,
       CASE WHEN last_post_at < {t} THEN post_refs END AS post_refs,
       CASE WHEN last_post_at < {t} THEN p_actual END AS p_actual,
       CASE WHEN last_post_at < {t} THEN p_subtype END AS p_subtype,
       jev_model, prompt_version, available_at
FROM prep_signal_events WHERE available_at < {t}"""}

SCHEMA = pa.schema([
    ("event_id", pa.string()), ("signal", pa.string()), ("subtype", pa.string()),
    ("first_post_at", pa.timestamp("us")), ("last_post_at", pa.timestamp("us")),
    ("n_channels", pa.int32()), ("n_posts", pa.int32()), ("aircraft_n", pa.int32()), ("toward_kyiv", pa.bool_()),
    ("post_refs", pa.list_(pa.string())), ("p_actual", pa.float64()), ("p_subtype", pa.float64()),
    ("jev_model", pa.string()), ("prompt_version", pa.string()), ("available_at", pa.timestamp("us"))])

# ---------------------------------------------------------------- Jev questions

LEAD = ("The state lists numbered posts from Ukrainian military Telegram channels that monitor Russian aviation and "
        "drones. The text is Ukrainian or Russian and has no dates. Answer only about post {pid}; ignore all other posts. ")
# name: (question, criteria true, criteria false); {pid} is the id of the post in the state
QUESTIONS = {
    "actual_now": (
        "Does post {pid} report something that is happening right now or happened within the last few minutes (for "
        "example a takeoff, a flight, a launch, aircraft or drones on the move, an all-clear), as opposed to a forecast, "
        "a plan, a warning about what may happen later, a summary of past hours or days, or a general comment?",
        "The post states that an event is happening now or happened minutes ago.",
        "The post is a forecast, a plan, a warning about a possible future event, a daily or multi-day summary, a "
        "retrospective, a general comment, an advertisement, or says that nothing is happening."),
    "takeoff": (
        "Does post {pid} say that Russian strategic bombers (Tu-95, Tu-160 or Tu-22M3) have taken off, are in the air, "
        "or are being relocated (transferred) to another airfield?",
        "The post reports a takeoff, a flight in progress or a relocation (transfer) of Tu-95, Tu-160 or Tu-22M3 bombers.",
        "The post does not report such a takeoff, flight or relocation: it only names an airfield or an aircraft type, "
        "says the bombers stay at their bases or that no takeoff is seen, reports only that bombers landed, or reports "
        "something else."),
    "mig31k_airborne": (
        "Does post {pid} say that a MiG-31K aircraft (the carrier of the Kinzhal missile) has taken off or is in the air?",
        "The post reports that a MiG-31K took off, departed, or is in the air.",
        "The post does not say that a MiG-31K is flying: it reports an all-clear or a landing, only mentions the Kinzhal "
        "missile or a MiG-31K in another context, or says no MiG-31K activity is seen."),
    "mig31k_all_clear": (
        "Does post {pid} say that the MiG-31K threat or flight is over (an all-clear, the aircraft landed or left the air)?",
        "The post announces the end of the MiG-31K threat or flight.",
        "The post does not announce the end of a MiG-31K threat (for example it reports a takeoff, or mentions the "
        "MiG-31K in another context)."),
    "drone_launch": (
        "Does post {pid} report attack drones (Shahed, Geran, jet drones, mopeds) that were launched or are flying "
        "now, one drone or many?",
        "The post reports that attack drones were launched or are flying (one drone, a group or a wave).",
        "The post does not report attack drones launched or in the air: it is a forecast, an all-clear, a statistic of "
        "past shootdowns, a report about other aircraft or weapons, or about something else."),
}
SIGNAL_Q = {"S1": ("takeoff",), "S2": ("mig31k_airborne", "mig31k_all_clear"), "S4": ("drone_launch",)}

MONTHS = ("січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня|января|февраля|"
          "марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря")
DATE_RX = [re.compile(p, re.I) for p in (
    r"\b20\d\d-\d{2}-\d{2}\b",
    r"\b\d{1,2}[./]\d{1,2}[./](?:20)?\d\d\b",
    rf"\b\d{{1,2}}\s+(?:{MONTHS})(?:\s+20\d\d)?(?:\s*(?:р\.|року|г\.|года))?",
    r"\b(?:0?[1-9]|[12]\d|3[01])[./](?:0?[1-9]|1[0-2])\b(?![\d:])",
    r"\b20[12]\d\b(?:\s*(?:р\.|року|г\.|года))?")]

# subtype of an S1 post by code: the relocation words of PARSING 7 (S1_TAKEOFF) without a takeoff word
RELOC = re.compile(r"передислок|перебазуван|перекидан|перел[іе]т|перелет", re.I)
FLIGHT = re.compile(r"зл[іе]т|взл[её]т|в[иі]л[іе]т|в повітрі|в воздухе", re.I)


def scrub(text):
    """The post text for Jev: dates and years removed (docs/JEV.md: the model must not place the post in time)."""
    for rx in DATE_RX:
        text = rx.sub(" ", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()[:MAX_TEXT]


def question(name, pid):
    q, true, false = QUESTIONS[name]
    return {"type": "noul", "instructions": LEAD.format(pid=pid) + q.format(pid=pid),
            "criteria": {"true": true, "false": false}}


def prob(a):
    return float(a["noul"] if isinstance(a, dict) else a)


def request_for(chunk):
    """(state, questions) for a chunk of posts that have the same signals."""
    state = {"posts": [{"id": f"p{i}", "text": scrub(r["text"])} for i, r in enumerate(chunk)]}
    qs = {}
    for i, r in enumerate(chunk):
        for name in ("actual_now",) + tuple(q for s in r["sigs"] for q in SIGNAL_Q[s]):
            qs[f"{name}_{i}"] = question(name, f"p{i}")
    return state, qs


def size_for(sigs, max_posts=None):
    """Posts per request: S1 and S2 posts (rare, decisive, often long) go one per request, S4 posts in batches."""
    if max_posts:
        return max_posts
    return 1 if ("S1" in sigs or "S2" in sigs) else MAX_POSTS


def chunks_of(posts, max_posts=None, max_chars=MAX_CHARS):
    groups = defaultdict(list)
    for r in posts:
        groups[r["sigs"]].append(r)
    out = []
    for sigs in sorted(groups):
        cur, chars = [], 0
        for r in groups[sigs]:
            n = len(scrub(r["text"]))
            if cur and (len(cur) >= size_for(sigs, max_posts) or chars + n > max_chars):
                out.append(cur)
                cur, chars = [], 0
            cur.append(r)
            chars += n
        if cur:
            out.append(cur)
    return out


def judge(posts, max_posts=None, log=print):
    """Jev probabilities for every post: {(channel, post_id): {question: p}}. Cached, so a rerun is free."""
    chunks = chunks_of(posts, max_posts)
    before = usage(TABLE)
    out, t0, wave = {}, time.time(), 400
    for w in range(0, len(chunks), wave):
        part = chunks[w:w + wave]
        answers = ask_many([request_for(c) for c in part], tag=TABLE, workers=WORKERS)
        for c, ans in zip(part, answers):
            for i, r in enumerate(c):
                names = ("actual_now",) + tuple(q for s in r["sigs"] for q in SIGNAL_Q[s])
                missing = [n for n in names if f"{n}_{i}" not in ans]
                if missing:
                    raise RuntimeError(f"Jev answer lacks {missing} for {r['channel']}/{r['post_id']}")
                out[(r["channel"], r["post_id"])] = {n: prob(ans[f"{n}_{i}"]) for n in names}
        log(f"  judged {min(w + wave, len(chunks))}/{len(chunks)} requests, {len(out)} posts, {time.time() - t0:.0f} s")
    after = usage(TABLE)
    log(f"Jev: {len(chunks)} requests for {len(posts)} posts; cache of {TABLE} now {after['calls']} calls, "
        f"{after['input_tokens']} input tokens, ${after['usd']} (new in this run: {after['calls'] - before['calls']} calls, "
        f"${round(after['usd'] - before['usd'], 4)})")
    return out


# ---------------------------------------------------------------- events

def load_posts():
    con = connect()
    chans = ",".join(f"'{c}'" for c in CHANNELS)
    since = FETCH_FROM.replace("T", " ").rstrip("Z")
    rows = con.execute(f"""SELECT channel, post_id, published_at, text, rx_signals, rx_classes, edited, is_original
        FROM read_parquet('{SRC}') WHERE channel IN ({chans}) AND published_at >= TIMESTAMP '{since}'
        AND (list_contains(rx_signals, 'S1') OR list_contains(rx_signals, 'S2') OR list_contains(rx_signals, 'S4'))
        ORDER BY published_at, channel, post_id""").fetchall()
    keys = ("channel", "post_id", "published_at", "text", "signals", "classes", "edited", "is_original")
    posts = []
    for row in rows:
        r = dict(zip(keys, row))
        r["sigs"] = tuple(s for s in r["signals"] if s in KEPT)
        posts.append(r)
    return posts


def subtype_of(r, sig, p):
    """(subtype, probability of the subtype question) of post r for signal sig, or None when Jev does not confirm it."""
    if p["actual_now"] < THRESHOLD:
        return None
    if sig == "S1":
        if p["takeoff"] < THRESHOLD:
            return None
        return ("relocation" if RELOC.search(r["text"]) and not FLIGHT.search(r["text"]) else "takeoff"), p["takeoff"]
    if sig == "S2":
        a, c = p["mig31k_airborne"], p["mig31k_all_clear"]
        if max(a, c) < THRESHOLD:
            return None
        return ("airborne", a) if a >= c else ("all_clear", c)
    if sig == "S4":
        return ("launch", p["drone_launch"]) if p["drone_launch"] >= THRESHOLD else None


def count_of(sig, text):
    """Aircraft (S1, S2) or drones (S4) stated in the text by the refinement regexes of PARSING 7. A number glued to a
    letter or a hyphen is not a count: the missile 'Х-101' is not 101 aircraft."""
    def ok(m):
        return m.start() == 0 or not (text[m.start() - 1].isalnum() or text[m.start() - 1] == "-")
    if sig == "S4":
        ns = [int(g) for m in S4_COUNT.finditer(text) if ok(m) for g in m.groups() if g]
    else:
        ns = [int(m.group(1)) for m in S1_COUNT.finditer(text) if ok(m)]
    return max(ns) if ns else None


def event_row(sig, st, items):
    posts = [it[0] for it in items]
    first, last = posts[0]["published_at"], posts[-1]["published_at"]
    counts = [c for c in (count_of(sig, r["text"]) for r in posts) if c is not None]
    return {"event_id": f"{sig}-{st}-{first:%Y%m%dT%H%M%SZ}", "signal": sig, "subtype": st,
            "first_post_at": first, "last_post_at": last, "n_channels": len({r["channel"] for r in posts}),
            "n_posts": len(posts), "aircraft_n": counts[0] if counts else None,
            "toward_kyiv": any("toward_kyiv" in r["classes"] for r in posts),
            "post_refs": [f"{r['channel']}/{r['post_id']}" for r in posts],
            "p_actual": max(it[1]["actual_now"] for it in items), "p_subtype": max(it[2] for it in items),
            "jev_model": MODEL, "prompt_version": PROMPT_VERSION, "available_at": first}


def build_events(posts, probs):
    groups = defaultdict(list)
    for r in posts:
        p = probs[(r["channel"], r["post_id"])]
        for sig in r["sigs"]:
            res = subtype_of(r, sig, p)
            if res:
                groups[(sig, res[0])].append((r, p, res[1]))
    rows = []
    for (sig, st), items in sorted(groups.items()):
        items.sort(key=lambda it: (it[0]["published_at"], it[0]["channel"], it[0]["post_id"]))
        cur = []
        for it in items:
            if cur and it[0]["published_at"] > cur[0][0]["published_at"] + GAP:
                rows.append(event_row(sig, st, cur))
                cur = []
            cur.append(it)
        if cur:
            rows.append(event_row(sig, st, cur))
    rows.sort(key=lambda e: (e["first_post_at"], e["signal"], e["subtype"]))
    return rows


def channel_ends():
    """Time of the newest post of each channel in tg_posts (any post, not only candidates)."""
    chans = ",".join(f"'{c}'" for c in CHANNELS)
    return dict(connect().execute(f"SELECT channel, max(published_at) FROM read_parquet('{SRC}') "
                                  f"WHERE channel IN ({chans}) GROUP BY channel").fetchall())


def main():
    t0 = time.time()
    posts = load_posts()
    per = Counter((r["channel"], s) for r in posts for s in r["sigs"])
    print(f"candidates: {len(posts)} posts; per channel and signal: {dict(sorted(per.items()))}")
    probs = judge(posts)
    rows = build_events(posts, probs)
    last = channel_ends()
    table = pa.Table.from_pylist(rows, schema=SCHEMA).replace_schema_metadata({
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "jev_model": MODEL,
        "prompt_version": PROMPT_VERSION, "threshold": str(THRESHOLD), "gap_min": "15",
        "candidates": str(len(posts)), "channels": ",".join(CHANNELS),
        "channels_last_post": json.dumps({c: f"{v:%Y-%m-%dT%H:%M:%SZ}" for c, v in last.items()}),
        "data_until": f"{min(last.values()):%Y-%m-%dT%H:%M:%SZ}"})
    tmp = PATH.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(PATH)
    print(f"wrote {PATH.name}: {len(rows)} events, "
          f"{dict(sorted(Counter((e['signal'], e['subtype']) for e in rows).items()))}, {time.time() - t0:.0f} s")


# ---------------------------------------------------------------- features for gold

SQL = """
WITH h AS (SELECT DISTINCT t_utc, CAST(t_utc AS TIMESTAMP) AS t FROM {t_table}),
s1 AS (SELECT available_at AS a FROM prep_signal_events WHERE signal = 'S1' AND subtype IN ('takeoff', 'relocation')),
air AS (SELECT available_at AS a FROM prep_signal_events WHERE signal = 'S2' AND subtype = 'airborne'),
clr AS (SELECT available_at AS a FROM prep_signal_events WHERE signal = 'S2' AND subtype = 'all_clear'),
dr AS (SELECT available_at AS a FROM prep_signal_events WHERE signal = 'S4' AND subtype = 'launch'),
h2 AS (SELECT h.*, (SELECT max(a) FROM air WHERE a >= h.t - INTERVAL '3 hours' AND a < h.t) AS last_air FROM h)
SELECT h2.t_utc,
  CAST((SELECT count(*) FROM s1 WHERE a >= h2.t - INTERVAL '6 hours' AND a < h2.t) AS INTEGER) AS s1_takeoff_6h,
  CAST((SELECT count(*) FROM s1 WHERE a >= h2.t - INTERVAL '24 hours' AND a < h2.t) AS INTEGER) AS s1_takeoff_24h,
  LEAST({cap}, COALESCE(date_diff('second', (SELECT max(a) FROM s1 WHERE a < h2.t), h2.t) / 3600.0, {cap})) AS hours_since_s1,
  CAST(h2.last_air IS NOT NULL AND (SELECT count(*) FROM clr WHERE a > h2.last_air AND a < h2.t) = 0 AS INTEGER) AS s2_mig31k_airborne,
  CAST((SELECT count(*) FROM dr WHERE a >= h2.t - INTERVAL '6 hours' AND a < h2.t) AS INTEGER) AS s4_drone_waves_6h
FROM h2 ORDER BY h2.t_utc
"""


def features(con, t_table):
    """Preparation-signal features for every t_utc of t_table, from events with available_at < t_utc.
    Columns: see docs/data/silver/prep_signal_events.md, section "Ознаки для gold"."""
    return con.execute(SQL.format(t_table=t_table, cap=repr(CAP_HOURS))).to_arrow_table()


def reference_features(events, t):
    """The same features in plain Python (events: list of (signal, subtype, available_at)); for the check."""
    s1 = [a for s, st, a in events if s == "S1" and st in ("takeoff", "relocation") and a < t]
    air = [a for s, st, a in events if s == "S2" and st == "airborne" and t - timedelta(hours=3) <= a < t]
    clr = [a for s, st, a in events if s == "S2" and st == "all_clear" and a < t]
    open_air = any(not any(c > a for c in clr) for a in air)
    return {"s1_takeoff_6h": sum(a >= t - timedelta(hours=6) for a in s1),
            "s1_takeoff_24h": sum(a >= t - timedelta(hours=24) for a in s1),
            "hours_since_s1": min(CAP_HOURS, (t - max(s1)).total_seconds() / 3600.0) if s1 else CAP_HOURS,
            "s2_mig31k_airborne": int(open_air),
            "s4_drone_waves_6h": sum(s == "S4" and st == "launch" and t - timedelta(hours=6) <= a < t
                                     for s, st, a in events)}


def features_check(first="2026-04-30 21:00:00", last=None, seed=20261010):
    """features() on every hour from first to last against plain Python, and ASOF views for 3 random t."""
    con = connect()
    con.execute(f"CREATE VIEW {TABLE} AS SELECT * FROM read_parquet('{PATH}')")
    events = [(s, st, a) for s, st, a in con.execute(f"SELECT signal, subtype, available_at FROM {TABLE}").fetchall()]
    if last is None:
        until = max(r[0] for r in con.execute(f"SELECT max(last_post_at) FROM {TABLE}").fetchall())
        last = f"{until:%Y-%m-%d %H}:00:00"
    f0, f1 = datetime.fromisoformat(first), datetime.fromisoformat(last)
    hours = [f0 + timedelta(hours=i) for i in range(int((f1 - f0).total_seconds() // 3600) + 1)]
    con.execute("CREATE TABLE t_hours AS SELECT * FROM (VALUES " + ",".join(f"(TIMESTAMP '{h}')" for h in hours) + ") v(t_utc)")
    tbl = features(con, "t_hours")
    cols = tbl.column_names
    nulls = {c: tbl.column(c).null_count for c in cols}
    assert tbl.num_rows == len(hours) and len(set(tbl.column("t_utc").to_pylist())) == len(hours), "one row per t_utc"
    assert cols[0] == "t_utc", cols
    bad = 0
    got = {c: tbl.column(c).to_pylist() for c in cols}
    for i, h in enumerate(hours):
        ref = reference_features(events, h)
        for c, v in ref.items():
            if abs(got[c][i] - v) > 1e-9:
                bad += 1
                if bad <= 5:
                    print("  MISMATCH", h, c, got[c][i], v)
    print(f"features on {len(hours)} hours {hours[0]}Z .. {hours[-1]}Z, columns {cols}")
    print(f"  null counts {nulls}; mismatches against plain Python: {bad}")
    print("  mean per column:", {c: round(sum(got[c]) / len(hours), 4) for c in cols if c != "t_utc"},
          "max:", {c: round(max(got[c]), 2) for c in cols if c != "t_utc"})
    t0 = hours[0]
    print(f"  at T0 {t0}: {dict(zip(cols[1:], [got[c][0] for c in cols[1:]]))}; earliest S1 event "
          f"{min(a for s, st, a in events if s == 'S1')}; latest S1 event before T0 "
          f"{max([a for s, st, a in events if s == 'S1' and st in ('takeoff', 'relocation') and a < t0] or [None])}")
    rnd = random.Random(seed)
    for t in sorted(rnd.sample(hours, 3)):
        asof = connect()
        sql = ASOF[TABLE].format(t=f"TIMESTAMP '{t}'")
        asof.register("tmp_asof", con.execute(sql).to_arrow_table())
        asof.execute(f"CREATE VIEW {TABLE} AS SELECT * FROM tmp_asof")
        asof.execute(f"CREATE TABLE one AS SELECT TIMESTAMP '{t}' AS t_utc")
        a = features(asof, "one").to_pylist()[0]
        full = {c: got[c][hours.index(t)] for c in cols}
        same = all(abs(a[c] - full[c]) < 1e-12 for c in cols[1:])
        print(f"  ASOF t={t}Z rows known {asof.execute(f'SELECT count(*) FROM {TABLE}').fetchone()[0]}: "
              f"{ {c: a[c] for c in cols[1:]} } identical to full: {same}")
        assert same
    assert bad == 0 and not any(nulls.values())


def check(outdir):
    out = Path(outdir)
    con = connect()
    con.execute(f"CREATE VIEW {TABLE} AS SELECT * FROM read_parquet('{PATH}')")
    con.execute(f"CREATE VIEW tg AS SELECT * FROM read_parquet('{SRC}')")
    q = lambda sql: con.execute(sql).fetchall()
    meta = pq.read_metadata(PATH).metadata
    print("rows", q(f"SELECT count(*) FROM {TABLE}")[0][0], {k.decode(): v.decode()[:200] for k, v in meta.items()
                                                              if k in (b"built_at", b"data_until", b"candidates")})
    print("DONE 1 (S2 events 2026-09-17 09:30..11:30 UTC):")
    for r in q(f"""SELECT event_id, subtype, first_post_at, last_post_at, n_channels, n_posts, post_refs,
        round(p_actual, 3), round(p_subtype, 3) FROM {TABLE} WHERE signal = 'S2'
        AND first_post_at BETWEEN TIMESTAMP '2026-09-17 09:30:00' AND TIMESTAMP '2026-09-17 11:30:00' ORDER BY first_post_at"""):
        print("  ", r)
    print("DONE 2 (events with kpszsu/83399):")
    for r in q(f"""SELECT event_id, signal, subtype, first_post_at, n_channels, n_posts, aircraft_n, post_refs
        FROM {TABLE} WHERE list_contains(post_refs, 'kpszsu/83399')"""):
        print("  ", r)
    posts = load_posts()
    probs = judge(posts, log=lambda m: print(m) if m.startswith("Jev:") else None)
    per = Counter((r["channel"], s) for r in posts for s in r["sigs"])
    print(f"candidates: {len(posts)} posts; per channel and signal: {dict(sorted(per.items()))}")
    print("requests by signal set:", dict(Counter("+".join(c[0]["sigs"]) for c in chunks_of(posts))))
    print("DONE 3 (events per month: month, s1_takeoff, s1_relocation, s2_airborne, s2_all_clear, s4_launch):")
    for r in q(f"""SELECT strftime(first_post_at, '%Y-%m') AS month,
        count(*) FILTER (WHERE signal = 'S1' AND subtype = 'takeoff'),
        count(*) FILTER (WHERE signal = 'S1' AND subtype = 'relocation'),
        count(*) FILTER (WHERE signal = 'S2' AND subtype = 'airborne'),
        count(*) FILTER (WHERE signal = 'S2' AND subtype = 'all_clear'),
        count(*) FILTER (WHERE signal = 'S4') FROM {TABLE} GROUP BY 1 ORDER BY 1"""):
        print("  ", r)
    print("  totals (signal, subtype, events, posts):", q(f"SELECT signal, subtype, count(*), sum(n_posts) FROM {TABLE} GROUP BY ALL ORDER BY ALL"))
    print("  toward_kyiv (signal, subtype, events, true):", q(f"SELECT signal, subtype, count(*), sum(CAST(toward_kyiv AS INTEGER)) FROM {TABLE} GROUP BY ALL ORDER BY ALL"))
    print("  events by n_channels (signal, n_channels, events):", q(f"SELECT signal, n_channels, count(*) FROM {TABLE} GROUP BY ALL ORDER BY ALL"))
    print("  longest event, minutes from first to last post:", q(f"SELECT max(date_diff('second', first_post_at, last_post_at)) / 60.0 FROM {TABLE}")[0][0])
    byref = {f"{r['channel']}/{r['post_id']}": r for r in posts}
    s1 = q(f"SELECT event_id, subtype, first_post_at, n_channels, n_posts, aircraft_n, toward_kyiv, post_refs, p_actual, p_subtype "
           f"FROM {TABLE} WHERE signal = 'S1' ORDER BY first_post_at")
    sample = random.Random(20261010).sample(s1, min(20, len(s1)))
    with open(out / "s1_sample_20.txt", "w", encoding="utf-8") as f:
        for e in sorted(sample, key=lambda e: e[2]):
            f.write(f"== {e[0]} subtype={e[1]} first={e[2]:%Y-%m-%dT%H:%M:%SZ} channels={e[3]} posts={e[4]} aircraft_n={e[5]} "
                    f"toward_kyiv={e[6]} p_actual={e[8]:.3f} p_subtype={e[9]:.3f}\n")
            for ref in e[7]:
                r, p = byref[ref], probs[(byref[ref]['channel'], byref[ref]['post_id'])]
                f.write(f"   {ref} {r['published_at']:%H:%M:%SZ} edited={r['edited']} actual_now={p['actual_now']:.2f} "
                        f"takeoff={p['takeoff']:.2f}: {r['text'][:400]!r}\n")
    print(f"DONE 3: 20 random S1 events written to {out / 's1_sample_20.txt'} ({len(s1)} S1 events in all)")
    # S1 candidates that Jev did not confirm, for a look at false negatives
    used = {ref for e in s1 for ref in e[7]}
    neg = [r for r in posts if "S1" in r["sigs"] and f"{r['channel']}/{r['post_id']}" not in used]
    with open(out / "s1_rejected_30.txt", "w", encoding="utf-8") as f:
        for r in random.Random(7).sample(neg, min(30, len(neg))):
            p = probs[(r["channel"], r["post_id"])]
            f.write(f"{r['channel']}/{r['post_id']} {r['published_at']:%Y-%m-%dT%H:%M:%SZ} actual_now={p['actual_now']:.2f} "
                    f"takeoff={p['takeoff']:.2f}: {r['text'][:300]!r}\n")
    print(f"S1 candidates not in any event: {len(neg)} of {sum('S1' in r['sigs'] for r in posts)}; sample in s1_rejected_30.txt")
    n_all, n_ed = Counter(), Counter()
    for sig, ref in q(f"SELECT signal, post_refs[1] FROM {TABLE}"):
        n_all[sig] += 1
        n_ed[sig] += bool(byref[ref]["edited"])
    print("events whose first post is edited (signal: edited of all):", {s: f"{n_ed[s]} of {n_all[s]}" for s in sorted(n_all)},
          "total", sum(n_ed.values()), "of", sum(n_all.values()))
    print("aircraft_n by signal (signal, events with a number, min, max):",
          q(f"SELECT signal, count(aircraft_n), min(aircraft_n), max(aircraft_n) FROM {TABLE} GROUP BY ALL ORDER BY ALL"))
    print("S1 aircraft_n values:", q(f"SELECT aircraft_n, count(*) FROM {TABLE} WHERE signal = 'S1' GROUP BY ALL ORDER BY ALL"))
    print("S1 events before T0 (count, first, last):",
          q(f"SELECT count(*), min(first_post_at), max(first_post_at) FROM {TABLE} WHERE signal = 'S1' AND available_at < TIMESTAMP '2026-04-30 21:00:00'")[0])
    print("newest post of any kind per channel:", sorted(channel_ends().items(), key=lambda kv: kv[1]))
    features_check()


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "check":
            check(sys.argv[2])
        else:
            main()
    except JevError as e:
        print("JevError:", e)
        sys.exit(3 if "vault is closed" in str(e) else 1)
