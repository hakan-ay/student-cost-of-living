-- One row per month, country and ECOICOP category; the two units are pivoted into columns.
select
    cast(period || '-01' as date)                                            as month,
    geo,
    coicop,
    max(case when unit = 'I25'   then try_cast(obs_value as double) end)    as index_2025,
    max(case when unit = 'RCH_A' then try_cast(obs_value as double) end)    as annual_rate_pct,
    max(nullif(obs_flag, ''))                                                as obs_flag,
    max(cast(fetched_at as timestamptz))                                     as fetched_at
from {{ source('raw', 'eurostat_hicp') }}
group by all
having max(case when unit = 'I25' then try_cast(obs_value as double) end) is not null
