import pytest
import requests

from src.fetcher import Fetcher, RetryableHTTPError, parse_retry_after

URL = "https://www.olympedia.org/results/123"
SAME_HOST_URL = "https://www.olympedia.org/results/456"
OTHER_HOST_URL = "https://worldathletics.org/athletes/example"


class FakeResponse:
    def __init__(self, status_code: int = 200, body: str = "<html>ok</html>", headers=None) -> None:
        self.status_code = status_code
        self.content = body.encode("utf-8")
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Returns (or raises) the queued items in order and records every call."""

    def __init__(self, items: list) -> None:
        self.items = list(items)
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        if not self.items:
            raise AssertionError(f"unexpected request to {url}")
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClock:
    """A clock that only moves when sleep() is called, so tests never really wait."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_fetcher(tmp_path, items):
    clock = FakeClock()
    session = FakeSession(items)
    fetcher = Fetcher(
        cache_dir=tmp_path,
        user_agent="TestAgent/1.0 (contact: test@example.com)",
        session=session,
        sleep=clock.sleep,
        clock=clock.time,
    )
    return fetcher, session, clock


def test_first_get_downloads_and_caches(tmp_path):
    fetcher, session, _ = make_fetcher(tmp_path, [FakeResponse(body="hello")])
    assert fetcher.get(URL) == "hello"
    assert len(session.calls) == 1
    assert fetcher.cache_path(URL).read_text(encoding="utf-8") == "hello"


def test_second_get_uses_cache_without_network(tmp_path):
    fetcher, session, _ = make_fetcher(tmp_path, [FakeResponse(body="hello")])
    fetcher.get(URL)
    assert fetcher.get(URL) == "hello"
    assert len(session.calls) == 1


def test_refresh_bypasses_cache(tmp_path):
    fetcher, session, _ = make_fetcher(
        tmp_path, [FakeResponse(body="old"), FakeResponse(body="new")]
    )
    fetcher.get(URL)
    assert fetcher.get(URL, refresh=True) == "new"
    assert len(session.calls) == 2


def test_sends_user_agent_header(tmp_path):
    fetcher, session, _ = make_fetcher(tmp_path, [FakeResponse()])
    fetcher.get(URL)
    _, headers = session.calls[0]
    assert headers["User-Agent"] == "TestAgent/1.0 (contact: test@example.com)"


def test_accented_names_survive_download_and_cache(tmp_path):
    fetcher, _, _ = make_fetcher(tmp_path, [FakeResponse(body="Jürgen Müller")])
    assert fetcher.get(URL) == "Jürgen Müller"
    assert fetcher.get(URL) == "Jürgen Müller"  # second read comes from the cache


def test_waits_between_requests_to_same_host(tmp_path):
    fetcher, _, clock = make_fetcher(tmp_path, [FakeResponse(), FakeResponse()])
    fetcher.get(URL)
    fetcher.get(SAME_HOST_URL)
    assert clock.sleeps == [2.0]


def test_no_wait_between_different_hosts(tmp_path):
    fetcher, _, clock = make_fetcher(tmp_path, [FakeResponse(), FakeResponse()])
    fetcher.get(URL)
    fetcher.get(OTHER_HOST_URL)
    assert clock.sleeps == []


def test_no_wait_if_enough_time_has_passed(tmp_path):
    fetcher, _, clock = make_fetcher(tmp_path, [FakeResponse(), FakeResponse()])
    fetcher.get(URL)
    clock.now += 5
    fetcher.get(SAME_HOST_URL)
    assert clock.sleeps == []


@pytest.mark.parametrize("status", [429, 503])
def test_retries_temporary_errors_then_succeeds(tmp_path, status):
    fetcher, session, _ = make_fetcher(
        tmp_path, [FakeResponse(status_code=status), FakeResponse(body="ok")]
    )
    assert fetcher.get(URL) == "ok"
    assert len(session.calls) == 2


def test_retries_dropped_connection(tmp_path):
    fetcher, session, _ = make_fetcher(
        tmp_path, [requests.ConnectionError("dropped"), FakeResponse(body="ok")]
    )
    assert fetcher.get(URL) == "ok"
    assert len(session.calls) == 2


def test_gives_up_after_max_attempts(tmp_path):
    fetcher, session, _ = make_fetcher(tmp_path, [FakeResponse(status_code=503)] * 4)
    with pytest.raises(RetryableHTTPError):
        fetcher.get(URL)
    assert len(session.calls) == 4
    assert not fetcher.cache_path(URL).exists()


