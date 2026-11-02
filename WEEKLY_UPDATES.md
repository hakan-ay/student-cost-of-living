# Weekly updates

A short brief every Monday on what a month as a Turkish student in Italy costs in euros and in lira, written
from that week's data refresh. Newest first.

**How it is made.** After the weekly data refresh, a Claude Code routine writes the brief from a fact sheet that
is generated from the dbt marts ([`src/brief_facts.py`](src/brief_facts.py)), following
[`docs/weekly_brief.md`](docs/weekly_brief.md). Before anything is published,
[`src/guardrail.py`](src/guardrail.py) checks that every number in the text exists in the fact sheet (rounding
only) and is cited with the fact it comes from; a draft that fails is not published. Each entry links to the
exact fact sheet and the structured brief it was checked against. Descriptive only, not financial advice.

| Week of | Headline |
|---|---|
| [2026-11-02](#2026-11-02) | Euro edges up to 55.8 lira; a month in Italy: 854 euros |
| [2026-10-26](#2026-10-26) | Euro steady near 55.7 lira; a month in Italy costs 854 euros |
| [2026-10-22](#2026-10-22) | A month in Italy: 854 euros, or 47,834 lira |

---

<a id="2026-11-02"></a>
## 2026-11-02: Euro edges up to 55.8 lira; a month in Italy: 854 euros

*Consumer prices up to September 2026, exchange rate up to 30 October 2026.*

Italian consumer prices are still published only up to September 2026, so the budget has not moved since last week. A month as a student in Turin costs 854 euros, 2.9 % more than in September 2025. Rent takes 468 euros and food 281 euros, while local transport is free for students under 26 in Piedmont. Converted at September's average rate of 56.01 lira per euro, the budget is 47,834 lira, 18.9 % more over a year.

The latest ECB reference rate, for 30 October 2026, was 55.8 lira per euro, up from 55.67 a week earlier. That is a rise of 0.23 % over the week and 0.25 % over 30 days; over 365 days the euro has gained 15.1 % against the lira. At the latest rate, 1,000 lira buys 17.92 euros.

Turkish consumer prices rose 29.7 % over a year, against 4.2 % in Italy. Measured in 2025 lira, the budget fell 8.4 %, from 38,035 to 34,854. The real EUR/TRY index stands at 95.6, under its 2025 level of 100, so in real terms Italy is cheaper for lira earners than in 2025.

<sub>33 numbers checked against the fact sheet: [`2026-11-02.facts.json`](reports/briefs/2026-11-02.facts.json) · structured brief: [`2026-11-02.brief.json`](reports/briefs/2026-11-02.brief.json)</sub>

---

<a id="2026-10-26"></a>
## 2026-10-26: Euro steady near 55.7 lira; a month in Italy costs 854 euros

*Consumer prices up to September 2026, exchange rate up to 23 October 2026.*

Italian price data still end in September 2026, so the budget is the same as last week. A month as a student in Turin costs 854 euros, 2.9 % more than a year earlier, with rent at 468 euros and food at 281 euros. At September's average of 56.01 lira per euro that comes to 47,834 lira, up 18.9 % over a year.

The latest ECB rate, for 23 October 2026, was 55.67 lira per euro, against 55.73 a week before. That is a dip of 0.1 % over the week and 0.1 % over 30 days, while over 365 days the euro is up 14.1 %. At the latest rate, 1,000 lira buys 17.96 euros.

Turkish consumer prices rose 29.7 % over a year, faster than the euro. Measured in 2025 lira, the budget fell 8.4 %, from 38,035 to 34,854. The real EUR/TRY index is 95.6, below its 2025 level of 100.

<sub>29 numbers checked against the fact sheet: [`2026-10-26.facts.json`](reports/briefs/2026-10-26.facts.json) · structured brief: [`2026-10-26.brief.json`](reports/briefs/2026-10-26.brief.json)</sub>

---

<a id="2026-10-22"></a>
## 2026-10-22: A month in Italy: 854 euros, or 47,834 lira

*Consumer prices up to September 2026, exchange rate up to 21 October 2026.*

In September 2026 the reference student budget in Turin came to 854 euros a month, 2.9 % more than a year earlier. At that month's average rate of 56.01 lira per euro it cost 47,834 lira, up 18.9 % from 40,237 lira in September 2025. Rent is the largest item at 468 euros, while local transport is free for students under 26.

The euro moved little against the lira this week. The latest ECB rate, on 21 October 2026, was 55.72 lira: 0.8 % above a week earlier and 0.6 % below its level 30 days ago. Over 365 days the euro has gained 14.4 %.

For a family whose income keeps pace with Turkish prices, the picture is better than the nominal figures suggest. Turkish consumer prices rose 29.7 % over a year, faster than the euro, so measured in 2025 lira the budget fell from 38,035 to 34,854, a drop of 8.4 %. The real EUR/TRY index stands at 95.6, below its 2025 level of 100.

<sub>28 numbers checked against the fact sheet: [`2026-10-22.facts.json`](reports/briefs/2026-10-22.facts.json) · structured brief: [`2026-10-22.brief.json`](reports/briefs/2026-10-22.brief.json)</sub>
