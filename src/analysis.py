"""Phase 3 analysis helpers. The notebook calls these; each has offline tests.

A fair threshold for every event: Olympic finals in distance events are often slow and tactical,
so besides the podium's final-race marks we use the podium finishers' season bests from the World
Athletics toplist of that Olympic season (Tokyo 2020 was held in the 2021 season).
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from src.scrapers.world_athletics import names_match

GAMES_SEASON = {2020: 2021}  # Tokyo 2020 was held in 2021
SB_COLUMNS = ["event_key", "season", "sb_bronze", "medallists_matched"]
MATCHED = {"name+country", "name", "surname+country"}
TOLERANCE = 0.01  # toplists round times to hundredths; Olympedia sometimes gives thousandths


def olympic_season(year: int) -> int:
    """The World Athletics season an Olympic Games was held in."""
    return GAMES_SEASON.get(year, year)


def _name_words(name: str) -> list[str]:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z]+", ascii_name.lower())


def find_in_toplist(name: str, country: str, candidates: pd.DataFrame) -> tuple[pd.Series | None, str]:
    """The toplist row for one athlete, and how it was found.

    Full-name match first (country breaks ties). If no name matches, Olympedia may use a short
    name ('Mondo Duplantis' for 'Armand DUPLANTIS'), so the same surname and country is accepted
    when exactly one athlete fits. Several fits are 'ambiguous' and never guessed.
    """
    names = candidates["athlete_name"]
    named = candidates[np.array([names_match(name, n) for n in names], dtype=bool)]
    same_country = named[named["country_code"] == country]
    if len(same_country) == 1:
        return same_country.iloc[0], "name+country"
    if len(named) == 1:
        return named.iloc[0], "name"
    if len(named) > 1:
        return None, "ambiguous"
    words = _name_words(name)
    if not words:
        return None, "not found"
    surname = words[-1]
    has_surname = np.array([surname in _name_words(n) for n in names], dtype=bool)
    by_surname = candidates[(candidates["country_code"] == country).to_numpy() & has_surname]
    if len(by_surname) == 1:
        return by_surname.iloc[0], "surname+country"
    return None, "ambiguous" if len(by_surname) > 1 else "not found"


def _not_worse(season_best, olympic_mark, higher_is_better) -> bool | None:
    """A season best can't be worse than the athlete's own Olympic mark that season."""
    if season_best is None or pd.isna(olympic_mark):
        return None
    if higher_is_better:
        return float(season_best) >= float(olympic_mark) - TOLERANCE
    return float(season_best) <= float(olympic_mark) + TOLERANCE


def match_medallists(podium: pd.DataFrame, toplists: pd.DataFrame) -> pd.DataFrame:
    """Each podium finisher with their season best from that season's world toplist.

    podium needs championship_year, event_key, athlete_name, country_code, mark_value and
    higher_is_better; toplists needs season, event_key, athlete_name, country_code, wa_id,
    mark_value and world_rank. 'match' says how each was found; 'sb_consistent' is False when the
    season best is worse than the Olympic mark, which means the match is wrong.
    """
    by_key = dict(tuple(toplists.groupby(["season", "event_key"])))
    rows = []
    for rec in podium.itertuples(index=False):
        season = olympic_season(int(rec.championship_year))
        found = {"wa_id": None, "season_best": None, "world_rank": None, "match": "not found"}
        candidates = by_key.get((season, rec.event_key))
        if candidates is not None:
            hit, how = find_in_toplist(rec.athlete_name, rec.country_code, candidates)
            found["match"] = how
            if hit is not None:
                found.update(wa_id=hit["wa_id"], season_best=hit["mark_value"],
                             world_rank=hit["world_rank"])  # fmt: skip
        found["sb_consistent"] = _not_worse(found["season_best"], rec.mark_value,
                                            rec.higher_is_better)  # fmt: skip
        rows.append({**rec._asdict(), "season": season, **found})
    return pd.DataFrame(rows)


def third_best(values: list[float], higher_is_better: bool) -> float | None:
    """The third-best value, best first by the event's direction; the worst if fewer than three."""
    ordered = sorted(values, reverse=higher_is_better)
    return ordered[min(2, len(ordered) - 1)] if ordered else None


def season_best_bronze(matched: pd.DataFrame) -> pd.DataFrame:
    """Per event and Olympic season: the third-best season best among the podium finishers.

    Only matches that pass the consistency check are used.
    """
    rows = []
    found = matched[matched["sb_consistent"].eq(True)]
    for (event_key, season), grp in found.groupby(["event_key", "season"]):
        higher = bool(grp["higher_is_better"].iloc[0])
        rows.append({"event_key": event_key, "season": int(season),
                     "sb_bronze": third_best(grp["season_best"].astype(float).tolist(), higher),
                     "medallists_matched": len(grp)})  # fmt: skip
    return pd.DataFrame(rows, columns=SB_COLUMNS)


def average_over_games(per_games: pd.DataFrame) -> pd.DataFrame:
    """The season-best threshold per event: the mean over the Games, and how many Games it used."""
    return (per_games.groupby("event_key")
            .agg(sb_threshold=("sb_bronze", "mean"), games_used=("season", "nunique"))
            .reset_index())  # fmt: skip


def _floats(values) -> np.ndarray:
    return pd.Series(values, dtype="Float64").to_numpy(dtype=float, na_value=np.nan)


def gap_pct(mark, threshold, higher_is_better) -> np.ndarray:
    """Percentage gap, signed so positive means behind the threshold (the TRD's gap metric)."""
    mark, threshold = _floats(mark), _floats(threshold)
    higher = np.asarray(higher_is_better, dtype=bool)
    return 100 * np.where(higher, (threshold - mark) / threshold, (mark - threshold) / threshold)

TACTICAL_GROUPS = {"middle_distance", "long_distance", "road"}


def medallist_rank_test(matched: pd.DataFrame) -> dict:
    """Do medallists in tactical events have worse season-best world ranks than in all-out events?

    One-sided Mann-Whitney U test on the matched medallists' world ranks (ranks are skewed, so the
    test compares rankings rather than means). Only consistent matches are used.
    """
    ok = matched[matched["sb_consistent"].eq(True)]
    tactical = ok["discipline_group"].isin(TACTICAL_GROUPS)
    t = ok.loc[tactical, "world_rank"].astype(float)
    a = ok.loc[~tactical, "world_rank"].astype(float)
    result = mannwhitneyu(t, a, alternative="greater")
    return {"n_tactical": len(t), "n_all_out": len(a),
            "median_rank_tactical": t.median(), "median_rank_all_out": a.median(),
            "share_outside_top10_tactical": (t > 10).mean(),
            "share_outside_top10_all_out": (a > 10).mean(),
            "u_statistic": result.statistic, "p_value": result.pvalue}  # fmt: skip

