"""Hourly missile strike label for Kyiv city: the Jev classifier of the posts of the 7 Kyiv channels (piece S3a).
Docs: docs/data/silver/kyiv_threat_hourly.md. Input: data/silver/tg_posts.parquet; bronze only for `fetched_at` (label_end).

Label of hour h = 1 when missiles (ballistic, cruise, hypersonic) exploded over, were shot down over, fell as debris on
or hit Kyiv city in [h, h+1h). Drones alone, the Kyiv region outside the city and a warning alone do not count.

What is here (S3b adds the silver build, ASOF, features and labels on top of it):
- label_end(), label_hours(): the data end of the label and the hours that may be labelled;
- build_requests(hours): one Jev request per hour (several for a busy hour), state = prefiltered posts of [h-1h, h+1h);
- post_probabilities(hours): probabilities per post of hour h (strike, threat, drone, ballistic), from the Jev cache or Jev;
- hour_labels(rows): the hour rule, post probabilities to four booleans;
- regex_rules(): rules A and B of PARSING 2 per hour (reference);
- commands: classify, check, pilot, stats, calibrate, label_end.
"""
import argparse
import bisect
import datetime as dt
import functools
import json
import random
import time
from collections import defaultdict

import pyarrow.parquet as pq

from .. import telegram
from ..db import connect
from ..jev import CACHE, MODEL, USD_PER_MTOK, ask_many, usage
from ..paths import FETCH_FROM, SILVER, T0
from .telegram_rx import KYIV_ONLY

TABLE = "kyiv_threat_hourly"          # Jev cache tag and name of the silver table
PROMPT_VERSION = "kyiv_threat_hourly-v1"  # change it together with any change of the questions or of the state layout
CHANNELS = ("VA_Kyiv", "vitaliy_klitschko", "truexakyiv", "war_monitor", "AerisRimor", "kyiv_nebo", "kyiv_airdef")
OFFICIAL = ("VA_Kyiv", "vitaliy_klitschko")
MONITORS = tuple(c for c in CHANNELS if c not in OFFICIAL)
KINDS = ("strike", "threat", "drone", "ballistic")  # question families; hour columns below
HOUR_COLUMNS = {"strike": "missile_strike", "threat": "missile_threat", "drone": "drone_threat", "ballistic": "ballistic"}
HOUR = dt.timedelta(hours=1)
MAX_POSTS = 60              # posts (questions of them) per request
MAX_STATE_TOKENS = 26000    # state over this: the oldest previous-hour posts are dropped (Jev allows 32k tokens of state)
MAX_REQUEST_TOKENS = 54000  # Jev limit is 64k for state and questions together; the estimate is up to ~8% low for big requests
# Jev counts about 1.63 characters per token in the state (Ukrainian and Russian JSON) and about 3.8 in the questions
# (English), measured on 121 answered requests (input_tokens of the response); the brief's 3 per token gave HTTP 400
# max_tokens_exceeded. Conservative values are used here.
STATE_CHARS_PER_TOKEN = 1.6
QUESTION_CHARS_PER_TOKEN = 3.5
MAX_WORKERS = 8
FALLBACK_CPT = (1.63, 3.81)  # characters per token (state, questions) for the spend estimate when the cache has too few requests
STRIKE_P = 0.5              # post-level threshold used by the checks (the hour rule is RULE below)

# Hour rule: post probabilities to the hour label. An hour is true when ANY of the enabled parts holds for the posts of the hour:
#   one      a single post with p >= one
#   official a post of VA_Kyiv or vitaliy_klitschko with p >= official
#   two      original (not repost) posts of at least 2 different channels, each with p >= two
# fresh (strike only): only posts that have a threat post (p_threat >= THREAT_GATE, any channel) in the FRESH_MINUTES up to them
# (this and the previous hour) count. It keeps out reports of damage hours after an attack and hours with drones only.
# originals (strike only): reposts (forwarded_from set) do not count; KMVA reposts recaps of the president, DSNS and DTEK.
THREAT_GATE = 0.5
FRESH_MINUTES = 90
RULE = {"strike": dict(one=0.7, official=0.5, two=0.5, fresh=True, originals=True),
        "threat": dict(one=0.8, official=0.5, two=0.5),
        "drone": dict(one=0.8, official=0.5, two=0.5),
        "ballistic": dict(one=0.8, official=0.5, two=0.5)}
