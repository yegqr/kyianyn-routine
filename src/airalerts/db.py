"""DuckDB connection inside the session limits (5 CPUs, 10 GB RAM for everything, see docs/PLAN.md)."""
import duckdb

from .paths import DB, SILVER, GOLD


def connect(path=":memory:", threads=2, memory_limit="2GB"):
    con = duckdb.connect(str(path))
    con.execute(f"SET threads = {int(threads)}")
    con.execute(f"SET memory_limit = '{memory_limit}'")
    con.execute("SET TimeZone = 'UTC'")
    return con


def register_layers(con):
    """A view per Parquet file: data/silver/<name>.parquet becomes view <name>, same for gold."""
    for layer in (SILVER, GOLD):
        for p in sorted(layer.glob("*.parquet")):
            con.execute(f"CREATE OR REPLACE VIEW {p.stem} AS SELECT * FROM read_parquet('{p}')")
    return con


if __name__ == "__main__":  # python -m airalerts.db: (re)build data/airalerts.duckdb with views over all layers
    con = register_layers(connect(DB))
    print(con.execute("SELECT table_name FROM information_schema.tables ORDER BY 1").fetchall())
