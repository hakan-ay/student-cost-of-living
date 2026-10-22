"""Recomputes the monthly student budget for any basket, with the same method as the dbt mart
student_budget_monthly: each 2025 base amount is moved with its Italian HICP index (2025 = 100), converted with
the month's average EUR/TRY and deflated by Turkish HICP. With the reference basket it reproduces the mart.
"""

import pandas as pd


def compute_budget(cpi: pd.DataFrame, budget_mart: pd.DataFrame, power_mart: pd.DataFrame,
                   basket: pd.DataFrame) -> pd.DataFrame:
    """basket: one row per component with columns component, coicop, base_amount_eur."""
    it = cpi[(cpi["source"] == "eurostat_hicp") & (cpi["geo"] == "IT") & cpi["coicop"].isin(basket["coicop"])]
    idx = it.pivot(index="month", columns="coicop", values="index_2025").dropna()  # every component published
    out = pd.DataFrame({row.component: row.base_amount_eur * idx[row.coicop] / 100 for row in basket.itertuples()})
    out["total_eur"] = out.sum(axis=1)
    out = (out.reset_index()
           .merge(budget_mart[["month", "eur_try_avg"]], on="month")
           .merge(power_mart[["month", "tr_hicp_index_2025"]], on="month"))
    out["total_try"] = out["total_eur"] * out["eur_try_avg"]
    out["budget_try_at_2025_prices"] = out["total_try"] / (out["tr_hicp_index_2025"] / 100)

    cols = ["total_eur", "total_try", "budget_try_at_2025_prices"]
    prev = out[["month", *cols]].assign(month=out["month"] + pd.DateOffset(years=1))
    out = out.merge(prev, on="month", how="left", suffixes=("", "_prev"))
    out["total_eur_yoy_pct"] = 100 * (out["total_eur"] / out["total_eur_prev"] - 1)
    out["total_try_yoy_pct"] = 100 * (out["total_try"] / out["total_try_prev"] - 1)
    out["budget_real_try_yoy_pct"] = 100 * (out["budget_try_at_2025_prices"] / out["budget_try_at_2025_prices_prev"] - 1)
    return out.sort_values("month", ignore_index=True)
