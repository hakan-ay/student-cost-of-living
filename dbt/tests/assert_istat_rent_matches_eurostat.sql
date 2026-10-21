-- Cross-source check: Istat NIC and Eurostat HICP measure Italian rents from the same survey, so their annual
-- rates for actual rentals (CP041) should not differ by more than 0.5 percentage points.
{{ config(severity = 'warn') }}

select n.month, n.annual_rate_pct as istat_rate, h.annual_rate_pct as eurostat_rate
from {{ ref('cpi_monthly') }} as n
join {{ ref('cpi_monthly') }} as h
    on h.month = n.month and h.geo = n.geo and h.coicop = n.coicop and h.source = 'eurostat_hicp'
where n.source = 'istat_nic' and n.coicop = 'CP041'
  and abs(n.annual_rate_pct - h.annual_rate_pct) > 0.5
