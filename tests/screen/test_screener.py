import pandas as pd

from src.screen import DailyScreener, ScreenerSettings
from src.store import ResultStore


def test_daily_screener_scores_and_filters(tmp_path):
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    data_a = pd.DataFrame(
        {
            "open": [100, 101, 102],
            "high": [110, 111, 112],
            "low": [90, 91, 92],
            "close": [109, 110, 111],
            "volume": [1_000_000, 1_100_000, 1_200_000],
        },
        index=dates,
    )
    data_b = pd.DataFrame(
        {
            "open": [200, 201, 202],
            "high": [210, 211, 212],
            "low": [190, 191, 192],
            "close": [205, 206, 207],
            "volume": [1000, 1000, 1000],
        },
        index=dates,
    )
    combined = pd.concat({"AAA": data_a, "BBB": data_b})
    market = pd.Series([1000, 1010, 1020], index=dates)
    sector = pd.Series([500, 510, 520], index=dates)
    store = ResultStore(tmp_path)
    screener = DailyScreener(store, ScreenerSettings(liquidity_min=5_000_000_000))
    result = screener.run(combined, market, sector)
    assert ("AAA", pd.Timestamp("2024-01-03")) in result.index
    assert ("BBB", pd.Timestamp("2024-01-03")) not in result.index
    assert result.iloc[0]["score"] >= 1