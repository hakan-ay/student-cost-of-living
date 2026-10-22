"""Unit tests for the numeric guardrail of the weekly brief (no API calls)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from guardrail import check_brief, extract_numbers, matches, parse_number  # noqa: E402

FACTS = [
    {"id": "budget_month", "value": "September 2026", "unit": "month", "description": ""},
    {"id": "fx_latest_date", "value": "21 October 2026", "unit": "date", "description": ""},
    {"id": "budget_eur", "value": 853.95, "unit": "EUR", "description": ""},
    {"id": "budget_try", "value": 47834.0, "unit": "TRY", "description": ""},
    {"id": "budget_try_yoy_pct", "value": 18.88, "unit": "%", "description": ""},
    {"id": "budget_real_try_yoy_pct", "value": -8.36, "unit": "%", "description": ""},
    {"id": "eur_try_latest", "value": 55.7233, "unit": "TRY per EUR", "description": ""},
    {"id": "try_amount_1000", "value": 1000, "unit": "TRY", "description": ""},
]


def cite(*pairs):
    return [{"fact_id": f, "as_written": w} for f, w in pairs]


def test_extract_numbers_handles_separators_signs_and_codes():
    found = [n.text for n in extract_numbers("€854 (47,834 TRY), −8.4 %, +18.9%, 30-day, CP041, 1,000 lira.")]
    assert found == ["854", "47,834", "−8.4", "+18.9", "30", "1,000"]


def test_rounding_tolerance_follows_written_decimals():
    assert matches(parse_number("854"), 853.95)
    assert matches(parse_number("853.9"), 853.95)  # 853.95 can round either way at one decimal
    assert matches(parse_number("18.9"), 18.88)
    assert not matches(parse_number("18.8"), 18.88)
    assert matches(parse_number("-8.4"), -8.36)
    assert matches(parse_number("8"), -8.36)
    assert not matches(parse_number("9"), -8.36)


def test_clean_brief_passes():
    text = ("In September 2026 a month costs 854 EUR, or 47,834 lira, up 18.9 % in a year. "
            "In real terms it is 8.4 % cheaper. On 21 October 2026 one euro cost 55.72 lira.")
    cited = cite(("budget_eur", "854"), ("budget_try", "47,834"), ("budget_try_yoy_pct", "18.9"),
                 ("budget_real_try_yoy_pct", "8.4"), ("eur_try_latest", "55.72"))
    assert check_brief(text, cited, FACTS) == []


def test_invented_number_is_rejected():
    text = "A month costs 854 EUR, about 24 EUR more than last year."
    violations = check_brief(text, cite(("budget_eur", "854"), ("budget_eur", "24")), FACTS)
    assert any("'24' does not match any fact" in v for v in violations)
    assert any("does not match fact 'budget_eur'" in v for v in violations)


def test_uncited_number_is_rejected():
    violations = check_brief("A month costs 854 EUR.", [], FACTS)
    assert violations == ["'854' appears in the brief but is not listed in cited_numbers"]


def test_misattributed_citation_is_rejected():
    text = "The lira budget rose 18.9 % in a year."
    violations = check_brief(text, cite(("budget_real_try_yoy_pct", "18.9")), FACTS)
    assert violations == ["'18.9' does not match fact 'budget_real_try_yoy_pct' = -8.36"]


def test_too_precise_number_is_rejected():
    violations = check_brief("One euro cost 55.75 lira.", cite(("eur_try_latest", "55.75")), FACTS)
    assert "'55.75' does not match any fact" in violations


def test_years_and_days_from_text_facts_are_allowed_without_citation():
    assert check_brief("Prices up to September 2026, rate of 21 October 2026.", [], FACTS) == []
