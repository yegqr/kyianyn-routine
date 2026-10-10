# kyiv_astro.py: python3 -I kyiv_astro.py day 2026-10-10  |  python3 -I kyiv_astro.py build data/bronze/astro [--from YYYY-MM-DD] [--to YYYY-MM-DD]
import csv, math, os, sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LAT, LON = 50.4501, 30.5234
UTC, KYIV = timezone.utc, ZoneInfo("Europe/Kyiv")
LEVELS = {"sun": -0.833, "civil": -6.0, "nautical": -12.0, "astro": -18.0}
NAMES = {"sun": ("sunrise", "sunset"), "civil": ("civil_dawn", "civil_dusk"),
         "nautical": ("nautical_dawn", "nautical_dusk"), "astro": ("astro_dawn", "astro_dusk")}


def sun_alt(t):
    """Geometric altitude of the Sun centre, degrees (NOAA solar equations, Meeus)."""
    t = t.astimezone(UTC)
    T = (t.timestamp() / 86400.0 + 2440587.5 - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360.0
    M = math.radians(357.52911 + T * (35999.05029 - 0.0001537 * T))
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    C = (math.sin(M) * (1.914602 - T * (0.004817 + 0.000014 * T))
         + math.sin(2 * M) * (0.019993 - 0.000101 * T) + math.sin(3 * M) * 0.000289)
    om = math.radians(125.04 - 1934.136 * T)
    lam = math.radians(L0 + C - 0.00569 - 0.00478 * math.sin(om))
    eps = math.radians(23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - 0.001813 * T))) / 60) / 60
                       + 0.00256 * math.cos(om))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    y, L0r = math.tan(eps / 2) ** 2, math.radians(L0)
    eqt = 4 * math.degrees(y * math.sin(2 * L0r) - 2 * e * math.sin(M)
                           + 4 * e * y * math.sin(M) * math.cos(2 * L0r)
                           - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * M))
    mins = t.hour * 60 + t.minute + t.second / 60 + t.microsecond / 6e7
    ha = math.radians(((mins + eqt + 4 * LON) % 1440) / 4 - 180)
    la = math.radians(LAT)
    s = math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)
    return math.degrees(math.asin(max(-1.0, min(1.0, s))))


def moon(t):
    """(illuminated fraction 0..1, phase 0..1: 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter)."""
    T = (t.astimezone(UTC).timestamp() / 86400.0 + 2440587.5 - 2451545.0) / 36525.0
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T ** 2 + T ** 3 / 545868 - T ** 4 / 113065000
    M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T ** 2 + T ** 3 / 24490000
    Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T ** 2 + T ** 3 / 69699 - T ** 4 / 14712000
    r = math.radians
    i = (180 - D - 6.289 * math.sin(r(Mp)) + 2.100 * math.sin(r(M)) - 1.274 * math.sin(r(2 * D - Mp))
         - 0.658 * math.sin(r(2 * D)) - 0.214 * math.sin(r(2 * Mp)) - 0.110 * math.sin(r(D)))
    return (1 + math.cos(r(i))) / 2, ((180 - i) % 360) / 360


def crossings(d, level):
    """(up, down): UTC times when the Sun centre crosses `level` on Kyiv local date d; None if it does not."""
    a = datetime(d.year, d.month, d.day, tzinfo=KYIV).astimezone(UTC)
    nd = d + timedelta(days=1)
    b = datetime(nd.year, nd.month, nd.day, tzinfo=KYIV).astimezone(UTC)
    up = down = None
    t0, f0 = a, sun_alt(a) - level
    while t0 < b:
        t1 = min(t0 + timedelta(minutes=10), b)
        f1 = sun_alt(t1) - level
        if (f0 < 0) != (f1 < 0):
            lo, hi, flo = t0, t1, f0
            while (hi - lo).total_seconds() > 0.5:
                mid = lo + (hi - lo) / 2
                fm = sun_alt(mid) - level
                if (fm < 0) == (flo < 0):
                    lo, flo = mid, fm
                else:
                    hi = mid
            tc = (lo + (hi - lo) / 2).replace(microsecond=0)
            if f0 < 0:
                up = up or tc
            else:
                down = tc
        t0, f0 = t1, f1
    return up, down


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else ""


def build(out_dir, d0=date(2026, 4, 23), d1=date(2026, 10, 31)):
    days = [d0 + timedelta(days=k) for k in range((d1 - d0).days + 2)]
    ev = {d: {lvl: crossings(d, x) for lvl, x in LEVELS.items()} for d in days}
    daily = []
    for d in days[:-1]:
        e, n, nd = ev[d], ev[d + timedelta(days=1)], d + timedelta(days=1)
        row = {"date_kyiv": d.isoformat()}
        for lvl, (a, b) in NAMES.items():
            row[a + "_utc"], row[b + "_utc"] = iso(e[lvl][0]), iso(e[lvl][1])
        row["day_length_h"] = round((e["sun"][1] - e["sun"][0]).total_seconds() / 3600, 3)
        for lvl in ("civil", "nautical"):
            row[f"night_{lvl}_h"] = round((n[lvl][0] - e[lvl][1]).total_seconds() / 3600, 3)
        il, ph = moon(datetime(nd.year, nd.month, nd.day, tzinfo=KYIV))
        row["moon_illum_midnight"], row["moon_phase_midnight"] = round(il, 4), round(ph, 4)
        daily.append(row)
    hourly, t = [], datetime(d0.year, d0.month, d0.day, tzinfo=UTC)
    while t <= datetime(d1.year, d1.month, d1.day, 23, tzinfo=UTC):
        alt, (il, ph) = sun_alt(t), moon(t)
        hourly.append({"hour_utc": iso(t), "sun_alt_deg": round(alt, 2), "dark_civil": int(alt < -6),
                       "dark_nautical": int(alt < -12), "moon_illum": round(il, 4), "moon_phase": round(ph, 4)})
        t += timedelta(hours=1)
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in (("kyiv_astro_daily.csv", daily), ("kyiv_astro_hourly.csv", hourly)):
        with open(os.path.join(out_dir, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(len(daily), "daily rows,", len(hourly), "hourly rows")


if __name__ == "__main__":
    if sys.argv[1] == "day":
        d = date.fromisoformat(sys.argv[2])
        for lvl, x in LEVELS.items():
            print(lvl, *map(iso, crossings(d, x)))
        nd = d + timedelta(days=1)
        print("moon at next Kyiv midnight: illum %.4f phase %.4f" % moon(datetime(nd.year, nd.month, nd.day, tzinfo=KYIV)))
    else:
        opt = dict(zip(sys.argv[3::2], sys.argv[4::2]))
        if len(sys.argv) % 2 == 0 or not set(opt) <= {"--from", "--to"}:
            sys.exit("usage: kyiv_astro.py build <out_dir> [--from YYYY-MM-DD] [--to YYYY-MM-DD]")
        kw = {k: date.fromisoformat(opt[o]) for k, o in (("d0", "--from"), ("d1", "--to")) if o in opt}
        build(sys.argv[2], **kw)
