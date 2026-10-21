-- Monthly cost of the reference student basket in Italy, in EUR and TRY.
-- Each component's 2025 base amount (seed basket_components) is moved with its Italian HICP index (2025=100);
-- the EUR total is converted with the month's average ECB EUR/TRY rate.
-- Only months where every component and the exchange rate are published are kept.
with basket as (
    select
        component,
        coicop,
        base_amount_eur,
        base_amount_eur / sum(base_amount_eur) over () as weight
    from {{ ref('basket_components') }}
),

component_cost as (
    select
        c.month,
        b.component,
        b.base_amount_eur * c.index_2025 / 100 as cost_eur
    from basket as b
    join {{ ref('cpi_monthly') }} as c
        on c.source = 'eurostat_hicp' and c.geo = 'IT' and c.coicop = b.coicop
),

budget_eur as (
    select
        month,
        sum(cost_eur) filter (where component = 'rent')      as rent_eur,
        sum(cost_eur) filter (where component = 'food')      as food_eur,
        sum(cost_eur) filter (where component = 'transport') as transport_eur,
        sum(cost_eur) filter (where component = 'other')     as other_eur,
        sum(cost_eur)                                        as total_eur
    from component_cost
    group by month
    having count(*) = (select count(*) from basket)
),

fx_month as (
    select date_trunc('month', rate_date) as month, avg(eur_try) as eur_try_avg, count(*) as fx_days
    from {{ ref('fx_daily') }}
    group by 1
),

joined as (
    select b.*, f.eur_try_avg, f.fx_days, b.total_eur * f.eur_try_avg as total_try
    from budget_eur as b
    join fx_month as f using (month)
)

select
    cur.month,
    round(cur.rent_eur, 2)                                             as rent_eur,
    round(cur.food_eur, 2)                                             as food_eur,
    round(cur.transport_eur, 2)                                        as transport_eur,
    round(cur.other_eur, 2)                                            as other_eur,
    round(cur.total_eur, 2)                                            as total_eur,
    round(cur.eur_try_avg, 4)                                          as eur_try_avg,
    cur.fx_days,
    round(cur.total_try, 0)                                            as total_try,
    round(100 * (cur.total_eur / prev.total_eur - 1), 2)               as total_eur_yoy_pct,
    round(100 * (cur.eur_try_avg / prev.eur_try_avg - 1), 2)           as eur_try_yoy_pct,
    round(100 * (cur.total_try / prev.total_try - 1), 2)               as total_try_yoy_pct
from joined as cur
left join joined as prev on prev.month = cur.month - interval 12 month
order by cur.month
