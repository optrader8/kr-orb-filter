import datetime as dt
from pathlib import Path

import pandas as pd

from src.data import DailyDataLoader, DailyDataRequest


def test_daily_data_loader_uses_csv_fallback(tmp_path: Path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [0.5, 1.5, 2.5],
            "close": [1.5, 2.5, 3.5],
            "volume": [100, 110, 120],
        }
    )
    df.to_csv(csv_dir / "005930.csv", index=False)
    loader = DailyDataLoader(cache_dir=tmp_path / "cache", csv_fallback=csv_dir)
    request = DailyDataRequest(start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 3), symbol="005930")
    result = loader.fetch(request)
    assert len(result) == 3
    assert "checksum" in result.attrs
    assert (tmp_path / "cache").exists()