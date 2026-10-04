"""Save trimmed copies of cached Olympedia pages as offline test fixtures.

Exploration helper. Keeps only what the scraper parses, so fixtures stay small, and never
overwrites an existing fixture. The pages must already be cached.
Usage: python -m scripts.make_olympedia_fixtures
"""

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from src.config import PROJECT_ROOT
from src.fetcher import Fetcher

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
RESULTS_PAGES = {
    "olympedia_2024_javelin_m.html": "https://www.olympedia.org/results/2013734",
    "olympedia_2024_800m_m.html": "https://www.olympedia.org/results/2013553",
}
# Pages whose standings table has no round columns: keep every heading and table in order.
OUTLINE_PAGES = {
    "olympedia_2024_100mh_w.html": "https://www.olympedia.org/results/2013905",
}
EVENTS_PAGE = ("olympedia_2024_ath_events.html", "https://www.olympedia.org/editions/63/sports/ATH")

# CSS selectors: links whose address starts with /athletes/ or /results/
ATHLETE_LINK = 'a[href^="/athletes/"]'
RESULT_LINK = 'a[href^="/results/"]'
HEADINGS = ["h1", "h2", "h3", "h4", "h5"]


def standings_table(soup: BeautifulSoup):
    """The first table whose header cells include 'Pos' and 'Competitor'."""
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "Pos" in headers and "Competitor" in headers:
            return table
    raise ValueError("no standings table found")


def event_link_tables(soup: BeautifulSoup) -> list:
    """Every table that contains a link to a results page."""
    tables = [t for t in soup.find_all("table") if t.select_one(RESULT_LINK)]
    if not tables:
        raise ValueError("no table with /results/ links found")
    return tables


def save(filename: str, url: str, elements: list) -> None:
    path = FIXTURES_DIR / filename
    if path.exists():
        print(f"skipped {path.name}: already exists")
        return
    body = "\n".join(str(e) for e in elements)
    html = (
        f"<!-- Trimmed from {url} on {datetime.now(UTC).date().isoformat()} for offline tests. -->\n"
        f'<html><head><meta charset="utf-8"></head><body>\n{body}\n</body></html>\n'
    )
    path.write_text(html, encoding="utf-8")
    print(f"saved {path.name}: {len(elements)} element(s), {path.stat().st_size} bytes")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher()

    for filename, url in RESULTS_PAGES.items():
        table = standings_table(BeautifulSoup(fetcher.get(url), "lxml"))
        save(filename, url, [table])

    for filename, url in OUTLINE_PAGES.items():
        soup = BeautifulSoup(fetcher.get(url), "lxml")
        elements = soup.find_all([*HEADINGS, "table"])  # document order
        save(filename, url, elements)
        tables = sum(e.name == "table" for e in elements)
        print(f"  {tables} tables, {len(elements) - tables} headings")

    filename, url = EVENTS_PAGE
    save(filename, url, event_link_tables(BeautifulSoup(fetcher.get(url), "lxml")))


if __name__ == "__main__":
    main()