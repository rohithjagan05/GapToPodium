-- One row per event on the latest Olympic programme: the bronze threshold (average of the last 3
-- Olympic thresholds), India's best current mark, and the gap between them in percent, signed so a
-- positive gap means India is behind and a smaller gap is always better. Podium depth counts the
-- countries that medalled in the event at the last 5 Games.
with olympic_thresholds as (
    select *
    from {{ ref('mart_podium_threshold') }}
    where championship_type = 'olympics'
),

programme as (
    select *
    from olympic_thresholds
    where championship_year = (select max(championship_year) from olympic_thresholds)
),

depth as (
    select event_key, count(distinct country_code) as podium_depth
    from {{ ref('stg_olympic_results') }}
    where medal is not null
        and championship_year > (select max(championship_year) from {{ ref('stg_olympic_results') }}) - 20
    group by 1
),

joined as (
    select
        p.event_key, p.discipline, p.sex, p.discipline_group, p.higher_is_better,
        p.bronze_rolling_3 as bronze_threshold,
        p.championships_in_rolling_3,
        p.bronze_mark as latest_bronze_mark,
        i.best_mark as india_best_mark,
        i.best_mark_raw as india_best_mark_raw,
        i.best_athlete as india_best_athlete,
        i.mark_date as india_mark_date,
        i.best_world_rank as india_world_rank,
        i.best_season as india_rank_season,
        -- championship finals in these events are tactical or weather-affected, so their marks
        -- understate medal pace; read gaps here alongside india_world_rank
        p.discipline_group in ('middle_distance', 'long_distance', 'road') as tactical_event,
        coalesce(d.podium_depth, 0) as podium_depth,
        round(100 * case
            when i.best_mark is null then null
            when p.higher_is_better then (p.bronze_rolling_3 - i.best_mark) / p.bronze_rolling_3
            else (i.best_mark - p.bronze_rolling_3) / p.bronze_rolling_3
        end, 2) as gap_pct
    from programme as p
    left join {{ ref('mart_india_best') }} as i using (event_key)
    left join depth as d using (event_key)
)

select
    *,
    if(gap_pct is null, null, rank() over (partition by gap_pct is null order by gap_pct)) as gap_rank
from joined