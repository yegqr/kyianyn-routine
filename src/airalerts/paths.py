"""Project paths and period constants shared by all three levels (bronze, silver, gold)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
BRONZE = DATA / "bronze"  # sources as they came, append-only
SILVER = DATA / "silver"  # one clean table per data class, Parquet
GOLD = DATA / "gold"      # one table for the model
DB = DATA / "airalerts.duckdb"  # views over silver and gold

T0 = "2026-04-30T21:00:00Z"          # 2026-05-01 00:00 Kyiv: first forecast hour
FETCH_FROM = "2026-04-16T21:00:00Z"  # T0 minus 14 days, so 14-day look-back windows are full at T0
KYIV_TZ = "Europe/Kyiv"              # UTC+3 until 2026-10-25, then UTC+2
