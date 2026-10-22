"""Exports the dbt marts from data/warehouse.duckdb to data/marts/<name>.parquet.

The warehouse is not committed; these small files are, so the dashboard and the weekly brief (W4, W5) can read
the latest marts straight from the repository.

Usage (after `dbt build`):
    uv run python src/export_marts.py
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
OUT_DIR = ROOT / "data" / "marts"
MARTS = ["fx_daily", "cpi_monthly", "student_budget_monthly", "try_purchasing_power"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    for name in MARTS:
        path = OUT_DIR / f"{name}.parquet"
        con.execute(f"copy (select * from marts.{name}) to '{path}' (format parquet, compression zstd)")
        rows = con.execute(f"select count(*) from marts.{name}").fetchone()[0]
        print(f"{name}: {rows} rows -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
