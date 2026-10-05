"""Print Phase 1's done-when evidence from the latest raw files: row counts, events with
podium marks, Indian athletes with marks, and a sample of recent Indian personal bests.
Usage: python -m scripts.phase1_summary
"""

from src.validate import load_inputs, with_values


def main() -> None:
    data = load_inputs()
    olympedia = with_values(data["olympedia"])
    worlds = with_values(data["worlds"])
    marks = with_values(data["wa_marks"])
    athletes = data["wa_athletes"]

    podium_o = olympedia[olympedia["medal"].notna() & olympedia["mark_value"].notna()]
    print(f"Olympedia: {len(olympedia)} rows, {olympedia['edition_year'].nunique()} Games; "
          f"podium marks for {podium_o.groupby(['edition_year', 'event_key']).ngroups} "
          f"event-Games ({podium_o['event_key'].nunique()} distinct events)")

    podium_w = worlds[worlds["mark_value"].notna()]
    print(f"Worlds: {len(worlds)} medallist rows; podium marks for "
          f"{podium_w.groupby(['championship_year', 'event_key']).ngroups} event-championships "
          f"({podium_w['event_key'].nunique()} distinct events)")

    pbs = marks[(marks["kind"] == "personal_best") & marks["mark_value"].notna()
                & ~marks["indoor"] & ~marks["not_legal"]]
    print(f"World Athletics: {len(athletes)} athletes "
          f"({athletes['birth_date'].notna().sum()} with birth dates), {len(marks)} marks; "
          f"{pbs['wa_id'].nunique()} athletes with an outdoor legal personal best")

    sample = (pbs.merge(athletes[["wa_id", "profile_name"]], on="wa_id")
              .sort_values("date", ascending=False).head(8))
    print("\nMost recent Indian personal bests:")
    print(sample[["profile_name", "event_key", "mark_raw", "date"]].to_string(index=False))


if __name__ == "__main__":
    main()