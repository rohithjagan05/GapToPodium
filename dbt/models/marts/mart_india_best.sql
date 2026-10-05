-- India's best current mark per event: each athlete's best outdoor, legal mark over the most recent
-- seasons in the data (var india_recent_seasons), then the best athlete per event by ROW_NUMBER().
with marks as (
    select *
    from {{ ref('stg_wa_marks') }}
    where kind in ('season_progression', 'season_best')
        and not indoor
        and not not_legal
        and mark_value is not null
),

recent as (
    select *
    from marks
    where season > (select max(season) from marks) - {{ var('india_recent_seasons') }}
),

athlete_best as (
    select
        wa_id, event_key, discipline, sex, discipline_group, higher_is_better,
        array_agg(
            struct(mark_value, mark_raw, mark_date, season)
            order by if(higher_is_better, -mark_value, mark_value), mark_date
            limit 1
        )[offset(0)] as best
    from recent
    group by 1, 2, 3, 4, 5, 6
),

ranked as (
    select
        b.*,
        a.athlete_name,
        row_number() over (
            partition by b.event_key
            order by if(b.higher_is_better, -b.best.mark_value, b.best.mark_value), b.best.mark_date
        ) as rank_in_event,
        count(*) over (partition by b.event_key) as athletes_in_window
    from athlete_best as b
    inner join {{ ref('stg_wa_athletes') }} as a using (wa_id)
)

select
    event_key, discipline, sex, discipline_group, higher_is_better,
    wa_id as best_wa_id,
    athlete_name as best_athlete,
    best.mark_value as best_mark,
    best.mark_raw as best_mark_raw,
    best.mark_date,
    best.season as best_season,
    athletes_in_window
from ranked
where rank_in_event = 1