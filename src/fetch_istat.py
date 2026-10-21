"""Fetches Italian consumer price detail from Istat (NIC, dataflow 167_745: monthly, base 2025=100, ECOICOP ver. 2).

NIC is Italy's national CPI. It is used next to the Eurostat HICP for detail the student basket cares about:
rents paid by tenants for their main residence (0411) and bus / coach transport (07321).
Dataflow 167_745 starts in January 2026 (the first year on base 2025).

Writes data/raw/istat_nic.parquet. Istat limits the request rate, so this script makes a single request.

Usage:
    uv run python src/fetch_istat.py
    uv run python src/fetch_istat.py --full
"""

import argparse

import pandas as pd

from fetch_eurostat import shift_month
from raw_store import get_csv, read_existing, upsert_parquet

DATAFLOW = "167_745"
URL = f"https://esploradati.istat.it/SDMXWS/rest/data/{DATAFLOW}"
NAME = "istat_nic"
REFRESH_MONTHS = 13

MEASURES = ["4", "6", "7"]  # index number, % change on previous month, % change on same month of previous year
ECOICOP = ["00", "01", "041", "0411", "0732", "07321", "0735"]


def fetch(start_month: str) -> pd.DataFrame:
    key = f"M.IT..{'+'.join(MEASURES)}.{'+'.join(ECOICOP)}"
    df = get_csv(f"{URL}/{key}", params={"startPeriod": start_month},
                 headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
    if df.empty:
        return df
    return df.rename(columns={"REF_AREA": "geo", "DATA_TYPE": "data_type", "MEASURE": "measure",
                              "ECOICOP_2": "ecoicop", "TIME_PERIOD": "period", "OBS_VALUE": "obs_value",
                              "OBS_STATUS": "obs_status"}).assign(dataflow=DATAFLOW)[
        ["dataflow", "geo", "data_type", "measure", "ecoicop", "period", "obs_value", "obs_status"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2026-01", help="first month for a full download, YYYY-MM")
    parser.add_argument("--full", action="store_true", help="ignore stored data and download everything again")
    args = parser.parse_args()

    existing = read_existing(NAME)
    if args.full or existing.empty:
        start = args.since
    else:
        start = max(args.since, shift_month(existing["period"].max(), -REFRESH_MONTHS))

    new = fetch(start)
    if new.empty:
        print(f"istat: no observations since {start}")
        return
    merged = upsert_parquet(NAME, new, keys=["dataflow", "geo", "data_type", "measure", "ecoicop", "period"])
    print(f"istat: fetched {len(new)} rows from {start}, stored {len(merged)} (latest month {merged['period'].max()})")


if __name__ == "__main__":
    main()
