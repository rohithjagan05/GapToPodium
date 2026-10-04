"""Save trimmed copies of two saved World Athletics profiles as offline test fixtures.

Exploration helper. Keeps only basicData, personalBests, seasonsBests and
progressionOfSeasonsBests from the newest run in data/raw/wa/, and never overwrites a fixture.
Usage: python -m scripts.make_wa_fixtures
"""

import json
from datetime import UTC, datetime

from src.config import PROJECT_ROOT, RAW_DIR

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
WA_IDS = {"14549089": "Neeraj Chopra", "14734731": "Jyothi Yarraji"}
KEEP = ("basicData", "personalBests", "seasonsBests", "progressionOfSeasonsBests")


def main() -> None:
    runs = sorted(p for p in (RAW_DIR / "wa").iterdir() if p.is_dir())
    if not runs:
        raise SystemExit("No World Athletics runs found; run the scraper first.")
    latest = runs[-1]
    for wa_id, name in WA_IDS.items():
        out = FIXTURES_DIR / f"wa_{wa_id}.json"
        if out.exists():
            print(f"skipped {out.name}: already exists")
            continue
        data = json.loads((latest / f"{wa_id}.json").read_text(encoding="utf-8"))
        competitor = data["props"]["pageProps"]["competitor"]
        trimmed = {
            "_source": f"World Athletics profile of {name} (ID {wa_id}), trimmed on "
            f"{datetime.now(UTC).date().isoformat()} for offline tests",
            "props": {"pageProps": {"competitor": {k: competitor.get(k) for k in KEEP}}},
        }
        out.write_text(json.dumps(trimmed, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"saved {out.name}: {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()