CANDIDATES = {"any>=0.5": dict(one=0.5),
              "any>=0.8": dict(one=0.8),
              "official>=0.5 or 2ch>=0.5": dict(official=0.5, two=0.5),
              "any>=0.8 or official>=0.5 or 2ch>=0.5": dict(one=0.8, official=0.5, two=0.5),
              "fresh and any>=0.5": dict(one=0.5, fresh=True),
              "fresh and any>=0.7": dict(one=0.7, fresh=True),
              "fresh and any>=0.8": dict(one=0.8, fresh=True),
              "fresh and (official>=0.5 or 2ch>=0.5)": dict(official=0.5, two=0.5, fresh=True),
              "fresh and (any>=0.7 or official>=0.5 or 2ch>=0.5)": dict(one=0.7, official=0.5, two=0.5, fresh=True),
              "fresh and (any>=0.8 or official>=0.5 or 2ch>=0.5)": dict(one=0.8, official=0.5, two=0.5, fresh=True),
              "fresh and (any>=0.7 or official>=0.7 or 2ch>=0.5)": dict(one=0.7, official=0.7, two=0.5, fresh=True),
              "fresh, originals and any>=0.7": dict(one=0.7, fresh=True, originals=True),
              "fresh, originals and (any>=0.7 or official>=0.5 or 2ch>=0.5)": dict(one=0.7, official=0.5, two=0.5, fresh=True, originals=True)}
EXAMPLE_HOURS = ("2026-10-07T00:00:00Z", "2026-10-07T01:00:00Z", "2026-10-10T11:00:00Z", "2026-06-15T00:00:00Z", "2026-08-16T06:00:00Z",
                 "2026-05-14T10:00:00Z", "2026-05-24T09:00:00Z", "2026-09-15T13:00:00Z", "2026-09-28T17:00:00Z", "2026-10-07T14:00:00Z")

# ---------------------------------------------------------------- questions (English, post texts stay as they are)
_LEAD = ('Post "{pid}" (a post without a place name from a Kyiv channel is about the city of Kyiv; '
         'war_monitor covers all of Ukraine). ')
_Q = {
    "strike": (
        "Does this post report that missiles caused explosions, a shoot-down, falling debris or a hit in the city of Kyiv? "
        "Earlier posts of the state only show the weapon type.",
        'The post itself reports explosions, a shoot-down, debris or a hit in the city of Kyiv, also in short words such as '
        '"Гучно", "Вибухи", "Пролунали вибухи", and this post or an earlier post of the state shows missiles (ballistic, '
        'cruise or hypersonic) flying at the city, even if drones fly too.',
        "Only a warning, a track or an all clear; an event outside the city of Kyiv (Kyiv region, other cities); only drones "
        "or no missile context; a recap of an earlier attack (overnight or morning summary); an advert or other news."),
    "threat": (
        "Does this post warn that missiles are flying toward the city of Kyiv or that the city of Kyiv is under a missile threat?",
        "Missiles (ballistic, cruise or hypersonic, for example Iskander, Kinzhal, Zircon, Kalibr, Kh-101) are launched, in the "
        "air or flying toward Kyiv, or the missile threat for Kyiv is declared or continues (for example a red danger level "
        "because of missiles).",
        "A threat only from drones; a warning only for other regions or cities; an all clear; a report of explosions with no "
        "warning; a recap of an earlier attack; an advert or other news."),
    "drone": (
        "Does this post say that drones are flying toward or over the city of Kyiv, or exploding there?",
        'Drones (Shahed, Geran, UAVs, "mopeds") are reported flying toward Kyiv, over the city or its districts, being shot '
        "down there or exploding there.",
        "Only missiles; drones only in other cities or regions (towns of the Kyiv region); an all clear; an advert or other news."),
    "ballistic": (
        "Does this post say that ballistic missiles are heading to the city of Kyiv?",
        'Ballistic missiles ("балістика", Iskander, Kinzhal) are reported launched, flying or heading to Kyiv, or the ballistic '
        "threat for Kyiv is declared or continues.",
        "Cruise missiles, other hypersonic missiles or drones only; other cities or regions only; an all clear of the ballistic "
        "threat; an advert or other news."),
}


def questions_for(i, pid):
    """The four noul questions about post number i of the hour (id `pid` as in the state)."""
    return {f"{k}_{i}": {"type": "noul", "instructions": _LEAD.format(pid=pid) + ask, "criteria": {"true": t, "false": f}}
            for k, (ask, t, f) in _Q.items()}


# ---------------------------------------------------------------- time and label end
def parse_utc(s):
    """'2026-10-10T17:11:14Z' (or a datetime) to a naive UTC datetime."""
    if isinstance(s, dt.datetime):
        return s if s.tzinfo is None else s.astimezone(dt.timezone.utc).replace(tzinfo=None)
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo is None else t.astimezone(dt.timezone.utc).replace(tzinfo=None)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def floor_hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


@functools.lru_cache(maxsize=1)
def label_end():
    """Data end of the label, ISO UTC: the earliest of the 7 channels of `fetched_at` of the newest post in bronze.
    Hours h with h + 1h <= label_end are complete in all 7 channels."""
    ends = []
    for c in CHANNELS:
        newest = max(telegram.load(c), key=lambda r: (r["published_at"], r["post_id"]))
        ends.append(newest["fetched_at"])
    return min(ends, key=parse_utc)