def test_404_fails_at_once_and_is_not_cached(tmp_path):
    fetcher, session, _ = make_fetcher(tmp_path, [FakeResponse(status_code=404)])
    with pytest.raises(requests.HTTPError):
        fetcher.get(URL)
    assert len(session.calls) == 1
    assert not fetcher.cache_path(URL).exists()


def test_cache_path_is_stable_and_grouped_by_host(tmp_path):
    fetcher, _, _ = make_fetcher(tmp_path, [])
    path = fetcher.cache_path(URL)
    assert path == fetcher.cache_path(URL)
    assert path != fetcher.cache_path(SAME_HOST_URL)
    assert path.parent.name == "www.olympedia.org"


def test_cached_page_needs_no_contact_email(tmp_path, monkeypatch):
    monkeypatch.delenv("CONTACT_EMAIL", raising=False)
    session = FakeSession([])
    fetcher = Fetcher(cache_dir=tmp_path, session=session)
    path = fetcher.cache_path(URL)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"cached page")
    assert fetcher.get(URL) == "cached page"
    assert session.calls == []


def test_missing_email_stops_before_any_request(tmp_path, monkeypatch):
    monkeypatch.delenv("CONTACT_EMAIL", raising=False)
    session = FakeSession([])
    fetcher = Fetcher(cache_dir=tmp_path, session=session)
    with pytest.raises(RuntimeError, match="CONTACT_EMAIL"):
        fetcher.get(URL)
    assert session.calls == []


# --- rate limiting and refusals (HTTP 429 and 202) --------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [("120", 120.0), ("0", 0.0), ("Wed, 21 Oct 2026 07:28:00 GMT", None), (None, None), ("-5", None)],
)
def test_parse_retry_after(value, expected):
    assert parse_retry_after(value) == expected


def test_429_waits_for_retry_after(tmp_path):
    fetcher, _, clock = make_fetcher(
        tmp_path, [FakeResponse(status_code=429, headers={"Retry-After": "17"}), FakeResponse()]
    )
    fetcher.get(URL)
    assert clock.sleeps == [17.0]


def test_429_without_retry_after_waits_a_minute(tmp_path):
    fetcher, _, clock = make_fetcher(tmp_path, [FakeResponse(status_code=429), FakeResponse()])
    fetcher.get(URL)
    assert clock.sleeps == [60.0]


def test_429_retry_after_is_capped(tmp_path):
    fetcher, _, clock = make_fetcher(
        tmp_path, [FakeResponse(status_code=429, headers={"Retry-After": "9999"}), FakeResponse()]
    )
    fetcher.get(URL)
    assert clock.sleeps == [600.0]


def test_server_error_keeps_short_retry(tmp_path):
    fetcher, _, clock = make_fetcher(tmp_path, [FakeResponse(status_code=503), FakeResponse()])
    fetcher.get(URL)
    assert clock.sleeps == [2.0]


def test_429_doubles_the_delay_for_that_host_only(tmp_path):
    fetcher, _, clock = make_fetcher(
        tmp_path, [FakeResponse(status_code=429), FakeResponse(), FakeResponse()]
    )
    fetcher.get(URL)  # 429, waits 60 s, then succeeds
    fetcher.get(SAME_HOST_URL)  # now waits 4 s instead of 2 s
    assert clock.sleeps == [60.0, 4.0]
    assert fetcher.delay_for("www.olympedia.org") == 4.0
    assert fetcher.delay_for("worldathletics.org") == 2.0


def test_202_challenge_page_is_retried_like_429_and_never_cached(tmp_path):
    fetcher, _, clock = make_fetcher(
        tmp_path, [FakeResponse(status_code=202, body="challenge"), FakeResponse(body="real page")]
    )
    assert fetcher.get(URL) == "real page"
    assert clock.sleeps == [60.0]
    assert fetcher.cache_path(URL).read_text(encoding="utf-8") == "real page"


def test_other_success_codes_are_not_cached(tmp_path):
    fetcher, _, _ = make_fetcher(tmp_path, [FakeResponse(status_code=203, body="odd")])
    with pytest.raises(requests.HTTPError):
        fetcher.get(URL)
    assert not fetcher.cache_path(URL).exists()