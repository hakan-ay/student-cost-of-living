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
