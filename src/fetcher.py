"""Polite page downloader: caches every page, waits between requests, retries temporary errors."""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import requests
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from src import config

logger = logging.getLogger(__name__)


class RetryableHTTPError(Exception):
    """A temporary server response (429 or 5xx) worth trying again."""

    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(f"HTTP {status_code} for {url}")
        self.url = url
        self.status_code = status_code


class Fetcher:
    """Download pages once, cache them, and space out requests to each site."""

    def __init__(
        self,
        cache_dir: Path = config.CACHE_DIR,
        delay_seconds: float = config.REQUEST_DELAY_SECONDS,
        max_attempts: int = 4,
        timeout_seconds: float = 30.0,
        user_agent: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.delay_seconds = delay_seconds
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: dict[str, float] = {}

    def cache_path(self, url: str) -> Path:
        """Where a URL's page is cached: data/cache/<host>/<hash of the URL>.html"""
        host = urlsplit(url).netloc.lower()
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / host / f"{digest}.html"

    def get(self, url: str, refresh: bool = False) -> str:
        """Return the page text, from the cache if present, otherwise from the network."""
        path = self.cache_path(url)
        if path.exists() and not refresh:
            logger.debug("cache hit %s", url)
            return path.read_bytes().decode("utf-8", errors="replace")

        retrying = Retrying(
            retry=retry_if_exception_type(
                (RetryableHTTPError, requests.ConnectionError, requests.Timeout)
            ),
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(multiplier=2, min=2, max=60),
            sleep=self._sleep,
            reraise=True,
        )
        for attempt in retrying:
            with attempt:
                content = self._download(url)

        # Write to a temporary file first, so an interrupted run never leaves a half page cached.
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_bytes(content)
        tmp_path.replace(path)
        return content.decode("utf-8", errors="replace")

    def _download(self, url: str) -> bytes:
        headers = {"User-Agent": self._get_user_agent()}
        host = urlsplit(url).netloc.lower()
        self._wait_for_turn(host)
        try:
            response = self._session.get(url, headers=headers, timeout=self.timeout_seconds)
        finally:
            self._last_request_at[host] = self._clock()
        logger.info("GET %s -> %s", url, response.status_code)
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableHTTPError(url, response.status_code)
        response.raise_for_status()  # other 4xx errors (e.g. 404) fail at once, no retry
        return response.content

    def _wait_for_turn(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is None:
            return
        wait = self.delay_seconds - (self._clock() - last)
        if wait > 0:
            logger.debug("waiting %.2f s before next request to %s", wait, host)
            self._sleep(wait)

    def _get_user_agent(self) -> str:
        if self._user_agent is None:
            self._user_agent = config.user_agent()
        return self._user_agent