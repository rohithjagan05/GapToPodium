"""Create data/seeds/india_athletes.csv from Indian Olympians (2016-2024) in the Olympedia data.

Exploration helper. Writes one row per athlete with an empty wa_id column, to fill in by hand
from each athlete's World Athletics profile URL. Never overwrites an existing seed file.
Usage: python -m scripts.make_india_seed
"""

import glob

import pandas as pd

from src.config import SEEDS_DIR

OUT = SEEDS_DIR / "india_athletes.csv"
FIRST_YEAR = 2016
COLUMNS = ["athlete_name", "sex", "events", "last_olympics", "olympedia_athlete_id", "wa_id", "notes"]


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} already exists; not overwriting.")
    paths = glob.glob("data/raw/olympedia/*.parquet")
    if not paths:
        raise SystemExit("No raw Olympedia files found; run the scraper first.")
    df = pd.read_parquet(max(paths))

    india = df[(df["noc"] == "IND") & (df["edition_year"] >= FIRST_YEAR)]
    seed = (
        india.groupby("olympedia_athlete_id", dropna=False)
        .agg(
            athlete_name=("athlete_name", "first"),
            events=("event_key", lambda keys: ";".join(sorted(set(keys)))),
            last_olympics=("edition_year", "max"),
        )
        .reset_index()
    )
    seed["sex"] = seed["events"].str.split(";").str[0].str[-1]  # event keys end in _m or _w
    seed = seed.assign(wa_id="", notes="").sort_values(
        ["last_olympics", "athlete_name"], ascending=[False, True]
    )
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    seed[COLUMNS].to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {len(seed)} athletes to {OUT}")
    print(seed[COLUMNS[:5]].to_string(index=False))


if __name__ == "__main__":
    main()