def label_hours(start=None, end=None):
    """Hours (naive UTC datetimes on the hour) a..b-1 that may be labelled. start default FETCH_FROM (the first hour of
    bronze), end exclusive, default and upper limit floor_hour(label_end()): h < floor_hour(L) is the same as h + 1h <= L."""
    stop = floor_hour(parse_utc(label_end()))
    a = floor_hour(parse_utc(start)) if start else parse_utc(FETCH_FROM)
    b = min(floor_hour(parse_utc(end)), stop) if end else stop
    return [a + i * HOUR for i in range(max(int((b - a) / HOUR), 0))]


# ---------------------------------------------------------------- posts
@functools.lru_cache(maxsize=1)
def _by_hour():
    """Prefiltered posts of the 7 channels by hour: non-empty text and (any rx class of PARSING 2 or channel in KYIV_ONLY).
    Posts of one hour are in time order (published_at, channel, post_id). Hours with none are absent."""
    t = pq.read_table(SILVER / "tg_posts.parquet", filters=[("channel", "in", list(CHANNELS))],
                      columns=["channel", "post_id", "published_at", "text", "forwarded_from", "rx_classes", "rx_evidence"])
    posts = [r for r in t.to_pylist() if r["text"] and (r["rx_classes"] or r["channel"] in KYIV_ONLY)]
    posts.sort(key=lambda r: (r["published_at"], r["channel"], r["post_id"]))
    by = defaultdict(list)
    for r in posts:
        by[floor_hour(r["published_at"])].append(r)
    return dict(by)


def _entry(p, h):
    return {"id": f'{p["channel"]}/{p["post_id"]}', "channel": p["channel"], "minute": f'{p["published_at"].minute:02d}',
            "hour": "this" if floor_hour(p["published_at"]) == h else "previous", "text": p["text"].strip()}


def _plan(prev, this, h):
    """Work windows of hour h: [(entries, chars, first, last, dropped, mode)]. entries is the state (posts in time order),
    first..last the range of this-hour posts the questions are about.
    full: one window. dropped: one window, the oldest previous-hour posts were dropped to fit MAX_STATE_TOKENS.
    windowed: the posts of the hour alone are over the limit, so the hour is cut in time into windows, each with the latest
    earlier posts (also of the previous hour) as context. Later posts are never in a state."""
    limit = MAX_STATE_TOKENS * STATE_CHARS_PER_TOKEN
    entries = [_entry(p, h) for p in prev + this]
    sizes = [len(json.dumps(e, ensure_ascii=False)) + 2 for e in entries]
    base, n0 = len('{"posts": []}'), len(prev)
    chars, dropped = base + sum(sizes), 0
    while chars > limit and dropped < n0:
        chars -= sizes[dropped]
        dropped += 1
    if chars <= limit:
        return [(entries[dropped:], chars, 0, len(this), dropped, "dropped" if dropped else "full")]
    out, start, ctx_budget = [], 0, limit // 4
    while start < len(this):
        end, size = start, base
        while end < len(this) and size + sizes[n0 + end] <= limit - ctx_budget:
            size += sizes[n0 + end]
            end += 1
        if end == start:
            raise ValueError(f"hour {iso(h)}: post {entries[n0 + start]['id']} alone is over the state limit")
        c, ctx = n0 + start, 0
        while c > 0 and ctx + sizes[c - 1] <= ctx_budget:
            c -= 1
            ctx += sizes[c]
        out.append((entries[c:n0 + end], ctx + size, start, end, 0, "windowed"))
        start = end
    return out


_PER_POST_TOKENS = len(json.dumps(questions_for(0, "vitaliy_klitschko/00000"), ensure_ascii=False)) / QUESTION_CHARS_PER_TOKEN


