"""Convert mark text from results pages into numbers: seconds, metres or points.

The unit depends on the event (see src/events.py); this module only reads the number.
Anything that is not a valid mark (DNF, DNS, DQ, NM, dashes, unknown formats) becomes None.
"""

from __future__ import annotations

import re

# Labels that annotate a mark without changing it: records and bests, optionally "equals" (=OR).
_RECORD_TOKEN = re.compile(r"^=?(WR|OR|AR|CR|NR|ER|PB|SB|WL)$", re.IGNORECASE)
# Stand-alone words that carry no value: a metres unit ("88.17 m") or a lone "=" before a label.
_NOISE_TOKENS = {"m", "="}
# A single letter stuck to the end of a number: metres (m), hand-timed (h), altitude (A), wind (w).
_ANNOTATION_SUFFIX = re.compile(r"(?<=\d)[mhAw]$")
# Olympedia writes h:mm:ss with a hyphen after the hours: "2-07:00" means 2:07:00.
_HOUR_HYPHEN = re.compile(r"^(\d+)-(?=\d{2}:\d{2})")
_PLAIN_NUMBER = re.compile(r"^\d+(\.\d+)?$")
_THOUSANDS = re.compile(r"^\d{1,3}(,\d{3})+$")
_CLOCK_PART = re.compile(r"^\d{1,2}$")
_SECONDS_PART = re.compile(r"^\d{1,2}(\.\d+)?$")


def parse_mark(text: str | None) -> float | None:
    """Return the mark as a float, or None if the text is not a valid mark.

    "10.62" -> 10.62, "1:43.03" -> 103.03, "2:06:26" or "2-06:26" -> 7586.0,
    "8,909" -> 8909.0, "88.17 m" -> 88.17, "2.41 WL, CR, =NR" -> 2.41, "DNF" -> None
    """
    if text is None:
        return None
    cleaned = re.sub(r"\(.*?\)", " ", str(text).replace("\xa0", " "))
    # A label list like "WL, CR" leaves commas on the labels; strip those before matching.
    tokens = [t.rstrip(",") for t in cleaned.split()]
    tokens = [t for t in tokens if t and t not in _NOISE_TOKENS and not _RECORD_TOKEN.match(t)]
    if len(tokens) != 1:
        return None
    token = _ANNOTATION_SUFFIX.sub("", tokens[0])
    token = _HOUR_HYPHEN.sub(r"\1:", token)

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