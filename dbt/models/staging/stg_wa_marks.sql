-- Indian athletes' marks in senior Olympic disciplines: personal bests, current season bests and
-- the best mark of every season. An equalled personal best appears twice on World Athletics (same
-- mark, two dates); only the earliest row is kept.
with marks as (
    select * from {{ source('raw', 'raw_wa_marks') }}
),

disciplines as (
    select * from {{ source('raw', 'raw_disciplines') }}
)

select
    m.wa_id,
    m.event_key,
    regexp_replace(m.event_key, r'_[mwx]$', '') as discipline,
    regexp_extract(m.event_key, r'_([mwx])$') as sex,
    d.discipline_group,
    d.higher_is_better,
    m.kind,
    m.season,
    m.mark_raw,
    m.mark_value,
    m.date as mark_date,
    m.venue,
    m.competition,
    m.wind,
    m.indoor,
    m.not_legal,
    m.list_position
from marks as m
left join disciplines as d
    on d.discipline = regexp_replace(m.event_key, r'_[mwx]$', '')
where true  -- BigQuery's QUALIFY needs a WHERE, GROUP BY or HAVING clause alongside it
qualify row_number() over (
        -- FLOAT64 can't be a partition key; marks are rounded to 3 decimals, so thousandths are exact
    partition by m.wa_id, m.event_key, m.kind, m.season, m.indoor, m.not_legal,
        cast(round(m.mark_value * 1000) as int64)
    order by m.date
) = 1