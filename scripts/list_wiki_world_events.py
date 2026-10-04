"""List the event names in each World Championships medal summary on Wikipedia.

Exploration helper, not part of the pipeline. Reads every medal-summary table (header row with
Event, Gold, Silver, Bronze), takes each row's 'details' link title, and prints how many events
each championship lists plus every distinct event name with the years it appears.
Usage: python -m scripts.list_wiki_world_events
"""

from collections import defaultdict

from bs4 import BeautifulSoup

from src.fetcher import Fetcher

WIKI = "https://en.wikipedia.org/wiki/"
PAGES = {
    2013: "2013_World_Championships_in_Athletics",
    2015: "2015_World_Championships_in_Athletics",
    2017: "2017_World_Championships_in_Athletics",
    2019: "2019_World_Athletics_Championships",
    2022: "2022_World_Athletics_Championships",
    2023: "2023_World_Athletics_Championships",
    2025: "2025_World_Athletics_Championships",
}


def medal_tables(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        first = table.find("tr")
        headers = {th.get_text(strip=True) for th in first.find_all("th")} if first else set()
        if {"Event", "Gold", "Silver", "Bronze"} <= headers:
            yield table


def main() -> None:
    fetcher = Fetcher()
    years_by_name: dict[str, list[int]] = defaultdict(list)
    for year, page in PAGES.items():
        soup = BeautifulSoup(fetcher.get(WIKI + page), "lxml")
        titles = [a["title"] for t in medal_tables(soup) for a in t.select("span.noprint a[title]")]
        print(f"{year}: {len(titles)} events on {page}")
        for title in titles:
            years_by_name[title.split(" – ", 1)[-1]].append(year)
    print(f"\n{len(years_by_name)} distinct event names:")
    for name in sorted(years_by_name):
        print(f"  {name}  {years_by_name[name]}")


if __name__ == "__main__":
    main()