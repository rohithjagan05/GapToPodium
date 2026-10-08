"""List World Athletics toplist URL slugs and event IDs for our events, from saved profiles.

Exploration helper. For every senior Olympic discipline in the newest World Athletics run, prints
the event key (sex from the seed file), the group and discipline slugs, and the event IDs seen.
Usage: python -m scripts.list_wa_event_slugs
"""

import json
from collections import defaultdict

from src.config import RAW_DIR
from src.events import wa_discipline_code
from src.scrapers.world_athletics import SEED_FILE, get_competitor, read_seeds


def main() -> None:
    run = max(p for p in (RAW_DIR / "wa").glob("*") if (p / "marks.parquet").exists())
    sex_by_id = {seed.wa_id: seed.sex for seed in read_seeds(SEED_FILE)}
    seen: dict[str, set] = defaultdict(set)
    for path in run.glob("*.json"):
        competitor = get_competitor(json.loads(path.read_text(encoding="utf-8")))
        sex = sex_by_id.get(path.stem)
        for item in (competitor.get("personalBests") or {}).get("results") or []:
            code = wa_discipline_code(item.get("discipline") or "")
            if code and sex:
                seen[f"{code}_{sex}"].add((item.get("typeNameUrlSlug"),
                                           item.get("disciplineNameUrlSlug"),
                                           item.get("eventId")))  # fmt: skip
    for key in sorted(seen):
        print(f"{key:<12} {sorted(seen[key], key=str)}")
    print(f"\n{len(seen)} event keys from {run.name}")


if __name__ == "__main__":
    main()