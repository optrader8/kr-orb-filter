"""Momentum indicators for Linda Raschke strategies."""
from __future__ import annotations

import pandas as pd
import numpy as np


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate standard RSI."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_rsi2(close: pd.Series) -> pd.Series:
    """Calculate 2-period RSI for Linda's Anti-Swing strategy."""
    return calculate_rsi(close, period=2)


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                        k_period: int = 14, d_period: int = 3) -> tuple[pd.Series, pd.Series]:
    """Calculate Stochastic oscillator (%K and %D)."""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    # %K calculation
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))

    # %D is the moving average of %K
    d_percent = k_percent.rolling(window=d_period).mean()

    return k_percent, d_percent


def stochastic_crossover_signals(k_percent: pd.Series, d_percent: pd.Series,
                               oversold_level: float = 20,
                               overbought_level: float = 80) -> pd.DataFrame:
    """Generate stochastic crossover signals for entry timing."""
    result = pd.DataFrame(index=k_percent.index)

    # Previous values for crossover detection
    k_prev = k_percent.shift(1)
    d_prev = d_percent.shift(1)

    # Basic crossover signals
    result['bullish_crossover'] = (k_percent > d_percent) & (k_prev <= d_prev)
    result['bearish_crossover'] = (k_percent < d_percent) & (k_prev >= d_prev)

    # Oversold/overbought conditions
    result['oversold'] = (k_percent < oversold_level) & (d_percent < oversold_level)
    result['overbought'] = (k_percent > overbought_level) & (d_percent > overbought_level)

    # High-quality signals (crossovers in extreme zones)
    result['quality_long_signal'] = result['bullish_crossover'] & result['oversold']
    result['quality_short_signal'] = result['bearish_crossover'] & result['overbought']

    return result


def momentum_divergence(close: pd.Series, rsi: pd.Series, period: int = 5) -> pd.DataFrame:
    """Detect momentum divergence between price and RSI."""
    result = pd.DataFrame(index=close.index)

    # Calculate price and RSI trends over the period
    price_change = close.diff(period)
    rsi_change = rsi.diff(period)

    # Bullish divergence: price makes lower low, RSI makes higher low
    result['bullish_divergence'] = (price_change < 0) & (rsi_change > 0)

    # Bearish divergence: price makes higher high, RSI makes lower high
    result['bearish_divergence'] = (price_change > 0) & (rsi_change < 0)

    return result


def rsi2_extreme_signals(close: pd.Series,
                        oversold_threshold: float = 10,
                        overbought_threshold: float = 90) -> pd.DataFrame:
    """Generate RSI2 extreme signals for Anti-Swing strategy."""
    rsi2 = calculate_rsi2(close)

    result = pd.DataFrame(index=close.index)
    result['rsi2'] = rsi2

    # Extreme conditions
    result['rsi2_oversold'] = rsi2 < oversold_threshold
    result['rsi2_overbought'] = rsi2 > overbought_threshold

    # Count consecutive days in extreme territory
    result['oversold_days'] = (result['rsi2_oversold'].groupby(
        (result['rsi2_oversold'] != result['rsi2_oversold'].shift()).cumsum()
    ).cumcount() + 1) * result['rsi2_oversold']

    result['overbought_days'] = (result['rsi2_overbought'].groupby(
        (result['rsi2_overbought'] != result['rsi2_overbought'].shift()).cumsum()
    ).cumcount() + 1) * result['rsi2_overbought']

    # Anti-swing setup conditions
    result['anti_swing_long_setup'] = (
        result['rsi2_oversold'] &
        (result['oversold_days'] >= 2)  # At least 2 days oversold
    )

    result['anti_swing_short_setup'] = (
        result['rsi2_overbought'] &
        (result['overbought_days'] >= 2)  # At least 2 days overbought
    )

    return result


def calculate_momentum_score(close: pd.Series, high: pd.Series, low: pd.Series,
                           rsi_period: int = 14,
                           stoch_k_period: int = 14,
                           stoch_d_period: int = 3) -> pd.DataFrame:
    """Calculate comprehensive momentum score for Linda's strategies."""
    result = pd.DataFrame(index=close.index)

    # Calculate indicators
    rsi14 = calculate_rsi(close, rsi_period)
    rsi2 = calculate_rsi2(close)
    k_percent, d_percent = calculate_stochastic(high, low, close, stoch_k_period, stoch_d_period)

    # Store raw indicators
    result['rsi14'] = rsi14
    result['rsi2'] = rsi2
    result['stoch_k'] = k_percent
    result['stoch_d'] = d_percent

    # Get signals
    rsi2_signals = rsi2_extreme_signals(close)
    stoch_signals = stochastic_crossover_signals(k_percent, d_percent)
    divergence_signals = momentum_divergence(close, rsi14)

    # Combine signals
    result = result.join(rsi2_signals[['rsi2_oversold', 'rsi2_overbought',
                                     'anti_swing_long_setup', 'anti_swing_short_setup']])
    result = result.join(stoch_signals[['quality_long_signal', 'quality_short_signal',
                                       'oversold', 'overbought']])
    result = result.join(divergence_signals)

    # Calculate momentum score
    momentum_score = 0

    # RSI2 extreme conditions (for anti-swing)
    momentum_score += result['anti_swing_long_setup'].astype(int) * 3
    momentum_score -= result['anti_swing_short_setup'].astype(int) * 3

    # Stochastic quality signals
    momentum_score += result['quality_long_signal'].astype(int) * 2
    momentum_score -= result['quality_short_signal'].astype(int) * 2

    # Divergence signals
    momentum_score += result['bullish_divergence'].astype(int) * 2
    momentum_score -= result['bearish_divergence'].astype(int) * 2

    result['momentum_score'] = momentum_score

    return result


def validate_anti_swing_conditions(close: pd.Series, high: pd.Series, low: pd.Series,
                                 strong_move_days: int = 3,
                                 strong_move_threshold: float = 0.05) -> pd.DataFrame:
    """Validate conditions for Anti-Swing strategy entry."""
    result = pd.DataFrame(index=close.index)

    # Calculate recent price movement
    price_change = close.pct_change(strong_move_days)
    result['strong_decline'] = price_change < -strong_move_threshold
    result['strong_rally'] = price_change > strong_move_threshold

    # Get RSI2 signals
    rsi2_signals = rsi2_extreme_signals(close)

    # Combine conditions for valid Anti-Swing setups
    result['valid_anti_swing_long'] = (
        result['strong_decline'] &
        rsi2_signals['anti_swing_long_setup']
    )

    result['valid_anti_swing_short'] = (
        result['strong_rally'] &
        rsi2_signals['anti_swing_short_setup']
    )

    return result