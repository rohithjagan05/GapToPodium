"""Phase 3 analysis helpers. The notebook calls these; each has offline tests.

A fair threshold for every event: Olympic finals in distance events are often slow and tactical,
so besides the podium's final-race marks we use the podium finishers' season bests from the World
Athletics toplist of that Olympic season (Tokyo 2020 was held in the 2021 season).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from src.events import DISCIPLINES
from src.scrapers.world_athletics import (
    RACE_COLUMNS,
    extract_races,
    get_competitor,
    names_match,
    read_seeds,
)
from src.validate import discipline_of, with_values

GAMES_SEASON = {2020: 2021}  # Tokyo 2020 was held in 2021
SB_COLUMNS = ["event_key", "season", "sb_bronze", "medallists_matched"]
MATCHED = {"name+country", "name", "surname+country"}
TOLERANCE = 0.01  # toplists round times to hundredths; Olympedia sometimes gives thousandths
TACTICAL_GROUPS = {"middle_distance", "long_distance", "road"}


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
    """Each podium finisher (or finalist) with their season best from that season's world toplist.

    podium needs championship_year, event_key, athlete_name, country_code, mark_value and
    higher_is_better; toplists needs season, event_key, athlete_name, country_code, wa_id,
    mark_value and world_rank. 'match' says how each was found; 'sb_consistent' is False when the
    season best is worse than the Olympic mark, which means the match is wrong.
    """
    by_key = dict(tuple(toplists.groupby(["season", "event_key"])))
    rows = []
    for rec in podium.itertuples(index=False):
        season = olympic_season(int(rec.championship_year))
        found = {"wa_id": None, "toplist_name": None, "season_best": None, "world_rank": None,
                 "match": "not found"}  # fmt: skip
        candidates = by_key.get((season, rec.event_key))
        if candidates is not None:
            hit, how = find_in_toplist(rec.athlete_name, rec.country_code, candidates)
            found["match"] = how
            if hit is not None:
                found.update(wa_id=hit["wa_id"], toplist_name=hit["athlete_name"],
                             season_best=hit["mark_value"], world_rank=hit["world_rank"])  # fmt: skip
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

# --- bootstrap confidence intervals on India's gaps --------------------------------------------

TOP_RACES = 3  # an athlete's repeatable level: the mean of their best three races this season


def clean_races(races: pd.DataFrame, marks: pd.DataFrame) -> pd.DataFrame:
    """Races that count: outdoor, legal, with a mark, and not part of a combined event.

    The results-by-year list does not always flag illegal marks, so a race is also dropped when the
    same athlete, event, date and mark appear as not legal among the profile's marks (Pooja's
    wind-aided 5632 heptathlon). Races coded 'CE' are a decathlon's or heptathlon's individual
    events and only count in the combined event itself.
    """
    races = with_values(races)

    def keys(df: pd.DataFrame) -> pd.Series:  # dates as text, so date and datetime types compare
        return df["wa_id"] + "|" + df["event_key"] + "|" + df["date"].astype(str) + "|" + df["mark_raw"]

    flagged = keys(races).isin(set(keys(marks[marks["not_legal"]])))
    group = races["event_key"].map(lambda key: DISCIPLINES.get(discipline_of(key), ("",))[0])
    combined_part = races["race"].fillna("").str.startswith("CE") & (group != "combined")
    keep = (~races["indoor"] & ~races["not_legal"] & races["mark_value"].notna()
            & ~flagged & ~combined_part)  # fmt: skip
    return races[keep]


def load_races(run_dir: Path, seed_file: Path) -> pd.DataFrame:
    """The races that count (see clean_races) from the saved profiles of one World Athletics run."""
    seeds = {seed.wa_id: seed for seed in read_seeds(seed_file)}
    rows = []
    for path in sorted(run_dir.glob("*.json")):
        seed = seeds.get(path.stem)
        competitor = get_competitor(json.loads(path.read_text(encoding="utf-8")))
        if seed is not None and competitor is not None:
            rows.extend(extract_races(seed, competitor))
    marks = pd.read_parquet(run_dir / "marks.parquet")
    return clean_races(pd.DataFrame(rows, columns=RACE_COLUMNS), marks)


def repeatable_level(values, higher_is_better: bool, top: int = TOP_RACES) -> float:
    """The mean of the best `top` marks; NaN if there are fewer races than that."""
    vals = np.sort(np.asarray(values, dtype=float))
    if len(vals) < top:
        return np.nan
    best = vals[::-1][:top] if higher_is_better else vals[:top]
    return float(best.mean())


def bootstrap_level(values, higher_is_better: bool, top: int = TOP_RACES, n_boot: int = 5000,
                    ci: float = 95.0, seed: int = 0) -> tuple[float, float, float]:  # fmt: skip
    """Repeatable level and its bootstrap percentile interval: (level, low, high).

    Races are resampled with replacement n_boot times and the level is recomputed each time; the
    interval is the middle ci% of those levels. A fixed seed makes the result reproducible.
    """
    vals = np.asarray(values, dtype=float)
    level = repeatable_level(vals, higher_is_better, top)
    if np.isnan(level):
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = np.sort(rng.choice(vals, size=(n_boot, len(vals)), replace=True), axis=1)
    best = samples[:, ::-1][:, :top] if higher_is_better else samples[:, :top]
    levels = best.mean(axis=1)
    tail = (100 - ci) / 2
    low, high = np.percentile(levels, [tail, 100 - tail])
    return level, float(low), float(high)


def gap_intervals(races: pd.DataFrame, best: pd.DataFrame, threshold_col: str = "bronze_threshold",
                  **kwargs) -> pd.DataFrame:  # fmt: skip
    """Per event: the gap from India's single best mark, and from the best athlete's repeatable
    level this season with a bootstrap interval.

    best needs event_key, best_wa_id, best_mark, higher_is_better and the threshold column.
    """
    rows = []
    for rec in best.itertuples(index=False):
        mine = races[(races["wa_id"] == rec.best_wa_id) & (races["event_key"] == rec.event_key)]
        level, low, high = bootstrap_level(mine["mark_value"], rec.higher_is_better, **kwargs)
        threshold = getattr(rec, threshold_col)
        gaps = gap_pct([rec.best_mark, level, low, high], [threshold] * 4,
                       [rec.higher_is_better] * 4)  # fmt: skip
        rows.append({"event_key": rec.event_key, "races": len(mine),
                     "gap_best": gaps[0], "gap_level": gaps[1],
                     "gap_low": np.nanmin(gaps[2:]) if len(mine) >= TOP_RACES else np.nan,
                     "gap_high": np.nanmax(gaps[2:]) if len(mine) >= TOP_RACES else np.nan})  # fmt: skip
    return pd.DataFrame(rows)

# --- H2: do Indian athletes improve as fast as eventual Olympic finalists? ---------------------

AGE_WINDOW = (18, 24)  # development years, inclusive: improvements into seasons at these ages


def season_bests(marks: pd.DataFrame, events: dict[str, set[str]]) -> pd.DataFrame:
    """One outdoor, legal season best per athlete, event and season, in each athlete's own events.

    marks is a World Athletics marks table; events maps wa_id to the events the athlete is seeded
    in (an athlete's other disciplines are left out).
    """
    m = with_values(marks)
    m = m[(m["kind"] == "season_progression") & ~m["indoor"] & ~m["not_legal"]
          & m["mark_value"].notna() & m["season"].notna()]  # fmt: skip
    m = m[[key in events.get(wa_id, set()) for wa_id, key in zip(m["wa_id"], m["event_key"])]]
    higher = m["event_key"].map(lambda key: DISCIPLINES[discipline_of(key)][1])
    m = m.assign(higher_is_better=higher, _sort=np.where(higher, -m["mark_value"], m["mark_value"]))
    best = m.sort_values("_sort").drop_duplicates(["wa_id", "event_key", "season"])
    return best.drop(columns="_sort")[["wa_id", "event_key", "season", "mark_value",
                                       "higher_is_better"]]  # fmt: skip


def annual_improvements(sbs: pd.DataFrame, birth_years: dict[str, int],
                        age_window: tuple[int, int] = AGE_WINDOW) -> pd.DataFrame:  # fmt: skip
    """Year-on-year improvement in percent (positive = better) between consecutive seasons.

    Only pairs of back-to-back seasons count, and only when the athlete's age in the later season
    is inside age_window.
    """
    rows = []
    for (wa_id, event_key), grp in sbs.groupby(["wa_id", "event_key"]):
        born = birth_years.get(wa_id)
        if born is None:
            continue
        grp = grp.sort_values("season")
        seasons, values = grp["season"].astype(int).to_numpy(), grp["mark_value"].to_numpy()
        higher = bool(grp["higher_is_better"].iloc[0])
        for i in range(1, len(grp)):
            age = seasons[i] - born
            if seasons[i] - seasons[i - 1] != 1 or not age_window[0] <= age <= age_window[1]:
                continue
            change = (values[i] - values[i - 1]) if higher else (values[i - 1] - values[i])
            rows.append({"wa_id": wa_id, "event_key": event_key, "season": int(seasons[i]),
                         "age": int(age), "improvement_pct": 100 * change / values[i - 1]})  # fmt: skip
    return pd.DataFrame(rows, columns=["wa_id", "event_key", "season", "age", "improvement_pct"])


def improvement_test(india: pd.DataFrame, finalists: pd.DataFrame) -> dict:
    """H2: do Indian athletes improve more slowly than eventual Olympic finalists?

    Each athlete counts once (their median yearly improvement), so prolific athletes don't
    dominate. One-sided Mann-Whitney U test: are Indian improvements smaller?
    """
    i = india.groupby("wa_id")["improvement_pct"].median()
    f = finalists.groupby("wa_id")["improvement_pct"].median()
    result = mannwhitneyu(i, f, alternative="less")
    return {"n_india": len(i), "n_finalists": len(f),
            "median_improvement_india": i.median(), "median_improvement_finalists": f.median(),
            "u_statistic": result.statistic, "p_value": result.pvalue}  # fmt: skip