import pandas as pd

from src.backtest import BacktestParams, run_backtest, summarize


def test_backtest_generates_metrics():
    prices = pd.DataFrame({"close": [100, 102, 101, 105, 107]})
    signals = pd.Series([0, 1, 1, -1, 0])
    params = BacktestParams()
    result = run_backtest(prices, signals, params)
    metrics = summarize(result)
    assert "total_return" in metrics
    assert metrics["exposure"] >= 0