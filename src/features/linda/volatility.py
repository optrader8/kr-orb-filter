"""Volatility calculations and analysis for Linda Raschke strategies."""
from __future__ import annotations

import pandas as pd
import numpy as np


def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calculate True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    return pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)


def enhanced_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
    """Calculate enhanced ATR with additional volatility metrics."""
    result = pd.DataFrame(index=high.index)

    # Basic ATR calculation
    true_range = calculate_true_range(high, low, close)
    atr = true_range.rolling(window=period).mean()

    result['true_range'] = true_range
    result['atr'] = atr

    # ATR as percentage of price
    result['atr_percent'] = (atr / close) * 100

    # ATR percentile over longer period
    atr_percentile_period = period * 4
    result['atr_percentile'] = atr.rolling(window=atr_percentile_period).rank(pct=True)

    # Volatility classifications
    result['low_volatility'] = result['atr_percentile'] < 0.2
    result['normal_volatility'] = (result['atr_percentile'] >= 0.2) & (result['atr_percentile'] <= 0.8)
    result['high_volatility'] = result['atr_percentile'] > 0.8

    # ATR trend
    result['atr_sma'] = atr.rolling(window=5).mean()
    result['atr_rising'] = atr > result['atr_sma']
    result['atr_falling'] = atr < result['atr_sma']

    return result


def volatility_contraction(high: pd.Series, low: pd.Series, close: pd.Series,
                         contraction_period: int = 5,
                         lookback_period: int = 20) -> pd.DataFrame:
    """Detect volatility contraction patterns (NR patterns)."""
    result = pd.DataFrame(index=high.index)

    # Calculate range
    daily_range = high - low
    result['daily_range'] = daily_range

    # Rolling minimum range over different periods
    for period in [4, 5, 6, 7, 10]:
        rolling_min = daily_range.rolling(window=period).min()
        result[f'nr{period}'] = (daily_range == rolling_min)

    # ATR-based contraction
    atr_data = enhanced_atr(high, low, close)
    result['atr'] = atr_data['atr']

    # Current range vs average range
    avg_range = daily_range.rolling(window=lookback_period).mean()
    result['range_ratio'] = daily_range / avg_range

    # Contraction signals
    result['range_contraction'] = result['range_ratio'] < 0.7  # 30% below average
    result['extreme_contraction'] = result['range_ratio'] < 0.5  # 50% below average

    # Consecutive contraction days
    result['contraction_days'] = (result['range_contraction'].groupby(
        (result['range_contraction'] != result['range_contraction'].shift()).cumsum()
    ).cumcount() + 1) * result['range_contraction']

    # Multi-day contraction patterns
    result['nr7_plus_contraction'] = result['nr7'] & (result['contraction_days'] >= 2)

    return result


def volatility_expansion(high: pd.Series, low: pd.Series, close: pd.Series,
                        expansion_threshold: float = 1.5,
                        lookback_period: int = 20) -> pd.DataFrame:
    """Detect volatility expansion after contraction."""
    result = pd.DataFrame(index=high.index)

    # Get contraction data
    contraction_data = volatility_contraction(high, low, close, lookback_period=lookback_period)
    result = result.join(contraction_data[['daily_range', 'range_ratio', 'atr', 'nr7']])

    # Expansion detection
    avg_range = result['daily_range'].rolling(window=lookback_period).mean()
    result['expansion_ratio'] = result['daily_range'] / avg_range

    # Expansion signals
    result['range_expansion'] = result['expansion_ratio'] > expansion_threshold
    result['extreme_expansion'] = result['expansion_ratio'] > 2.0

    # Expansion after contraction (key signal)
    result['contraction_yesterday'] = (
        contraction_data['range_contraction'].shift(1) |
        contraction_data['nr7'].shift(1)
    )

    result['expansion_after_contraction'] = (
        result['range_expansion'] &
        result['contraction_yesterday']
    )

    # ATR expansion
    result['atr_expansion'] = result['atr'] > result['atr'].rolling(window=10).mean() * 1.2

    # Volume-price expansion (if volume available)
    result['high_volume_expansion'] = result['range_expansion']  # Placeholder

    return result


