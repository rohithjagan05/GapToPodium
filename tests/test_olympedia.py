from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from src.config import OLYMPEDIA_EDITIONS
from src.events import parse_event_name
from src.marks import parse_mark
from src.scrapers import olympedia

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def javelin():
    return olympedia.parse_standings(load("olympedia_2024_javelin_m.html"))


@pytest.fixture(scope="module")
def eight_hundred():
    return olympedia.parse_standings(load("olympedia_2024_800m_m.html"))


@pytest.fixture(scope="module")
def links():
    return olympedia.parse_event_links(load("olympedia_2024_ath_events.html"))


def by_medal(rows, medal):
    return next(r for r in rows if r["medal"] == medal)


# --- command line ---------------------------------------------------------


def test_default_years_are_all_editions():
    args = olympedia.build_parser().parse_args([])
    assert args.years == sorted(OLYMPEDIA_EDITIONS)


def test_selected_years_are_parsed_as_ints():
    args = olympedia.build_parser().parse_args(["--years", "2024", "2016"])
    assert args.years == [2024, 2016]


def test_unknown_year_is_rejected():
    with pytest.raises(SystemExit) as exc:
        olympedia.build_parser().parse_args(["--years", "1996"])
    assert exc.value.code == 2


# --- event list (real 2024 athletics page) ---------------------------------


def test_event_links_are_deduplicated(links):
    assert len(links) == 48
    assert len({link.result_id for link in links}) == 48


def test_event_links_keep_the_first_spelling(links):
    names = {link.result_id: link.name for link in links}
    assert names[2013734] == "Javelin Throw, Men"
    assert names[2013622] == "Steeplechase (3,000 metres), Men"


def test_2024_has_42_individual_events(links):
    events = [parse_event_name(link.name) for link in links]
    assert None not in events
    assert sum(not e.is_relay for e in events) == 42


# --- 2024 men's javelin (real page) ----------------------------------------


def test_javelin_has_one_row_per_athlete(javelin):
    assert len(javelin) == 32


def test_javelin_medallists(javelin):
    gold, silver, bronze = (by_medal(javelin, m) for m in olympedia.MEDALS)
    assert (gold["athlete_name"], gold["noc"], gold["position"]) == ("Arshad Nadeem", "PAK", 1)
    assert gold["olympedia_athlete_id"] == 145843
    assert parse_mark(gold["mark_raw"]) == pytest.approx(92.97)
    assert (silver["athlete_name"], silver["noc"]) == ("Neeraj Chopra", "IND")
    assert parse_mark(silver["mark_raw"]) == pytest.approx(89.45)
    assert (bronze["athlete_name"], bronze["noc"]) == ("Anderson Peters", "GRN")
    assert parse_mark(bronze["mark_raw"]) == pytest.approx(88.54)


def test_javelin_has_exactly_three_medals(javelin):
    assert sorted(r["medal"] for r in javelin if r["medal"]) == ["Bronze", "Gold", "Silver"]


def test_javelin_has_twelve_finalists(javelin):
    assert sum(r["round_reached"] == "Final" for r in javelin) == 12


def test_javelin_every_athlete_has_id_and_country(javelin):
    assert all(r["olympedia_athlete_id"] is not None for r in javelin)
    assert all(r["noc"] for r in javelin)


# --- 2024 men's 800 m (real page, four rounds) -----------------------------


def test_800m_has_one_row_per_athlete(eight_hundred):
    assert len(eight_hundred) == 53


def test_800m_medallists(eight_hundred):
    gold, bronze = by_medal(eight_hundred, "Gold"), by_medal(eight_hundred, "Bronze")
    assert (gold["athlete_name"], gold["noc"]) == ("Emmanuel Wanyonyi", "KEN")
    assert gold["olympedia_athlete_id"] == 150270
    assert parse_mark(gold["mark_raw"]) == pytest.approx(101.19)
    assert (bronze["athlete_name"], bronze["noc"]) == ("Djamel Sedjati", "ALG")
    assert parse_mark(bronze["mark_raw"]) == pytest.approx(101.50)


def test_800m_has_eight_finalists(eight_hundred):
    assert sum(r["round_reached"] == "Final" for r in eight_hundred) == 8


def test_800m_skipped_rounds_never_become_marks(eight_hundred):
    assert not any(r["mark_raw"] in olympedia.EMPTY_CELLS for r in eight_hundred)


