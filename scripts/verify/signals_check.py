"""Blind check of silver prep_signal_events (S1 strategic aviation, S2 MiG-31K, S4 attack drones), hour by hour.

The reading itself is done by agents (Claude Code Workflow tool, scripts in scripts/verify/workflows/); this script cuts the
input, turns the agent answers into CSV and compares. Run from the project root with .venv/bin/python -I.

  batches DIR                         every post of the 6 signal channels, 2026-04-29T09Z..2026-10-10T17Z, cut into files of
                                      whole UTC hours (DIR/bNNNN.txt, DIR/index.json); a file never crosses 09:00Z (12:00 Kyiv),
                                      so a night stays in one file, and holds at most 45000 characters
  export-blind JOURNAL                answers of signals_blind_read.js (its journal.jsonl) -> data/verification/signals_blind_hours.csv
  compare DIR                         silver vs the blind reading per hour and signal; summary and the disagreeing hours
                                      -> data/verification/signals_compare.txt, DIR/cmp/*.tsv
  judge-inputs DIR                    the disagreeing hours with their posts, no verdicts shown -> DIR/judge/gN.txt, items.json
  export-judge DIR JOURNAL            answers of signals_judge.js -> data/verification/signals_judge.csv and the score per signal
"""
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "verification"
CHANNELS = ["war_monitor", "kpszsu", "AerisRimor", "StrategicaviationT", "monitorwarr", "kyiv_airdef"]  # S4 without vanek_nikolaev
H0, H1 = datetime(2026, 4, 29, 9), datetime(2026, 10, 10, 17)  # [H0, H1): T0 minus 36 h (24 h windows full at T0) to the gold cutoff
MAX_CHARS = 45000
KEYS = {"s1": "S1 strategic aviation", "s2a": "S2 MiG-31K airborne", "s2c": "S2 MiG-31K all clear", "s4": "S4 attack drones"}
QUESTIONS = {
    "s1": "Did a post in this hour report that Russian strategic or long-range bombers (Tu-95MS, Tu-160, Tu-22M3) took off, are in the air, "
          "are launching missiles, or are relocating between airfields NOW or within the last hour? A summary of earlier activity, a forecast, "
          "satellite imagery or analysis is NO.",
    "s2a": "Did a post in this hour report that a MiG-31K took off or is in the air now?",
    "s2c": "Did a post in this hour report that the MiG-31K landed or give an all clear for the MiG-31K?",
    "s4": "Did a post in this hour report attack drones (Shahed, Geran, Gerbera, 'мопеди', jet drones, 'ударні БпЛА') launched or flying over "
          "or toward Ukraine now? A summary of last night alone is NO; reconnaissance drones only is NO."}


def batches(d):
    d = Path(d)
    con = duckdb.connect()
    rows = con.execute(f"""SELECT channel, post_id, published_at, text, forwarded_from FROM read_parquet('{ROOT}/data/silver/tg_posts.parquet')
        WHERE channel IN ({','.join(repr(c) for c in CHANNELS)}) AND published_at >= TIMESTAMP '{H0}' AND published_at < TIMESTAMP '{H1}'
        ORDER BY published_at, channel, post_id""").fetchall()
    by_hour = {}
    for ch, pid, ts, text, fwd in rows:
        t = (text or "").replace("\n", " / ").strip()
        t = t[:1500] + " [...]" if len(t) > 1500 else t
        by_hour.setdefault(ts.replace(minute=0, second=0, microsecond=0), []).append(
            f"[{ts:%Y-%m-%d %H:%M}Z] {ch}/{pid}{f' (repost of {fwd})' if fwd else ''}: {t}")
    groups, cur, size, day = [], [], 0, None
    for h in sorted(by_hour):
        n = sum(len(x) + 1 for x in by_hour[h])
        if cur and ((h - timedelta(hours=9)).date() != day or size + n > MAX_CHARS):
            groups.append(cur)
            cur, size = [], 0
        cur.append(h)
        size += n
        day = (h - timedelta(hours=9)).date()
    groups.append(cur)
    d.mkdir(parents=True, exist_ok=True)
    index = []
    for i, hs in enumerate(groups):
        lines = []
        for h in hs:
            lines += [f"=== HOUR {h:%Y-%m-%dT%H}:00Z ({len(by_hour[h])} posts)"] + by_hour[h]
        (d / f"b{i:04d}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        index.append({"batch": f"b{i:04d}", "first_hour": f"{hs[0]:%Y-%m-%dT%H}", "last_hour": f"{hs[-1]:%Y-%m-%dT%H}",
                      "n_posts": sum(len(by_hour[h]) for h in hs)})
    (d / "index.json").write_text(json.dumps(index))
    print(f"posts {len(rows)}, hours with posts {len(by_hour)}, batches {len(index)} in {d}")


def results(journal):
    for line in Path(journal).read_text().splitlines():
        o = json.loads(line)
        if o.get("type") == "result" and isinstance(o.get("result"), dict):
            yield o["result"]


