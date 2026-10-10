"""Silver weather_runs: ECMWF IFS forecast runs for Kyiv, and the wx_* features for gold.

Doc: docs/data/silver/weather_runs.md. Rebuild: .venv/bin/python -I -m airalerts.silver.weather
"""
import os

from ..db import connect
from ..paths import BRONZE, SILVER

SRC = BRONZE / "weather" / "ecmwf_ifs_runs.csv"
OUT = SILVER / "weather_runs.parquet"
LAG_H = 8  # available_at = run_utc + 8 h: actual delay 6.4 h plus margin (PARSING 3)

CSV_COLUMNS = {
    "run_utc": "VARCHAR", "valid_utc": "VARCHAR", "lead_h": "INTEGER", "cloud_cover_pct": "DOUBLE",
    "precipitation_mm": "DOUBLE", "wind_speed_10m_kmh": "DOUBLE", "wind_gusts_10m_kmh": "DOUBLE",
    "wind_direction_10m_deg": "DOUBLE", "visibility_m": "DOUBLE", "available_at_utc": "VARCHAR",
    "fetched_at_utc": "VARCHAR",
}
ASOF = {"weather_runs": "SELECT * FROM weather_runs WHERE available_at < {t}"}


def _table(res):
    t = res.to_arrow_table() if hasattr(res, "to_arrow_table") else res.fetch_arrow_table()
    return t.read_all() if hasattr(t, "read_all") else t


def main():
    con = connect()
    SILVER.mkdir(parents=True, exist_ok=True)
    cols = ", ".join(f"'{k}': '{v}'" for k, v in CSV_COLUMNS.items())
    src = f"read_csv('{SRC}', header = true, columns = {{{cols}}})"
    tmp = OUT.with_name(OUT.name + ".tmp")
    con.execute(f"""
        COPY (
            WITH one AS (
                SELECT * FROM {src}
                QUALIFY row_number() OVER (PARTITION BY run_utc, valid_utc ORDER BY fetched_at_utc) = 1
            )
            SELECT strptime(run_utc, '%Y-%m-%dT%H:%M:%SZ') AS run_utc,
                   strptime(valid_utc, '%Y-%m-%dT%H:%M:%SZ') AS valid_utc,
                   lead_h, cloud_cover_pct, precipitation_mm, wind_speed_10m_kmh, wind_gusts_10m_kmh,
                   wind_direction_10m_deg, visibility_m,
                   strptime(run_utc, '%Y-%m-%dT%H:%M:%SZ') + INTERVAL {LAG_H} HOUR AS available_at
            FROM one
            ORDER BY 1, 2
        ) TO '{tmp}' (FORMAT PARQUET)""")
    os.replace(tmp, OUT)
    n_csv = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
    n, runs, r0, r1 = con.execute(
        f"SELECT count(*), count(DISTINCT run_utc), min(run_utc), max(run_utc) FROM read_parquet('{OUT}')").fetchone()
    print(f"weather_runs: {n} rows, {runs} runs {r0}..{r1}, duplicates dropped {n_csv - n} -> {OUT}")


def _by_hour(col):
    """Value of `col` for hour t+k as three columns col0, col1, col2 (fixed order: same float result every time)."""
    return ", ".join(f"max({col}) FILTER (WHERE k = {k}) AS {col}{k}" for k in range(3))


def features(con, t_table):
    """Per t_utc: forecast cloud, precipitation, wind, visibility over the hours t, t+1h, t+2h.

    Forecast = newest run with available_at < t; an empty value is taken from the next older run that has it
    (the newest non-empty value among runs known before t). NULL if any of the 3 hours has no value.
    """
    sql = f"""
    WITH t AS (SELECT DISTINCT t_utc FROM {t_table}),
    tv AS (SELECT t.t_utc, k, t.t_utc + k * INTERVAL 1 HOUR AS v FROM t, range(3) r(k)),
    hr AS (
        SELECT tv.t_utc, tv.k,
               arg_max(w.cloud_cover_pct, w.run_utc) FILTER (WHERE w.cloud_cover_pct IS NOT NULL) AS cloud,
               arg_max(w.precipitation_mm, w.run_utc) FILTER (WHERE w.precipitation_mm IS NOT NULL) AS precip,
               arg_max(w.wind_speed_10m_kmh, w.run_utc) FILTER (WHERE w.wind_speed_10m_kmh IS NOT NULL) AS wind,
               arg_max(w.visibility_m, w.run_utc) FILTER (WHERE w.visibility_m IS NOT NULL) AS vis
        FROM tv JOIN weather_runs w ON w.valid_utc = tv.v AND w.available_at < tv.t_utc
        GROUP BY tv.t_utc, tv.k
    ),
    agg AS (
        SELECT t_utc, {_by_hour('cloud')}, {_by_hour('precip')}, {_by_hour('wind')}, {_by_hour('vis')}
        FROM hr GROUP BY t_utc
    )
    SELECT t.t_utc,
           (a.cloud0 + a.cloud1 + a.cloud2) / 3.0 AS wx_cloud_mean_3h,
           (a.precip0 + a.precip1) + a.precip2 AS wx_precip_sum_3h,
           CASE WHEN a.wind0 IS NULL OR a.wind1 IS NULL OR a.wind2 IS NULL THEN NULL
                ELSE greatest(a.wind0, a.wind1, a.wind2) END AS wx_wind_max_3h,
           CASE WHEN a.vis0 IS NULL OR a.vis1 IS NULL OR a.vis2 IS NULL THEN NULL
                ELSE least(a.vis0, a.vis1, a.vis2) END AS wx_visibility_min_3h
    FROM t LEFT JOIN agg a ON a.t_utc = t.t_utc
    ORDER BY t.t_utc"""
    return _table(con.execute(sql))


if __name__ == "__main__":
    main()
