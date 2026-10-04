import pytest

from src.events import (
    DISCIPLINES,
    OLYMPEDIA_NAMES,
    WIKI_WORLDS_EXCLUDED,
    is_excluded,
    is_worlds_excluded,
    parse_event_name,
    parse_worlds_event_name,
)

# Every medal-event name seen on Olympedia's 2024 and 2000 athletics pages, both spellings.
REAL_NAMES = [
    "100 metres, Men", "200 metres, Men", "400 metres, Men", "800 metres, Men",
    "1,500 metres, Men", "5,000 metres, Men", "10,000 metres, Men", "Marathon, Men",
    "110 metres Hurdles, Men", "400 metres Hurdles, Men",
    "Steeplechase (3,000 metres), Men", "Steeplechase, Men",
    "4 × 100 metres Relay, Men", "4 × 400 metres Relay, Men",
    "20 kilometres Race Walk, Men", "50 kilometres Race Walk, Men",
    "High Jump, Men", "Long Jump, Men", "Pole Vault, Men", "Triple Jump, Men",
    "Shot Put, Men", "Discus Throw, Men", "Hammer Throw, Men", "Javelin Throw, Men",
    "Decathlon, Men",
    "100 metres, Women", "200 metres, Women", "400 metres, Women", "800 metres, Women",
    "1,500 metres, Women", "5,000 metres, Women", "10,000 metres, Women", "Marathon, Women",
    "100 / 80 metres Hurdles (100 m), Women", "100 / 80 metres Hurdles, Women",
    "400 metres Hurdles, Women", "Steeplechase (3,000 metres), Women",
    "4 × 100 metres Relay, Women", "4 × 400 metres Relay, Women",
    "20 kilometres Race Walk, Women",
    "High Jump, Women", "Pole Vault, Women", "Long Jump, Women", "Triple Jump, Women",
    "Shot Put, Women", "Discus Throw, Women", "Hammer Throw, Women", "Javelin Throw, Women",
    "Heptathlon, Women",
    "4 × 400 metres Relay, Mixed", "Marathon Race Walk Relay, Mixed",
]  # fmt: skip


def test_every_real_name_is_recognised():
    unknown = [name for name in REAL_NAMES if parse_event_name(name) is None]
    assert unknown == []


def test_real_names_give_49_distinct_events():
    keys = {parse_event_name(name).key for name in REAL_NAMES}
    assert len(keys) == 49


@pytest.mark.parametrize(
    ("name", "key", "higher_is_better"),
    [
        ("400 metres Hurdles, Men", "400mh_m", False),
        ("1,500 metres, Men", "1500m_m", False),
        ("Marathon, Women", "marathon_w", False),
        ("Javelin Throw, Women", "jt_w", True),
        ("Decathlon, Men", "dec_m", True),
        ("Heptathlon, Women", "hep_w", True),
        ("4 × 400 metres Relay, Mixed", "4x400m_x", False),
    ],
)
def test_known_events(name, key, higher_is_better):
    event = parse_event_name(name)
    assert event.key == key
    assert event.higher_is_better is higher_is_better


@pytest.mark.parametrize(
    ("long_name", "short_name"),
    [
        ("Steeplechase (3,000 metres), Men", "Steeplechase, Men"),
        ("100 / 80 metres Hurdles (100 m), Women", "100 / 80 metres Hurdles, Women"),
    ],
)
def test_both_spellings_give_the_same_key(long_name, short_name):
    assert parse_event_name(long_name).key == parse_event_name(short_name).key


def test_relays_are_flagged():
    assert parse_event_name("4 × 100 metres Relay, Men").is_relay
    assert parse_event_name("Marathon Race Walk Relay, Mixed").is_relay
    assert not parse_event_name("100 metres, Men").is_relay


@pytest.mark.parametrize("name", ["1,500 metres Wheelchair, Men", "800 metres Wheelchair, Women"])
def test_wheelchair_exhibition_races_are_excluded(name):
    assert parse_event_name(name) is None
    assert is_excluded(name)


@pytest.mark.parametrize("name", ["Tug of War, Men", "100 metres", "100 metres, Juniors"])
def test_unknown_names_are_not_guessed(name):
    assert parse_event_name(name) is None
    assert not is_excluded(name)


def test_extra_and_non_breaking_spaces_are_ignored():
    assert parse_event_name("100\xa0metres,  Men").key == "100m_m"


def test_every_name_maps_to_a_discipline_with_a_direction():
    assert set(OLYMPEDIA_NAMES.values()) == set(DISCIPLINES)

# --- World Championships names (real list from the 2013-2025 Wikipedia pages) ---------

REAL_WORLDS_NAMES = [
    "Men's 10,000 metres", "Men's 100 metres", "Men's 110 metres hurdles", "Men's 1500 metres",
    "Men's 20 kilometres walk", "Men's 200 metres", "Men's 3000 metres steeplechase",
    "Men's 35 kilometres walk", "Men's 4 × 100 metres relay", "Men's 4 × 400 metres relay",
    "Men's 400 metres", "Men's 400 metres hurdles", "Men's 50 kilometres walk",
    "Men's 5000 metres", "Men's 800 metres", "Men's decathlon", "Men's discus throw",
    "Men's hammer throw", "Men's high jump", "Men's javelin throw", "Men's long jump",
    "Men's marathon", "Men's masters 800 metres", "Men's pole vault", "Men's shot put",
    "Men's triple jump", "Mixed 4 × 400 metres relay",
    "Women's 10,000 metres", "Women's 100 metres", "Women's 100 metres hurdles",
    "Women's 1500 metres", "Women's 20 kilometres walk", "Women's 200 metres",
    "Women's 3000 metres steeplechase", "Women's 35 kilometres walk",
    "Women's 4 × 100 metres relay", "Women's 4 × 400 metres relay", "Women's 400 metres",
    "Women's 400 metres hurdles", "Women's 50 kilometres walk", "Women's 5000 metres",
    "Women's 800 metres", "Women's discus throw", "Women's hammer throw", "Women's heptathlon",
    "Women's high jump", "Women's javelin throw", "Women's long jump", "Women's marathon",
    "Women's masters 400 metres", "Women's pole vault", "Women's shot put",
    "Women's triple jump", "World Team",
]  # fmt: skip


def test_every_worlds_name_is_mapped_or_excluded():
    unknown = [
        n for n in REAL_WORLDS_NAMES
        if parse_worlds_event_name(n) is None and not is_worlds_excluded(n)
    ]  # fmt: skip
    assert unknown == []


def test_worlds_names_give_48_distinct_events():
    keys = {e.key for n in REAL_WORLDS_NAMES if (e := parse_worlds_event_name(n))}
    assert len(keys) == 48


def test_worlds_keys_match_olympic_keys():
    olympic = {parse_event_name(n).key for n in REAL_NAMES}
    worlds = {e.key for n in REAL_WORLDS_NAMES if (e := parse_worlds_event_name(n))}
    assert worlds <= olympic  # same key system, so the two sources can be combined


def test_worlds_exclusions_are_real_names():
    assert WIKI_WORLDS_EXCLUDED <= set(REAL_WORLDS_NAMES)
    assert parse_worlds_event_name("Women's 50 kilometres walk") is None
    assert parse_worlds_event_name("Men's 50 kilometres walk").key == "50kmw_m"