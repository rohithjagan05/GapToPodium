-- The gold mark must be at least as good as the bronze threshold in every championship and event.
select *
from {{ ref('mart_podium_threshold') }}
where (higher_is_better and gold_mark < bronze_mark)
    or (not higher_is_better and gold_mark > bronze_mark)