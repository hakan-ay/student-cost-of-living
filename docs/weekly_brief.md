# Weekly brief: writing guide

The weekly brief is written every Monday by a Claude Code routine (or by hand) and published only through
`src/brief.py`, which rejects any draft whose numbers do not come from the fact sheet.

## Procedure

```bash
git pull                                          # includes the Monday data refresh from GitHub Actions
uv run python src/brief.py facts                  # writes reports/briefs/<date>.facts.json and prints it
# write reports/briefs/<date>.draft.json (format below)
uv run python src/brief.py publish reports/briefs/<date>.draft.json
```

`publish` either prints `published` (the draft becomes `<date>.brief.json` and `WEEKLY_UPDATES.md` is rebuilt)
or `REJECTED` with the list of violations, in which case nothing is published. Fix the draft and run `publish`
again. Commit `reports/briefs/<date>.facts.json`, `reports/briefs/<date>.brief.json` and `WEEKLY_UPDATES.md`.

## Audience and content

Turkish students who plan to study in Italy and their families, who usually pay in Turkish lira. The brief
explains what a month as a student in Italy costs in euros and in lira, and how fast that is changing.

- A headline of at most 12 words.
- 2 or 3 short paragraphs, about 150 words in total, in plain English:
  1. the monthly budget in euros and in lira, and its change over a year;
  2. the exchange rate this week (latest rate, change over the last week and the last 30 days);
  3. what it means in real terms for a family earning in lira (inflation-adjusted budget, real EUR/TRY index).
- Describe the data only: no financial advice, no exchange-rate forecasts, no recommendations on when to
  convert money.

## Number rules (enforced by `src/guardrail.py`)

- Every number must come from the fact sheet. Rounding is allowed (853.95 can be written as 854 or 853.9);
  computing new numbers (differences, sums, ratios) is not.
- Write numbers as digits, months and dates as words ("September 2026", "21 October 2026"), never ISO dates.
  Say "over a year" rather than "12 months".
- List every number you write, each time it appears, in `cited_numbers`, with the id of the fact it comes from
  and the number exactly as written. Signs do not matter ("fell 8.4 %" cites `-8.36` as `"8.4"`).
- Years and day numbers that are part of a month or date fact (for example "September 2026") need no citation.

## Draft format

```json
{
  "headline": "A month in Italy costs 854 euros, 47,834 lira",
  "paragraphs": ["...", "...", "..."],
  "cited_numbers": [
    {"fact_id": "budget_eur", "as_written": "854"},
    {"fact_id": "budget_try", "as_written": "47,834"}
  ]
}
```
