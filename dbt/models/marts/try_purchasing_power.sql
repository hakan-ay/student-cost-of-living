-- How the Italian student budget looks to a family that earns and saves in Turkish lira.
--   real_eur_try_index_2025: EUR/TRY corrected for the inflation gap between Italy and Turkey, 2025 = 100.
--     Above 100: since 2025, the lira lost more value against the euro than Turkish prices rose
--     (Italy became more expensive for TRY earners). Below 100: the opposite.
--   budget_try_at_2025_prices: the monthly budget in TRY deflated by Turkish HICP, i.e. in 2025 lira.
--     If this rises, the budget costs a Turkish household more in real terms.
with hicp as (
    select
        month,
        max(index_2025)      filter (where geo = 'TR') as tr_hicp_index_2025,
        max(index_2025)      filter (where geo = 'IT') as it_hicp_index_2025,
        max(annual_rate_pct) filter (where geo = 'TR') as tr_inflation_yoy_pct,
        max(annual_rate_pct) filter (where geo = 'IT') as it_inflation_yoy_pct
    from {{ ref('cpi_monthly') }}
    where source = 'eurostat_hicp' and coicop = 'TOTAL'
    group by month
),

budget as (
    select month, total_eur, total_try, eur_try_avg, eur_try_yoy_pct
    from {{ ref('student_budget_monthly') }}
),

fx_2025 as (
    select avg(eur_try_avg) as eur_try_avg_2025
    from budget
    where year(month) = 2025
),

joined as (
    select
        b.month,
        b.eur_try_avg,
        b.eur_try_yoy_pct,
        h.tr_inflation_yoy_pct,
        h.it_inflation_yoy_pct,
        h.tr_hicp_index_2025,
        h.it_hicp_index_2025,
        100 * (b.eur_try_avg / f.eur_try_avg_2025) * h.it_hicp_index_2025 / h.tr_hicp_index_2025 as real_eur_try_index_2025,
        b.total_try,
        b.total_try / (h.tr_hicp_index_2025 / 100)                                               as budget_try_at_2025_prices
    from budget as b
    join hicp as h using (month)
    cross join fx_2025 as f
)

select
    cur.month,
    round(cur.eur_try_avg, 4)                                                          as eur_try_avg,
    cur.eur_try_yoy_pct,
    cur.tr_inflation_yoy_pct,
    cur.it_inflation_yoy_pct,
    cur.tr_hicp_index_2025,
    cur.it_hicp_index_2025,
    round(cur.real_eur_try_index_2025, 2)                                              as real_eur_try_index_2025,
    cur.total_try                                                                      as budget_try,
    round(cur.budget_try_at_2025_prices, 0)                                            as budget_try_at_2025_prices,
    round(100 * (cur.budget_try_at_2025_prices / prev.budget_try_at_2025_prices - 1), 2) as budget_real_try_yoy_pct
from joined as cur
left join joined as prev on prev.month = cur.month - interval 12 month
order by cur.month
