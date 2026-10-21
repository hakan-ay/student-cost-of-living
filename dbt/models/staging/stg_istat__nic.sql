-- One row per month and ECOICOP category. Istat codes are mapped to the Eurostat style ('00' -> 'TOTAL', '041' -> 'CP041').
select
    cast(period || '-01' as date)                                                       as month,
    geo,
    case when ecoicop = '00' then 'TOTAL' else 'CP' || ecoicop end                      as coicop,
    max(case when measure = '4' then try_cast(obs_value as double) end)                 as index_2025,
    max(case when measure = '6' then try_cast(obs_value as double) end)                 as monthly_rate_pct,
    max(case when measure = '7' then try_cast(obs_value as double) end)                 as annual_rate_pct,
    max(cast(fetched_at as timestamptz))                                                as fetched_at
from {{ source('raw', 'istat_nic') }}
group by all
having max(case when measure = '4' then try_cast(obs_value as double) end) is not null
