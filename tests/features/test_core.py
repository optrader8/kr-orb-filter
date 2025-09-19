import pandas as pd

from src.features import gap_percent, kospi_bias, move_off_open, nr7_flag, sector_momentum


def test_nr7_flag_identifies_minimum_range():
    highs = pd.Series([10, 11, 12, 13, 14, 15, 16])
    lows = pd.Series([9, 10, 11, 12, 13, 14, 15])
    flags = nr7_flag(highs, lows, window=3)
    assert flags.iloc[-1]


def test_gap_percent_uses_previous_close():
    open_ = pd.Series([105])
    prev_close = pd.Series([100])
    assert gap_percent(open_, prev_close).iloc[0] == 0.05


def test_move_off_open_handles_zero_range():
    open_ = pd.Series([100, 100])
    close = pd.Series([105, 95])
    highs = pd.Series([110, 100])
    lows = pd.Series([90, 100])
    result = move_off_open(open_, close, highs, lows)
    assert pd.isna(result.iloc[1])
    assert result.iloc[0] == 0.5


def test_kospi_bias_differs_fast_and_slow_mas():
    index_close = pd.Series(range(1, 21))
    bias = kospi_bias(index_close)
    assert bias.iloc[-1] > 0


def test_sector_momentum_returns_pct_change():
    sector_close = pd.Series([100, 110, 121])
    result = sector_momentum(sector_close, lookback=2)
    assert result.iloc[-1] == 0.21