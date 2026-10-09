-- The world's top 100 athletes per event and season (World Athletics outdoor toplists, one season
-- best per athlete), in the shared vocabulary. Marks were converted by src/marks.py at load time.
with toplists as (
    select * from {{ source('raw', 'raw_wa_toplists') }}
),

disciplines as (
    select * from {{ source('raw', 'raw_disciplines') }}
)

select
    t.season,
    t.event_key,
    regexp_replace(t.event_key, r'_[mwx]$', '') as discipline,
    regexp_extract(t.event_key, r'_([mwx])$') as sex,
    d.discipline_group,
    d.higher_is_better,
    t.rank as world_rank,
    t.wa_id,
    trim(t.athlete_name) as athlete_name,
    t.birth_date,
    upper(trim(t.country_code)) as country_code,
    t.place,
    t.venue,
    t.date as mark_date,
    t.mark_raw,
    t.mark_value,
    t.result_score,
    t.source_url
from toplists as t
left join disciplines as d
    on d.discipline = regexp_replace(t.event_key, r'_[mwx]$', '')