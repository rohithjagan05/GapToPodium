"""Save the header and first 12 rows of the cached 2024 men's javelin toplist as a test fixture.

Exploration helper; reads the cache only. Usage: python -m scripts.make_toplist_fixture
"""

from bs4 import BeautifulSoup

from src.config import PROJECT_ROOT
from src.fetcher import Fetcher
from src.scrapers.wa_toplists import toplist_url

OUT = PROJECT_ROOT / "tests" / "fixtures" / "wa_toplist_jt_m_2024.html"


def main() -> None:
    if OUT.exists():
        print(f"skipped {OUT.name}: already exists")
        return
    url = toplist_url("jt_m", 2024)
    rows = BeautifulSoup(Fetcher().get(url), "lxml").find("table").find_all("tr")[:13]
    body = "".join(str(r) for r in rows)
    OUT.write_text(
        f"<!-- First 12 rows of {url}, saved for offline tests. -->\n"
        f'<html><head><meta charset="utf-8"></head><body><table>{body}</table></body></html>\n',
        encoding="utf-8",
    )
    print(f"saved {OUT.name}: {len(rows) - 1} athlete rows, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()