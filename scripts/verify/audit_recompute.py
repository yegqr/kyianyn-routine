"""Audit of gold kyiv_hourly (2026-10-11, docs/data/VERIFICATION.md): every column recomputed by plain Python loops, without the
project modules and their SQL, from the silver Parquet files (weather and astronomy from bronze), following the definitions in
docs/data/gold/kyiv_hourly.md. Unlike tests/test_gold_hourly.py it does not reuse features(), so a wrong window or a wrong
available_at in a module shows up as a mismatch.

Run from the project root: .venv/bin/python -I scripts/verify/audit_recompute.py   (writes data/verification/audit_recompute.txt)

Last, a planted leak: the same loops for alerts_started_3h and threat_prev_1h with data one hour later than allowed must differ
from gold, or the check is empty and the script fails.
"""
import csv
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
SIL, BRONZE = ROOT / "data" / "silver", ROOT / "data" / "bronze"
OUT = ROOT / "data" / "verification" / "audit_recompute.txt"
H, D = timedelta(hours=1), timedelta(days=1)
KYIV = ZoneInfo("Europe/Kyiv")
CAP = 336.0  # hours_since_* cap
DAYS_CAP = 14  # *_days_to_* cap


def rows(name, columns=None):
    return pq.read_table(SIL / f"{name}.parquet", columns=columns).to_pylist()


def utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") if s else None


def kyiv(t):
    return t.replace(tzinfo=timezone.utc).astimezone(KYIV)


def between(sorted_times, lo, hi):
    """Number of times in [lo, hi)."""
    return bisect_left(sorted_times, hi) - bisect_left(sorted_times, lo)


# ---------------------------------------------------------------- inputs
alerts = rows("kyiv_alerts", ["start_utc", "end_utc", "available_at"])
flags = {r["hour_utc"]: r for r in rows("kyiv_threat_hourly", ["hour_utc", "missile_strike", "missile_threat", "drone_threat",
                                                                "ballistic", "available_at"])}
