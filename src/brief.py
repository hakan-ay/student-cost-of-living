"""Weekly brief: fact sheet, numeric guardrail and publishing. No API key is needed.

The brief is written every Monday by a Claude Code routine that follows docs/weekly_brief.md. This script owns
everything around the writing: it freezes the fact sheet the brief must be written from, rejects a draft whose
numbers do not come from that fact sheet, and rebuilds WEEKLY_UPDATES.md from all published briefs.

Usage:
    uv run python src/brief.py facts                        # write reports/briefs/<date>.facts.json, print it
    uv run python src/brief.py publish <draft.json>         # check the draft; publish only if it passes
    uv run python src/brief.py index [--check]              # rebuild WEEKLY_UPDATES.md (or check it is current)
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from brief_facts import build_facts
from guardrail import check_brief, extract_numbers

ROOT = Path(__file__).resolve().parents[1]
BRIEF_DIR = ROOT / "reports" / "briefs"
UPDATES_PAGE = ROOT / "WEEKLY_UPDATES.md"
DRAFT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.draft\.json$")

PAGE_INTRO = """# Weekly updates

A short brief every Monday on what a month as a Turkish student in Italy costs in euros and in lira, written
from that week's data refresh. Newest first.

**How it is made.** After the weekly data refresh, a Claude Code routine writes the brief from a fact sheet that
is generated from the dbt marts ([`src/brief_facts.py`](src/brief_facts.py)), following
[`docs/weekly_brief.md`](docs/weekly_brief.md). Before anything is published,
[`src/guardrail.py`](src/guardrail.py) checks that every number in the text exists in the fact sheet (rounding
only) and is cited with the fact it comes from; a draft that fails is not published. Each entry links to the
exact fact sheet and the structured brief it was checked against. Descriptive only, not financial advice.
"""


def validate_draft(draft: dict) -> list[str]:
    """Shape check of a draft: {"headline": str, "paragraphs": [str], "cited_numbers": [{"fact_id", "as_written"}]}."""
    errors = []
    if not isinstance(draft.get("headline"), str) or not draft["headline"].strip():
        errors.append("headline must be a non-empty string")
    paragraphs = draft.get("paragraphs")
    if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 4 or not all(isinstance(p, str) for p in paragraphs):
        errors.append("paragraphs must be a list of 1 to 4 strings")
    cited = draft.get("cited_numbers")
    if not isinstance(cited, list) or not all(isinstance(c, dict) and {"fact_id", "as_written"} <= c.keys() for c in cited):
        errors.append("cited_numbers must be a list of {fact_id, as_written} objects")
    extra = set(draft) - {"headline", "paragraphs", "cited_numbers"}
    if extra:
        errors.append(f"unexpected keys: {sorted(extra)}")
    return errors


def brief_text(draft: dict) -> str:
    return "\n".join([draft["headline"], *draft["paragraphs"]])


def write_facts(brief_dir: Path, day: str) -> Path:
    brief_dir.mkdir(parents=True, exist_ok=True)
    path = brief_dir / f"{day}.facts.json"
    path.write_text(json.dumps(build_facts(), indent=1, ensure_ascii=False) + "\n")
    return path


def publish(draft_path: Path, brief_dir: Path) -> list[str]:
    """Checks a draft against the fact sheet of the same date. On success it is saved as <date>.brief.json and
    the draft is removed; on failure nothing changes and the violations are returned."""
    m = DRAFT_RE.match(draft_path.name)
    if not m:
        return [f"draft file must be named <YYYY-MM-DD>.draft.json, got '{draft_path.name}'"]
    day = m.group(1)
    facts_path = brief_dir / f"{day}.facts.json"
    if not facts_path.exists():
        return [f"fact sheet {facts_path.name} not found: run `brief.py facts` first"]

    draft = json.loads(draft_path.read_text())
    errors = validate_draft(draft)
    if errors:
        return errors
    facts = json.loads(facts_path.read_text())
    violations = check_brief(brief_text(draft), draft["cited_numbers"], facts)
    if violations:
        return violations

    (brief_dir / f"{day}.brief.json").write_text(json.dumps(draft, indent=1, ensure_ascii=False) + "\n")
    draft_path.unlink()
    return []


def render_page(brief_dir: Path) -> str:
    entries = []
    for path in sorted(brief_dir.glob("*.brief.json"), reverse=True):
        day = path.name.split(".")[0]
        brief = json.loads(path.read_text())
        facts = {f["id"]: f["value"] for f in json.loads((brief_dir / f"{day}.facts.json").read_text())}
        entries.append((day, brief, facts))

    lines = [PAGE_INTRO, "| Week of | Headline |", "|---|---|"]
    lines += [f"| [{day}](#{day}) | {brief['headline']} |" for day, brief, _ in entries]
    if not entries:
        lines.append("| | No briefs yet. |")
    for day, brief, facts in entries:
        n_numbers = len(extract_numbers(brief_text(brief)))
        lines += [
            "",
            "---",
            "",
            f'<a id="{day}"></a>',
            f"## {day}: {brief['headline']}",
            "",
            f"*Consumer prices up to {facts['budget_month']}, exchange rate up to {facts['fx_latest_date']}.*",
            "",
            "\n\n".join(brief["paragraphs"]),
            "",
            f"<sub>{n_numbers} numbers checked against the fact sheet: "
            f"[`{day}.facts.json`](reports/briefs/{day}.facts.json) · "
            f"structured brief: [`{day}.brief.json`](reports/briefs/{day}.brief.json)</sub>",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_facts = sub.add_parser("facts", help="write the fact sheet for a date and print it")
    p_facts.add_argument("--date", default=date.today().isoformat(), help="brief date, YYYY-MM-DD (default: today)")
    p_pub = sub.add_parser("publish", help="check a draft and publish it if it passes")
    p_pub.add_argument("draft", type=Path)
    p_index = sub.add_parser("index", help="rebuild WEEKLY_UPDATES.md")
    p_index.add_argument("--check", action="store_true", help="exit 1 if WEEKLY_UPDATES.md is out of date")
    args = parser.parse_args()

    if args.command == "facts":
        path = write_facts(BRIEF_DIR, args.date)
        print(path.read_text())
        print(f"fact sheet written to {path.relative_to(ROOT)}; write the draft to "
              f"reports/briefs/{args.date}.draft.json (see docs/weekly_brief.md)", file=sys.stderr)
    elif args.command == "publish":
        violations = publish(args.draft, BRIEF_DIR)
        if violations:
            print("REJECTED, nothing published:")
            for v in violations:
                print(f"  - {v}")
            sys.exit(1)
        UPDATES_PAGE.write_text(render_page(BRIEF_DIR))
        print(f"published; {UPDATES_PAGE.name} updated")
    elif args.command == "index":
        page = render_page(BRIEF_DIR)
        if args.check:
            if not UPDATES_PAGE.exists() or UPDATES_PAGE.read_text() != page:
                print(f"{UPDATES_PAGE.name} is out of date: run src/brief.py index")
                sys.exit(1)
            print(f"{UPDATES_PAGE.name} is up to date")
            return
        UPDATES_PAGE.write_text(page)
        print(f"{UPDATES_PAGE.name} rebuilt from {len(list(BRIEF_DIR.glob('*.brief.json')))} briefs")


if __name__ == "__main__":
    main()
