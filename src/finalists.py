"""Seed file of Olympic finalists (top 8) with their World Athletics IDs (Phase 3 H2, Phase 4).

Each finalist is matched to the world toplist of their Olympic season with the same tested matcher
as the medallists, and only clean matches are kept. The output has the same columns as
india_athletes.csv plus country_code, so the profile scraper can read it unchanged.
Usage: python -m src.finalists [--year 2024]
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import pandas as pd

from src.analysis import MATCHED, match_medallists, olympic_season
from src.config import GCP_PROJECT_ID, SEEDS_DIR

SEED_COLUMNS = ["athlete_name", "sex", "events", "last_olympics", "olympedia_athlete_id", "wa_id",
                "country_code", "notes"]  # fmt: skip


def finalists_seed(finalists: pd.DataFrame, toplists: pd.DataFrame) -> pd.DataFrame:
    """One seed row per matched finalist; an athlete in two finals gets both events.

    A match must be clean ('name+country', 'name' or 'surname+country') and must not fail the
    season-best check; finalists without a mark (DNF) can't be checked and are kept.
    """
    matched = match_medallists(finalists, toplists)
    ok = matched[matched["match"].isin(MATCHED) & matched["sb_consistent"].ne(False)]
    rows = []
    for wa_id, grp in ok.groupby("wa_id", sort=False):
        first = grp.iloc[0]
        rows.append({
            "athlete_name": first["toplist_name"],
            "sex": first["event_key"].rsplit("_", 1)[1],
            "events": ";".join(sorted(grp["event_key"].unique())),
            "last_olympics": int(first["championship_year"]),
            "olympedia_athlete_id": first.get("olympedia_athlete_id"),
            "wa_id": str(wa_id),
            "country_code": first["country_code"],
            "notes": f"Olympic finalist {int(first['championship_year'])} ({first['match']})",
        })
    return pd.DataFrame(rows, columns=SEED_COLUMNS)


def main(argv: Sequence[str] | None = None) -> int:
    from src.warehouse import query  # BigQuery is only needed when run, not in tests

    parser = argparse.ArgumentParser(prog="python -m src.finalists")
    parser.add_argument("--year", type=int, default=2024, help="Olympic year (default: 2024)")
    year = parser.parse_args(argv).year
    finalists = query(f"""
        SELECT championship_year, event_key, athlete_name, country_code, position, mark_value,
               higher_is_better, olympedia_athlete_id
        FROM `{GCP_PROJECT_ID}.staging.stg_olympic_results`
        WHERE championship_year = {year} AND position BETWEEN 1 AND 8
    """)
    toplists = query(f"""
        SELECT season, event_key, athlete_name, country_code, wa_id, mark_value, world_rank
        FROM `{GCP_PROJECT_ID}.staging.stg_wa_toplists`
        WHERE season = {olympic_season(year)}
    """)
    seeds = finalists_seed(finalists, toplists)
    path = SEEDS_DIR / f"finalists_{year}.csv"
    seeds.to_csv(path, index=False)
    matched = match_medallists(finalists, toplists)
    print(f"{len(finalists)} finalists at the {year} Olympics; matches: "
          f"{matched['match'].value_counts().to_dict()}")  # fmt: skip
    print(f"Wrote {len(seeds)} athletes to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())