"""Phase 4 trajectory helpers: line up athletes' season bests by age on one common scale.

The question from Phase 3: Indian athletes improve as fast as eventual Olympic finalists and peak
at the same age, so is the gap already there at 18? To compare athletes across events, every
season best becomes a performance index: the mark as a percentage of the event's bronze
threshold, where 100 means bronze level and a higher number is always better.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

AGE_RANGE = (15, 40)  # ages outside this are almost certainly wrong birth dates or seasons
TRAJECTORY_COLUMNS = ["wa_id", "event_key", "season", "age", "mark_value", "higher_is_better",
                      "perf_index"]  # fmt: skip


def performance_index(mark, threshold, higher_is_better) -> np.ndarray:
    """Mark as a percentage of the bronze threshold: 100 = bronze level, higher is always better.

    Jumps and throws: 100 * mark / threshold. Running and walking: 100 * threshold / mark, so a
    faster time gives a bigger number. An index of 97 means about 3% short of bronze level.
    """
    mark = np.asarray(mark, dtype=float)
    threshold = np.asarray(threshold, dtype=float)
    higher = np.asarray(higher_is_better, dtype=bool)
    return np.where(higher, 100 * mark / threshold, 100 * threshold / mark)


def age_aligned(sbs: pd.DataFrame, birth_years: dict[str, int], thresholds: dict[str, float],
                age_range: tuple[int, int] = AGE_RANGE) -> pd.DataFrame:  # fmt: skip
    """One row per athlete, event and season, with the athlete's age and performance index.

    sbs is the output of analysis.season_bests; birth_years maps wa_id to birth year; thresholds
    maps event_key to that event's bronze threshold. Age is season minus birth year (the age the
    athlete turns during the season), as in Phase 3. Rows without a birth year or a threshold are
    dropped, and so are ages outside age_range.
    """
    thresholds = {k: v for k, v in thresholds.items() if pd.notna(v)}
    df = sbs[sbs["wa_id"].isin(birth_years.keys()) & sbs["event_key"].isin(thresholds.keys())]
    df = df.assign(age=df["season"].astype(int) - df["wa_id"].map(birth_years).astype(int))
    df = df[df["age"].between(*age_range)]
    df = df.assign(perf_index=performance_index(df["mark_value"], df["event_key"].map(thresholds),
                                                df["higher_is_better"]))  # fmt: skip
    df = df.sort_values(["wa_id", "event_key", "season"]).reset_index(drop=True)
    return df[TRAJECTORY_COLUMNS]