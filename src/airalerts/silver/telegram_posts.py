"""Silver tg_posts: every Telegram post of every bronze channel in one table, with the regex classes of PARSING 2 and the
signals of PARSING 7 (patterns: telegram_rx.py). Input of the label (kyiv_threat_*) and signal (prep_signal_events) builders.
Rules: docs/PARSING.md 0.1, 2, 7. Table: docs/data/silver/tg_posts.md.
Build:     .venv/bin/python -I -m airalerts.silver.telegram_posts
Self-test: .venv/bin/python -I -m airalerts.silver.telegram_posts check
The whole table is rebuilt on every run, so a rerun after the downloads finish picks up the complete files."""
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..db import connect
from ..paths import SILVER, T0
from ..telegram import TG, channels, load
from .telegram_rx import KYIV, classify, signals

TABLE = SILVER / "tg_posts.parquet"
TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
ROLES = {
    "VA_Kyiv": "kyiv_official", "vitaliy_klitschko": "kyiv_official",
    "truexakyiv": "kyiv_monitor", "AerisRimor": "kyiv_monitor", "kyiv_nebo": "kyiv_monitor", "kyiv_airdef": "kyiv_monitor",
    "war_monitor": "monitor_ua", "kpszsu": "monitor_ua", "StrategicaviationT": "monitor_ua", "monitorwarr": "monitor_ua",
    "vanek_nikolaev": "monitor_ua",
    "mod_russia": "rf_official", "mos_sobyanin": "rf_official", "favt_info": "rf_official",
    "GeneralStaffZSU": "ua_official", "OP_UA": "ua_official", "V_Zelenskiy_official": "ua_official",
    "UkraineAlarmSignal": "alert_feed"}
SCHEMA = pa.schema([
    ("channel", pa.string()), ("post_id", pa.int64()), ("published_at", pa.timestamp("us")), ("text", pa.string()),
    ("edited", pa.bool_()), ("forwarded_from", pa.string()), ("is_original", pa.bool_()), ("views", pa.int64()),
    ("url", pa.string()), ("channel_role", pa.string()), ("rx_classes", pa.list_(pa.string())),
    ("rx_kyiv_city", pa.bool_()), ("rx_evidence", pa.bool_()), ("rx_signals", pa.list_(pa.string())),
    ("available_at", pa.timestamp("us"))])

# A post is known the moment it is published (PARSING 0). Posts with edited = true may carry text added later: PARSING 0.1.
ASOF = {"tg_posts": "SELECT * FROM tg_posts WHERE available_at < {t}"}

VIEWS = re.compile(r"(\d+(?:\.\d+)?)([KM]?)")
UNIT = {"": 1, "K": 1000, "M": 1000000}


def parse_views(v):
    """'6.83K' is 6830, '1.2M' is 1200000, '55' is 55, None stays None; any other form stops the build."""
    if v is None:
        return None
    m = VIEWS.fullmatch(v)
    if not m:
        raise ValueError(f"views in an unknown form: {v!r}")
    return int(Decimal(m.group(1)) * UNIT[m.group(2)])


def complete_channels():
    """Channels with a line '<time> done <channel>' in one of the lane logs A, B, C (PLAN: how the downloads report)."""
    done = set()
    for lane in "ABC":
        p = TG / "logs" / f"{lane}.log"
        if p.exists():
            done |= set(re.findall(r"^\S+ done (\S+)[ \t]*$", p.read_text(encoding="utf-8"), re.M))
    return done


def load_retry(channel, tries=6):
    """telegram.load, repeated while a downloader is appending and the last line of the file is cut."""
    for _ in range(tries - 1):
        try:
            return load(channel)
        except json.JSONDecodeError:
            time.sleep(2)
    return load(channel)


