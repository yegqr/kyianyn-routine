"""External check of the missile strike label (silver kyiv_threat_hourly) against the blind references in data/verification.

Run from the project root: .venv/bin/python -I scripts/verify/label_check.py   (writes data/verification/label_compare.txt)

1. nights: every Kyiv date with a label strike hour or a reference verdict, label hours (Kyiv time) next to the verdicts of the
   official summaries (V1, label_reference_official.csv) and of the news (V2, label_reference_news.csv): M missile_city,
   ? unclear_type, d drone_only, o missile_oblast_only, . not listed. V1 counts an attack after 18:00 Kyiv to the next date.
2. launches: label strike days on which dronestrikemap (silver strike_days, country UA) has missiles launched at Ukraine.
3. regex-only hours: hours where rule A or B of PARSING 2 fires and the label does not, split by attack drones in the hour
   (blind reading, signals_blind_hours.csv), by distance to a label strike hour and by the reference verdict of the day.
4. thresholds: strike hours of the current rule and of looser variants (no Jev call: kyiv_threat_posts holds the probabilities).
"""
import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from airalerts.silver import threat_hourly as th  # noqa: E402

V = ROOT / "data" / "verification"
SIL = ROOT / "data" / "silver"
KYIV = timedelta(hours=3)  # the whole period is summer time (UTC+3)
T0 = datetime(2026, 4, 30, 21)
AB = {"missile_city": "M", "unclear_type": "?", "drone_only": "d", "missile_oblast_only": "o"}


def ref(name):
    return {r["date_kyiv"]: r["verdict"] for r in csv.DictReader(open(V / name, encoding="utf-8"))}


def main():
    con = duckdb.connect()
    A, B = ref("label_reference_official.csv"), ref("label_reference_news.csv")
    hourly = con.execute(f"SELECT hour_utc, missile_strike, rx_rule_a OR rx_rule_b, corrected FROM read_parquet('{SIL}/kyiv_threat_hourly.parquet') "
                         f"WHERE hour_utc >= TIMESTAMP '{T0}' ORDER BY 1").fetchall()
    strike = [h for h, s, _, _ in hourly if s]
    lab = defaultdict(list)
    for h in strike:
        lab[str((h + KYIV).date())].append(f"{(h + KYIV).hour:02d}")
    L = ["1. NIGHTS: date | label hours (Kyiv) | V1 | V2", f"label strike hours {len(strike)}, Kyiv dates {len(lab)}; "
         f"corrected hours {[f'{h:%Y-%m-%dT%H}' for h, _, _, c in hourly if c]}"]
    days = sorted(set(lab) | {d for d, v in A.items() if v != "drone_only"} | {d for d, v in B.items() if v != "drone_only"})
    for d in days:
        L.append(f"{d} | {','.join(lab.get(d, [])) or '-'} | {AB.get(A.get(d), '.')} | {AB.get(B.get(d), '.')}")
    conf = [d for d in lab if "missile_city" in (A.get(d), B.get(d), A.get(str((datetime.fromisoformat(d) + timedelta(days=1)).date())))]
    L.append(f"label dates confirmed as missile_city by V1 or V2 (V1 also on the next date): {len(conf)} of {len(lab)}; not confirmed: "
             f"{sorted(set(lab) - set(conf))}")
    miss = [d for d in days if d not in lab and ("missile_city" in (A.get(d), B.get(d)))]
    L.append(f"dates that V1 or V2 call missile_city and the label does not: {miss}")

    ua = dict(con.execute(f"SELECT CAST(date AS VARCHAR), missiles_max FROM read_parquet('{SIL}/strike_days.parquet') WHERE country = 'UA'").fetchall())
    no = [d for d in lab if not ua.get(d)]
    L += ["2. LAUNCHES", f"label strike dates with missiles launched at Ukraine that UTC day (dronestrikemap): {len(lab) - len(no)} of {len(lab)}; without: {no}"]

    blind = {r["hour_utc"]: r["s4"] for r in csv.DictReader(open(V / "signals_blind_hours.csv"))}
    c = Counter()
    for h, s, rx, _ in hourly:
        if rx and not s:
            d = str((h + KYIV).date())
            near = any(abs((h - x).total_seconds()) <= 3 * 3600 for x in strike)
            day = "M" if "missile_city" in (A.get(d), B.get(d)) else ("?" if "unclear_type" in (A.get(d), B.get(d)) else "-")
            c[(blind.get(f"{h:%Y-%m-%dT%H}") == "attack", near, day)] += 1
    L += ["3. REGEX-ONLY HOURS (rule A or B, no label): attack drones in the hour | within 3 h of a label strike hour | reference day: hours",
          f"total {sum(c.values())}"] + [f"  {k[0]} | {k[1]} | {k[2]}: {v}" for k, v in sorted(c.items(), key=lambda x: -x[1])]

    rows = con.execute(f"""SELECT k.channel, k.published_at, k.hour_utc, k.p_strike, k.p_threat, t.forwarded_from IS NULL
        FROM read_parquet('{SIL}/kyiv_threat_posts.parquet') k JOIN read_parquet('{SIL}/tg_posts.parquet') t USING (channel, post_id)
        WHERE k.hour_utc >= TIMESTAMP '{T0 - timedelta(hours=1)}'""").fetchall()
    by = defaultdict(list)
    for ch, pub, h, ps, pt, orig in rows:
        by[h].append({"channel": ch, "published_at": pub, "p_strike": ps, "p_threat": pt, "is_original": orig})
    rule = {h for h in by if h >= T0 and th.strike_flag(by[h], by.get(h - th.HOUR, []), **th.RULE["strike"])}
    L += ["4. THRESHOLDS (before CORRECTIONS)", f"current rule {th.RULE['strike']}: {len(rule)} hours"]
    for name, kw in (("one=0.6", dict(one=0.6)), ("one=0.5", dict(one=0.5)), ("one=0.7 or official>=0.5", dict(one=0.7, official=0.5))):
        alt = {h for h in by if h >= T0 and th.strike_flag(by[h], by.get(h - th.HOUR, []), fresh=True, originals=True, **kw)}
        L.append(f"{name}: {len(alt)} hours, added {sorted(f'{h:%Y-%m-%dT%H}' for h in alt - rule)}, removed {sorted(f'{h:%Y-%m-%dT%H}' for h in rule - alt)}")
    (V / "label_compare.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-12:]))


if __name__ == "__main__":
    main()
