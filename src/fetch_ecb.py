"""Fetches the daily ECB euro reference rate for the Turkish lira (series EXR.D.TRY.EUR.SP00.A).

Writes data/raw/ecb_exr_try_eur.parquet. The first run downloads the full history from --since; later runs only
request the last few days before the newest stored date (the ECB can publish a correction a day late).

Usage:
    uv run python src/fetch_ecb.py
    uv run python src/fetch_ecb.py --since 2005-01-01 --full
"""

import argparse
from datetime import date, timedelta

import pandas as pd

from raw_store import get_csv, read_existing, upsert_parquet

SERIES = "EXR/D.TRY.EUR.SP00.A"
URL = f"https://data-api.ecb.europa.eu/service/data/{SERIES}"
NAME = "ecb_exr_try_eur"
REFRESH_DAYS = 7


def fetch(start: date) -> pd.DataFrame:
    df = get_csv(URL, params={"format": "csvdata", "startPeriod": start.isoformat()})
    if df.empty:
        return df
    return df.rename(columns={"KEY": "series_key", "TIME_PERIOD": "period", "OBS_VALUE": "obs_value",
                              "OBS_STATUS": "obs_status"})[["series_key", "period", "obs_value", "obs_status"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=date.fromisoformat, default=date(2005, 1, 1),
                        help="start date for the first (full) download, YYYY-MM-DD; the TRY series starts in 2005")
    parser.add_argument("--full", action="store_true", help="ignore stored data and download everything again")
    args = parser.parse_args()

    existing = read_existing(NAME)
    if args.full or existing.empty:
        start = args.since
    else:
        start = date.fromisoformat(existing["period"].max()) - timedelta(days=REFRESH_DAYS)

    new = fetch(start)
    if new.empty:
        print(f"ecb: no observations since {start}")
        return
    merged = upsert_parquet(NAME, new, keys=["series_key", "period"])
    print(f"ecb: fetched {len(new)} rows from {start}, stored {len(merged)} "
          f"({merged['period'].min()} .. {merged['period'].max()})")


if __name__ == "__main__":
    main()
