"""Moving average calculations and signals for Linda Raschke strategies."""
from __future__ import annotations

import pandas as pd
import numpy as np


def calculate_ema(close: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return close.ewm(span=period, adjust=False).mean()


def calculate_sma(close: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return close.rolling(window=period).mean()


def ema_crossover(close: pd.Series, fast_period: int = 20, slow_period: int = 50) -> pd.DataFrame:
    """Calculate EMA crossover signals for Linda's moving average strategy."""
    result = pd.DataFrame(index=close.index)

    fast_ema = calculate_ema(close, fast_period)
    slow_ema = calculate_ema(close, slow_period)

    result['ema_fast'] = fast_ema
    result['ema_slow'] = slow_ema
    result['ema_spread'] = fast_ema - slow_ema

    # Previous values for crossover detection
    fast_prev = fast_ema.shift(1)
    slow_prev = slow_ema.shift(1)

    # Crossover signals
    result['bullish_crossover'] = (fast_ema > slow_ema) & (fast_prev <= slow_prev)
    result['bearish_crossover'] = (fast_ema < slow_ema) & (fast_prev >= slow_prev)

    # Trend strength based on EMA separation
    result['ema_separation_pct'] = (result['ema_spread'] / slow_ema * 100).abs()
    result['strong_trend'] = result['ema_separation_pct'] > 2.0  # 2% separation
    result['weak_trend'] = result['ema_separation_pct'] < 0.5   # 0.5% separation

    # Trend direction
    result['uptrend'] = fast_ema > slow_ema
    result['downtrend'] = fast_ema < slow_ema

    return result


def ma_3period_signal(close: pd.Series, volume: pd.Series = None) -> pd.DataFrame:
    """Generate 3-period MA signals for short-term entries."""
    result = pd.DataFrame(index=close.index)

    ma3 = calculate_sma(close, 3)
    result['ma3'] = ma3

    # Entry signals
    result['above_ma3'] = close > ma3
    result['below_ma3'] = close < ma3

    # Calculate distance from MA3 for stop placement
    result['distance_from_ma3'] = close - ma3
    result['distance_pct'] = (result['distance_from_ma3'] / ma3 * 100)

    # Entry conditions (Linda's 3-period MA strategy)
    result['long_entry_signal'] = (close > ma3) & (close.shift(1) <= ma3.shift(1))
    result['short_entry_signal'] = (close < ma3) & (close.shift(1) >= ma3.shift(1))

    # Stop levels (2-3 points below/above MA3)
    # Using percentage-based stops for different price levels
    stop_distance_pct = 0.5  # 0.5% stop distance
    result['long_stop_level'] = ma3 * (1 - stop_distance_pct / 100)
    result['short_stop_level'] = ma3 * (1 + stop_distance_pct / 100)

    # Volume confirmation if available
    if volume is not None:
        volume_ma = volume.rolling(window=10).mean()
        result['volume_confirmation'] = volume > volume_ma
        result['confirmed_long_entry'] = result['long_entry_signal'] & result['volume_confirmation']
        result['confirmed_short_entry'] = result['short_entry_signal'] & result['volume_confirmation']
    else:
        result['confirmed_long_entry'] = result['long_entry_signal']
        result['confirmed_short_entry'] = result['short_entry_signal']

    return result


def ma_bias_filter(close: pd.Series, fast_period: int = 20, slow_period: int = 50) -> pd.DataFrame:
    """Calculate moving average bias for overall market direction."""
    result = pd.DataFrame(index=close.index)

    fast_ma = calculate_ema(close, fast_period)
    slow_ma = calculate_ema(close, slow_period)

    result['ma_fast'] = fast_ma
    result['ma_slow'] = slow_ma

    # Bias calculation
    result['ma_bias'] = fast_ma - slow_ma
    result['ma_bias_normalized'] = result['ma_bias'] / slow_ma * 100

    # Slope of bias (trend acceleration/deceleration)
    result['bias_slope'] = result['ma_bias'].diff()
    result['bias_slope_5'] = result['ma_bias'].diff(5)

    # Bias classifications
    result['bullish_bias'] = result['ma_bias'] > 0
    result['bearish_bias'] = result['ma_bias'] < 0
    result['bias_strengthening'] = result['bias_slope'] > 0
    result['bias_weakening'] = result['bias_slope'] < 0

    # Strong bias conditions
    bias_threshold = 1.0  # 1% threshold for strong bias
    result['strong_bullish_bias'] = result['ma_bias_normalized'] > bias_threshold
    result['strong_bearish_bias'] = result['ma_bias_normalized'] < -bias_threshold

    return result


def calculate_ma_confluence(close: pd.Series,
                          periods: list[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """Calculate moving average confluence for support/resistance levels."""
    result = pd.DataFrame(index=close.index)

    # Calculate multiple EMAs
    for period in periods:
        result[f'ema_{period}'] = calculate_ema(close, period)

    # Price relative to each MA
    for period in periods:
        result[f'above_ema_{period}'] = close > result[f'ema_{period}']

    # Count how many MAs price is above
    above_cols = [col for col in result.columns if col.startswith('above_ema_')]
    result['mas_above'] = result[above_cols].sum(axis=1)
    result['all_mas_above'] = result['mas_above'] == len(periods)
    result['all_mas_below'] = result['mas_above'] == 0

    # MA alignment (all MAs in order)
    ma_cols = [f'ema_{period}' for period in sorted(periods)]
    result['bullish_alignment'] = True
    result['bearish_alignment'] = True

    for i in range(len(ma_cols) - 1):
        result['bullish_alignment'] &= result[ma_cols[i]] > result[ma_cols[i + 1]]
        result['bearish_alignment'] &= result[ma_cols[i]] < result[ma_cols[i + 1]]

    # Confluence strength
    result['confluence_strength'] = result['mas_above'] / len(periods)

    return result


def linda_ma_strategy_signals(close: pd.Series, volume: pd.Series = None,
                            fast_period: int = 20, slow_period: int = 50) -> pd.DataFrame:
    """Generate comprehensive MA strategy signals according to Linda's methodology."""
    result = pd.DataFrame(index=close.index)

    # Get EMA crossover signals
    ema_signals = ema_crossover(close, fast_period, slow_period)
    result = result.join(ema_signals)

    # Get 3-period MA signals
    ma3_signals = ma_3period_signal(close, volume)
    result = result.join(ma3_signals, rsuffix='_ma3')

    # Get bias filter
    bias_signals = ma_bias_filter(close, fast_period, slow_period)
    result = result.join(bias_signals, rsuffix='_bias')

    # Volume expansion for crossovers
    if volume is not None:
        volume_ma20 = volume.rolling(window=20).mean()
        result['volume_expansion'] = volume > volume_ma20 * 1.5

        # Enhanced crossover signals with volume
        result['enhanced_bullish_crossover'] = (
            result['bullish_crossover'] &
            result['volume_expansion']
        )
        result['enhanced_bearish_crossover'] = (
            result['bearish_crossover'] &
            result['volume_expansion']
        )
    else:
        result['enhanced_bullish_crossover'] = result['bullish_crossover']
        result['enhanced_bearish_crossover'] = result['bearish_crossover']

    # Combined strategy signals
    result['ma_long_signal'] = (
        result['enhanced_bullish_crossover'] |
        (result['confirmed_long_entry'] & result['bullish_bias'])
    )

    result['ma_short_signal'] = (
        result['enhanced_bearish_crossover'] |
        (result['confirmed_short_entry'] & result['bearish_bias'])
    )

    # Risk management levels
    result['long_risk_level'] = result['long_stop_level']
    result['short_risk_level'] = result['short_stop_level']

    return result


def calculate_ma_support_resistance(close: pd.Series, high: pd.Series, low: pd.Series,
                                  periods: list[int] = [20, 50, 200]) -> pd.DataFrame:
    """Identify MA-based support and resistance levels."""
    result = pd.DataFrame(index=close.index)

    for period in periods:
        ma = calculate_ema(close, period)
        result[f'ma_{period}'] = ma

        # Support/resistance identification
        result[f'ma_{period}_support'] = (low <= ma) & (close > ma)
        result[f'ma_{period}_resistance'] = (high >= ma) & (close < ma)

        # Distance to MA (for entry timing)
        result[f'distance_to_ma_{period}'] = (close - ma) / ma * 100

    # Dynamic support/resistance based on recent price action
    result['key_ma_support'] = False
    result['key_ma_resistance'] = False

    for period in periods:
        result['key_ma_support'] |= result[f'ma_{period}_support']
        result['key_ma_resistance'] |= result[f'ma_{period}_resistance']

    return result