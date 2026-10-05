-- What it took to medal, per championship and event: the gold and silver marks and the bronze
-- threshold (the third-best podium mark, not the bronze-medal holder's, so ties, stripped medals,
-- vacant bronzes and appeal-shared bronzes are all handled), plus a rolling average of the last 3
-- thresholds. Olympics use positions 1-3; Worlds use medals.
with olympic_podium as (
    select
        championship_type, championship_year, event_key, discipline, sex,
        discipline_group, higher_is_better, position, mark_value
    from {{ ref('stg_olympic_results') }}
    where position between 1 and 3 and mark_value is not null
),

worlds_podium as (
    select
        championship_type, championship_year, event_key, discipline, sex,
        discipline_group, higher_is_better,
        case medal when 'Gold' then 1 when 'Silver' then 2 when 'Bronze' then 3 end as position,
        mark_value
    from {{ ref('stg_worlds_podium') }}
    where mark_value is not null
),

podium as (
    select * from olympic_podium
    union all
    select * from worlds_podium
),

per_championship as (
    select
        championship_type, championship_year, event_key, discipline, sex,
        discipline_group, higher_is_better,
        case when higher_is_better then max(if(position = 1, mark_value, null))
            else min(if(position = 1, mark_value, null)) end as gold_mark,
        case when higher_is_better then max(if(position = 2, mark_value, null))
            else min(if(position = 2, mark_value, null)) end as silver_mark,
        -- best three podium marks, best first; the third of them is the bronze threshold
        array_agg(mark_value order by if(higher_is_better, -mark_value, mark_value) limit 3)
            as best_three,
        case when higher_is_better then min(mark_value) else max(mark_value) end as worst_podium_mark,
        count(*) as podium_finishers
    from podium
    group by 1, 2, 3, 4, 5, 6, 7
),

thresholds as (
    select
        * except (best_three, worst_podium_mark),
        coalesce(best_three[safe_offset(2)], worst_podium_mark) as bronze_mark
    from per_championship
)

select
    *,
    avg(bronze_mark) over recent_three as bronze_rolling_3,
    count(*) over recent_three as championships_in_rolling_3
from thresholds
window recent_three as (
    partition by championship_type, event_key
    order by championship_year
    rows between 2 preceding and current row
)