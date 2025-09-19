import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from src.cli import load_series_from_csv, parse_symbols, prepare_daily_dataset
from src.data import DailyDataLoader


def test_parse_symbols_from_string():
    symbols = parse_symbols("005930, 000660", None)
    assert symbols == ["005930", "000660"]


def test_parse_symbols_from_file(tmp_path: Path):
    file_path = tmp_path / "symbols.txt"
    file_path.write_text("005930\n000660\n", encoding="utf-8")
    symbols = parse_symbols(None, file_path)
    assert symbols == ["005930", "000660"]


def test_prepare_daily_dataset_uses_loader(tmp_path: Path):
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
    dataset = prepare_daily_dataset(["005930"], dt.date(2024, 1, 1), dt.date(2024, 1, 3), loader)
    assert dataset.index.names == ["symbol", "date"]
    assert len(dataset) == 3


def test_load_series_from_csv(tmp_path: Path):
    csv_path = tmp_path / "index.csv"
    pd.DataFrame({"date": pd.date_range("2024-01-01", periods=2, freq="D"), "close": [100, 101]}).to_csv(csv_path, index=False)
    series = load_series_from_csv(csv_path)
    assert series.index[0] == pd.Timestamp("2024-01-01")


def test_parse_symbols_requires_input():
    with pytest.raises(ValueError):
        parse_symbols(None, None)