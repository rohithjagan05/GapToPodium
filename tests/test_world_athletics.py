import json
from datetime import date
from pathlib import Path

import pytest
import requests

from src.scrapers import world_athletics as wa

# Real field names and Neeraj Chopra's real values from his profile JSON (4 Oct 2026), trimmed.
NEERAJ = {
    "basicData": {"givenName": "Neeraj", "familyName": "CHOPRA", "countryCode": "IND",
                  "birthDate": "24 DEC 1997"},
    "personalBests": {"results": [{"discipline": "Javelin Throw", "indoor": False,
                                   "mark": "90.23"}]},
    "progressionOfSeasonsBests": [
        {"discipline": "Javelin Throw", "indoor": False, "results": []},
        {"discipline": "Javelin Throw (700g)", "indoor": False, "results": []},
    ],
}  # fmt: skip

HEADER = "athlete_name,sex,events,last_olympics,olympedia_athlete_id,wa_id,notes\n"


def page(competitor: dict) -> str:
    data = {"props": {"pageProps": {"competitor": competitor}}}
    return f'<html><body><script id="__NEXT_DATA__">{json.dumps(data)}</script></body></html>'


class FakeFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get(self, url: str) -> str:
        if url not in self.pages:
            raise requests.HTTPError(f"404 Client Error for url: {url}")
        return self.pages[url]


def url(wa_id: str) -> str:
    return wa.PROFILE_URL.format(wa_id=wa_id)


# --- seed file ------------------------------------------------------------------


def test_read_seeds_keeps_rows_with_numeric_ids(tmp_path, caplog):
    path = tmp_path / "seeds.csv"
    path.write_text(
        HEADER
        + "Neeraj Chopra,m,jt_m,2024,143754,14549089,\n"
        + "No Id Yet,w,100m_w,,,,\n"
        + "Bad Id,m,lj_m,,,abc,\n"
        + "Two Events,w,3000msc_w;5000m_w,,,123,added by hand\n",
        encoding="utf-8",
    )
    with caplog.at_level("INFO"):
        seeds = wa.read_seeds(path)
    assert [s.wa_id for s in seeds] == ["14549089", "123"]
    assert seeds[1].events == ("3000msc_w", "5000m_w")
    assert "'abc' is not a number" in caplog.text
    assert "1 seeded athletes have no wa_id" in caplog.text


def test_read_seeds_warns_on_duplicate_ids(tmp_path, caplog):
    path = tmp_path / "seeds.csv"
    path.write_text(HEADER + "A,m,jt_m,,,111,\nB,m,jt_m,,,111,\n", encoding="utf-8")
    with caplog.at_level("WARNING"):
        wa.read_seeds(path)
    assert "wa_id 111 appears 2 times" in caplog.text


# --- names ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("seed_name", "profile", "expected"),
    [
        ("Neeraj Chopra", "Neeraj CHOPRA", True),
        ("Pahal Kiran", "Kiran PAHAL", True),  # word order differs
        ("Avinash Sable", "Avinash Mukund SABLE", True),  # extra middle name on WA
        ("Annu Rani Dharayan", "Annu RANI", True),  # extra name in the seed
        ("Jürgen Müller", "Jurgen MULLER", True),  # accents ignored
        ("Neeraj Chopra", "Jyothi YARRAJI", False),  # wrong ID loads someone else
        ("", "Neeraj CHOPRA", False),
    ],
)
def test_names_match(seed_name, profile, expected):
    assert wa.names_match(seed_name, profile) is expected


def test_profile_name_joins_given_and_family_name():
    assert wa.profile_name(NEERAJ) == "Neeraj CHOPRA"


# --- page data ------------------------------------------------------------------


def test_extract_next_data_reads_the_embedded_json():
    data = wa.extract_next_data(page(NEERAJ))
    assert wa.get_competitor(data)["basicData"]["birthDate"] == "24 DEC 1997"


def test_page_without_next_data_gives_none():
    assert wa.extract_next_data("<html><body>no data</body></html>") is None
    assert wa.get_competitor(None) is None


def test_profile_url_uses_a_generic_name_part():
    assert url("14549089") == "https://worldathletics.org/athletes/india/athlete-14549089"


# --- scraping -------------------------------------------------------------------


