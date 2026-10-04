"""Per event in the newest raw Olympedia file: athletes, marks, medals, and medals with a mark.

Exploration helper. Lists only events that look wrong: not exactly 3 medals, or a medallist
without a mark. Usage: python -m scripts.medal_mark_report
"""

import glob

import pandas as pd


def main() -> None:
    paths = glob.glob("data/raw/olympedia/*.parquet")
    if not paths:
        raise SystemExit("No raw Olympedia files found; run the scraper first.")
    path = max(paths)  # names carry UTC timestamps, so the largest is the newest
    df = pd.read_parquet(path)
    df["medal_mark"] = df["mark_raw"].where(df["medal"].notna())
    report = df.groupby(["edition_year", "event_key"]).agg(
        rows=("athlete_name", "size"),
        marks=("mark_raw", "count"),
        medals=("medal", "count"),
        medal_marks=("medal_mark", "count"),
    )
    problems = report[(report["medals"] != 3) | (report["medal_marks"] < report["medals"])]
    print(f"{path}: {len(report)} events, {len(problems)} with problems")
    print(problems.to_string() if len(problems) else "none")


if __name__ == "__main__":
    main()