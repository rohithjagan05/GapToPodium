-- Grain check: one row per athlete per event and season in the world toplists.
select season, event_key, wa_id, count(*) as n
from {{ ref('stg_wa_toplists') }}
group by 1, 2, 3
having count(*) > 1