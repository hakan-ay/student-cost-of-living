"""Numeric guardrail for the weekly brief: every number in the text must come from the fact sheet.

Three checks, all on the final text (not on what the model says it did):
1. Every number written in the brief matches at least one fact, allowing only the rounding implied by the
   number of decimals written ("854" matches 853.95, "18.9" matches 18.88). Signs are ignored because the
   direction is carried by words ("fell 8.4 %").
2. Every number written in the brief is listed in `cited_numbers`.
3. Every cited number matches the fact it is attributed to.
Numbers inside text facts (month names with years, the latest rate date) are allowed as written.
"""

import re
from dataclasses import dataclass

# A number not glued to letters, digits or another number: 1,000 / 47,834 / 56.01 / 8 / −8.4
NUMBER_RE = re.compile(r"(?<![\w.,])[-−+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w])")


@dataclass(frozen=True)
class WrittenNumber:
    text: str
    value: float
    decimals: int


def parse_number(text: str) -> WrittenNumber:
    clean = text.replace("−", "-").replace(",", "").lstrip("+")
    decimals = len(clean.split(".")[1]) if "." in clean else 0
    return WrittenNumber(text=text, value=abs(float(clean)), decimals=decimals)


def extract_numbers(text: str) -> list[WrittenNumber]:
    return [parse_number(m.group(0)) for m in NUMBER_RE.finditer(text)]


def matches(written: WrittenNumber, value: float) -> bool:
    """True if `value` rounds to the written number at the written precision."""
    tolerance = 0.5 * 10 ** -written.decimals + 1e-9
    return abs(written.value - abs(value)) <= tolerance


def check_brief(text: str, cited: list[dict], facts: list[dict]) -> list[str]:
    """Returns a list of violations; an empty list means the brief passed."""
    numeric = {f["id"]: float(f["value"]) for f in facts if isinstance(f["value"], (int, float))}
    allowed_tokens = {n.value for f in facts if isinstance(f["value"], str) for n in extract_numbers(f["value"])}
    violations = []

    written = extract_numbers(text)
    for n in written:
        if n.value in allowed_tokens and n.decimals == 0:
            continue
        if not any(matches(n, v) for v in numeric.values()):
            violations.append(f"'{n.text}' does not match any fact")

    cited_written = set()
    for c in cited:
        fact_id, as_written = c.get("fact_id"), c.get("as_written", "")
        found = extract_numbers(as_written)
        if fact_id not in numeric and fact_id not in {f["id"] for f in facts}:
            violations.append(f"cited fact '{fact_id}' does not exist")
            continue
        if len(found) != 1:
            violations.append(f"citation for '{fact_id}' must contain exactly one number, got '{as_written}'")
            continue
        cited_written.add((found[0].value, found[0].decimals))
        if fact_id in numeric and not matches(found[0], numeric[fact_id]):
            violations.append(f"'{as_written}' does not match fact '{fact_id}' = {numeric[fact_id]}")

    for n in written:
        if n.value in allowed_tokens and n.decimals == 0:
            continue
        if (n.value, n.decimals) not in cited_written:
            violations.append(f"'{n.text}' appears in the brief but is not listed in cited_numbers")
    return violations
