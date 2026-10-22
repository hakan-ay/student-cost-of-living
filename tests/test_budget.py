"""Unit tests for app/budget.py on small synthetic tables (no data files involved)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from budget import compute_budget  # noqa: E402

MONTHS = pd.date_range("2025-01-01", "2026-02-01", freq="MS")  # 14 months: 2025 base year + 2 months of 2026
IN_2026 = MONTHS.year == 2026


def cpi_table() -> pd.DataFrame:
    rows = []
    for m, new in zip(MONTHS, IN_2026):
        rows += [
            {"source": "eurostat_hicp", "geo": "IT", "coicop": "CP041", "month": m, "index_2025": 110.0 if new else 100.0},
            {"source": "eurostat_hicp", "geo": "IT", "coicop": "CP01", "month": m, "index_2025": 100.0},
            {"source": "eurostat_hicp", "geo": "IT", "coicop": "CP0732", "month": m, "index_2025": 100.0},
            # rows that must be ignored: Turkish prices and the Istat source for the same categories
            {"source": "eurostat_hicp", "geo": "TR", "coicop": "CP041", "month": m, "index_2025": 999.0},
            {"source": "istat_nic", "geo": "IT", "coicop": "CP041", "month": m, "index_2025": 999.0},
        ]
    return pd.DataFrame(rows)


BUDGET_MART = pd.DataFrame({"month": MONTHS, "eur_try_avg": [60.0 if n else 50.0 for n in IN_2026]})
POWER_MART = pd.DataFrame({"month": MONTHS, "tr_hicp_index_2025": [130.0 if n else 100.0 for n in IN_2026]})


def basket(rent=400, food=200, transport=0) -> pd.DataFrame:
    return pd.DataFrame({"component": ["rent", "food", "transport"], "coicop": ["CP041", "CP01", "CP0732"],
                         "base_amount_eur": [rent, food, transport]})


def row(df: pd.DataFrame, month: str) -> pd.Series:
    return df.set_index("month").loc[pd.Timestamp(month)]


def test_base_year_equals_base_amounts():
    out = compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket())
    r = row(out, "2025-06-01")
    assert (r["rent"], r["food"], r["transport"], r["total_eur"]) == (400, 200, 0, 600)


def test_each_component_moves_with_its_own_index():
    r = row(compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket()), "2026-01-01")
    assert r["rent"] == pytest.approx(440)  # rent index 110
    assert r["food"] == pytest.approx(200)  # food index 100
    assert r["total_eur"] == pytest.approx(640)


def test_eur_to_try_uses_the_month_average_rate():
    out = compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket())
    assert row(out, "2025-01-01")["total_try"] == pytest.approx(600 * 50)
    assert row(out, "2026-01-01")["total_try"] == pytest.approx(640 * 60)


def test_real_terms_deflate_by_turkish_prices():
    r = row(compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket()), "2026-01-01")
    assert r["budget_try_at_2025_prices"] == pytest.approx(640 * 60 / 1.3)


def test_year_on_year_changes():
    out = compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket())
    r = row(out, "2026-01-01")
    assert r["total_eur_yoy_pct"] == pytest.approx(100 * (640 / 600 - 1))
    assert r["total_try_yoy_pct"] == pytest.approx(100 * (640 * 60 / (600 * 50) - 1))
    assert r["budget_real_try_yoy_pct"] == pytest.approx(100 * ((640 * 60 / 1.3) / (600 * 50) - 1))
    assert out[out["month"].dt.year == 2025]["total_eur_yoy_pct"].isna().all()  # no month a year earlier


def test_scaling_the_basket_scales_the_budget_but_not_the_rates():
    base = compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket())
    double = compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket(rent=800, food=400))
    assert (double["total_eur"] / base["total_eur"]).round(9).eq(2).all()
    assert (double["total_try"] / base["total_try"]).round(9).eq(2).all()
    pd.testing.assert_series_equal(double["total_try_yoy_pct"], base["total_try_yoy_pct"])


def test_adding_a_component_adds_its_cost():
    out = compute_budget(cpi_table(), BUDGET_MART, POWER_MART, basket(transport=40))
    assert row(out, "2026-02-01")["total_eur"] == pytest.approx(640 + 40)


def test_months_without_every_index_or_a_rate_are_dropped():
    cpi = cpi_table()
    cpi = cpi[~((cpi["coicop"] == "CP01") & (cpi["month"] == pd.Timestamp("2025-03-01")))]
    fx = BUDGET_MART[BUDGET_MART["month"] != pd.Timestamp("2025-04-01")]
    out = compute_budget(cpi, fx, POWER_MART, basket())
    assert pd.Timestamp("2025-03-01") not in set(out["month"])  # food index missing
    assert pd.Timestamp("2025-04-01") not in set(out["month"])  # exchange rate missing
    assert len(out) == len(MONTHS) - 2
    assert out["month"].is_monotonic_increasing
