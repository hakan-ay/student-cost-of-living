-- The EUR total must equal the sum of its components (rounding tolerance of 5 cents).
select *
from {{ ref('student_budget_monthly') }}
where abs(total_eur - (rent_eur + food_eur + transport_eur + other_eur)) > 0.05
