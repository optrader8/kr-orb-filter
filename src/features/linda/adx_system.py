"""ADX/DMI system implementation for trend strength and direction."""
from __future__ import annotations

import pandas as pd
import numpy as np


def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calculate True Range for ADX calculation."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    return pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)


def calculate_directional_movement(high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Calculate positive and negative directional movement."""
    high_diff = high.diff()
    low_diff = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)

    # Plus DM: high_diff > low_diff and high_diff > 0
    plus_condition = (high_diff > low_diff) & (high_diff > 0)
    plus_dm[plus_condition] = high_diff[plus_condition]

    # Minus DM: low_diff > high_diff and low_diff > 0
    minus_condition = (low_diff > high_diff) & (low_diff > 0)
    minus_dm[minus_condition] = low_diff[minus_condition]

    return plus_dm, minus_dm


def calculate_di(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series]:
    """Calculate Directional Indicators (+DI and -DI)."""
    true_range = calculate_true_range(high, low, close)
    plus_dm, minus_dm = calculate_directional_movement(high, low)

    # Smooth the values using Wilder's smoothing (similar to EMA with alpha = 1/period)
    alpha = 1.0 / period

    smoothed_tr = true_range.ewm(alpha=alpha, adjust=False).mean()
    smoothed_plus_dm = plus_dm.ewm(alpha=alpha, adjust=False).mean()
    smoothed_minus_dm = minus_dm.ewm(alpha=alpha, adjust=False).mean()

    plus_di = 100 * (smoothed_plus_dm / smoothed_tr)
    minus_di = 100 * (smoothed_minus_dm / smoothed_tr)

    return plus_di, minus_di


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate ADX (Average Directional Index) along with +DI and -DI."""
    plus_di, minus_di = calculate_di(high, low, close, period)

    # Calculate DX (Directional Index)
    di_sum = plus_di + minus_di
    di_diff = (plus_di - minus_di).abs()

    # Avoid division by zero
    dx = pd.Series(0.0, index=high.index)
    non_zero_mask = di_sum != 0
    dx[non_zero_mask] = 100 * (di_diff[non_zero_mask] / di_sum[non_zero_mask])

    # Smooth DX to get ADX using Wilder's smoothing
    alpha = 1.0 / period
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    return adx, plus_di, minus_di


def adx_trend_filter(high: pd.Series, low: pd.Series, close: pd.Series,
                    strong_threshold: float = 30.0,
                    weak_threshold: float = 20.0,
                    period: int = 14) -> pd.DataFrame:
    """
    Apply ADX trend filter according to Linda Raschke's methodology.

    Returns DataFrame with trend strength and direction signals.
    """
    adx, plus_di, minus_di = calculate_adx(high, low, close, period)

    result = pd.DataFrame(index=high.index)
    result['adx'] = adx
    result['plus_di'] = plus_di
    result['minus_di'] = minus_di

    # Trend strength classification
    result['trend_strong'] = adx > strong_threshold
    result['trend_weak'] = adx < weak_threshold
    result['trend_moderate'] = (adx >= weak_threshold) & (adx <= strong_threshold)

    # Trend direction
    result['bullish_bias'] = plus_di > minus_di
    result['bearish_bias'] = minus_di > plus_di

    # Combined signals for Linda's methodology
    result['strong_uptrend'] = result['trend_strong'] & result['bullish_bias']
    result['strong_downtrend'] = result['trend_strong'] & result['bearish_bias']
    result['choppy_market'] = result['trend_weak']

    # Strategy recommendations based on ADX
    result['use_trend_following'] = result['trend_strong']
    result['use_mean_reversion'] = result['trend_weak']
    result['caution_zone'] = result['trend_moderate']

    return result


def calculate_adx_slope(adx: pd.Series, period: int = 5) -> pd.Series:
    """Calculate ADX slope to identify trend strength changes."""
    return adx.diff(period)


def adx_crossover_signals(plus_di: pd.Series, minus_di: pd.Series) -> pd.DataFrame:
    """Generate crossover signals between +DI and -DI."""
    result = pd.DataFrame(index=plus_di.index)

    # Current and previous values
    plus_di_prev = plus_di.shift(1)
    minus_di_prev = minus_di.shift(1)

    # Crossover signals
    result['bullish_crossover'] = (plus_di > minus_di) & (plus_di_prev <= minus_di_prev)
    result['bearish_crossover'] = (minus_di > plus_di) & (minus_di_prev <= plus_di_prev)

    return result


def linda_adx_strategy_signals(high: pd.Series, low: pd.Series, close: pd.Series,
                              adx_period: int = 14,
                              strong_adx_threshold: float = 30.0,
                              weak_adx_threshold: float = 20.0) -> pd.DataFrame:
    """
    Generate comprehensive ADX-based strategy signals according to Linda Raschke's methodology.

    This combines trend strength, direction, and timing for strategy selection.
    """
    # Get basic ADX system
    adx_data = adx_trend_filter(high, low, close, strong_adx_threshold, weak_adx_threshold, adx_period)

    # Get crossover signals
    crossover_signals = adx_crossover_signals(adx_data['plus_di'], adx_data['minus_di'])

    # Combine into comprehensive signal set
    result = adx_data.copy()
    result = result.join(crossover_signals)

    # ADX slope for trend acceleration/deceleration
    result['adx_slope'] = calculate_adx_slope(result['adx'])
    result['adx_rising'] = result['adx_slope'] > 0
    result['adx_falling'] = result['adx_slope'] < 0

    # High-confidence signals
    result['high_confidence_long'] = (
        result['strong_uptrend'] &
        result['adx_rising'] &
        result['bullish_crossover']
    )

    result['high_confidence_short'] = (
        result['strong_downtrend'] &
        result['adx_rising'] &
        result['bearish_crossover']
    )

    # Strategy mode recommendations
    result['holy_grail_mode'] = result['trend_strong']  # Strong trend for pullback entries
    result['turtle_soup_mode'] = result['trend_weak']   # Weak trend for false breakout fades
    result['anti_swing_mode'] = result['trend_moderate']  # Moderate trend for counter-trend

    return result