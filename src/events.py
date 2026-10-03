"""Olympic athletics events: Olympedia names -> short keys, group, and which direction wins.

Built from the real event names on Olympedia's 2024 and 2000 athletics pages (checked 4 Oct 2026).
Olympedia lists each event twice, sometimes with a shorter name the second time, so both
spellings are mapped. Names not in the table return None so they can be flagged, never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

SEXES: dict[str, str] = {"Men": "m", "Women": "w", "Mixed": "x"}

# Discipline code -> (group, higher_is_better). Groups decide which gaps are comparable (Phase 3).
DISCIPLINES: dict[str, tuple[str, bool]] = {
    "100m": ("sprints", False),
    "200m": ("sprints", False),
    "400m": ("sprints", False),
    "110mh": ("hurdles", False),
    "100mh": ("hurdles", False),
    "400mh": ("hurdles", False),
    "800m": ("middle_distance", False),
    "1500m": ("middle_distance", False),
    "3000msc": ("long_distance", False),
    "5000m": ("long_distance", False),
    "10000m": ("long_distance", False),
    "marathon": ("road", False),
    "20kmw": ("road", False),
    "50kmw": ("road", False),
    "hj": ("jumps", True),
    "pv": ("jumps", True),
    "lj": ("jumps", True),
    "tj": ("jumps", True),
    "sp": ("throws", True),
    "dt": ("throws", True),
    "ht": ("throws", True),
    "jt": ("throws", True),
    "dec": ("combined", True),
    "hep": ("combined", True),
    "4x100m": ("relays", False),
    "4x400m": ("relays", False),
    "marwr": ("relays", False),
}

# Olympedia event name, without the ", Men" / ", Women" / ", Mixed" ending -> discipline code.
OLYMPEDIA_NAMES: dict[str, str] = {
    "100 metres": "100m",
    "200 metres": "200m",
    "400 metres": "400m",
    "800 metres": "800m",
    "1,500 metres": "1500m",
    "5,000 metres": "5000m",
    "10,000 metres": "10000m",
    "Marathon": "marathon",
    "110 metres Hurdles": "110mh",
    "100 / 80 metres Hurdles (100 m)": "100mh",
    "100 / 80 metres Hurdles": "100mh",
    "400 metres Hurdles": "400mh",
    "Steeplechase (3,000 metres)": "3000msc",
    "Steeplechase": "3000msc",
    "20 kilometres Race Walk": "20kmw",
    "50 kilometres Race Walk": "50kmw",
    "High Jump": "hj",
    "Pole Vault": "pv",
    "Long Jump": "lj",
    "Triple Jump": "tj",
    "Shot Put": "sp",
    "Discus Throw": "dt",
    "Hammer Throw": "ht",
    "Javelin Throw": "jt",
    "Decathlon": "dec",
    "Heptathlon": "hep",
    "4 × 100 metres Relay": "4x100m",
    "4 × 400 metres Relay": "4x400m",
    "Marathon Race Walk Relay": "marwr",
}

# On Olympedia's athletics pages but not Olympic medal events: skip these without a warning.
EXCLUDED_NAMES: set[str] = {
    "1,500 metres Wheelchair",  # 2000 exhibition race
    "800 metres Wheelchair",  # 2000 exhibition race
}


@dataclass(frozen=True)
class Event:
    key: str  # e.g. "400mh_m"
    discipline: str  # e.g. "400mh"
    sex: str  # "m", "w" or "x" (mixed)
    group: str  # e.g. "hurdles"
    higher_is_better: bool

    @property
    def is_relay(self) -> bool:
        return self.group == "relays"


def _split_name(name: str) -> tuple[str, str] | None:
    """'400 metres Hurdles, Men' -> ('400 metres Hurdles', 'm'), or None if there is no sex."""
    base, sep, sex_word = " ".join(name.split()).rpartition(", ")
    if not sep or sex_word not in SEXES:
        return None
    return base, SEXES[sex_word]


def parse_event_name(name: str) -> Event | None:
    """Return the Event for an Olympedia name, or None if the name is not in the table."""
    parts = _split_name(name)
    if parts is None:
        return None
    base, sex = parts
    discipline = OLYMPEDIA_NAMES.get(base)
    if discipline is None:
        return None
    group, higher_is_better = DISCIPLINES[discipline]
    return Event(f"{discipline}_{sex}", discipline, sex, group, higher_is_better)


def is_excluded(name: str) -> bool:
    """True for names we skip on purpose (e.g. exhibition races), so they are not flagged."""
    parts = _split_name(name)
    return parts is not None and parts[0] in EXCLUDED_NAMES