"""Write a cross-check sheet of World Championships podium rows to verify on the official site.

Picks a fixed random sample plus every shared-medal row (ties), from the newest raw Worlds file,
and writes docs/worlds_crosscheck.csv with empty columns to fill in from worldathletics.org.
Never overwrites an existing sheet. Usage: python -m scripts.make_worlds_crosscheck
"""

import glob

import pandas as pd

from src.config import PROJECT_ROOT

OUT = PROJECT_ROOT / "docs" / "worlds_crosscheck.csv"
SAMPLE_SIZE = 10
SEED = 2026  # fixed, so the same rows are picked every time


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} already exists; not overwriting.")
    paths = glob.glob("data/raw/worlds/*.parquet")
    if not paths:
        raise SystemExit("No raw Worlds files found; run the scraper first.")
    df = pd.read_parquet(max(paths))

    shared = df[df.duplicated(["championship_year", "event_key", "medal"], keep=False)]
    sample = df.drop(shared.index).sample(n=SAMPLE_SIZE, random_state=SEED)
    columns = ["championship_year", "event_key", "medal", "athlete_name", "country_name",
               "mark_raw"]  # fmt: skip
    sheet = (
        pd.concat([sample, shared])
        .sort_values(["championship_year", "event_key", "medal"])[columns]
        .assign(official_mark="", official_url="", matches="")
    )
    OUT.parent.mkdir(exist_ok=True)
    sheet.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(sheet)} rows to {OUT}: {SAMPLE_SIZE} random + {len(shared)} shared-medal")
    print(sheet[columns].to_string(index=False))


if __name__ == "__main__":
    main()