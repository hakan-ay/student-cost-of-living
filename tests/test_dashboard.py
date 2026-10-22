"""Smoke test: the dashboard runs end to end on the committed marts and briefs, for every period."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "dashboard.py")


def test_dashboard_renders_every_period():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert [m.label for m in at.metric][:2] == ["Monthly budget, EUR", "Monthly budget, TRY"]
    assert any(h.value.startswith("Weekly brief") for h in at.subheader)
    for period in ("1Y", "10Y", "All"):
        at.button_group[0].set_value(period).run()
        assert not at.exception, period


def test_reference_basket_reproduces_the_dbt_mart():
    import sys

    import duckdb
    import pandas as pd

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "app"))
    from budget import compute_budget

    con = duckdb.connect()
    marts = {n: con.execute(f"select * from read_parquet('{root / 'data' / 'marts' / n}.parquet')").df()
             for n in ("cpi_monthly", "student_budget_monthly", "try_purchasing_power")}
    mine = compute_budget(marts["cpi_monthly"], marts["student_budget_monthly"], marts["try_purchasing_power"],
                          pd.read_csv(root / "dbt" / "seeds" / "basket_components.csv"))
    merged = mine.merge(marts["student_budget_monthly"], on="month", suffixes=("", "_mart"))
    assert len(merged) == len(marts["student_budget_monthly"])
    assert (merged["total_eur"] - merged["total_eur_mart"]).abs().max() < 0.01
    assert (merged["total_try"] - merged["total_try_mart"]).abs().max() < 1


def test_custom_basket_changes_the_tiles():
    at = AppTest.from_file(APP, default_timeout=60).run()
    reference = at.metric[0].value
    at.number_input(key="basket_transport").set_value(40).run()
    assert not at.exception
    assert at.metric[0].value != reference
    assert any("Custom basket" in c.value for c in at.caption)
