-- One row per World Championships medallist (2013-2025), in the same vocabulary as the
-- Olympic results. Countries are names; codes exist only on pages before 2019.
with podium as (
    select * from {{ source('raw', 'raw_worlds_podium') }}
),

disciplines as (
    select * from {{ source('raw', 'raw_disciplines') }}
)

select
    'worlds' as championship_type,
    p.championship_year,
    p.event_key,
    regexp_replace(p.event_key, r'_[mwx]$', '') as discipline,
    regexp_extract(p.event_key, r'_([mwx])$') as sex,
    d.discipline_group,
    d.higher_is_better,
    p.medal,
    trim(p.athlete_name) as athlete_name,
    trim(p.country_name) as country_name,
    p.country_code,
    p.mark_raw,
    p.mark_value,
    p.source_url,
    p.scraped_at
from podium as p
left join disciplines as d
    on d.discipline = regexp_replace(p.event_key, r'_[mwx]$', '')