def export_blind(journal):
    n, rows = 0, []
    for r in results(journal):
        n += 1
        for h in r.get("hours", []):
            rows.append([r["batch"], h["hour"][:13], h.get("s1"), " ".join(h.get("s1_refs") or []), int(bool(h.get("s2_airborne"))),
                         int(bool(h.get("s2_all_clear"))), " ".join(h.get("s2_refs") or []), h.get("s4"), h.get("s4_ref") or ""])
    rows.sort(key=lambda x: x[1])
    with open(OUT / "signals_blind_hours.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["batch", "hour_utc", "s1", "s1_refs", "s2_airborne", "s2_all_clear", "s2_refs", "s4", "s4_ref"])
        w.writerows(rows)
    print(f"batches {n}, hours with any mark {len(rows)} -> {OUT / 'signals_blind_hours.csv'}")


def blind_marks():
    return {datetime.strptime(r["hour_utc"], "%Y-%m-%dT%H"): r for r in csv.DictReader(open(OUT / "signals_blind_hours.csv"))}


def compare(d):
    d = Path(d)
    index = json.loads((d / "index.json").read_text())
    covered = set()
    for b in index:
        a, z = datetime.strptime(b["first_hour"], "%Y-%m-%dT%H"), datetime.strptime(b["last_hour"], "%Y-%m-%dT%H")
        while a <= z:
            covered.add(a)
            a += timedelta(hours=1)
    marks = blind_marks()
    ev = duckdb.connect().execute(f"""SELECT date_trunc('hour', first_post_at), signal, subtype
        FROM read_parquet('{ROOT}/data/silver/prep_signal_events.parquet')""").fetchall()
    sil = {}
    for h, sig, sub in ev:
        sil.setdefault(h, set()).add((sig, sub))
    test = {"s1": lambda e: any(s == "S1" for s, _ in e), "s2a": lambda e: ("S2", "airborne") in e,
            "s2c": lambda e: ("S2", "all_clear") in e, "s4": lambda e: any(s == "S4" for s, _ in e)}
    blind = {"s1": lambda m: m["s1"] == "live", "s2a": lambda m: m["s2_airborne"] == "1", "s2c": lambda m: m["s2_all_clear"] == "1",
             "s4": lambda m: m["s4"] == "attack"}
    hs = sorted(covered)
    (d / "cmp").mkdir(exist_ok=True)
    lines = [f"hours covered {len(hs)} ({hs[0]:%Y-%m-%dT%H}Z..{hs[-1]:%Y-%m-%dT%H}Z)"]
    for k, name in KEYS.items():
        c = Counter((test[k](sil.get(h, set())), bool(marks.get(h)) and blind[k](marks[h])) for h in hs)
        lines.append(f"{name}: both {c[(True, True)]}, silver only {c[(True, False)]}, blind only {c[(False, True)]}, neither {c[(False, False)]}")
        for side, want in (("silver_only", (True, False)), ("blind_only", (False, True))):
            (d / "cmp" / f"{k}_{side}.tsv").write_text("".join(
                f"{h:%Y-%m-%dT%H}\n" for h in hs if (test[k](sil.get(h, set())), bool(marks.get(h)) and blind[k](marks[h])) == want))
    lines.append(f"blind S1 recap-only hours {sum(1 for h in hs if marks.get(h, {}).get('s1') == 'recap')}; "
                 f"blind S4 other_drone hours {sum(1 for h in hs if marks.get(h, {}).get('s4') == 'other_drone')}")
    (OUT / "signals_compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def judge_inputs(d):
    d = Path(d)
    hours = {}
    for f in sorted(d.glob("b*.txt")):
        cur = None
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"=== HOUR (\d{4}-\d{2}-\d{2}T\d{2}):00Z", line)
            if m:
                cur = m.group(1)
                hours[cur] = []
            elif cur:
                hours[cur].append(line)
    items = [{"key": k, "hour": h, "side": side} for k in KEYS for side in ("silver_only", "blind_only")
             for h in (d / "cmp" / f"{k}_{side}.tsv").read_text().split()]
    items.sort(key=lambda x: (x["hour"], x["key"]))
    (d / "judge").mkdir(exist_ok=True)
    groups = [items[i:i + 19] for i in range(0, len(items), 19)]
    for g, its in enumerate(groups):
        out = []
        for n, it in enumerate(its):
            it["id"] = f"j{g}_{n}"
            out += [f"##### ITEM {it['id']} | hour {it['hour']}:00Z UTC | QUESTION: {QUESTIONS[it['key']]}"] + hours.get(it["hour"], ["(no posts)"]) + [""]
        (d / "judge" / f"g{g}.txt").write_text("\n".join(out), encoding="utf-8")
    (d / "judge" / "items.json").write_text(json.dumps([i for g in groups for i in g], ensure_ascii=False))
    print(f"{len(items)} items in {len(groups)} files in {d / 'judge'}")


def export_judge(d, journal):
    items = {i["id"]: i for i in json.loads((Path(d) / "judge" / "items.json").read_text())}
    ans = {a["id"]: a for r in results(journal) for a in r["items"]}
    rows, score = [], Counter()
    for iid, it in sorted(items.items(), key=lambda x: (x[1]["hour"], x[1]["key"])):
        a = ans.get(iid, {})
        yes = a.get("answer") == "yes"
        right = "unclear" if a.get("answer") in (None, "unclear") else (
            "silver" if (yes and it["side"] == "silver_only") or (not yes and it["side"] == "blind_only") else "blind")
        score[(it["key"], it["side"], right)] += 1
        reason = a.get("reason", "").replace("\u2014", "-").replace("\u00b7", ",")  # characters banned in this repo
        rows.append([it["hour"], it["key"], it["side"], a.get("answer", "missing"), right, " ".join(a.get("refs") or []), reason])
    with open(OUT / "signals_judge.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hour_utc", "signal", "disagreement", "judge_answer", "judge_agrees_with", "refs", "reason"])
        w.writerows(rows)
    for k in sorted(score):
        print(f"{KEYS[k[0]]}, {k[1]}: judge agrees with {k[2]}: {score[k]}")
    print(f"items {len(items)}, answered {len(ans)} -> {OUT / 'signals_judge.csv'}")


if __name__ == "__main__":
    cmd, args = sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2:]
    fn = {"batches": batches, "export-blind": export_blind, "compare": compare, "judge-inputs": judge_inputs, "export-judge": export_judge}.get(cmd)
    if not fn:
        sys.exit(__doc__)
    fn(*args)
