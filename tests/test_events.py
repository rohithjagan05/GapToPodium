import pytest

from src.events import DISCIPLINES, OLYMPEDIA_NAMES, is_excluded, parse_event_name

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