def channel_table(ch):
    """(pyarrow table, stats) of one channel; every column of SCHEMA, rx_* computed once per distinct text."""
    if ch not in ROLES:
        sys.exit(f"channel {ch} has no role: add it to ROLES in telegram_posts.py and to docs/data/silver/tg_posts.md")
    rows = load_retry(ch)
    n = len(rows)
    if not n:
        return None, dict(channel=ch, rows=0)
    memo, cls, kyiv, evid, sig = {}, [], [], [], []
    for r in rows:
        text = r["text"]
        m = memo.get(text)
        if m is None:
            c, k, e = classify(ch, text)
            m = memo[text] = (c, k, e, signals(text))
        cls.append(m[0]), kyiv.append(m[1]), evid.append(m[2]), sig.append(m[3])
    when = pc.strptime(pa.array([r["published_at"] for r in rows], pa.string()), format=TIME_FMT, unit="us")
    fwd = [r["forwarded_from"] for r in rows]
    arrays = [pa.array([ch] * n, pa.string()), pa.array([r["post_id"] for r in rows], pa.int64()), when,
              pa.array([r["text"] for r in rows], pa.string()), pa.array([r["edited"] for r in rows], pa.bool_()),
              pa.array(fwd, pa.string()), pa.array([f is None for f in fwd], pa.bool_()),
              pa.array([parse_views(r["views"]) for r in rows], pa.int64()),
              pa.array([r["url"] for r in rows], pa.string()), pa.array([ROLES[ch]] * n, pa.string()),
              pa.array(cls, pa.list_(pa.string())), pa.array(kyiv, pa.bool_()), pa.array(evid, pa.bool_()),
              pa.array(sig, pa.list_(pa.string())), when]
    ids = [r["post_id"] for r in rows]
    return pa.Table.from_arrays(arrays, schema=SCHEMA), dict(
        channel=ch, rows=n, first=min(r["published_at"] for r in rows), last=max(r["published_at"] for r in rows),
        min_id=min(ids), max_id=max(ids))


def main():
    t0 = time.time()
    done = complete_channels()
    parts, stats = [], []
    for ch in channels():
        t, s = channel_table(ch)
        s["complete"] = ch in done
        stats.append(s)
        if t is not None:
            parts.append(t)
    table = pa.concat_tables(parts)
    table = table.take(pc.sort_indices(table, sort_keys=[("published_at", "ascending"), ("channel", "ascending"),
                                                           ("post_id", "ascending")]))
    present = {s["channel"] for s in stats}
    meta = {"built_at": datetime.now(timezone.utc).strftime(TIME_FMT),
            "channels_complete": ",".join(sorted(done & present)),
            "channels_incomplete": ",".join(sorted(set(ROLES) - (done & present)))}
    tmp = TABLE.with_suffix(".tmp")
    pq.write_table(table.replace_schema_metadata(meta), tmp, compression="zstd", row_group_size=100_000)
    os.replace(tmp, TABLE)
    print(f"{'channel':22}{'rows':>8}  {'first published_at':21}{'last published_at':21}{'min_id':>8}{'max_id':>8}  complete")
    for s in stats:
        print(f"{s['channel']:22}{s['rows']:>8}  {s.get('first', ''):21}{s.get('last', ''):21}"
              f"{s.get('min_id', ''):>8}{s.get('max_id', ''):>8}  {'yes' if s['complete'] else 'no'}")
    for ch in sorted(set(ROLES) - present):
        print(f"{ch:22}{'no bronze file yet':>8}  complete no")
    total = sum(s["rows"] for s in stats)
    print(f"tg_posts: {table.num_rows} rows (sum of unique post_id per channel {total}), {len(present)} channels with files, "
          f"{len(done & present)} complete, run time {time.time() - t0:.1f} s")


# ---- self-test: python -m airalerts.silver.telegram_posts check ----

CONTROL_01 = [  # control posts of PARSING 0.1: channel, post_id, published_at
    ("VA_Kyiv", 17852, "2026-05-01T05:59:01Z"), ("vitaliy_klitschko", 6552, "2026-05-02T20:10:48Z"),
    ("truexakyiv", 74876, "2026-05-01T04:15:54Z"), ("war_monitor", 39394, "2026-04-30T21:00:41Z"),
    ("AerisRimor", 68042, "2026-04-30T22:00:41Z"), ("kpszsu", 61012, "2026-04-30T22:09:30Z"),
    ("mod_russia", 63081, "2026-05-01T03:07:01Z"), ("GeneralStaffZSU", 37996, "2026-05-01T03:47:32Z"),
    ("mos_sobyanin", 19581, "2026-05-01T07:00:04Z"), ("favt_info", 4747, "2026-04-30T22:05:45Z"),
    ("StrategicaviationT", 30395, "2026-04-30T23:05:15Z"), ("monitorwarr", 35743, "2026-04-30T22:22:16Z"),
    ("vanek_nikolaev", 40385, "2026-04-30T22:02:22Z"), ("OP_UA", 18635, "2026-05-01T11:49:35Z"),
    ("V_Zelenskiy_official", 18830, "2026-05-01T07:01:12Z"), ("kyiv_nebo", 22901, "2026-05-01T06:51:13Z"),
    ("kyiv_airdef", 33830, "2026-04-30T21:44:25Z")]
