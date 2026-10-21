-- The base amounts are defined at 2025 average prices and the indices are 2025=100,
-- so the 2025 average of the EUR budget must equal the sum of the base amounts (tolerance 1 EUR).
with avg_2025 as (
    select avg(total_eur) as total_eur_2025
    from {{ ref('student_budget_monthly') }}
    where year(month) = 2025
),

base as (
    select sum(base_amount_eur) as base_total from {{ ref('basket_components') }}
)

select *
from avg_2025 cross join base
where abs(total_eur_2025 - base_total) > 1
