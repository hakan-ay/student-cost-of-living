"""Fetches monthly HICP data for Italy and Turkey from Eurostat (dataset prc_hicp_minr, ECOICOP ver. 2).

Why prc_hicp_minr and not prc_hicp_manr / prc_hicp_midx: with the January 2026 release Eurostat moved the HICP to
ECOICOP ver. 2 (COICOP 2018). The old datasets are frozen at December 2025; prc_hicp_minr carries the full history
(back to 1996) on the new classification, with both indices and rates of change in one dataset.

Writes data/raw/eurostat_hicp.parquet. Later runs re-download the last 13 months so revisions are picked up.

Usage:
    uv run python src/fetch_eurostat.py
    uv run python src/fetch_eurostat.py --full
"""

import argparse
from datetime import date

import pandas as pd

from raw_store import get_csv, read_existing, upsert_parquet

DATASET = "prc_hicp_minr"
URL = f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{DATASET}"
NAME = "eurostat_hicp"
REFRESH_MONTHS = 13

UNITS = ["I25", "RCH_A"]  # index 2025=100, annual rate of change (%)
GEOS = ["IT", "TR"]
# All items plus the categories of the student reference basket (see dbt/seeds/basket_components.csv).
COICOP = ["TOTAL", "CP01", "CP041", "CP0732"]


def fetch(start_month: str) -> pd.DataFrame:
    key = f"M.{'+'.join(UNITS)}.{'+'.join(COICOP)}.{'+'.join(GEOS)}"
    df = get_csv(f"{URL}/{key}", params={"format": "SDMX-CSV", "startPeriod": start_month})
    if df.empty:
        return df
    return df.rename(columns={"coicop18": "coicop", "TIME_PERIOD": "period", "OBS_VALUE": "obs_value",
                              "OBS_FLAG": "obs_flag", "LAST UPDATE": "last_update"}).assign(dataset=DATASET)[
        ["dataset", "unit", "coicop", "geo", "period", "obs_value", "obs_flag", "last_update"]]


def shift_month(month: str, months: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2005-01", help="first month for a full download, YYYY-MM")
    parser.add_argument("--full", action="store_true", help="ignore stored data and download everything again")
    args = parser.parse_args()

    existing = read_existing(NAME)
    if args.full or existing.empty:
        start = args.since
    else:
        start = shift_month(existing["period"].max(), -REFRESH_MONTHS)

    new = fetch(start)
    if new.empty:
        print(f"eurostat: no observations since {start}")
        return
    merged = upsert_parquet(NAME, new, keys=["dataset", "unit", "coicop", "geo", "period"])
    print(f"eurostat: fetched {len(new)} rows from {start}, stored {len(merged)} "
          f"(latest month {merged['period'].max()}, run {date.today()})")


if __name__ == "__main__":
    main()