CONTROL_2 = [  # PARSING 2, "Перевірка"
    ("VA_Kyiv", 21514, "2026-10-07T00:10:14Z"), ("AerisRimor", 89451, "2026-10-07T00:31:57Z"),
    ("vitaliy_klitschko", 7775, "2026-10-07T00:35:44Z"), ("vitaliy_klitschko", 7822, "2026-10-10T11:04:10Z"),
    ("VA_Kyiv", 21658, "2026-10-10T11:20:27Z"), ("VA_Kyiv", 21659, "2026-10-10T11:35:57Z")]
# channel, post_id, class, rx_kyiv_city required, rx_evidence required (None: not required)
CLASS_EXAMPLES = [("kyiv_airdef", 75885, "missile_threat", None, None), ("AerisRimor", 89451, "explosion", True, None),
                  ("vitaliy_klitschko", 7775, "impact_damage", None, True), ("VA_Kyiv", 21514, "missile_threat", None, None)]
# views: K with 2 decimals, M, plain number, null (channel, post_id)
VIEW_EXAMPLES = [("GeneralStaffZSU", 37672), ("V_Zelenskiy_official", 18768), ("VA_Kyiv", 21675), ("GeneralStaffZSU", 42097)]
# id gaps over 30 (PARSING 2 reads such a gap as a pagination failure). This one lies inside one page response (both posts carry
# the same fetched_at in bronze), so it is a run of ids deleted in the channel: docs/data/silver/tg_posts.md, section Пастки
EXPLAINED_GAPS = {("truexakyiv", 79219, 79250)}
DAY = ("2026-10-09 00:00:00", "2026-10-10 00:00:00")
EXPECT_DAY = {  # posts, S1, S2, S3, S4, S5, KYIV counted on the stored text (no reply quote, PARSING 0.1)
    "war_monitor": (37, 0, 0, 0, 30, 0, 28), "kpszsu": (455, 0, 0, 0, 382, 0, 104), "AerisRimor": (105, 0, 0, 0, 39, 0, 1),
    "StrategicaviationT": (116, 3, 1, 0, 14, 0, 1), "monitorwarr": (97, 0, 0, 0, 61, 0, 35),
    "vanek_nikolaev": (1, 0, 0, 0, 0, 0, 0), "kyiv_airdef": (791, 0, 0, 0, 17, 0, 1)}


def views_float(v):  # independent of parse_views: float arithmetic
    if v is None:
        return None
    m = re.fullmatch(r"([\d.]+)([KM]?)", v)
    return round(float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6}[m.group(2)])


def read_raw():
    """Bronze read again with plain json (not telegram.load): channel -> {post_id: first row}; a cut last line is skipped."""
    raw = {}
    for p in sorted(TG.glob("*.jsonl")):
        d = {}
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d.setdefault(r["post_id"], r)
        raw[p.stem] = d
    return raw


