"""Shared helpers for the fetch scripts: HTTP with retries and the Parquet raw layer under data/raw/.

Each source keeps one Parquet file that holds the full history seen so far. A fetch only downloads a recent
window and upserts it on the source's key columns, so revised observations replace the old ones.
"""

import io
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
USER_AGENT = "student-cost-of-living/0.1 (open-data portfolio project)"


def get_csv(url: str, params: dict | None = None, headers: dict | None = None, retries: int = 3) -> pd.DataFrame:
    """Downloads a CSV response into a DataFrame (all columns as strings). Retries on network errors and 5xx/429."""
    headers = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=120)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            if not resp.text.strip():  # SDMX APIs answer an empty body when the window has no new data
                return pd.DataFrame()
            return pd.read_csv(io.StringIO(resp.text), dtype=str, keep_default_na=False)
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
    raise RuntimeError("unreachable")


def read_existing(name: str) -> pd.DataFrame:
    path = RAW_DIR / f"{name}.parquet"
    return duckdb.sql(f"select * from read_parquet('{path}')").df() if path.exists() else pd.DataFrame()


def upsert_parquet(name: str, new: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Merges `new` into data/raw/<name>.parquet: rows with the same key are replaced, the rest are kept."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.parquet"
    new = new.assign(fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    old = read_existing(name)
    if not old.empty:
        old = old.merge(new[keys].drop_duplicates(), on=keys, how="left", indicator=True)
        old = old[old["_merge"] == "left_only"].drop(columns="_merge")
    merged = pd.concat([old, new], ignore_index=True).sort_values(keys, ignore_index=True)  # noqa: F841 (used by duckdb)
    duckdb.sql(f"copy (select * from merged) to '{path}' (format parquet, compression zstd)")
    return merged