# --- positions and edge cases ------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("1", 1), ("12", 12), ("=3", 3), ("DNS", None), ("", None), ("AC", None)],
)
def test_parse_position(text, expected):
    assert olympedia.parse_position(text) == expected


SMALL_TABLE = """<table>
<tr><th>Pos</th><th>Number</th><th>Competitor</th><th>NOC</th><th>Final</th><th></th></tr>
<tr><td>=3</td><td>1</td><td>No Link Athlete</td><td>IND</td><td>8.10</td>
    <td><span class="Bronze">Bronze</span></td></tr>
<tr><td>DNS</td><td>2</td><td><a href="/athletes/42">Did Not Start</a></td><td>KEN</td>
    <td>–</td><td></td></tr>
</table>"""


def test_athlete_without_link_and_tied_bronze():
    row = olympedia.parse_standings(SMALL_TABLE)[0]
    assert row["athlete_name"] == "No Link Athlete"
    assert row["olympedia_athlete_id"] is None
    assert (row["position"], row["medal"], row["mark_raw"]) == (3, "Bronze", "8.10")


def test_athlete_with_no_mark():
    row = olympedia.parse_standings(SMALL_TABLE)[1]
    assert row["olympedia_athlete_id"] == 42
    assert (row["position"], row["position_raw"]) == (None, "DNS")
    assert (row["round_reached"], row["mark_raw"], row["medal"]) == (None, None, None)


def test_page_without_standings_returns_empty_list():
    assert olympedia.parse_standings("<html><p>nothing here</p></html>") == []

SPLIT_TABLE = """<table>
<tr><th>Pos</th><th>Number</th><th>Competitor</th><th>NOC</th><th>Time</th><th>5 km</th>
    <th>40 km</th><th></th></tr>
<tr><td>3</td><td>974</td><td><a href="/athletes/1">Road Runner</a></td><td>KEN</td>
    <td>2-07:00</td><td class="split" style="display: none">15:41 (6)</td>
    <td class="split" style="display: none">2-00:26 (3)</td>
    <td><span class="Bronze">Bronze</span></td></tr>
</table>"""


def test_road_event_uses_finish_time_not_last_split():
    row = olympedia.parse_standings(SPLIT_TABLE)[0]
    assert (row["round_reached"], row["mark_raw"]) == ("Time", "2-07:00")
    assert parse_mark(row["mark_raw"]) == pytest.approx(7620.0)

# --- one whole Games, with a fake fetcher ------------------------------------

EVENTS_HTML = """<table>
<tr><td><a href="/results/2013734">Javelin Throw, Men</a></td></tr>
<tr><td><a href="/results/2013553">800 metres, Men</a></td></tr>
<tr><td><a href="/results/2013628">4 × 100 metres Relay, Men</a></td></tr>
<tr><td><a href="/results/901204">1,500 metres Wheelchair, Men</a></td></tr>
<tr><td><a href="/results/999">Tug of War, Men</a></td></tr>
</table>"""


class FakeFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str) -> str:
        self.calls.append(url)
        return self.pages[url]  # KeyError means an unexpected request


def test_scrape_edition_skips_relays_exhibitions_and_unknown_names(caplog):
    base = olympedia.BASE_URL
    fetcher = FakeFetcher(
        {
            f"{base}/editions/63/sports/ATH": EVENTS_HTML,
            f"{base}/results/2013734": load("olympedia_2024_javelin_m.html"),
            f"{base}/results/2013553": load("olympedia_2024_800m_m.html"),
        }
    )
    with caplog.at_level("WARNING"):
        df = olympedia.scrape_edition(2024, fetcher)

    assert list(df.columns) == olympedia.COLUMNS
    assert len(df) == 32 + 53
    assert set(df["event_key"]) == {"jt_m", "800m_m"}
    assert (df["edition_year"] == 2024).all()
    assert len(fetcher.calls) == 3  # events page + 2 results pages; relay never fetched
    assert "Tug of War" in caplog.text
    assert "Wheelchair" not in caplog.text


def test_save_raw_writes_parquet_and_never_overwrites(tmp_path):
    df = pd.DataFrame({"a": [1]})
    now = datetime(2026, 10, 4, 1, 2, 3, tzinfo=UTC)
    path = olympedia.save_raw(df, tmp_path, now=now)
    assert path.name == "olympedia_results_20261004T010203Z.parquet"
    back = pd.read_parquet(path)
    assert back["a"].tolist() == [1]
    assert "scraped_at" in back.columns
    with pytest.raises(FileExistsError):
        olympedia.save_raw(df, tmp_path, now=now)