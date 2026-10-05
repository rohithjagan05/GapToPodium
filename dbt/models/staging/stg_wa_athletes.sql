-- One row per verified Indian athlete, named as on their World Athletics profile.
select
    wa_id,
    trim(profile_name) as athlete_name,
    trim(seed_name) as seed_name,
    sex,
    birth_date,
    country_code
from {{ source('raw', 'raw_wa_athletes') }}