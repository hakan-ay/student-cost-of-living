"""Writes the weekly brief with the Claude API and publishes it only if it passes the numeric guardrail.

Flow: fact sheet from the marts (brief_facts.py) -> Claude writes a structured brief (headline, paragraphs and
the list of numbers it cites) -> guardrail.py checks every number against the fact sheet -> on failure the
violations are sent back for one correction -> a brief that still fails is not written.

Output: reports/briefs/<date>.md, reports/briefs/<date>.facts.json (the exact input) and reports/latest_brief.md.
Credentials: ANTHROPIC_API_KEY (in GitHub Actions: the repository secret of the same name).

Usage:
    uv run python src/write_brief.py
    uv run python src/write_brief.py --dry-run     # print the prompt and the fact sheet, no API call
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import anthropic
from pydantic import BaseModel

from brief_facts import build_facts
from guardrail import check_brief, extract_numbers

ROOT = Path(__file__).resolve().parents[1]
BRIEF_DIR = ROOT / "reports" / "briefs"
MODEL = "claude-opus-5-5"
MAX_ATTEMPTS = 2

SYSTEM = """You write a short weekly brief for Turkish students who plan to study in Italy and for their \
families, who usually pay in Turkish lira. The brief explains what a month as a student in Italy costs in euros \
and in lira, and how fast that is changing.

You receive a fact sheet as JSON. It is the only source you may use.
- Every number you write must come from the fact sheet. You may round a value (853.95 can be written as 854), \
but do not compute new numbers such as differences, ratios or sums that are not in the fact sheet.
- Write numbers as digits, months and dates as words ("September 2026", "21 October 2026"), never as ISO dates. \
Say "over a year" or "in a year" rather than "12 months".
- List every number you write, each time it appears, in cited_numbers with the fact id it comes from and the \
number exactly as you wrote it (for example "854" or "-8.4").
- Describe the data; do not give financial advice, exchange-rate forecasts or recommendations on when to \
convert money.

Format: a headline of at most 12 words and 2 or 3 short paragraphs (about 150 words in total) in plain English: \
first the budget in euros and lira, then the exchange rate this week, then what it means in real terms for a \
family earning in lira."""


class Citation(BaseModel):
    fact_id: str
    as_written: str


class Brief(BaseModel):
    headline: str
    paragraphs: list[str]
    cited_numbers: list[Citation]


def output_schema(fact_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "headline": {"type": "string"},
            "paragraphs": {"type": "array", "items": {"type": "string"}},
            "cited_numbers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"fact_id": {"type": "string", "enum": fact_ids}, "as_written": {"type": "string"}},
                    "required": ["fact_id", "as_written"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["headline", "paragraphs", "cited_numbers"],
        "additionalProperties": False,
    }


def request_brief(client: anthropic.Anthropic, messages: list, schema: dict):
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # a declined request is re-run on Anthropic's recommended fallback model
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        system=SYSTEM,
        messages=messages,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"request declined (stop_details: {response.stop_details})")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("response hit max_tokens")
    text = next(b.text for b in response.content if b.type == "text")
    return response, Brief.model_validate_json(text)


def render(brief: Brief, facts: dict, model: str, run_date: str, n_numbers: int) -> str:
    paragraphs = "\n\n".join(brief.paragraphs)
    return f"""# {brief.headline}

*Weekly brief, {run_date}. Consumer prices up to {facts['budget_month']}, \
exchange rate up to {facts['fx_latest_date']}.*

{paragraphs}

---

<sub>Written by `{model}` from the fact sheet [`{run_date}.facts.json`](briefs/{run_date}.facts.json), \
which is generated from the dbt marts. Guardrail: all {n_numbers} numbers in this brief were matched to the fact \
sheet before publishing ([`src/guardrail.py`](../src/guardrail.py)). Descriptive only, not financial advice.</sub>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print the prompt and the fact sheet, no API call")
    args = parser.parse_args()

    facts = build_facts()
    facts_json = json.dumps(facts, indent=1, ensure_ascii=False)
    if args.dry_run:
        print(SYSTEM, "\n\n", facts_json)
        return

    schema = output_schema([f["id"] for f in facts])
    messages = [{"role": "user", "content": f"Fact sheet:\n{facts_json}\n\nWrite this week's brief."}]
    client = anthropic.Anthropic()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response, brief = request_brief(client, messages, schema)
        except anthropic.APIError as e:
            print(f"API error: {e}", file=sys.stderr)
            sys.exit(2)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(2)

        text = "\n".join([brief.headline, *brief.paragraphs])
        violations = check_brief(text, [c.model_dump() for c in brief.cited_numbers], facts)
        print(f"attempt {attempt}: {len(violations)} guardrail violations (model {response.model})")
        if not violations:
            break
        for v in violations:
            print(f"  - {v}")
        messages += [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": "The brief failed the numeric check:\n- " + "\n- ".join(violations)
             + "\nRewrite it so that every number comes from the fact sheet and is listed in cited_numbers."},
        ]
    else:
        print("brief rejected: guardrail still failing after the correction attempt; nothing written",
              file=sys.stderr)
        sys.exit(1)

    run_date = date.today().isoformat()
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    by_id = {f["id"]: f["value"] for f in facts}
    markdown = render(brief, by_id, response.model, run_date, len(extract_numbers(text)))
    (BRIEF_DIR / f"{run_date}.facts.json").write_text(facts_json + "\n")
    (BRIEF_DIR / f"{run_date}.md").write_text(markdown.replace("](briefs/", "](").replace("](../src/", "](../../src/"))
    (ROOT / "reports" / "latest_brief.md").write_text(markdown)
    print(markdown)


if __name__ == "__main__":
    main()
