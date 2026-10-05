-- One row per athlete per individual event per Olympic Games, with typed, renamed fields and
-- the event's discipline, sex and direction. Marks were converted by src/marks.py at load time.
with results as (
    select * from {{ source('raw', 'raw_olympedia_results') }}
),

disciplines as (
    select * from {{ source('raw', 'raw_disciplines') }}
)

select
    'olympics' as championship_type,
    r.edition_year as championship_year,
    r.event_key,
    regexp_replace(r.event_key, r'_[mwx]$', '') as discipline,
    regexp_extract(r.event_key, r'_([mwx])$') as sex,
    d.discipline_group,
    d.higher_is_better,
    r.result_id,
    r.olympedia_athlete_id,
    trim(r.athlete_name) as athlete_name,
    upper(trim(r.noc)) as country_code,
    r.position,
    r.position_raw,
    r.medal,
    r.round_reached,
    r.mark_raw,
    r.mark_value,
    r.scraped_at
from results as r
left join disciplines as d
    on d.discipline = regexp_replace(r.event_key, r'_[mwx]$', '')