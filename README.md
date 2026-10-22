# Student Cost of Living: Italy in EUR and TRY

[![CI](https://github.com/hakan-ay/student-cost-of-living/actions/workflows/ci.yml/badge.svg)](https://github.com/hakan-ay/student-cost-of-living/actions/workflows/ci.yml)
[![Weekly refresh](https://github.com/hakan-ay/student-cost-of-living/actions/workflows/refresh.yml/badge.svg)](https://github.com/hakan-ay/student-cost-of-living/actions/workflows/refresh.yml)

**How much does a month as a Turkish student in Italy cost in EUR and in TRY, and how fast is it changing?**

An automated data pipeline on official open data: Python fetchers pull exchange rates and consumer prices from
the ECB, Eurostat and Istat into Parquet snapshots, and a **dbt** project on **DuckDB** turns them into tested
marts. A GitHub Actions job refreshes everything every week, commits the new data and publishes a short
[weekly brief](reports/latest_brief.md) written with the Claude API, which is only published if every number in
it can be traced to the data. A dashboard comes next (see [Roadmap](#roadmap)).

> **Status:** milestones W1-W4 (sources, raw layer, dbt models and tests, weekly automation, LLM brief). The data
> pipeline needs no API keys; only the weekly brief uses an Anthropic API key.

## Latest numbers

<!-- latest-numbers:start -->
Generated from the marts: consumer prices up to September 2026, exchange rate up to 21 October 2026.

| | Sep 2025 | Sep 2026 | Change |
|---|---:|---:|---:|
| Monthly budget in EUR | 830 | 854 | +2.9 % |
| Average EUR/TRY | 48.5 | 56.0 | +15.5 % |
| Monthly budget in TRY | 40,237 | 47,834 | +18.9 % |
| Budget in TRY at 2025 Turkish prices | 38,035 | 34,854 | −8.4 % |

In nominal lira the budget changed by +18.9 % in a year. Turkish prices rose faster than the euro did (Turkish HICP +29.7 % against EUR/TRY +15.5 %), so for a household whose income keeps up with Turkish inflation the same month in Italy became about 8 % cheaper in real terms.
<!-- latest-numbers:end -->

## Sources

| Source | Series | Frequency | Used for |
|---|---|---|---|
| [ECB Data Portal](https://data.ecb.europa.eu/) | `EXR.D.TRY.EUR.SP00.A`, euro reference rate for the Turkish lira | Daily, from 2005 | `fx_daily`, EUR to TRY conversion |
| [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table) | `prc_hicp_minr`, HICP (ECOICOP ver. 2), Italy and Turkey, index 2025=100 and annual rate | Monthly, from 2005 | `cpi_monthly`, basket indexation, inflation gap |
| [Istat](https://esploradati.istat.it/) | NIC dataflow `167_745`, Italian national CPI detail, base 2025=100 | Monthly, from 2026 | `cpi_monthly` detail (tenants' rents, bus and coach), cross-check of rents |

**Note on Eurostat datasets.** The original plan used `prc_hicp_manr` (annual rates) and `prc_hicp_midx` (indices).
With the January 2026 release Eurostat moved the HICP to ECOICOP ver. 2 and froze those datasets at December
2025. `prc_hicp_minr` carries the full history on the new classification and holds both indices and rates, so it
replaces both. Category codes follow ECOICOP ver. 2 (for example `CP041` actual rentals, `CP0732` passenger
transport by road).

## Reference basket

The budget is a fixed basket for a Turkish student living in a shared flat in Turin, priced at **2025 average
prices**. Each component is moved over time with the Italian HICP index of its category (2025 = 100), so the
2025 average of the budget equals the base total.

| Component | Base (EUR / month, 2025) | Weight | Indexed with |
|---|---:|---:|---|
| Rent (single room, shared flat, utilities included) | 450 | 54.5 % | HICP `CP041` actual rentals for housing |
| Food (groceries, occasional canteen meal; midpoint of 250-300) | 275 | 33.3 % | HICP `CP01` food and non-alcoholic beverages |
| Transport (free for students under 26 with the Piemove regional pass) | 0 | 0.0 % | HICP `CP0732` passenger transport by road |
| Other (phone, personal care, clothing, study material, leisure) | 100 | 12.1 % | HICP all items |
| **Total** | **825** | **100 %** | |

The base amounts are the author's assumptions from student consulting work, not an official statistic. They live
in [`dbt/seeds/basket_components.csv`](dbt/seeds/basket_components.csv) and can be changed without touching SQL.
Transport is kept as a zero-amount component so that a student aged 26 or over only needs a new base amount
(for example a monthly pass) instead of a model change.

## Data model

```mermaid
flowchart LR
    subgraph Sources
        ECB["ECB Data Portal<br/>EXR.D.TRY.EUR.SP00.A"]
        ESTAT["Eurostat<br/>prc_hicp_minr"]
        ISTAT["Istat SDMX<br/>NIC 167_745"]
    end
    subgraph raw["Raw layer: data/raw/*.parquet"]
        R1[(ecb_exr_try_eur)]
        R2[(eurostat_hicp)]
        R3[(istat_nic)]
    end
    subgraph staging["dbt staging"]
        S1[stg_ecb__exr_try_eur]
        S2[stg_eurostat__hicp]
        S3[stg_istat__nic]
    end
    subgraph marts["dbt marts"]
        FX[fx_daily]
        CPI[cpi_monthly]
        BUD[student_budget_monthly]
        PP[try_purchasing_power]
    end
    SEED[/"seeds: basket_components,<br/>coicop_labels"/]

    ECB -- src/fetch_ecb.py --> R1 --> S1 --> FX
    ESTAT -- src/fetch_eurostat.py --> R2 --> S2 --> CPI
    ISTAT -- src/fetch_istat.py --> R3 --> S3 --> CPI
    SEED --> CPI
    SEED --> BUD
    FX --> BUD
    CPI --> BUD
    CPI --> PP
    BUD --> PP
```

| Mart | Grain | What it answers |
|---|---|---|
| `fx_daily` | ECB business day | EUR/TRY, euros per 1,000 lira, change over 1, 30 and 365 days |
| `cpi_monthly` | source × country × category × month | Price indices (2025=100) and monthly / annual rates for Italy and Turkey |
| `student_budget_monthly` | month | The basket in EUR by component, converted to TRY at the month's average rate, with year-on-year changes |
| `try_purchasing_power` | month | Inflation-adjusted EUR/TRY (2025=100) and the budget in constant 2025 lira |

**Definitions.**
- `real_eur_try_index_2025` = (EUR/TRY ÷ 2025 average) × (Italian HICP ÷ Turkish HICP) × 100. Above 100 means
  the lira lost more value against the euro than Turkish prices rose since 2025, so Italy became more expensive
  for lira earners.
- `budget_try_at_2025_prices` = budget in TRY ÷ (Turkish HICP / 100), the budget in 2025 lira.

## Data tests

`dbt build` runs 59 tests on every model and seed:

- **Keys and grain:** `not_null` / `unique` on dates, and a custom `unique_combination_of_columns` test on the
  long CPI tables.
- **Accepted ranges:** a custom `accepted_range` test (EUR/TRY between 1 and 500, daily moves within ±30 %,
  annual inflation between −50 % and 200 %, budget between 300 and 3,000 EUR, ...).
- **Referential integrity:** every category in `cpi_monthly` and in the basket has a label.
- **Business rules:** the EUR total equals the sum of its components; the 2025 average of the budget equals the
  base total (checks the 2025=100 indexation).
- **Cross-source check (warn):** Istat NIC and Eurostat HICP annual rates for Italian rents differ by at most
  0.5 percentage points.
- **Source freshness:** `dbt source freshness` warns when a raw file was not refreshed for 8 days.

## How to run

Requires [uv](https://docs.astral.sh/uv/) (Python 3.12 is installed automatically).

```bash
uv sync
uv run python src/fetch_all.py        # incremental fetch of all three sources into data/raw/
cd dbt
uv run dbt build                      # seeds, models and tests into data/warehouse.duckdb
uv run dbt source freshness
uv run dbt docs generate && uv run dbt docs serve   # optional: lineage graph and column docs
cd ..
uv run python src/export_marts.py     # marts to data/marts/*.parquet
uv run python src/update_readme.py    # rewrite the "Latest numbers" block from the marts
```

Run dbt from the `dbt/` folder: the profile and the raw Parquet paths are relative to it.

**Incremental fetch.** The first run downloads the full history. Later runs only request a recent window and
upsert it on the series key: the last 7 days for the ECB rate, the last 13 months for Eurostat and Istat
(statistical offices revise recent months). `--full` re-downloads everything.

The raw Parquet files are public statistics and are committed, so `dbt build` works on a fresh clone without
network access. The DuckDB warehouse is rebuilt by dbt and is not committed; the marts are exported to
`data/marts/` instead.

## Automation

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | every push and pull request | guardrail unit tests, `dbt build` on the committed raw data, then checks that the README numbers match the marts |
| [`refresh.yml`](.github/workflows/refresh.yml) | Mondays 06:00 UTC, or manually | fetch all sources → `dbt build` → `dbt source freshness` → export marts → regenerate the README block → write the weekly brief → commit `data/`, `reports/` and `README.md` to `main` |

The refresh job is built to fail loudly but degrade gracefully: if one source cannot be reached, the other
sources are still refreshed and committed, and the job is marked as failed at the end. A failing data test stops
the job before anything is committed, so `main` only ever holds data that passed every test. The latest numbers
are also written to the run's summary page.

## Weekly brief

Every week the refresh job asks Claude (`claude-opus-5-5`) for a short plain-English brief for Turkish students
and their families: the budget in euros and lira, this week's exchange rate, and what it means in real terms.
Latest: [`reports/latest_brief.md`](reports/latest_brief.md); archive: [`reports/briefs/`](reports/briefs/).

```mermaid
flowchart LR
    M[(data/marts)] --> F["brief_facts.py<br/>fact sheet (JSON)"]
    F --> C["Claude API<br/>structured output:<br/>headline, paragraphs,<br/>cited numbers"]
    C --> G{"guardrail.py<br/>every number<br/>in the facts?"}
    G -- yes --> P["reports/briefs/&lt;date&gt;.md<br/>+ &lt;date&gt;.facts.json"]
    G -- "no (once)" --> R["violations sent back<br/>for a correction"] --> C
    G -- "no (again)" --> X["not published,<br/>job marked failed"]
```

**Guardrail: every number in the brief must exist in the input tables.**
- The model only sees a fact sheet built from the marts ([`src/brief_facts.py`](src/brief_facts.py)): about 35
  facts with an id, value, unit and description. The exact fact sheet is saved next to each brief.
- The answer is structured output (JSON schema): a headline, 2-3 paragraphs and `cited_numbers`, where each
  number written is listed with the id of the fact it comes from (the id is constrained to the fact sheet's ids).
- [`src/guardrail.py`](src/guardrail.py) then checks the final text, not the model's claims: every number in the
  text must match a fact up to the rounding implied by the decimals written (`854` for 853.95, `18.9` for 18.88),
  must be listed in `cited_numbers`, and every citation must match the fact it names. Derived numbers that are
  not in the fact sheet (a difference, a sum) are rejected.
- On failure the violations are sent back once for a correction. A brief that still fails is not written and
  the job is marked as failed, so a wrong number never reaches `main`.
- The guardrail is covered by unit tests ([`tests/test_guardrail.py`](tests/test_guardrail.py)) that run in CI.

The check covers numbers, not wording: a sentence with a correct number and the wrong direction ("rose" instead
of "fell") would pass. The prompt also tells the model to describe the data only, without financial advice or
exchange-rate forecasts.

**Setup and cost.** Add an `ANTHROPIC_API_KEY` repository secret (Settings → Secrets and variables → Actions).
Without it the brief step is skipped and the rest of the pipeline runs as before. One brief is a few thousand
tokens, roughly USD 0.05 per week at Claude Opus 5.5 prices. Locally: `uv run python src/write_brief.py`
(or `--dry-run` to print the prompt and the fact sheet without calling the API).

## Project layout

```
src/
  raw_store.py          HTTP with retries, Parquet upsert helper
  fetch_ecb.py          ECB daily EUR/TRY
  fetch_eurostat.py     Eurostat HICP (prc_hicp_minr), IT and TR
  fetch_istat.py        Istat NIC detail for Italy
  fetch_all.py          runs the three fetchers
  export_marts.py       marts to data/marts/*.parquet
  update_readme.py      "Latest numbers" block of this README, generated from the marts
  brief_facts.py        fact sheet for the weekly brief, built from data/marts
  write_brief.py        weekly brief with the Claude API (structured output, one correction round)
  guardrail.py          checks that every number in the brief comes from the fact sheet
data/raw/               Parquet snapshots (one file per source)
data/marts/             exported marts, refreshed weekly
reports/                weekly briefs and the fact sheets they were written from
tests/                  unit tests for the guardrail
.github/workflows/      CI and weekly refresh
dbt/
  models/staging/       one model per source, typed and pivoted
  models/marts/         fx_daily, cpi_monthly, student_budget_monthly, try_purchasing_power
  seeds/                reference basket and category labels
  tests/                custom generic tests and singular business-rule tests
```

## Roadmap

- [x] **W1-W2: sources and model.** Fetchers for ECB, Eurostat and Istat, Parquet raw layer, dbt staging and
  marts, 59 data tests.
- [x] **W3: scheduled pipeline.** Weekly GitHub Actions refresh that commits tested data back to `main`, CI on
  every push, README numbers generated from the marts (see [Automation](#automation)).
- [x] **W4: LLM weekly brief.** Claude API brief with structured output and a numeric guardrail (see
  [Weekly brief](#weekly-brief)).
- [ ] **W5: dashboard.** TODO: Streamlit app on the marts: budget in EUR and TRY over time, component breakdown,
  real EUR/TRY index, and an editable basket.

## Limitations

- The basket amounts are assumptions for one city (Turin) and one lifestyle; the indices are national, so local
  rent dynamics in Turin can differ from the Italian average.
- HICP rents (`CP041`) follow existing tenancies, which move more slowly than asking rents for new contracts,
  which is what an arriving student faces.
- `try_purchasing_power` assumes the household's lira income grows with Turkish inflation; real wage changes are
  not modelled.
- Istat NIC detail on base 2025 starts in January 2026, so it is used for detail and cross-checks, not for history.
