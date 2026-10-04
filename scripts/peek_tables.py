"""Show the tables on any web page: count, size, column names and first rows.

Exploration helper, not part of the pipeline. Uses the cached, polite Fetcher.
Usage: python -m scripts.peek_tables <url> [max_tables]
"""

import sys
from io import StringIO

import pandas as pd

from src.fetcher import Fetcher


def main() -> None:
    url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    fetcher = Fetcher()
    html = fetcher.get(url)
    tables = pd.read_html(StringIO(html))
    print(f"{len(tables)} tables on {url}")
    print(f"cached at {fetcher.cache_path(url)}")
    with pd.option_context("display.width", 250, "display.max_columns", None):
        for i, table in enumerate(tables[:limit]):
            print(f"\n--- table {i}: {table.shape[0]} rows x {table.shape[1]} columns")
            print("columns:", list(table.columns))
            print(table.head(4).to_string())


if __name__ == "__main__":
    main()