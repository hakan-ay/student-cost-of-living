-- Monthly consumer prices in one long table: Eurostat HICP (Italy and Turkey) and Istat NIC detail (Italy).
-- Grain: source, geo, coicop, month. All indices are on base 2025=100, so Italy and Turkey are comparable as growth.
with hicp as (
    select
        'eurostat_hicp'                                                                         as source,
        month, geo, coicop, index_2025, annual_rate_pct,
        100 * (index_2025 / lag(index_2025) over (partition by geo, coicop order by month) - 1) as monthly_rate_pct
    from {{ ref('stg_eurostat__hicp') }}
),

nic as (
    select 'istat_nic' as source, month, geo, coicop, index_2025, annual_rate_pct, monthly_rate_pct
    from {{ ref('stg_istat__nic') }}
)

select
    u.source,
    u.geo,
    u.coicop,
    l.label                         as coicop_label,
    u.month,
    u.index_2025,
    round(u.monthly_rate_pct, 2)    as monthly_rate_pct,
    u.annual_rate_pct
from (select * from hicp union all select * from nic) as u
left join {{ ref('coicop_labels') }} as l using (coicop)
order by source, geo, coicop, month
