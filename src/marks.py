"""Convert mark text from results pages into numbers: seconds, metres or points.

The unit depends on the event (see src/events.py); this module only reads the number.
Anything that is not a valid mark (DNF, DNS, DQ, NM, dashes, unknown formats) becomes None.
"""

from __future__ import annotations

import re

# Upper-case labels that annotate a mark without changing it: WR, =OR, PB, SB, WMR, WU20R...
# Alone (DNF, NM, DQ) they leave no number, so the result is still None.
_LABEL_TOKEN = re.compile(r"^=?[A-Z][A-Z0-9]*$")
# Lower-case words that carry no value: metres, points, wind-assisted, a lone "=".
_NOISE_TOKENS = {"m", "pts", "w", "="}
# A single character stuck to the end of a number: metres (m), hand-timed (h), altitude (A),
# wind (w), or "=" (World Athletics marks an equalled best as "17.19=").
_ANNOTATION_SUFFIX = re.compile(r"(?<=\d)[mhAw=]$")
# Olympedia writes h:mm:ss with a hyphen after the hours: "2-07:00" means 2:07:00.
_HOUR_HYPHEN = re.compile(r"^(\d+)-(?=\d{2}:\d{2})")
# Wikipedia writes some road times as h:mm.ss: "1:26.34" for a 20 km walk means 1:26:34.
_ROAD_DOT_HOURS = re.compile(r"^(\d):(\d{2})\.(\d{2})$")
_PLAIN_NUMBER = re.compile(r"^\d+(\.\d+)?$")
_THOUSANDS = re.compile(r"^\d{1,3}(,\d{3})+$")
_CLOCK_PART = re.compile(r"^\d{1,2}$")
_SECONDS_PART = re.compile(r"^\d{1,2}(\.\d+)?$")


def parse_mark(text: str | None, road: bool = False) -> float | None:
    """Return the mark as a float, or None if the text is not a valid mark.

    "10.62" -> 10.62, "1:43.03" -> 103.03, "2:06:26" or "2-06:26" -> 7586.0,
    "8,909" or "9045 pts WR" -> points, "88.17 m" -> 88.17, "17.19=" -> 17.19, "DNF" -> None.
    With road=True (marathon, race walks), "1:26.34" means 1:26:34, since a road race cannot
    last 86 seconds.
    """
    if text is None:
        return None
    # Drop wind readings "(+0.4)", place notes "(1 h3)" and footnote references "[47]".
    cleaned = re.sub(r"\(.*?\)|\[.*?\]", " ", str(text).replace("\xa0", " "))
    # A label list like "WL, CR" leaves commas on the labels; strip those before matching.
    tokens = [t.rstrip(",") for t in cleaned.split()]
    tokens = [t for t in tokens if t and t not in _NOISE_TOKENS and not _LABEL_TOKEN.match(t)]
    if len(tokens) > 1 and len(set(tokens)) == 1:
        tokens = tokens[:1]  # the same mark repeated, e.g. once per tied athlete
    if len(tokens) != 1:
        return None
    token = _ANNOTATION_SUFFIX.sub("", tokens[0])
    token = _HOUR_HYPHEN.sub(r"\1:", token)
    if road:
        token = _ROAD_DOT_HOURS.sub(r"\1:\2:\3", token)

    if _PLAIN_NUMBER.match(token):
        return round(float(token), 3)
    if _THOUSANDS.match(token):
        return float(token.replace(",", ""))
    if ":" in token:
        return _parse_clock(token)
    return None


def _parse_clock(token: str) -> float | None:
    """'m:ss.xx' or 'h:mm:ss.xx' -> total seconds."""
    first, *rest = token.split(":")
    if len(rest) not in (1, 2) or not first.isdigit():
        return None
    *middle, last = rest
    if not all(_CLOCK_PART.match(p) for p in middle) or not _SECONDS_PART.match(last):
        return None
    seconds = float(last)
    if seconds >= 60 or any(int(p) >= 60 for p in middle):
        return None

    total = 0
    for part in [first, *middle]:
        total = total * 60 + int(part)
    return round(total * 60 + seconds, 3)