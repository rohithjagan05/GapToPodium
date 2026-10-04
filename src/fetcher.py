"""Polite page downloader: caches every page, waits between requests, retries temporary errors.

If a site rate-limits us (HTTP 429), the fetcher honours its Retry-After header (or waits a
minute and more), and doubles its delay for that site for the rest of the run.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import requests
from tenacity import RetryCallState, Retrying, retry_if_exception_type, stop_after_attempt

from src import config

logger = logging.getLogger(__name__)


class RetryableHTTPError(Exception):
    """A temporary server response (429 or 5xx) worth trying again."""

    def __init__(self, url: str, status_code: int, retry_after: float | None = None) -> None:
        super().__init__(f"HTTP {status_code} for {url}")
        self.url = url
        self.status_code = status_code
        self.retry_after = retry_after


def parse_retry_after(value: str | None) -> float | None:
    """Retry-After header in seconds ('120' -> 120.0). Dates, junk or missing -> None."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


class Fetcher:
    """Download pages once, cache them, and space out requests to each site."""

    def __init__(
        self,
        cache_dir: Path = config.CACHE_DIR,
        delay_seconds: float = config.REQUEST_DELAY_SECONDS,
        max_attempts: int = 4,
        timeout_seconds: float = 30.0,
        rate_limit_wait_seconds: float = 60.0,
        max_wait_seconds: float = 600.0,
        max_delay_seconds: float = 30.0,
        user_agent: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.delay_seconds = delay_seconds
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self.rate_limit_wait_seconds = rate_limit_wait_seconds
        self.max_wait_seconds = max_wait_seconds
        self.max_delay_seconds = max_delay_seconds
        self._user_agent = user_agent
        self._session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: dict[str, float] = {}
        self._delay_by_host: dict[str, float] = {}

    def cache_path(self, url: str) -> Path:
        """Where a URL's page is cached: data/cache/<host>/<hash of the URL>.html"""
        host = urlsplit(url).netloc.lower()
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / host / f"{digest}.html"

    def delay_for(self, host: str) -> float:
        """Current minimum gap between requests to this host (grows after a 429)."""
        return self._delay_by_host.get(host, self.delay_seconds)

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
            wait=self._retry_wait,
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

    def _retry_wait(self, retry_state: RetryCallState) -> float:
        """Seconds to wait before the next attempt."""
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        attempt = retry_state.attempt_number
        if isinstance(exc, RetryableHTTPError) and exc.status_code == 429:
            if exc.retry_after is not None:
                return min(exc.retry_after, self.max_wait_seconds)
            return min(self.rate_limit_wait_seconds * attempt, self.max_wait_seconds)
        return min(2.0**attempt, self.max_wait_seconds)  # 2, 4, 8 s for server errors

    def _download(self, url: str) -> bytes:
        headers = {"User-Agent": self._get_user_agent()}
        host = urlsplit(url).netloc.lower()
        self._wait_for_turn(host)
        try:
            response = self._session.get(url, headers=headers, timeout=self.timeout_seconds)
        finally:
            self._last_request_at[host] = self._clock()
        logger.info("GET %s -> %s", url, response.status_code)

        if response.status_code == 429:
            header = response.headers.get("Retry-After")
            self._slow_down(host)
            logger.warning(
                "%s rate-limited us (429, Retry-After=%r); now %.0f s between its requests",
                host, header, self.delay_for(host),
            )  # fmt: skip
            raise RetryableHTTPError(url, 429, parse_retry_after(header))
        if response.status_code >= 500:
            raise RetryableHTTPError(url, response.status_code)
        response.raise_for_status()  # other 4xx errors (e.g. 404) fail at once, no retry
        return response.content

    def _slow_down(self, host: str) -> None:
        self._delay_by_host[host] = min(self.delay_for(host) * 2, self.max_delay_seconds)

    def _wait_for_turn(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is None:
            return
        wait = self.delay_for(host) - (self._clock() - last)
        if wait > 0:
            logger.debug("waiting %.2f s before next request to %s", wait, host)
            self._sleep(wait)

    def _get_user_agent(self) -> str:
        if self._user_agent is None:
            self._user_agent = config.user_agent()
        return self._user_agent