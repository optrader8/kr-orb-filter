"""Feature engineering utilities for NR7, gaps, MOO, and bias metrics."""
from __future__ import annotations

import pandas as pd


def nr7_flag(high: pd.Series, low: pd.Series, window: int = 7) -> pd.Series:
    """Return boolean NR7 flag where range equals rolling min of past window."""
    daily_range = high - low
    rolling_min = daily_range.rolling(window=window, min_periods=window).min()
    return (daily_range == rolling_min).astype(bool)


def gap_percent(open_: pd.Series, prev_close: pd.Series) -> pd.Series:
    """Compute gap percentage between open and previous close."""
    return (open_ - prev_close) / prev_close


def move_off_open(open_: pd.Series, close: pd.Series, high: pd.Series, low: pd.Series) -> pd.Series:
    """Normalize distance between close and open by intraday range."""
    range_ = (high - low).replace(0, pd.NA)
    return (close - open_).abs() / range_


def kospi_bias(index_close: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    """Simple bias metric: slope of moving averages difference."""
    fast_ma = index_close.rolling(window=fast, min_periods=fast).mean()
    slow_ma = index_close.rolling(window=slow, min_periods=slow).mean()
    bias = fast_ma - slow_ma
    return bias.diff()


def sector_momentum(sector_close: pd.Series, lookback: int = 5) -> pd.Series:
    """Compute simple momentum using percentage change over lookback."""
    return sector_close.pct_change(periods=lookback)