"""Project paths and period constants shared by all three levels (bronze, silver, gold).
DATA is ROOT/data, or the dir in the env var AIRALERTS_DATA (a relative path is taken from ROOT), so the live product runs
the same steps on its own copy: AIRALERTS_DATA=data/live .venv/bin/python -I -m airalerts.silver.alerts"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / os.environ["AIRALERTS_DATA"] if os.environ.get("AIRALERTS_DATA") else ROOT / "data"
BRONZE = DATA / "bronze"  # sources as they came, append-only
SILVER = DATA / "silver"  # one clean table per data class, Parquet
GOLD = DATA / "gold"      # one table for the model
DB = DATA / "airalerts.duckdb"  # views over silver and gold

T0 = "2026-04-30T21:00:00Z"          # 2026-05-01 00:00 Kyiv: first forecast hour
FETCH_FROM = "2026-04-16T21:00:00Z"  # T0 minus 14 days, so 14-day look-back windows are full at T0
