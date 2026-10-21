-- Daily EUR/TRY with day, 30-day and 365-day changes. The 30/365-day comparison uses the latest ECB business day
-- on or before the calendar date 30/365 days earlier (ASOF join), so weekends and holidays do not leave gaps.
with fx as (
    select
        rate_date,
        eur_try,
        rate_date - interval 30 day  as date_30d_ago,
        rate_date - interval 365 day as date_365d_ago
    from {{ ref('stg_ecb__exr_try_eur') }}
),

with_30d as (
    select fx.*, p.eur_try as eur_try_30d_ago
    from fx
    asof left join fx as p on fx.date_30d_ago >= p.rate_date
),

with_365d as (
    select f.*, p.eur_try as eur_try_365d_ago
    from with_30d as f
    asof left join fx as p on f.date_365d_ago >= p.rate_date
)

select
    rate_date,
    eur_try,
    round(1000 / eur_try, 4)                                                         as eur_per_1000_try,
    round(100 * (eur_try / lag(eur_try) over (order by rate_date) - 1), 4)           as change_1d_pct,
    round(100 * (eur_try / eur_try_30d_ago - 1), 4)                                  as change_30d_pct,
    round(100 * (eur_try / eur_try_365d_ago - 1), 4)                                 as change_365d_pct,
    rate_date = max(rate_date) over ()                                               as is_latest
from with_365d
order by rate_date
