from pathlib import Path

import pytest

from src.marks import parse_mark
from src.scrapers import wikipedia_worlds as ww

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def worlds_2023():
    return ww.parse_medal_tables(load("wiki_worlds_2023.html"))


@pytest.fixture(scope="module")
def worlds_2013():
    return ww.parse_medal_tables(load("wiki_worlds_2013.html"))


def podium(rows, event_key, medal):
    return [r for r in rows if r["event_key"] == event_key and r["medal"] == medal]


# --- 2023 Budapest (real tables) ---------------------------------------------


def test_2023_has_42_individual_olympic_events(worlds_2023):
    assert len({r["event_key"] for r in worlds_2023}) == 42


def test_2023_mens_javelin_podium(worlds_2023):
    (gold,) = podium(worlds_2023, "jt_m", "Gold")
    (silver,) = podium(worlds_2023, "jt_m", "Silver")
    (bronze,) = podium(worlds_2023, "jt_m", "Bronze")
    assert (gold["athlete_name"], gold["country_name"]) == ("Neeraj Chopra", "India")
    assert parse_mark(gold["mark_raw"]) == pytest.approx(88.17)
    assert (silver["athlete_name"], silver["country_name"]) == ("Arshad Nadeem", "Pakistan")
    assert parse_mark(silver["mark_raw"]) == pytest.approx(87.82)
    assert (bronze["athlete_name"], bronze["country_name"]) == ("Jakub Vadlejch", "Czech Republic")
    assert parse_mark(bronze["mark_raw"]) == pytest.approx(86.67)


def test_2023_has_no_country_codes(worlds_2023):
    assert all(r["country_code"] is None for r in worlds_2023)


def test_2023_skips_relays(worlds_2023):
    assert not any("4x" in r["event_key"] for r in worlds_2023)


def test_2023_every_event_has_a_gold(worlds_2023):
    events = {r["event_key"] for r in worlds_2023}
    golds = {r["event_key"] for r in worlds_2023 if r["medal"] == "Gold"}
    assert events == golds


def test_2023_every_row_has_athlete_and_country(worlds_2023):
    assert all(r["athlete_name"] and r["country_name"] for r in worlds_2023)
def test_2023_womens_pole_vault_shared_gold_and_no_silver(worlds_2023):
    golds = podium(worlds_2023, "pv_w", "Gold")
    assert {r["athlete_name"] for r in golds} == {"Katie Moon", "Nina Kennedy"}
    assert all(parse_mark(r["mark_raw"]) == pytest.approx(4.90) for r in golds)
    assert podium(worlds_2023, "pv_w", "Silver") == []  # merged "Not awarded" cell
    assert len(podium(worlds_2023, "pv_w", "Bronze")) == 1


@pytest.mark.parametrize("fixture_name", ["wiki_worlds_2013.html","wiki_worlds_2019.html", "wiki_worlds_2023.html"])
def test_real_pages_parse_without_warnings(caplog, fixture_name):
    with caplog.at_level("WARNING"):
        ww.parse_medal_tables(load(fixture_name))
    assert caplog.text == ""

# --- 2013 Moscow (real tables, older layout) ---------------------------------


def test_2013_has_43_individual_olympic_events(worlds_2013):
    assert len({r["event_key"] for r in worlds_2013}) == 43


def test_2013_mens_high_jump_gold_with_country_code(worlds_2013):
    (gold,) = podium(worlds_2013, "hj_m", "Gold")
    assert (gold["athlete_name"], gold["country_code"]) == ("Bohdan Bondarenko", "UKR")
    assert parse_mark(gold["mark_raw"]) == pytest.approx(2.41)  # "2.41 WL, CR, =NR"


