"""Print the athletics result links and event names Olympedia lists for one Games.

Exploration helper, not part of the pipeline: run it to see real event names before
writing parsers. Usage: python -m scripts.list_olympedia_events 2024
"""

import sys

from bs4 import BeautifulSoup

from src.config import OLYMPEDIA_EDITIONS
from src.fetcher import Fetcher


def main() -> None:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    url = f"https://www.olympedia.org/editions/{OLYMPEDIA_EDITIONS[year]}/sports/ATH"
    soup = BeautifulSoup(Fetcher().get(url), "lxml")
    links = [
        (a["href"], a.get_text(" ", strip=True))
        for a in soup.select('a[href^="/results/"]')
    ]
    for href, name in links:
        print(f"{href}\t{name}")
    print(f"{len(links)} result links on {url}")


if __name__ == "__main__":
    main()