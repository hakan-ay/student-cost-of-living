-- One row per ECB business day. Days without a published rate (holidays) are dropped.
select
    cast(period as date)                     as rate_date,
    try_cast(obs_value as double)            as eur_try,
    obs_status,
    cast(fetched_at as timestamptz)          as fetched_at
from {{ source('raw', 'ecb_exr_try_eur') }}
where try_cast(obs_value as double) is not null