def test_scrape_profiles_saves_json_and_flags_problems(tmp_path):
    seeds = [
        wa.SeedAthlete("Neeraj Chopra", "m", ("jt_m",), "1"),
        wa.SeedAthlete("Someone Else", "w", ("100m_w",), "2"),  # this ID loads Neeraj
        wa.SeedAthlete("Missing Person", "m", ("lj_m",), "3"),  # no such profile
    ]
    fetcher = FakeFetcher({url("1"): page(NEERAJ), url("2"): page(NEERAJ)})
    competitors, problems = wa.scrape_profiles(seeds, fetcher, tmp_path)
    assert set(competitors) == {"1"}  # the mismatched profile is not used for marks
    assert (tmp_path / "2.json").exists()  # but it is saved as evidence
    assert json.loads((tmp_path / "1.json").read_text(encoding="utf-8"))["props"]
    assert {(p["wa_id"], p["issue"]) for p in problems} == {
        ("2", "name mismatch"),
        ("3", "profile not found"),
    }


def test_scrape_profiles_flags_another_country(tmp_path):
    other = {**NEERAJ, "basicData": {**NEERAJ["basicData"], "countryCode": "PAK"}}
    seeds = [wa.SeedAthlete("Neeraj Chopra", "m", ("jt_m",), "1")]
    competitors, problems = wa.scrape_profiles(seeds, FakeFetcher({url("1"): page(other)}), tmp_path)
    assert competitors == {}
    assert [(p["issue"], p["detail"]) for p in problems] == [("country is not IND", "PAK")]


def test_disciplines_seen_counts_each_athlete_once():
    seen = wa.disciplines_seen({"1": NEERAJ})
    assert seen == {("Javelin Throw", False): 1, ("Javelin Throw (700g)", False): 1}

# --- extraction from trimmed real profiles -----------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def load_competitor(wa_id: str) -> dict:
    data = json.loads((FIXTURES / f"wa_{wa_id}.json").read_text(encoding="utf-8"))
    return wa.get_competitor(data)


@pytest.fixture(scope="module")
def neeraj():
    seed = wa.SeedAthlete("Neeraj Chopra", "m", ("jt_m",), "14549089")
    return wa.extract_athlete(seed, load_competitor("14549089"))


@pytest.fixture(scope="module")
def jyothi():
    seed = wa.SeedAthlete("Jyothi Yarraji", "w", ("100mh_w",), "14734731")
    return wa.extract_athlete(seed, load_competitor("14734731"))


@pytest.mark.parametrize(
    ("text", "expected"),
    [("24 DEC 1997", date(1997, 12, 24)), ("", None), ("2013", None)],
)
def test_parse_wa_date(text, expected):
    assert wa.parse_wa_date(text) == expected


def test_neeraj_athlete_row(neeraj):
    athlete, _ = neeraj
    assert athlete["profile_name"] == "Neeraj CHOPRA"
    assert athlete["birth_date"] == date(1997, 12, 24)
    assert athlete["country_code"] == "IND"


def test_neeraj_personal_and_season_best(neeraj):
    _, marks = neeraj
    (pb,) = [m for m in marks if m["kind"] == "personal_best"]
    assert (pb["event_key"], pb["mark_raw"], pb["date"]) == ("jt_m", "90.23", date(2025, 5, 16))
    (sb,) = [m for m in marks if m["kind"] == "season_best"]
    assert (sb["mark_raw"], sb["season"], sb["date"]) == ("88.05", 2026, date(2026, 8, 21))


def test_neeraj_progression_starts_in_2013(neeraj):
    _, marks = neeraj
    first = [m for m in marks if m["kind"] == "season_progression" and m["season"] == 2013]
    assert [m["mark_raw"] for m in first] == ["69.66"]


def test_junior_javelin_is_not_mapped(neeraj):
    _, marks = neeraj
    assert {m["event_key"] for m in marks} == {"jt_m"}  # "Javelin Throw (700g)" ignored


def test_jyothi_sprint_events_without_indoor_60m(jyothi):
    athlete, marks = jyothi
    keys = {m["event_key"] for m in marks}
    assert {"100m_w", "200m_w", "100mh_w"} <= keys
    assert all(k.endswith("_w") for k in keys)  # no 60 m: it is not a mapped discipline
    assert athlete["birth_date"] == date(1999, 8, 28)


def test_extract_tables_builds_both_tables():
    seed = wa.SeedAthlete("Neeraj Chopra", "m", ("jt_m",), "14549089")
    athletes, marks = wa.extract_tables([seed], {"14549089": load_competitor("14549089")})
    assert list(athletes.columns) == wa.ATHLETE_COLUMNS
    assert list(marks.columns) == wa.MARK_COLUMNS
    assert len(athletes) == 1 and len(marks) > 2