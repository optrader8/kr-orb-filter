import pandas as pd

from src.screen import DailyScreener, ScreenerSettings
from src.store import ResultStore


def test_daily_screener_scores_and_filters(tmp_path):
    data = pd.DataFrame(
        {
            "open": [100, 200],
            "high": [110, 210],
            "low": [90, 190],
            "close": [109, 205],
            "prev_close": [95, 195],
            "liquidity": [6_000_000_000, 1_000_000_000],
        },
        index=pd.Index(["2024-01-02", "2024-01-03"], name="date"),
    )
    market = pd.Series([1000, 1010], index=data.index)
    sector = pd.Series([500, 520], index=data.index)
    store = ResultStore(tmp_path)
    screener = DailyScreener(store, ScreenerSettings(liquidity_min=5_000_000_000))
    result = screener.run(data, market, sector)
    assert len(result) == 1
    assert result.iloc[0]["score"] >= 1