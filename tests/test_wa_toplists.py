from datetime import date
from pathlib import Path

from src.events import WA_TOPLIST_SLUGS, programme_event_keys
from src.scrapers import wa_toplists as wt

FIXTURE = Path(__file__).parent / "fixtures" / "wa_toplist_jt_m_2024.html"


def rows():
    return wt.parse_toplist(FIXTURE.read_text(encoding="utf-8"))


class FakeFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get(self, url: str) -> str:
        return self.pages[url]


def test_url_matches_the_confirmed_pattern():
    assert wt.toplist_url("jt_m", 2024) == (
        "https://worldathletics.org/records/toplists/throws/javelin-throw/outdoor/men/senior/2024"
        "?regionType=world&page=1&bestResultsOnly=true"
    )
    assert "/hurdles/100-metres-hurdles/outdoor/women/senior/2021?" in wt.toplist_url("100mh_w", 2021)


def test_parses_the_real_2024_javelin_list():
    parsed = rows()
    assert len(parsed) == 12
    first = parsed[0]
    assert (first["rank"], first["mark_raw"], first["athlete_name"], first["country_code"]) == (
        1, "92.97", "Arshad NADEEM", "PAK")
    neeraj = next(r for r in parsed if r["wa_id"] == "14549089")
    assert (neeraj["rank"], neeraj["mark_raw"], neeraj["place"]) == (4, "89.49", "2")
    assert (neeraj["birth_date"], neeraj["date"]) == (date(1997, 12, 24), date(2024, 8, 22))


def test_every_real_row_has_an_athlete_id():
    assert all(r["wa_id"] for r in rows())


def test_scrape_adds_season_and_event():
    url = wt.toplist_url("jt_m", 2024)
    df = wt.scrape_toplists(["jt_m"], [2024], FakeFetcher({url: FIXTURE.read_text(encoding="utf-8")}))
    assert list(df.columns) == wt.COLUMNS
    assert len(df) == 12
    assert (df["season"] == 2024).all() and (df["event_key"] == "jt_m").all()


def test_page_without_a_table_is_skipped_with_a_warning(caplog):
    url = wt.toplist_url("jt_m", 2024)
    with caplog.at_level("WARNING"):
        df = wt.scrape_toplists(["jt_m"], [2024], FakeFetcher({url: "<html></html>"}))
    assert df.empty
    assert "no toplist rows" in caplog.text


def test_programme_has_42_events_each_with_slugs():
    keys = programme_event_keys()
    assert len(keys) == 42
    assert {"jt_m", "hep_w", "dec_m", "100mh_w", "110mh_m"} <= set(keys)
    assert not {"50kmw_m", "hep_m", "dec_w", "110mh_w"} & set(keys)
    assert all(k.rsplit("_", 1)[0] in WA_TOPLIST_SLUGS for k in keys)


def test_default_seasons_use_2021_for_tokyo():
    assert 2021 in wt.DEFAULT_SEASONS and 2020 not in wt.DEFAULT_SEASONS