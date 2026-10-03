import pytest

from src import config


def test_editions_cover_2000_to_2024():
    assert sorted(config.OLYMPEDIA_EDITIONS) == [2000, 2004, 2008, 2012, 2016, 2020, 2024]


def test_edition_ids_are_unique():
    ids = list(config.OLYMPEDIA_EDITIONS.values())
    assert len(ids) == len(set(ids))


def test_data_folders_live_inside_project():
    assert config.DATA_DIR.parent == config.PROJECT_ROOT
    for folder in (config.RAW_DIR, config.CACHE_DIR, config.SEEDS_DIR):
        assert folder.parent == config.DATA_DIR


def test_delay_is_at_least_two_seconds():
    assert config.REQUEST_DELAY_SECONDS >= 2


def test_user_agent_includes_contact_email(monkeypatch):
    monkeypatch.setenv("CONTACT_EMAIL", "someone@example.com")
    assert "someone@example.com" in config.user_agent()


@pytest.mark.parametrize("value", ["", "   ", "not-an-email"])
def test_missing_or_bad_email_raises(monkeypatch, value):
    monkeypatch.setenv("CONTACT_EMAIL", value)
    with pytest.raises(RuntimeError, match="CONTACT_EMAIL"):
        config.get_contact_email()