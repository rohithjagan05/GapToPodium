-- A gap beyond these bounds would point to a unit or direction error, not a real gap: no Indian
-- best is 60% better than the bronze threshold, and none is more than 100% behind it.
select event_key, gap_pct, india_best_mark, bronze_threshold
from {{ ref('mart_gap_to_podium') }}
where gap_pct < -60 or gap_pct > 100