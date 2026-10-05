-- Grain check: one row per championship type, year and event in mart_podium_threshold.
select championship_type, championship_year, event_key, count(*) as n
from {{ ref('mart_podium_threshold') }}
group by 1, 2, 3
having count(*) > 1