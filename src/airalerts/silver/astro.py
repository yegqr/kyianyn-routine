"""Silver astro_hourly: Kyiv sun altitude, share of civil darkness and Moon per UTC hour, and the astro features.

Doc: docs/data/silver/astro_hourly.md. Rebuild: .venv/bin/python -I -m airalerts.silver.astro
"""
import csv
import importlib.util
import os
from datetime import datetime, timedelta, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from ..paths import BRONZE, ROOT, SILVER

SRC = BRONZE / "astro" / "kyiv_astro_hourly.csv"
OUT = SILVER / "astro_hourly.parquet"
KYIV_ASTRO = ROOT / "scripts" / "bronze" / "kyiv_astro.py"
KNOWN_AT = datetime(2000, 1, 1)  # formulas, no network: known in advance (UTC)
DARK_DEG = -6.0                  # civil twilight: Sun centre below -6 degrees
ASOF = {"astro_hourly": "SELECT * FROM astro_hourly WHERE available_at < {t}"}


def _table(res):
    t = res.to_arrow_table() if hasattr(res, "to_arrow_table") else res.fetch_arrow_table()
    return t.read_all() if hasattr(t, "read_all") else t


def _kyiv_astro():
    spec = importlib.util.spec_from_file_location("kyiv_astro", KYIV_ASTRO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ka = _kyiv_astro()
    with open(SRC, newline="") as f:
        rows = list(csv.DictReader(f))
    hours, frac = [], []
    for r in rows:
        h = datetime.strptime(r["hour_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        dark = sum(ka.sun_alt(h + timedelta(minutes=m)) < DARK_DEG for m in range(60))  # minutes h+0..h+59
        hours.append(h.replace(tzinfo=None))
        frac.append(dark / 60)
    ts = pa.timestamp("us")
    tbl = pa.table({
        "hour_utc": pa.array(hours, ts),
        "sun_alt_deg": pa.array([float(r["sun_alt_deg"]) for r in rows], pa.float64()),
        "dark_civil_frac": pa.array(frac, pa.float64()),
        "moon_illum": pa.array([float(r["moon_illum"]) for r in rows], pa.float64()),
        "moon_phase": pa.array([float(r["moon_phase"]) for r in rows], pa.float64()),
        "available_at": pa.array([KNOWN_AT] * len(rows), ts),
    })
    SILVER.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_name(OUT.name + ".tmp")
    pq.write_table(tbl, tmp)
    os.replace(tmp, OUT)
    print(f"astro_hourly: {tbl.num_rows} rows {hours[0]}..{hours[-1]} -> {OUT}")


def features(con, t_table):
    """Per t_utc: dark_share_3h = mean dark_civil_frac over hours t, t+1h, t+2h; moon_illum at hour t.

    NULL if the table does not cover the hours. t_utc must be a full UTC hour.
    """
    sql = f"""
    WITH t AS (SELECT DISTINCT t_utc FROM {t_table}),
    tv AS (SELECT t.t_utc, k, t.t_utc + k * INTERVAL 1 HOUR AS h FROM t, range(3) r(k)),
    agg AS (
        SELECT tv.t_utc,
               max(a.dark_civil_frac) FILTER (WHERE tv.k = 0) AS d0,
               max(a.dark_civil_frac) FILTER (WHERE tv.k = 1) AS d1,
               max(a.dark_civil_frac) FILTER (WHERE tv.k = 2) AS d2
        FROM tv JOIN astro_hourly a ON a.hour_utc = tv.h AND a.available_at < tv.t_utc
        GROUP BY tv.t_utc
    )
    SELECT t.t_utc, (g.d0 + g.d1 + g.d2) / 3.0 AS dark_share_3h, m.moon_illum
    FROM t LEFT JOIN agg g ON g.t_utc = t.t_utc
           LEFT JOIN astro_hourly m ON m.hour_utc = t.t_utc AND m.available_at < t.t_utc
    ORDER BY t.t_utc"""
    return _table(con.execute(sql))


if __name__ == "__main__":
    main()