def check():
    ok = True

    def say(flag, msg):
        nonlocal ok
        ok = ok and flag
        print(("OK   " if flag else "FAIL ") + msg)

    con = connect()
    con.execute(f"CREATE VIEW tg_posts AS SELECT * FROM read_parquet('{TABLE}')")
    done = complete_channels()
    raw = read_raw()
    meta = pq.read_metadata(TABLE).metadata
    print("built_at", meta[b"built_at"].decode(), "| complete in the build:", meta[b"channels_complete"].decode())
    by = {r[0]: r for r in con.execute("""SELECT channel, count(*), count(DISTINCT post_id), min(published_at),
        max(published_at), min(post_id), max(post_id) FROM tg_posts GROUP BY channel ORDER BY channel""").fetchall()}

    # largest difference between neighbouring post_id of a channel (1 = no hole) and how many differences exceed 30
    idgap = {r[0]: r[1:] for r in con.execute("""SELECT channel, max(d), count(*) FILTER (WHERE d > 30) FROM (
        SELECT channel, post_id - lag(post_id) OVER (PARTITION BY channel ORDER BY post_id) AS d FROM tg_posts)
        GROUP BY channel""").fetchall()}

    print("\n1. rows per channel against the bronze files (unique post_id read again with plain json)")
    print(f"{'channel':22}{'rows':>8}{'bronze':>8}  {'first published_at':21}{'last published_at':21}{'min_id':>8}{'max_id':>8}"
          f"{'max_gap':>9}{'gaps>30':>9}  complete")
    for ch in sorted(ROLES):
        if ch not in by:
            print(f"{ch:22}{'':>8}{len(raw.get(ch, {})):>8}  no rows (no bronze file yet)" if ch not in raw else f"{ch:22} empty")
            continue
        _, n, nu, lo, hi, a, b = by[ch]
        print(f"{ch:22}{n:>8}{len(raw[ch]):>8}  {lo.strftime(TIME_FMT):21}{hi.strftime(TIME_FMT):21}{a:>8}{b:>8}"
              f"{str(idgap[ch][0]):>9}{idgap[ch][1]:>9}  {'yes' if ch in done else 'no'}")
        say(n == nu, f"{ch}: post_id unique in the table")
        say(n == len(raw[ch]) if ch in done else n <= len(raw[ch]),
            f"{ch}: rows {'=' if ch in done else '<='} unique post_id in bronze ({n} vs {len(raw[ch])})")
    total = con.execute("SELECT count(*), count(DISTINCT (channel, post_id)) FROM tg_posts").fetchone()
    say(total[0] == total[1] == sum(v[2] for v in by.values()), f"rows {total[0]} = sum over channels of unique post_id")
    over = [tuple(r) for r in con.execute("""SELECT channel, prev_id, post_id FROM (SELECT channel, post_id,
        lag(post_id) OVER (PARTITION BY channel ORDER BY post_id) AS prev_id FROM tg_posts)
        WHERE post_id - prev_id > 30 ORDER BY channel, post_id""").fetchall()]
    say(all(r in EXPLAINED_GAPS for r in over), f"id gaps over 30 (PARSING 2) are all explained: {over}")
    print(f"     bronze files now: {sum(len(d) for d in raw.values())} unique posts (more than the table only if a download went on)")

    print("\n   same values as bronze (published_at, text, edited, forwarded_from, url, views)")
    bad = 0
    for ch, pid, pub, text, edited, fwd, views, url, orig, avail in con.execute(
            "SELECT channel, post_id, published_at, text, edited, forwarded_from, views, url, is_original, available_at "
            "FROM tg_posts").fetchall():
        r = raw[ch][pid]
        bad += not (pub.strftime(TIME_FMT) == r["published_at"] and text == r["text"] and edited == r["edited"]
                    and fwd == r["forwarded_from"] and url == r["url"] and views == views_float(r["views"])
                    and orig == (r["forwarded_from"] is None) and avail == pub)
    say(bad == 0, f"{bad} rows differ from bronze")

    print("\n   control posts (PARSING 0.1 for complete channels, PARSING 2 for all)")
    for src, ctl in (("0.1", CONTROL_01), ("2", CONTROL_2)):
        for ch, pid, when in ctl:
            row = con.execute("SELECT published_at FROM tg_posts WHERE channel = ? AND post_id = ?", [ch, pid]).fetchone()
            if row:
                say(row[0].strftime(TIME_FMT) == when, f"{ch}/{pid} present at {row[0].strftime(TIME_FMT)} (PARSING {src})")
                continue
            lo_hi = by.get(ch)
            if ch in done:
                say(False, f"{ch}/{pid} missing in a complete channel (PARSING {src})")
            elif lo_hi and lo_hi[3].strftime(TIME_FMT) <= when <= lo_hi[4].strftime(TIME_FMT):
                say(False, f"{ch}/{pid} missing, although {when} is inside the downloaded range (PARSING {src})")
            else:
                print(f"PEND {ch}/{pid} {when}: channel incomplete, {'range not reached yet' if lo_hi else 'no bronze file yet'}"
                      f" (PARSING {src})")

    print("\n2. classes on the examples of PARSING 2")
    for ch, pid, cl, want_kyiv, want_ev in CLASS_EXAMPLES:
        row = con.execute("SELECT rx_classes, rx_kyiv_city, rx_evidence, text FROM tg_posts WHERE channel = ? AND post_id = ?",
                          [ch, pid]).fetchone()
        if not row:
            print(f"PEND {ch}/{pid}: not in the table (channel incomplete or no file yet)")
            continue
        flag = cl in row[0] and (want_kyiv is None or row[1] == want_kyiv) and (want_ev is None or row[2] == want_ev)
        say(flag, f"{ch}/{pid} classes {row[0]} kyiv_city {row[1]} evidence {row[2]} | {row[3][:50]!r}")
    c, k, e = classify("AerisRimor", "Пролунали вибухи.")  # text of AerisRimor/89451 (PARSING 2) through the function
    say("explosion" in c and k, f"classify('AerisRimor', 'Пролунали вибухи.') = {c}, {k}, {e}")

    print("\n3. signals on 2026-10-09 UTC: posts S1 S2 S3 S4 S5 KYIV (expected in brackets, counted on text without reply quote)")
    cnt = {}
    for ch, text, sg in con.execute(f"SELECT channel, text, rx_signals FROM tg_posts WHERE published_at >= TIMESTAMP '{DAY[0]}' "
                                    f"AND published_at < TIMESTAMP '{DAY[1]}'").fetchall():
        a = cnt.setdefault(ch, [0] * 7)
        a[0] += 1
        for i, s in enumerate(("S1", "S2", "S3", "S4", "S5")):
            a[i + 1] += s in sg
        a[6] += bool(KYIV.search(text))
    for ch, exp in EXPECT_DAY.items():
        if ch not in by:
            print(f"PEND {ch}: no bronze file yet")
            continue
        got = tuple(cnt.get(ch, [0] * 7))
        covered = by[ch][3].strftime("%Y-%m-%d %H:%M:%S") <= DAY[0] and (
            by[ch][4].strftime("%Y-%m-%d %H:%M:%S") >= DAY[1] or ch in done)  # a complete channel reaches its newest post
        say(got == exp and covered and ch in done, f"{ch:20} {'/'.join(map(str, got))} [{'/'.join(map(str, exp))}] | channel "
            f"{'complete' if ch in done else 'incomplete'}, day {'in the file' if covered else 'NOT in the file yet'}")

    print("\n4. views: 6.83K is 6830, 1.2M is 1200000, 55 is 55, null stays null; raw -> table")
    say([parse_views(v) for v in ("6.83K", "1.2M", "55", None)] == [6830, 1200000, 55, None], "parse_views on the four forms")
    for ch, pid in VIEW_EXAMPLES:
        v = raw[ch][pid]["views"]
        got = con.execute("SELECT views FROM tg_posts WHERE channel = ? AND post_id = ?", [ch, pid]).fetchone()[0]
        say(got == views_float(v), f"{ch}/{pid} {v!r} -> {got}")

    print("\n5. invariants and ASOF")
    say(con.execute("SELECT count(*) FROM tg_posts WHERE available_at <> published_at OR channel_role IS NULL "
                    "OR rx_classes IS NULL OR rx_signals IS NULL OR rx_kyiv_city IS NULL OR rx_evidence IS NULL").fetchone()[0] == 0,
        "available_at = published_at; channel_role, rx_classes, rx_signals, rx_kyiv_city, rx_evidence never NULL")
    say(con.execute("SELECT count(*) FROM tg_posts WHERE rx_evidence AND NOT rx_kyiv_city").fetchone()[0] == 0,
        "rx_evidence implies rx_kyiv_city")
    full = pq.read_table(TABLE, columns=["published_at", "available_at"])
    last = full.column("published_at").to_pylist()[-1]
    rnd = random.Random(20261010)
    t_lo = datetime.strptime(T0, TIME_FMT)
    hours = int((last - t_lo).total_seconds() // 3600)
    for t in sorted(t_lo + timedelta(hours=rnd.randrange(hours)) for _ in range(3)):
        got = con.execute(f"SELECT count(*), max(published_at) FROM ({ASOF['tg_posts'].format(t=f'TIMESTAMP {str(t)!r}')})").fetchone()
        want = pc.sum(pc.less(full.column("available_at"), pa.scalar(t, pa.timestamp("us")))).as_py()
        say(got[0] == want and got[1] < t, f"ASOF at {t.strftime(TIME_FMT)}: {got[0]} rows known, last {got[1]}")
    print("\nALL OK" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    check() if sys.argv[1:] == ["check"] else main()
