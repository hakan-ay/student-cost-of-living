"""Builds the fact sheet the weekly brief is written from, using the exported marts in data/marts/.

Every fact has an id, a value (a number or a short text such as a month name), a unit and a description.
The brief may only contain numbers that appear in this fact sheet; see guardrail.py.

Usage:
    uv run python src/brief_facts.py            # print the fact sheet as JSON
"""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"


def _row(con: duckdb.DuckDBPyConnection, sql: str) -> dict:
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return dict(zip(names, cur.fetchone()))


def build_facts() -> list[dict]:
    con = duckdb.connect()
    for name in ("fx_daily", "cpi_monthly", "student_budget_monthly", "try_purchasing_power"):
        con.execute(f"create view {name} as select * from read_parquet('{MARTS / name}.parquet')")

    fx = _row(con, """
        with latest as (select * from fx_daily where is_latest),
             week_ago as (
                 select f.eur_try from fx_daily as f, latest as l
                 where f.rate_date <= l.rate_date - interval 7 day
                 order by f.rate_date desc limit 1)
        select l.rate_date, l.eur_try, l.eur_per_1000_try, l.change_30d_pct, l.change_365d_pct,
               w.eur_try as eur_try_week_ago, 100 * (l.eur_try / w.eur_try - 1) as change_7d_pct
        from latest as l, week_ago as w
    """)
    cur = _row(con, """
        select b.*, p.real_eur_try_index_2025, p.budget_try_at_2025_prices, p.budget_real_try_yoy_pct,
               p.tr_inflation_yoy_pct, p.it_inflation_yoy_pct
        from student_budget_monthly as b join try_purchasing_power as p using (month)
        order by month desc limit 1
    """)
    prev = _row(con, f"""
        select b.*, p.budget_try_at_2025_prices
        from student_budget_monthly as b join try_purchasing_power as p using (month)
        where month = date '{cur['month']}' - interval 12 month
    """)
    it_rates = dict(con.execute(f"""
        select coicop, annual_rate_pct from cpi_monthly
        where source = 'eurostat_hicp' and geo = 'IT' and month = date '{cur['month']}'
    """).fetchall())

    def fact(fact_id: str, value, unit: str, description: str) -> dict:
        if isinstance(value, float):
            value = round(value, 2)
        return {"id": fact_id, "value": value, "unit": unit, "description": description}

    month, prev_month = f"{cur['month']:%B %Y}", f"{prev['month']:%B %Y}"
    facts = [
        fact("budget_month", month, "month", "Latest month with published consumer prices"),
        fact("budget_month_prev_year", prev_month, "month", "Same month one year earlier"),
        fact("fx_latest_date", f"{fx['rate_date']:%-d %B %Y}", "date", "Date of the latest ECB EUR/TRY rate"),
        fact("price_base_year", 2025, "year", "Base year of all price indices and of the basket amounts"),
        fact("index_base_value", 100, "index", "Value of every price index in its base year"),
        fact("budget_eur", cur["total_eur"], "EUR", f"Monthly student budget in Italy, {month}"),
        fact("budget_eur_prev_year", prev["total_eur"], "EUR", f"Monthly student budget in Italy, {prev_month}"),
        fact("budget_eur_yoy_pct", cur["total_eur_yoy_pct"], "%", "Change of the EUR budget over a year"),
        fact("rent_eur", cur["rent_eur"], "EUR", f"Rent component of the budget, {month}"),
        fact("food_eur", cur["food_eur"], "EUR", f"Food component of the budget, {month}"),
        fact("transport_eur", cur["transport_eur"], "EUR",
             "Transport component (free local transport for students under 26 in Piedmont)"),
        fact("free_transport_age_limit", 26, "years", "Students below this age travel free on local transport in Piedmont"),
        fact("other_eur", cur["other_eur"], "EUR", f"Other spending component of the budget, {month}"),
        fact("it_rent_inflation_yoy_pct", it_rates.get("CP041"), "%", "Italian rents, annual change (HICP CP041)"),
        fact("it_food_inflation_yoy_pct", it_rates.get("CP01"), "%", "Italian food prices, annual change (HICP CP01)"),
        fact("it_inflation_yoy_pct", cur["it_inflation_yoy_pct"], "%", "Italian consumer prices, annual change (HICP)"),
        fact("tr_inflation_yoy_pct", cur["tr_inflation_yoy_pct"], "%", "Turkish consumer prices, annual change (HICP)"),
        fact("eur_try_month_avg", cur["eur_try_avg"], "TRY per EUR", f"Average ECB EUR/TRY rate in {month}"),
        fact("eur_try_month_avg_prev_year", prev["eur_try_avg"], "TRY per EUR",
             f"Average ECB EUR/TRY rate in {prev_month}"),
        fact("eur_try_month_avg_yoy_pct", cur["eur_try_yoy_pct"], "%", "Change of the monthly average EUR/TRY over a year"),
        fact("budget_try", cur["total_try"], "TRY", f"Monthly student budget converted to lira, {month}"),
        fact("budget_try_prev_year", prev["total_try"], "TRY", f"Monthly student budget converted to lira, {prev_month}"),
        fact("budget_try_yoy_pct", cur["total_try_yoy_pct"], "%", "Change of the lira budget over a year"),
        fact("budget_try_at_2025_prices", cur["budget_try_at_2025_prices"], "TRY (2025 prices)",
             f"Lira budget deflated by Turkish HICP, {month}"),
        fact("budget_try_at_2025_prices_prev_year", prev["budget_try_at_2025_prices"], "TRY (2025 prices)",
             f"Lira budget deflated by Turkish HICP, {prev_month}"),
        fact("budget_real_try_yoy_pct", cur["budget_real_try_yoy_pct"], "%",
             "Change of the inflation-adjusted lira budget over a year (negative = cheaper in real terms)"),
        fact("real_eur_try_index", cur["real_eur_try_index_2025"], "index (2025 = 100)",
             "EUR/TRY corrected for the Italy-Turkey inflation gap; above 100 = Italy dearer for lira earners than in 2025"),
        fact("eur_try_latest", fx["eur_try"], "TRY per EUR", "Latest ECB EUR/TRY reference rate"),
        fact("eur_try_week_ago", fx["eur_try_week_ago"], "TRY per EUR", "ECB EUR/TRY rate about one week before the latest"),
        fact("eur_try_change_7d_pct", fx["change_7d_pct"], "%", "Change of EUR/TRY over the last week"),
        fact("eur_try_change_30d_pct", fx["change_30d_pct"], "%", "Change of EUR/TRY over the last 30 days"),
        fact("eur_try_change_365d_pct", fx["change_365d_pct"], "%", "Change of EUR/TRY over the last 365 days"),
        fact("days_in_30d_window", 30, "days", "Length of the 30-day exchange-rate window"),
        fact("days_in_365d_window", 365, "days", "Length of the 365-day exchange-rate window"),
        fact("eur_per_1000_try", fx["eur_per_1000_try"], "EUR", "Euros bought with 1,000 lira at the latest rate"),
        fact("try_amount_1000", 1000, "TRY", "Reference amount of lira for eur_per_1000_try"),
    ]
    return [f for f in facts if f["value"] is not None]


if __name__ == "__main__":
    print(json.dumps(build_facts(), indent=1, ensure_ascii=False))
