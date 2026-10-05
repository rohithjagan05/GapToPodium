-- FR-9: the gap mart has exactly one row for every individual event at the latest Olympic Games.
with expected as (
    select count(distinct event_key) as n
    from {{ ref('stg_olympic_results') }}
    where championship_year = (select max(championship_year) from {{ ref('stg_olympic_results') }})
),

actual as (
    select count(*) as n from {{ ref('mart_gap_to_podium') }}
)

select expected.n as expected_rows, actual.n as actual_rows
from expected cross join actual
where expected.n != actual.n