def calculate_volatility_breakout_signals(high: pd.Series, low: pd.Series, close: pd.Series,
                                        volume: pd.Series = None) -> pd.DataFrame:
    """Generate volatility breakout signals according to Linda's methodology."""
    result = pd.DataFrame(index=high.index)

    # Get volatility data
    contraction_data = volatility_contraction(high, low, close)
    expansion_data = volatility_expansion(high, low, close)
    atr_data = enhanced_atr(high, low, close)

    # Combine key indicators
    result['nr7'] = contraction_data['nr7']
    result['range_contraction'] = contraction_data['range_contraction']
    result['expansion_after_contraction'] = expansion_data['expansion_after_contraction']
    result['atr'] = atr_data['atr']
    result['atr_percent'] = atr_data['atr_percent']

    # Setup identification
    result['volatility_setup'] = (
        contraction_data['nr7'] |
        contraction_data['extreme_contraction']
    )

    # Trigger identification
    result['volatility_trigger'] = expansion_data['expansion_after_contraction']

    # Volume confirmation
    if volume is not None:
        volume_ma = volume.rolling(window=20).mean()
        result['volume_expansion'] = volume > volume_ma * 1.5
        result['confirmed_breakout'] = result['volatility_trigger'] & result['volume_expansion']
    else:
        result['confirmed_breakout'] = result['volatility_trigger']

    # Target calculation (Linda's 2-3x range rule)
    narrow_range = contraction_data['daily_range'].rolling(window=7).min()
    result['breakout_target_2x'] = narrow_range * 2
    result['breakout_target_3x'] = narrow_range * 3

    # Entry levels (break of previous day's high/low after setup)
    result['breakout_high'] = high.shift(1)
    result['breakout_low'] = low.shift(1)

    # Risk levels (opposite side of narrow range)
    result['long_stop'] = result['breakout_low'] - result['atr'] * 0.5
    result['short_stop'] = result['breakout_high'] + result['atr'] * 0.5

    return result


def adaptive_stop_levels(close: pd.Series, high: pd.Series, low: pd.Series,
                        atr_multiplier: float = 1.5,
                        time_stop_days: int = 5) -> pd.DataFrame:
    """Calculate adaptive stop levels based on volatility."""
    result = pd.DataFrame(index=close.index)

    # Get ATR data
    atr_data = enhanced_atr(high, low, close)
    result['atr'] = atr_data['atr']

    # Volatility-based stops
    result['volatility_stop_long'] = close - (result['atr'] * atr_multiplier)
    result['volatility_stop_short'] = close + (result['atr'] * atr_multiplier)

    # Technical stops (support/resistance)
    support_period = 20
    resistance_period = 20
    result['support_level'] = low.rolling(window=support_period).min()
    result['resistance_level'] = high.rolling(window=resistance_period).max()

    result['technical_stop_long'] = result['support_level'] * 0.99  # 1% below support
    result['technical_stop_short'] = result['resistance_level'] * 1.01  # 1% above resistance

    # Combined stop (more conservative of the two)
    result['combined_stop_long'] = pd.DataFrame({
        'vol': result['volatility_stop_long'],
        'tech': result['technical_stop_long']
    }).min(axis=1)

    result['combined_stop_short'] = pd.DataFrame({
        'vol': result['volatility_stop_short'],
        'tech': result['technical_stop_short']
    }).max(axis=1)

    # Time-based stop tracking
    result['days_in_trade'] = range(len(result))  # Placeholder - would be updated in real trading

    return result


def volatility_regime_detection(high: pd.Series, low: pd.Series, close: pd.Series,
                               short_period: int = 10,
                               long_period: int = 50) -> pd.DataFrame:
    """Detect volatility regime changes for strategy adaptation."""
    result = pd.DataFrame(index=close.index)

    # Calculate different volatility measures
    atr_data = enhanced_atr(high, low, close)
    result['atr'] = atr_data['atr']

    # Short and long-term volatility
    result['vol_short'] = result['atr'].rolling(window=short_period).mean()
    result['vol_long'] = result['atr'].rolling(window=long_period).mean()

    # Volatility ratio
    result['vol_ratio'] = result['vol_short'] / result['vol_long']

    # Regime classification
    result['low_vol_regime'] = result['vol_ratio'] < 0.8
    result['normal_vol_regime'] = (result['vol_ratio'] >= 0.8) & (result['vol_ratio'] <= 1.2)
    result['high_vol_regime'] = result['vol_ratio'] > 1.2

    # Regime transitions
    result['entering_high_vol'] = (
        result['high_vol_regime'] &
        ~result['high_vol_regime'].shift(1)
    )

    result['entering_low_vol'] = (
        result['low_vol_regime'] &
        ~result['low_vol_regime'].shift(1)
    )

    # Strategy recommendations based on regime
    result['favor_breakouts'] = result['high_vol_regime']
    result['favor_mean_reversion'] = result['low_vol_regime']
    result['neutral_strategy'] = result['normal_vol_regime']

    return result