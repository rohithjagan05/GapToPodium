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

# --- World Championships (Wikipedia medal summaries) ------------------------------------
# Wikipedia event name without "Men's " / "Women's " / "Mixed " -> the same discipline codes,
# so jt_m means the same event in Olympedia and Worlds data. Built from the real names on
# the 2013-2025 championship pages (checked 4 Oct 2026).
WIKI_WORLDS_NAMES: dict[str, str] = {
    "100 metres": "100m",
    "200 metres": "200m",
    "400 metres": "400m",
    "800 metres": "800m",
    "1500 metres": "1500m",
    "5000 metres": "5000m",
    "10,000 metres": "10000m",
    "marathon": "marathon",
    "110 metres hurdles": "110mh",
    "100 metres hurdles": "100mh",
    "400 metres hurdles": "400mh",
    "3000 metres steeplechase": "3000msc",
    "20 kilometres walk": "20kmw",
    "50 kilometres walk": "50kmw",
    "high jump": "hj",
    "pole vault": "pv",
    "long jump": "lj",
    "triple jump": "tj",
    "shot put": "sp",
    "discus throw": "dt",
    "hammer throw": "ht",
    "javelin throw": "jt",
    "decathlon": "dec",
    "heptathlon": "hep",
    "4 × 100 metres relay": "4x100m",
    "4 × 400 metres relay": "4x400m",
}

# Full names on the Worlds pages that are not Olympic events: skipped without a warning.
WIKI_WORLDS_EXCLUDED: set[str] = {
    "Men's 35 kilometres walk",  # Worlds only, 2022 onwards
    "Women's 35 kilometres walk",
    "Women's 50 kilometres walk",  # Worlds only (2017, 2019); never an Olympic event
    "Men's masters 800 metres",  # 2015 exhibition races
    "Women's masters 400 metres",
    "World Team",  # 2022 row that is not an event
}

_WORLDS_SEXES = {"Men's": "m", "Women's": "w", "Mixed": "x"}


def parse_worlds_event_name(name: str) -> Event | None:
    """"Men's javelin throw" -> Event(key='jt_m', ...); None for unknown or excluded names."""
    cleaned = " ".join(name.split())
    if cleaned in WIKI_WORLDS_EXCLUDED:
        return None
    sex_word, _, base = cleaned.partition(" ")
    sex = _WORLDS_SEXES.get(sex_word)
    discipline = WIKI_WORLDS_NAMES.get(base)
    if sex is None or discipline is None:
        return None
    group, higher_is_better = DISCIPLINES[discipline]
    return Event(f"{discipline}_{sex}", discipline, sex, group, higher_is_better)


def is_worlds_excluded(name: str) -> bool:
    """True for Worlds names skipped on purpose (non-Olympic events), so they are not flagged."""
    return " ".join(name.split()) in WIKI_WORLDS_EXCLUDED

# --- World Athletics profiles ------------------------------------------------------------
# Discipline names on athlete profiles -> the same discipline codes. Only senior Olympic
# disciplines are mapped; everything else is ignored on purpose: indoor events ("60 Metres",
# anything "Short Track"), junior implements ("Javelin Throw (700g)", "(76.2cm)" hurdles),
# road races, relays and non-Olympic distances. The profile's own "indoor" flag is not reliable.
# Checked on 10 Indian profiles (5 Oct 2026); the five marked "unconfirmed" follow the same
# naming pattern but did not appear in those profiles yet.
WA_PROFILE_NAMES: dict[str, str] = {
    "100 Metres": "100m",
    "200 Metres": "200m",
    "400 Metres": "400m",
    "800 Metres": "800m",  # unconfirmed
    "1500 Metres": "1500m",
    "5000 Metres": "5000m",
    "10,000 Metres": "10000m",
    "Marathon": "marathon",  # unconfirmed
    "110 Metres Hurdles": "110mh",
    "100 Metres Hurdles": "100mh",
    "400 Metres Hurdles": "400mh",
    "3000 Metres Steeplechase": "3000msc",
    "20 Kilometres Race Walk": "20kmw",
    "50 Kilometres Race Walk": "50kmw",  # unconfirmed
    "High Jump": "hj",
    "Pole Vault": "pv",
    "Long Jump": "lj",
    "Triple Jump": "tj",
    "Shot Put": "sp",
    "Discus Throw": "dt",
    "Hammer Throw": "ht",  # unconfirmed
    "Javelin Throw": "jt",
    "Decathlon": "dec",
    "Heptathlon": "hep",  # unconfirmed
}


def wa_discipline_code(name: str) -> str | None:
    """'Javelin Throw' -> 'jt'; None for anything that is not a senior Olympic discipline."""
    return WA_PROFILE_NAMES.get(" ".join(name.split()))

# --- World Athletics toplists -------------------------------------------------------------
# Toplist URL parts per discipline (the same for both sexes), read from the saved profiles by
# scripts/list_wa_event_slugs.py on 9 Oct 2026.
WA_TOPLIST_SLUGS: dict[str, tuple[str, str]] = {
    "100m": ("sprints", "100-metres"),
    "200m": ("sprints", "200-metres"),
    "400m": ("sprints", "400-metres"),
    "800m": ("middlelong", "800-metres"),
    "1500m": ("middlelong", "1500-metres"),
    "5000m": ("middlelong", "5000-metres"),
    "10000m": ("middlelong", "10000-metres"),
    "3000msc": ("middlelong", "3000-metres-steeplechase"),
    "marathon": ("road-running", "marathon"),
    "110mh": ("hurdles", "110-metres-hurdles"),
    "100mh": ("hurdles", "100-metres-hurdles"),
    "400mh": ("hurdles", "400-metres-hurdles"),
    "20kmw": ("race-walks", "20-kilometres-race-walk"),
    "50kmw": ("race-walks", "50-kilometres-race-walk"),
    "hj": ("jumps", "high-jump"),
    "pv": ("jumps", "pole-vault"),
    "lj": ("jumps", "long-jump"),
    "tj": ("jumps", "triple-jump"),
    "sp": ("throws", "shot-put"),
    "dt": ("throws", "discus-throw"),
    "ht": ("throws", "hammer-throw"),
    "jt": ("throws", "javelin-throw"),
    "dec": ("combined-events", "decathlon"),
    "hep": ("combined-events", "heptathlon"),
}

# Discipline-sex pairs that do not exist at the Olympics.
_NOT_ON_PROGRAMME = {"110mh_w", "100mh_m", "dec_w", "hep_m"}


def programme_event_keys() -> list[str]:
    """The 42 individual events on the Paris 2024 Olympic programme (no 50 km walk, no relays)."""
    return [
        f"{discipline}_{sex}"
        for discipline, (group, _) in DISCIPLINES.items()
        if group != "relays" and discipline != "50kmw"
        for sex in ("m", "w")
        if f"{discipline}_{sex}" not in _NOT_ON_PROGRAMME
    ]