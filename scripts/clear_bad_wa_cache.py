"""Delete cached World Athletics pages that hold no profile data (e.g. 202 challenge pages).

One-off clean-up after the fetcher cached refusals on 5 Oct 2026; the fetcher no longer caches
anything but HTTP 200. Usage: python -m scripts.clear_bad_wa_cache
"""

from src.config import CACHE_DIR


def main() -> None:
    folder = CACHE_DIR / "worldathletics.org"
    removed = 0
    for path in folder.glob("*.html"):
        if "__NEXT_DATA__" not in path.read_text(encoding="utf-8", errors="replace"):
            path.unlink()
            removed += 1
    print(f"Removed {removed} cached pages without profile data from {folder}")


if __name__ == "__main__":
    main()