def test_2013_womens_high_jump_tie_and_vacant_bronze(worlds_2013):
    (gold,) = podium(worlds_2013, "hj_w", "Gold")
    assert (gold["athlete_name"], gold["country_code"]) == ("Brigetta Barrett", "USA")
    assert parse_mark(gold["mark_raw"]) == pytest.approx(2.00)
    silvers = podium(worlds_2013, "hj_w", "Silver")
    assert {(r["athlete_name"], r["country_code"]) for r in silvers} == {
        ("Anna Chicherova", "RUS"),
        ("Ruth Beitia", "ESP"),
    }
    assert all(parse_mark(r["mark_raw"]) == pytest.approx(1.97) for r in silvers)
    assert podium(worlds_2013, "hj_w", "Bronze") == []  # "Not awarded"


def test_2013_annulled_pink_row_is_skipped(worlds_2013):
    assert not any(r["athlete_name"] == "Svetlana Shkolina" for r in worlds_2013)


# --- edge cases with a small synthetic table ----------------------------------


def medal_row(title: str) -> str:
    athlete = '<a href="/wiki/{n}">{n}</a><br/><a href="/wiki/Kenya_at_the_2099_X">Kenya</a>'
    return (
        f'<tr><td>X<br/><span class="noprint"><a href="/wiki/x" title="2099 Worlds – {title}">'
        f"details</a></span></td>"
        f"<td>{athlete.format(n='A')}</td><td>10.00</td>"
        f"<td>{athlete.format(n='B')}</td><td>10.10</td>"
        f"<td>{athlete.format(n='C')}</td><td>10.20</td></tr>"
    )


SYNTHETIC = (
    "<table><tr><th>Event</th><th colspan='2'>Gold</th><th colspan='2'>Silver</th>"
    "<th colspan='2'>Bronze</th></tr>"
    + medal_row("Men's 100 metres")
    + medal_row("Men's 35 kilometres walk")
    + medal_row("Men's tug of war")
    + "</table>"
)


def test_unknown_names_warn_and_excluded_names_are_skipped_quietly(caplog):
    with caplog.at_level("WARNING"):
        rows = ww.parse_medal_tables(SYNTHETIC)
    assert {r["event_key"] for r in rows} == {"100m_m"}
    assert [r["athlete_name"] for r in rows] == ["A", "B", "C"]
    assert "tug of war" in caplog.text
    assert "35 kilometres" not in caplog.text


# --- one championship with a fake fetcher, and the command line ---------------


class FakeFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get(self, url: str) -> str:
        return self.pages[url]


def test_scrape_championship_adds_year_and_source():
    url = ww.WIKI_BASE + ww.WORLDS_PAGES[2023]
    df = ww.scrape_championship(2023, FakeFetcher({url: load("wiki_worlds_2023.html")}))
    assert list(df.columns) == ww.COLUMNS
    assert (df["championship_year"] == 2023).all()
    assert (df["source_url"] == url).all()


def test_default_years_are_all_championships():
    assert ww.build_parser().parse_args([]).years == sorted(ww.WORLDS_PAGES)

# --- shared medals with one mark per athlete -----------------------------------


@pytest.mark.parametrize(
    ("text", "n", "expected"),
    [
        ("13.18 13.30 [ 47 ]", 2, ["13.18", "13.30"]),  # one mark per athlete, in order
        ("4.65 m = NR 4.65 m", 2, ["4.65", "4.65"]),
        ("1.97", 2, ["1.97", "1.97"]),  # one mark shared by both
        ("88.17 m", 1, ["88.17 m"]),  # single athlete keeps the full text
        ("", 0, []),  # "Not awarded"
    ],
)
def test_split_marks(text, n, expected):
    assert ww.split_marks(text, n) == expected


def test_2019_shared_bronze_gives_each_athlete_their_own_mark():
    rows = ww.parse_medal_tables(load("wiki_worlds_2019.html"))
    bronzes = {r["athlete_name"]: parse_mark(r["mark_raw"]) for r in rows
               if r["event_key"] == "110mh_m" and r["medal"] == "Bronze"}  # fmt: skip
    assert bronzes == {
        "Pascal Martinot-Lagarde": pytest.approx(13.18),
        "Orlando Ortega": pytest.approx(13.30),
    }