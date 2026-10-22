"""Tests for publishing briefs and rebuilding WEEKLY_UPDATES.md (no network, temporary folders)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from brief import publish, render_page  # noqa: E402

FACTS = [
    {"id": "budget_month", "value": "September 2026", "unit": "month", "description": ""},
    {"id": "fx_latest_date", "value": "21 October 2026", "unit": "date", "description": ""},
    {"id": "budget_eur", "value": 853.95, "unit": "EUR", "description": ""},
]
GOOD = {"headline": "A month costs 854 euros", "paragraphs": ["In September 2026 it was 854 euros."],
        "cited_numbers": [{"fact_id": "budget_eur", "as_written": "854"}] * 2}


def setup(tmp_path: Path, draft: dict, day: str = "2026-10-26") -> Path:
    (tmp_path / f"{day}.facts.json").write_text(json.dumps(FACTS))
    draft_path = tmp_path / f"{day}.draft.json"
    draft_path.write_text(json.dumps(draft))
    return draft_path


def test_good_draft_is_published_and_listed(tmp_path):
    draft_path = setup(tmp_path, GOOD)
    assert publish(draft_path, tmp_path) == []
    assert not draft_path.exists() and (tmp_path / "2026-10-26.brief.json").exists()
    page = render_page(tmp_path)
    assert "| [2026-10-26](#2026-10-26) | A month costs 854 euros |" in page
    assert "Consumer prices up to September 2026" in page


def test_bad_draft_is_rejected_and_nothing_is_written(tmp_path):
    bad = {**GOOD, "paragraphs": ["It was 854 euros, 30 euros more than last year."]}
    draft_path = setup(tmp_path, bad)
    violations = publish(draft_path, tmp_path)
    assert any("'30' does not match any fact" in v for v in violations)
    assert draft_path.exists() and not (tmp_path / "2026-10-26.brief.json").exists()


def test_malformed_draft_is_rejected(tmp_path):
    draft_path = setup(tmp_path, {"headline": "", "paragraphs": "text"})
    assert len(publish(draft_path, tmp_path)) >= 2


def test_page_lists_newest_first(tmp_path):
    for day in ("2026-10-19", "2026-10-26"):
        assert publish(setup(tmp_path, GOOD, day), tmp_path) == []
    page = render_page(tmp_path)
    assert page.index("## 2026-10-26") < page.index("## 2026-10-19")
