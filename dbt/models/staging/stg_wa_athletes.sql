-- One row per verified Indian athlete, named as on their World Athletics profile.
select
    wa_id,
        -- single-name athletes have "." as their given name on World Athletics (". SEEMA")
    regexp_replace(trim(profile_name), r'^\.\s*', '') as athlete_name,
    trim(seed_name) as seed_name,
    sex,
    birth_date,
    country_code
from {{ source('raw', 'raw_wa_athletes') }}