label_end = utc(pq.read_metadata(SIL / "kyiv_threat_hourly.parquet").metadata[b"label_end"].decode())
events = rows("prep_signal_events", ["signal", "subtype", "available_at"])
s1 = sorted(e["available_at"] for e in events if e["signal"] == "S1" and e["subtype"] in ("takeoff", "relocation"))
s2_air = sorted(e["available_at"] for e in events if e["signal"] == "S2" and e["subtype"] == "airborne")
s2_clear = sorted(e["available_at"] for e in events if e["signal"] == "S2" and e["subtype"] == "all_clear")
s4 = sorted(e["available_at"] for e in events if e["signal"] == "S4" and e["subtype"] == "launch")
runs = defaultdict(dict)  # valid hour -> run -> (cloud, precipitation, wind, visibility), from the bronze CSV
with open(BRONZE / "weather" / "ecmwf_ifs_runs.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        val = tuple(float(r[k]) if r[k] != "" else None for k in ("cloud_cover_pct", "precipitation_mm", "wind_speed_10m_kmh", "visibility_m"))
        runs[utc(r["valid_utc"])].setdefault(utc(r["run_utc"]), val)
with open(BRONZE / "astro" / "kyiv_astro_daily.csv", encoding="utf-8") as f:
    civil_light = [(utc(r["civil_dawn_utc"]), utc(r["civil_dusk_utc"])) for r in csv.DictReader(f)]
with open(BRONZE / "astro" / "kyiv_astro_hourly.csv", encoding="utf-8") as f:
    moon = {utc(r["hour_utc"]): float(r["moon_illum"]) for r in csv.DictReader(f)}
calendar = rows("calendar_dates", ["date", "group", "symbolism", "high", "available_at"])
political = rows("political_events", ["event_id", "version_of", "revid", "class", "event_date", "end_date", "importance", "available_at"])
points = [p for p in rows("strike_points", ["country", "occupied", "region", "is_energy", "is_moscow", "available_at"])
          if p["country"] == "RU" and not p["occupied"]]
days = rows("strike_days", ["country", "drones_intercepted", "missiles_max", "drones_max", "available_at"])


# ---------------------------------------------------------------- columns
def alert_cols(t, late=timedelta(0)):
    known = [a for a in alerts if a["available_at"] < t + late]
    ends = [a["end_utc"] for a in known if a["end_utc"] is not None and a["end_utc"] < t]  # an end at or after t is not known yet
    active = [a for a in known if a["end_utc"] is None or a["end_utc"] >= t]
    minutes = 0.0
    for a in known:
        stop = a["end_utc"] if a["end_utc"] is not None and a["end_utc"] < t else t
        minutes += max(timedelta(0), stop - max(a["start_utc"], t - 24 * H)).total_seconds() / 60
    return {"alert_active": bool(active), "alert_active_min": (t - active[0]["start_utc"]).total_seconds() / 60 if active else 0.0,
            **{f"alerts_started_{n}h": sum(t - n * H <= a["start_utc"] < t + late for a in known) for n in (3, 6, 24)},
            "alert_minutes_24h": minutes, "alerts_7d": sum(t - 7 * D <= a["start_utc"] < t for a in known),
            "alerts_14d": sum(t - 14 * D <= a["start_utc"] < t for a in known),
            "hours_since_alert_end": 0.0 if active else (t - max(ends)).total_seconds() / 3600}


def threat_cols(t, late=timedelta(0)):
    def flag(k, col):  # the hour [t - k h, t - (k - 1) h), known when it has ended
        r = flags.get(t - k * H)
        return bool(r and r["available_at"] <= t + late and r[col])
    strike = [k for k in range(1, 337) if flag(k, "missile_strike")]
    return {"threat_prev_1h": flag(1 - late // H, "missile_threat"), "threat_hours_6h": sum(flag(k, "missile_threat") for k in range(1, 7)),
            "threat_hours_24h": sum(flag(k, "missile_threat") for k in range(1, 25)),
            **{f"ballistic_hours_{n}h": sum(flag(k, "ballistic") for k in range(1, n + 1)) for n in (3, 6, 24)},
            "drone_threat_prev_1h": flag(1, "drone_threat"), "strikes_7d": sum(k <= 168 for k in strike), "strikes_14d": len(strike),
            "hours_since_strike": float(strike[0] - 1) if strike else CAP}


def signal_cols(t):
    known = s1[:bisect_left(s1, t)]
    airborne = [a for a in s2_air if t - 3 * H <= a < t]
    return {"s1_takeoff_6h": between(s1, t - 6 * H, t), "s1_takeoff_24h": between(s1, t - 24 * H, t),
            "hours_since_s1": min(CAP, (t - known[-1]).total_seconds() / 3600) if known else CAP,
            "s2_mig31k_airborne": int(bool(airborne) and not any(max(airborne) < c < t for c in s2_clear)),
            "s4_drone_waves_6h": between(s4, t - 6 * H, t)}


def weather_cols(t):
    per_hour = []
    for k in range(3):  # the newest run known before t (run + 8 h < t) that has the value
        known = sorted((run, v) for run, v in runs.get(t + k * H, {}).items() if run + 8 * H < t)
        per_hour.append([next((v[i] for _, v in reversed(known) if v[i] is not None), None) for i in range(4)])
    c, p, w, v = zip(*per_hour)
    return {"wx_cloud_mean_3h": (c[0] + c[1] + c[2]) / 3.0, "wx_precip_sum_3h": (p[0] + p[1]) + p[2], "wx_wind_max_3h": max(w),
            "wx_visibility_min_3h": min(v)}


def astro_cols(t):
    lit = sum(max(timedelta(0), min(t + 3 * H, b) - max(t, a)).total_seconds() for a, b in civil_light)
    return {"dark_share_3h": 1 - lit / (3 * 3600), "moon_illum": moon[t]}


def calendar_cols(t):
    d = kyiv(t).date()
    known = [r for r in calendar if r["available_at"] < t]
    nxt = [(r["date"] - d).days for r in known if r["high"] and r["date"] >= d]
    return {"hol_rf_symb_today": max([r["symbolism"] for r in known if r["date"] == d and r["group"] == "RF"], default=0.0),
            "hol_ua_symb_today": max([r["symbolism"] for r in known if r["date"] == d and r["group"] == "UA"], default=0.0),
            "hol_high_tomorrow": any(r["high"] for r in known if r["date"] == d + D),
            "hol_days_to_next_high": min(DAYS_CAP, min(nxt, default=DAYS_CAP))}


def political_cols(t):
    d, latest = kyiv(t).date(), {}
    for r in political:  # the newest version of each event known before t
        if r["available_at"] < t:
            k = r["version_of"] or r["event_id"]
            if k not in latest or (r["available_at"], r["revid"] or -1) > (latest[k]["available_at"], latest[k]["revid"] or -1):
                latest[k] = r
    out = {}
    for c in ("kyiv", "russia"):
        ev = [r for r in latest.values() if r["class"] == c]
        out[f"{c}_imp_today"] = max([r["importance"] for r in ev if r["event_date"] <= d <= r["end_date"]], default=0)
        out[f"{c}_days_to_imp4"] = min(DAYS_CAP, min([max(0, (r["event_date"] - d).days) for r in ev
                                                      if r["importance"] >= 4 and r["end_date"] >= d], default=DAYS_CAP))
    return out


def rf_cols(t):
    p1 = [p for p in points if t - 24 * H <= p["available_at"] < t]
    p3 = [p for p in points if t - 72 * H <= p["available_at"] < t]
    d1 = [r for r in days if t - 24 * H <= r["available_at"] < t]
    missiles = [r["missiles_max"] for r in d1 if r["country"] == "UA" and r["missiles_max"] is not None]
    energy = [p["available_at"] for p in points if p["is_energy"] and p["available_at"] < t]
    return {"rf_points_1d": len(p1), "rf_points_3d": len(p3), "rf_regions_3d": len({p["region"] for p in p3}),
            "rf_energy_1d": sum(p["is_energy"] for p in p1), "rf_energy_3d": sum(p["is_energy"] for p in p3),
            "rf_moscow_3d": int(any(p["is_moscow"] for p in p3)),
            "rf_drones_intercepted_1d": sum(r["drones_intercepted"] or 0 for r in d1 if r["country"] == "RU"),
            "ua_missiles_launched_1d": sum(missiles) if missiles else None,
            "ua_drones_launched_1d": sum(r["drones_max"] or 0 for r in d1 if r["country"] == "UA"),
            "hours_since_rf_energy": min(CAP, (t - max(energy)).total_seconds() / 3600) if energy else CAP}


def label(t):
    if t + 3 * H > label_end:
        return None
    return any(flags[t + k * H]["missile_strike"] for k in range(3))


def expected(t):
    k = kyiv(t)
    return {"hour_kyiv": k.hour, "dow_kyiv": k.weekday(), **alert_cols(t), **threat_cols(t), **signal_cols(t), **weather_cols(t),
            **astro_cols(t), **calendar_cols(t), **political_cols(t), **rf_cols(t), "y_strike_3h": label(t)}


def same(c, a, b):
    if a is None or b is None:
        return a is None and b is None
    if c == "dark_share_3h":  # silver integrates the sun altitude, the check uses dawn and dusk times
        return abs(a - b) <= 0.02
    return abs(a - b) < 1e-9 if isinstance(b, float) else a == b


def main():
    gold = pq.read_table(ROOT / "data" / "gold" / "kyiv_hourly.parquet").to_pylist()
    cols = [c for c in gold[0] if c != "t_utc"]
    bad, lines = defaultdict(list), []
    for g in gold:
        e = expected(g["t_utc"])
        missing = set(cols) ^ set(e)
        if missing:
            sys.exit(f"columns not recomputed or not in gold: {sorted(missing)}")
        for c in cols:
            if not same(c, g[c], e[c]):
                bad[c].append((g["t_utc"], g[c], e[c]))
    lines.append(f"gold {len(gold)} rows {gold[0]['t_utc']:%Y-%m-%dT%H}Z..{gold[-1]['t_utc']:%Y-%m-%dT%H}Z, {len(cols)} columns "
                 f"recomputed without the project modules; mismatches per column (3 examples: t, gold, recomputed):")
    lines += [f"  {c:26} {len(bad[c])}" + (f"  {bad[c][:3]}" if bad[c] else "") for c in cols]
    planted = {"alerts_started_3h, alerts known 1 h late": sum(alert_cols(g["t_utc"], H)["alerts_started_3h"] != g["alerts_started_3h"] for g in gold),
               "threat_prev_1h, hour flags known 1 h early": sum(threat_cols(g["t_utc"], H)["threat_prev_1h"] != g["threat_prev_1h"] for g in gold)}
    lines.append("planted leak, rows that differ from gold (must be > 0): " + ", ".join(f"{k}: {v}" for k, v in planted.items()))
    ok = not any(bad.values()) and all(planted.values())
    lines.append("AUDIT RECOMPUTE " + ("PASS" if ok else "FAIL"))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
