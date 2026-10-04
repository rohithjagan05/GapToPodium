from datetime import UTC, datetime

import pandas as pd
import pytest

from src.raw import save_raw


def test_save_raw_names_file_by_prefix_and_time_and_never_overwrites(tmp_path):
    now = datetime(2026, 10, 4, 15, 0, 0, tzinfo=UTC)
    path = save_raw(pd.DataFrame({"a": [1]}), tmp_path, "worlds_podium", now=now)
    assert path.name == "worlds_podium_20261004T150000Z.parquet"
    assert "scraped_at" in pd.read_parquet(path).columns
    with pytest.raises(FileExistsError):
        save_raw(pd.DataFrame({"a": [1]}), tmp_path, "worlds_podium", now=now)