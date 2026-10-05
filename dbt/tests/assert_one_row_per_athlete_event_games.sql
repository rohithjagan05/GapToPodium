-- Grain check: an athlete appears at most once per event per Games (rows without an Olympedia
-- athlete ID are not compared). Any row returned here is a duplicate, and the test fails.
select championship_year, event_key, olympedia_athlete_id, count(*) as n
from {{ ref('stg_olympic_results') }}
where olympedia_athlete_id is not null
group by 1, 2, 3
having count(*) > 1