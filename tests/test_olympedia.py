import pytest

from src.config import OLYMPEDIA_EDITIONS
from src.scrapers import olympedia


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


def test_main_runs_without_network(capsys):
    assert olympedia.main(["--years", "2024"]) == 0
    assert "2024: 63" in capsys.readouterr().out