def build_requests(hours, by_hour=None):
    """Jev requests for the given hours (datetimes or ISO strings, on the hour, h + 1h <= label_end). Hours without
    prefiltered posts give no request (all four labels false). Per hour: state = {"posts": [{id, channel, minute, hour, text}]}
    with the prefiltered posts of [h-1h, h+1h) in time order, hour "previous" or "this". Posts at or after h+1h are never in it.
    Questions are asked only about the posts of hour h, at most MAX_POSTS (fewer for a big state) per request, same state.
    A state over MAX_STATE_TOKENS loses its oldest previous-hour posts first; if the posts of the hour alone are over it, the
    hour is cut in time into windows (see _plan). Each request is {hour, part, state, questions, posts: [(i, post)],
    dropped, mode}; i is the number of the post among the prefiltered posts of hour h, the same in every part."""
    by = _by_hour() if by_hour is None else by_hour
    last = parse_utc(label_end())
    out = []
    for h in sorted({parse_utc(x) for x in hours}):
        if h != floor_hour(h):
            raise ValueError(f"{h} is not on the hour")
        if h + HOUR > last:
            raise ValueError(f"hour {iso(h)} ends after label_end {iso(last)}")
        this = by.get(h, [])
        if not this:
            continue
        part = 0
        for entries, chars, first, end, dropped, mode in _plan(by.get(h - HOUR, []), this, h):
            state = {"posts": entries}
            per = max(1, min(MAX_POSTS, int((MAX_REQUEST_TOKENS - chars / STATE_CHARS_PER_TOKEN) // _PER_POST_TOKENS)))
            for k in range(first, end, per):
                idx = range(k, min(k + per, end))
                qs = {}
                for i in idx:
                    qs.update(questions_for(i, f'{this[i]["channel"]}/{this[i]["post_id"]}'))
                out.append({"hour": h, "part": part, "state": state, "questions": qs, "posts": [(i, this[i]) for i in idx],
                            "dropped": dropped, "mode": mode})
                part += 1
    return out


def _prob(a):
    return float(a["noul"] if isinstance(a, dict) else a)


def post_probabilities(hours, workers=MAX_WORKERS, by_hour=None):
    """One row per prefiltered post of the given hours: p_strike, p_threat, p_drone, p_ballistic (probabilities of "true"),
    jev_model, prompt_version. Answers come from the Jev cache (tag kyiv_threat_hourly) or are asked and cached."""
    reqs = build_requests(hours, by_hour)
    answers = ask_many([(r["state"], r["questions"]) for r in reqs], tag=TABLE, workers=workers)
    rows = []
    for r, ans in zip(reqs, answers):
        for i, p in r["posts"]:
            rows.append({"hour": r["hour"], "channel": p["channel"], "post_id": p["post_id"], "published_at": p["published_at"],
                         "is_original": not p["forwarded_from"], "rx_evidence": p["rx_evidence"], "rx_classes": p["rx_classes"],
                         "text": p["text"], **{f"p_{k}": _prob(ans[f"{k}_{i}"]) for k in KINDS},
                         "jev_model": MODEL, "prompt_version": PROMPT_VERSION})
    return rows


# ---------------------------------------------------------------- hour rule
def hour_flag(rows, kind, one=None, two=None, official=None):
    """True when the rule parts say so; rows: post rows of ONE hour (channel, is_original, p_<kind>)."""
    p = f"p_{kind}"
    if one is not None and any(r[p] >= one for r in rows):
        return True
    if official is not None and any(r["channel"] in OFFICIAL and r[p] >= official for r in rows):
        return True
    return two is not None and len({r["channel"] for r in rows if r["is_original"] and r[p] >= two}) >= 2


def fresh_rows(rows, prev_rows=()):
    """Posts of the hour that have a threat post (p_threat >= THREAT_GATE, any channel) in the FRESH_MINUTES up to them, looking
    at this and the previous hour. A report of damage hours after the attack has none."""
    times = sorted(r["published_at"] for r in list(prev_rows) + list(rows) if r["p_threat"] >= THREAT_GATE)
    span = dt.timedelta(minutes=FRESH_MINUTES)
    out = []
    for r in rows:
        i = bisect.bisect_right(times, r["published_at"])
        if i and times[i - 1] >= r["published_at"] - span:
            out.append(r)
    return out


def strike_flag(rows, prev_rows=(), fresh=False, originals=False, **kw):
    use = fresh_rows(rows, prev_rows) if fresh else rows
    if originals:
        use = [r for r in use if r["is_original"]]
    return hour_flag(use, "strike", **kw)


def hour_labels(rows, prev_rows=()):
    """The four hour labels from the post rows of hour h and of hour h-1 (only the strike rule reads prev_rows). Empty rows:
    all false, no Jev call was made."""
    out = {}
    for k in KINDS:
        rule = dict(RULE[k])
        use = fresh_rows(rows, prev_rows) if rule.pop("fresh", False) else rows
        if rule.pop("originals", False):
            use = [r for r in use if r["is_original"]]
        out[HOUR_COLUMNS[k]] = hour_flag(use, k, **rule)
    return out


# ---------------------------------------------------------------- regex rules A and B of PARSING 2 (reference only)
@functools.lru_cache(maxsize=1)
def regex_rules():
    """Per hour with prefiltered posts: {n_ev, A, B}. n_ev = posts with rx_evidence. A: a post of VA_Kyiv or vitaliy_klitschko
    with rx_evidence; B: original rx_evidence posts of 2 different monitoring channels within 30 min of each other; both
    need a missile_threat post (any of the 7 channels) in the 90 min up to that post (up to the earlier post for B)."""
    by = _by_hour()
    threats = sorted(p["published_at"] for ps in by.values() for p in ps if "missile_threat" in p["rx_classes"])

    def threat_before(t):
        i = bisect.bisect_right(threats, t)
        return i > 0 and threats[i - 1] >= t - dt.timedelta(minutes=90)

    out = {}
    for h, ps in by.items():
        ev = [p for p in ps if p["rx_evidence"]]
        a = any(p["channel"] in OFFICIAL and threat_before(p["published_at"]) for p in ev)
        mon = [p for p in ev if p["channel"] in MONITORS and not p["forwarded_from"]]
        b = False
        for i, p in enumerate(mon):
            if not threat_before(p["published_at"]):
                continue
            for q in mon[i + 1:]:
                if q["published_at"] - p["published_at"] > dt.timedelta(minutes=30):
                    break
                if q["channel"] != p["channel"]:
                    b = True
                    break
            if b:
                break
        out[h] = {"n_ev": len(ev), "A": a, "B": b}
    return out


# ---------------------------------------------------------------- classify
def _cache_files():
    d = CACHE / TABLE
    return set(d.rglob("*.json")) if d.exists() else set()


def classify(start=None, end=None, workers=MAX_WORKERS, chunk_hours=24, log=print):
    """Send every request of the hours [start, end) to Jev (answers cached, so a rerun costs nothing)."""
    if not 1 <= workers <= MAX_WORKERS:
        raise SystemExit(f"--workers must be 1..{MAX_WORKERS}")
    hours = label_hours(start, end)
    if not hours:
        raise SystemExit("no hours in the range")
    todo = [h for h in hours if _by_hour().get(h)]
    log(f"label_end {label_end()}; hours {len(hours)} from {iso(hours[0])} to {iso(hours[-1])}; "
        f"{len(todo)} with prefiltered posts, {len(hours) - len(todo)} without (all labels false, no Jev call)")
    seen, calls, tokens, n_req, t0 = _cache_files(), 0, 0, 0, time.time()
    for i in range(0, len(todo), chunk_hours):
        reqs = build_requests(todo[i:i + chunk_hours])
        ask_many([(r["state"], r["questions"]) for r in reqs], tag=TABLE, workers=workers)
        n_req += len(reqs)
        for p in _cache_files() - seen:
            seen.add(p)
            calls += 1
            tokens += json.loads(p.read_text(encoding="utf-8"))["response"].get("usage", {}).get("input_tokens", 0)
        log(f"hours {min(i + chunk_hours, len(todo))}/{len(todo)}  requests {n_req}  new calls {calls}  "
            f"new input tokens {tokens}  spend of this run ${tokens / 1e6 * USD_PER_MTOK:.4f}  {time.time() - t0:.0f} s")
    log(f"done: requests {n_req}, new calls {calls}; cache {TABLE}: {usage(TABLE)}")


def calibrate():
    """Characters per token that Jev billed, by least squares of `input_tokens` of the cached answers on the characters of the
    state and of the questions. Returns (state, questions, n_requests, largest request in tokens)."""
    pts = []
    for f in (CACHE / TABLE).rglob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        pts.append((len(json.dumps(d["request"]["state"], ensure_ascii=False)),
                    len(json.dumps(d["request"]["questions"], ensure_ascii=False)), d["response"]["usage"]["input_tokens"]))
    if len(pts) < 50:
        return (*FALLBACK_CPT, len(pts), max((p[2] for p in pts), default=0))
    s11, s12, s22 = sum(a * a for a, _, _ in pts), sum(a * b for a, b, _ in pts), sum(b * b for _, b, _ in pts)
    t1, t2 = sum(a * t for a, _, t in pts), sum(b * t for _, b, t in pts)
    det = s11 * s22 - s12 * s12
    return 1 / ((t1 * s22 - t2 * s12) / det), 1 / ((s11 * t2 - s12 * t1) / det), len(pts), max(p[2] for p in pts)


def stats(start=None, end=None, log=print):
    """Size of the full classification of label_hours(): hours, requests by mode, estimated tokens and spend (no Jev calls)."""
    from collections import Counter
    hours = label_hours(start, end)
    todo = [h for h in hours if _by_hour().get(h)]
    cs, cq, n_cal, _ = calibrate()
    modes, n, multi, tokens, peak = Counter(), 0, 0, 0.0, 0.0
    for i in range(0, len(todo), 50):
        for r in build_requests(todo[i:i + 50]):
            t = len(json.dumps(r["state"], ensure_ascii=False)) / cs + \
                len(json.dumps(r["questions"], ensure_ascii=False)) / cq
            n, tokens, peak = n + 1, tokens + t, max(peak, t)
            modes[r["mode"]] += r["part"] == 0
            multi += r["part"] == 1
    log(f"label_end {label_end()}; hours {len(hours)} from {iso(hours[0])} to {iso(hours[-1])}; with prefiltered posts {len(todo)}")
    log(f"requests {n}; hours by mode {dict(modes)}; hours with more than one request {multi}")
    log(f"estimated input tokens {tokens:.0f} (largest request {peak:.0f}), estimated spend ${tokens / 1e6 * USD_PER_MTOK:.2f}; "
        f"characters per token {cs:.2f} (state) and {cq:.2f} (questions) from {n_cal} cached requests")


# ---------------------------------------------------------------- leak test (no Jev calls)
def check(n=20, seed=20261010, log=print):
    """For n random hours plus up to 10 hours with a dropped or windowed state: no state holds a post at or after h+1h (read
    back through DuckDB, independent of the module), the hour tags are right, the states hold exactly the prefiltered posts
    of [h-1h, h+1h) (a full state all of them, a dropped one without the oldest), the questions cover each post of hour h
    once, and the requests do not change when all later posts are cut away."""
    rng = random.Random(seed)
    by = _by_hour()
    hours = [h for h in label_hours(T0) if by.get(h)]
    special = [h for h in hours if _plan(by.get(h - HOUR, []), by[h], h)[0][5] != "full"]
    sample = sorted(set(rng.sample(hours, n)) | set(rng.sample(special, min(10, len(special)))))
    con = connect()
    src = SILVER / "tg_posts.parquet"
    chans = ", ".join(f"'{c}'" for c in CHANNELS)
    kyonly = ", ".join(f"'{c}'" for c in sorted(KYIV_ONLY))
    bad = 0
    for h in sample:
        reqs = build_requests([h])
        uniq = sorted({e["id"] for r in reqs for e in r["state"]["posts"]})
        pub = dict(con.execute("SELECT channel || '/' || post_id, published_at FROM read_parquet(?) "
                               "WHERE list_contains(?, channel || '/' || post_id)", [str(src), uniq]).fetchall())
        rows = con.execute(
            f"SELECT channel || '/' || post_id, published_at FROM read_parquet('{src}') WHERE channel IN ({chans}) "
            f"AND text <> '' AND (len(rx_classes) > 0 OR channel IN ({kyonly})) AND published_at >= ? AND published_at < ? "
            f"ORDER BY published_at, channel, post_id", [h - HOUR, h + HOUR]).fetchall()
        want = [i for i, _ in rows]
        want_this = [i for i, t in rows if t >= h]
        late = [i for i in uniq if pub[i] >= h + HOUR]
        wrong_tag = [e["id"] for r in reqs for e in r["state"]["posts"]
                     if (e["hour"] == "this") != (h <= pub[e["id"]] < h + HOUR) or not (h - HOUR <= pub[e["id"]] < h + HOUR)]
        mode, dropped = reqs[0]["mode"], reqs[0]["dropped"]
        first_ids = [e["id"] for e in reqs[0]["state"]["posts"]]
        content_ok = set(uniq) <= set(want) and (first_ids == want[dropped:] if mode != "windowed" else True)
        asked = [f'{p["channel"]}/{p["post_id"]}' for r in reqs for _, p in r["posts"]]
        cut_by = {k: v for k, v in by.items() if k < h + HOUR}
        same_cut = json.dumps([(r["state"], r["questions"]) for r in build_requests([h], by_hour=cut_by)], sort_keys=True) == \
            json.dumps([(r["state"], r["questions"]) for r in reqs], sort_keys=True)
        later = sum(len(v) for k, v in by.items() if k >= h + HOUR)
        ok = not late and not wrong_tag and content_ok and asked == want_this and same_cut and later > 0
        bad += not ok
        log(f"{iso(h)} {mode:8} requests {len(reqs):2} state posts {len(uniq):3} (dropped {dropped}) latest {max(pub.values())} "
            f"h+1h {h + HOUR} later posts in the data {later} asked {len(asked)}: "
            f"{'ok' if ok else f'FAIL late={late} wrong_tag={wrong_tag} content_ok={content_ok} same_cut={same_cut}'}")
    try:
        build_requests([floor_hour(parse_utc(label_end()))])
        bad += 1
        log("FAIL: the hour that ends after label_end was accepted")
    except ValueError as e:
        log(f"hour after label_end refused: {e}")
    log(f"label_end {label_end()}; {len(sample)} hours checked ({n} random, {len(sample) - n} dropped or windowed), "
        f"{len(special)} such hours in all, {bad} failures")
    log("ALL OK" if not bad else "FAIL")
    return not bad


# ---------------------------------------------------------------- pilot
def pilot_hours(seed=20261010):
    """~93 hours: 3 known events, the 20 hours with the most rx_evidence posts, 30 random hours with posts, 20 random hours
    where rule A or B is true, 20 borderline (10 with rx_evidence but neither A nor B, 10 with a missile_threat post and an
    explosion/debris/impact post but no rx_evidence), the borderline ones spread over the months. Dict hour: group."""
    rng, rules, by = random.Random(seed), regex_rules(), _by_hour()
    hours = label_hours(T0)
    picked = {}

    def add(h, g):
        picked.setdefault(h, g)

    for s in ("2026-10-07T00:00:00Z", "2026-10-07T01:00:00Z", "2026-10-10T11:00:00Z"):
        add(parse_utc(s), "known")
    k = 0
    for h in sorted((h for h in hours if h in rules), key=lambda h: (-rules[h]["n_ev"], h)):
        if k >= 20:
            break
        if h not in picked:
            add(h, "top_ev")
            k += 1

    def sample(pool, k, g):
        pool = [h for h in pool if h not in picked]
        for h in sorted(rng.sample(pool, min(k, len(pool)))):
            add(h, g)

    def spread(pool, k, g):
        groups = defaultdict(list)
        for h in pool:
            if h not in picked:
                groups[(h.year, h.month)].append(h)
        for v in groups.values():
            rng.shuffle(v)
        n = 0
        while n < k and any(groups.values()):
            for m in sorted(groups):
                if n < k and groups[m]:
                    add(groups[m].pop(), g)
                    n += 1

    def boom(h):
        return any(c in p["rx_classes"] for p in by[h] for c in ("explosion", "debris", "impact_damage"))

    sample([h for h in hours if h in by], 30, "random")
    sample([h for h in hours if h in rules and (rules[h]["A"] or rules[h]["B"])], 20, "rule_ab")
    spread([h for h in hours if h in rules and rules[h]["n_ev"] and not (rules[h]["A"] or rules[h]["B"])], 10, "border_ev")
    spread([h for h in hours if h in rules and not rules[h]["n_ev"] and boom(h)
            and any("missile_threat" in p["rx_classes"] for p in by[h])], 10, "border_noev")
    return dict(sorted(picked.items()))


def _txt(r, n=150):
    return r["text"].replace("\n", " / ")[:n]


def pilot(workers=MAX_WORKERS, log=print):
    """Classify the pilot hours and the hours before them (cached after the first run) and print the table, the agreement with
    rules A and B, the known events, the candidate strike rules, the examples and the hours where the hour rule and the regex
    rules disagree."""
    picked = pilot_hours()
    hours = list(picked)
    rows = post_probabilities(sorted(set(hours) | {h - HOUR for h in hours}), workers=workers)
    by_h = defaultdict(list)
    for r in rows:
        by_h[r["hour"]].append(r)
    rules = regex_rules()

    def labels(h):
        return hour_labels(by_h.get(h, []), by_h.get(h - HOUR, []))

    log(f"pilot hours {len(hours)}: " + ", ".join(f"{g} {sum(1 for v in picked.values() if v == g)}" for g in dict.fromkeys(picked.values())))
    log("hour | group | n_posts | n_ev | rule | A | B | max_p_strike | posts>=0.5 | threat | drone | ballistic")
    table = {}
    for h in hours:
        rs, lab = by_h.get(h, []), labels(h)
        a, b = rules[h]["A"], rules[h]["B"]
        table[h] = (lab, a, b)
        log(f"{iso(h)} | {picked[h]} | {len(rs)} | {rules[h]['n_ev']} | {int(lab['missile_strike'])} | {int(a)} | {int(b)} | "
            f"{max((r['p_strike'] for r in rs), default=0):.2f} | {sum(r['p_strike'] >= STRIKE_P for r in rs)} | "
            f"{int(lab['missile_threat'])} | {int(lab['drone_threat'])} | {int(lab['ballistic'])}")
    both = sum(1 for h in hours if table[h][0]["missile_strike"] and (table[h][1] or table[h][2]))
    jev_only = sum(1 for h in hours if table[h][0]["missile_strike"] and not (table[h][1] or table[h][2]))
    rx_only = sum(1 for h in hours if not table[h][0]["missile_strike"] and (table[h][1] or table[h][2]))
    log(f"hour rule {RULE['strike']}: missile_strike true {both + jev_only}; with A or B {both + rx_only}; "
        f"both {both}, Jev only {jev_only}, A or B only {rx_only}, neither {len(hours) - both - jev_only - rx_only}")
    log("candidate strike rules: name | true | both with A or B | Jev only | A or B only")
    for name, kw in CANDIDATES.items():
        t = {h: strike_flag(by_h.get(h, []), by_h.get(h - HOUR, []), **kw) for h in hours}
        bo = sum(1 for h in hours if t[h] and (rules[h]["A"] or rules[h]["B"]))
        log(f"  {name} | {sum(t.values())} | {bo} | {sum(t.values()) - bo} | "
            f"{sum(1 for h in hours if not t[h] and (rules[h]['A'] or rules[h]['B']))}")
    log("known events:")
    for s in ("2026-10-07T00:00:00Z", "2026-10-07T01:00:00Z", "2026-10-10T11:00:00Z"):
        h = parse_utc(s)
        hot = [r for r in by_h.get(h, []) if r["p_strike"] >= STRIKE_P]
        first = min(hot, key=lambda r: r["published_at"]) if hot else None
        log(f"  {s} missile_strike {labels(h)['missile_strike']}; posts with p_strike >= {STRIKE_P}: {len(hot)}; "
            + (f"earliest {first['channel']}/{first['post_id']} {first['published_at']:%H:%M:%S}Z p={first['p_strike']:.2f} | {_txt(first, 90)}" if first else "none"))
        top = [r for r in by_h.get(h, []) if r["p_strike"] >= 0.7]
        if top:
            f7 = min(top, key=lambda r: r["published_at"])
            log(f"    earliest with p_strike >= 0.7: {f7['channel']}/{f7['post_id']} {f7['published_at']:%H:%M:%S}Z p={f7['p_strike']:.2f}")
    log("  posts of 2026-10-07T00:00:00Z from minute 08 to 20 with p_strike >= 0.25 (s strike, t threat, d drone, b ballistic):")
    for r in by_h.get(parse_utc("2026-10-07T00:00:00Z"), []):
        if 8 <= r["published_at"].minute <= 20 and r["p_strike"] >= 0.25:
            log(f"    s={r['p_strike']:.2f} t={r['p_threat']:.2f} d={r['p_drone']:.2f} b={r['p_ballistic']:.2f} {r['published_at']:%H:%M:%S} "
                f"{r['channel']}/{r['post_id']} | {_txt(r, 70)}")
    log("EXAMPLES (hour rule, A, B, the 4 posts with the highest p_strike; s strike, t threat, d drone, b ballistic):")
    for s in EXAMPLE_HOURS:
        h = parse_utc(s)
        log(f"== {s} rule={labels(h)['missile_strike']} A={rules.get(h, {}).get('A')} B={rules.get(h, {}).get('B')} posts={len(by_h.get(h, []))}")
        for r in sorted(sorted(by_h.get(h, []), key=lambda r: -r["p_strike"])[:4], key=lambda r: r["published_at"]):
            log(f"   s={r['p_strike']:.2f} t={r['p_threat']:.2f} d={r['p_drone']:.2f} b={r['p_ballistic']:.2f} {r['published_at']:%H:%M:%S} "
                f"{r['channel']}/{r['post_id']}{'' if r['is_original'] else ' fwd'} | {_txt(r, 120)}")
    log("DISAGREEMENTS (hour rule vs A or B), posts with the highest p_strike and the rx_evidence posts:")
    for h in hours:
        lab, a, b = table[h]
        if lab["missile_strike"] != bool(a or b):
            log(f"== {iso(h)} {picked[h]} rule={lab['missile_strike']} A={a} B={b}")
            show = sorted(by_h.get(h, []), key=lambda r: -r["p_strike"])[:5]
            show += [r for r in by_h.get(h, []) if r["rx_evidence"] and r not in show][:3]
            for r in sorted(show, key=lambda r: r["published_at"]):
                log(f"   p={r['p_strike']:.2f} thr={r['p_threat']:.2f} {r['published_at']:%H:%M:%S} {r['channel']}/{r['post_id']}"
                    f"{' EV' if r['rx_evidence'] else ''}{'' if r['is_original'] else ' fwd'} | {_txt(r, 120)}")
    return table


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -I -m airalerts.silver.threat_hourly",
                                 description="Jev classifier of the Kyiv posts (S3a). The silver build is added by S3b.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify", help="send every request of a range of hours to Jev (cached, resumable)")
    c.add_argument("--from", dest="start", help="first hour, ISO UTC (default: first hour of bronze, FETCH_FROM)")
    c.add_argument("--to", dest="end", help="end, exclusive, ISO UTC (default and limit: floor_hour(label_end))")
    c.add_argument("--workers", type=int, default=MAX_WORKERS, help=f"Jev workers, 1..{MAX_WORKERS}")
    sub.add_parser("check", help="leak test on 20 random hours, no Jev calls")
    sub.add_parser("label_end", help="print label_end")
    st = sub.add_parser("stats", help="size and estimated spend of the classification of a range, no Jev calls")
    st.add_argument("--from", dest="start")
    st.add_argument("--to", dest="end")
    sub.add_parser("calibrate", help="characters per token Jev billed, from the cache")
    p = sub.add_parser("pilot", help="classify the pilot hours and print the report")
    p.add_argument("--workers", type=int, default=MAX_WORKERS)
    a = ap.parse_args(argv)
    if a.cmd == "classify":
        classify(a.start, a.end, a.workers)
    elif a.cmd == "check":
        raise SystemExit(0 if check() else 1)
    elif a.cmd == "label_end":
        print(label_end())
    elif a.cmd == "stats":
        stats(a.start, a.end)
    elif a.cmd == "calibrate":
        cs, cq, n, big = calibrate()
        print(f"requests {n}; state {cs:.2f} characters per token, questions {cq:.2f}; largest request {big} tokens")
    elif a.cmd == "pilot":
        pilot(a.workers)


if __name__ == "__main__":
    main()
