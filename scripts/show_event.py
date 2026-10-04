"""Print the first rows of one event from the newest raw Olympedia file.

Exploration helper. Usage: python -m scripts.show_event 2004 ht_m 8
"""

import glob
import sys

import pandas as pd


def main() -> None:
    year, event_key = int(sys.argv[1]), sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    paths = glob.glob("data/raw/olympedia/*.parquet")
    if not paths:
        raise SystemExit("No raw Olympedia files found; run the scraper first.")
    df = pd.read_parquet(max(paths))
    rows = df[(df["edition_year"] == year) & (df["event_key"] == event_key)]
    columns = ["position_raw", "athlete_name", "noc", "round_reached", "mark_raw", "medal"]
    print(f"{year} {event_key}: {len(rows)} rows")
    print(rows[columns].head(n).to_string(index=False))


if __name__ == "__main__":
    main()