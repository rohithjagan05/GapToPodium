"""Show the tables on one Olympedia results page: count, size, column names and first rows.

Exploration helper, not part of the pipeline.
Usage: python -m scripts.peek_results_page 2013734
"""

import sys
from io import StringIO

import pandas as pd

from src.fetcher import Fetcher


def main() -> None:
    result_id = sys.argv[1] if len(sys.argv) > 1 else "2013734"
    url = f"https://www.olympedia.org/results/{result_id}"
    fetcher = Fetcher()
    html = fetcher.get(url)
    tables = pd.read_html(StringIO(html))
    print(f"{len(tables)} tables on {url}")
    print(f"cached at {fetcher.cache_path(url)}")
    with pd.option_context("display.width", 250, "display.max_columns", None):
        for i, table in enumerate(tables):
            print(f"\n--- table {i}: {table.shape[0]} rows x {table.shape[1]} columns")
            print("columns:", list(table.columns))
            print(table.head(5).to_string())


if __name__ == "__main__":
    main()