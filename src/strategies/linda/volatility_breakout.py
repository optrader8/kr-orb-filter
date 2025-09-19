"""Volatility Breakout Strategy - Linda Raschke.

Combines volatility contraction/expansion with NR7 patterns for breakout detection.
Targets 2-3x the recent range when volatility expands after contraction.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import datetime as dt

from src.features.linda.patterns import NarrowRangePattern
from src.config import get_linda_strategy_config


@dataclass
class VolatilityBreakoutSignal:
    """Volatility breakout signal."""
    timestamp: pd.Timestamp
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    target_price: float
    confidence: float
    volatility_contraction_days: int
    nr_pattern: str  # NR7, NR4, ID etc.
    volume_confirmation: bool
    range_expansion_ratio: float


@dataclass
class VolatilityMetrics:
    """Volatility analysis metrics."""
    current_volatility: float
    volatility_percentile: float  # 0-100 percentile rank
    contraction_days: int
    expansion_potential: float
    is_contracted: bool
    breakout_threshold: float


class VolatilityBreakoutStrategy:
    """
    Volatility Breakout Strategy.

    Strategy Logic:
    1. Detect volatility contraction (low volatility periods)
    2. Identify narrow range patterns (NR7, NR4)
    3. Wait for breakout with volume confirmation
    4. Target 2-3x recent range expansion
    5. Use tight stops based on pattern support/resistance
    """

    def __init__(self):
        self.config = get_linda_strategy_config('volatility_breakout')
        self.nr_pattern = NarrowRangePattern()

        # Strategy parameters
        self.volatility_lookback = self.config.parameters.get('volatility_lookback', 20)
        self.contraction_threshold = self.config.parameters.get('contraction_threshold', 25)  # percentile
        self.expansion_multiplier = self.config.parameters.get('expansion_multiplier', 2.5)
        self.volume_threshold = self.config.parameters.get('volume_threshold', 1.2)
        self.min_contraction_days = self.config.parameters.get('min_contraction_days', 3)

    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze volatility patterns and generate signals.

        Args:
            data: OHLCV DataFrame

        Returns:
            DataFrame with volatility analysis and signals
        """
        df = data.copy()

        # Calculate volatility metrics
        volatility_metrics = self._calculate_volatility_metrics(df)

        # Add volatility columns
        for key, values in volatility_metrics.items():
            df[f'vb_{key}'] = values

        # Detect narrow range patterns
        nr_patterns = self._detect_narrow_range_patterns(df)
        df['vb_nr_pattern'] = nr_patterns

        # Identify volatility contraction
        contraction_signals = self._identify_contraction_periods(df)
        df['vb_contraction'] = contraction_signals

        # Generate breakout signals
        signals = self._generate_breakout_signals(df)
        df['vb_signal'] = signals

        # Calculate confidence scores
        confidence = self._calculate_confidence(df)
        df['vb_confidence'] = confidence

        return df

    def get_signals(self, data: pd.DataFrame) -> List[VolatilityBreakoutSignal]:
        """
        Get volatility breakout signals.

        Args:
            data: OHLCV DataFrame

        Returns:
            List of VolatilityBreakoutSignal objects
        """
        df = self.analyze(data)
        signals = []

        # Find signal rows
        signal_rows = df[df['vb_signal'].notna() & (df['vb_signal'] != 0)]

        for idx, row in signal_rows.iterrows():
            try:
                signal = self._create_signal(row, df)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"Error creating volatility breakout signal: {e}")
                continue

        return signals

    def _calculate_volatility_metrics(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate comprehensive volatility metrics."""
        # True range
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )

        # Average True Range
        atr = df['tr'].rolling(self.volatility_lookback).mean()

        # Price-based volatility (returns)
        returns = df['close'].pct_change()
        price_volatility = returns.rolling(self.volatility_lookback).std() * np.sqrt(252)

        # Range-based volatility
        range_volatility = (df['high'] - df['low']) / df['close']
        avg_range_volatility = range_volatility.rolling(self.volatility_lookback).mean()

        # Volatility percentile rank
        volatility_percentile = price_volatility.rolling(100).rank(pct=True) * 100

        # Contraction detection
        is_contracted = volatility_percentile < self.contraction_threshold

        # Count consecutive contraction days
        contraction_days = pd.Series(0, index=df.index)
        consecutive_count = 0

        for i in range(len(is_contracted)):
            if is_contracted.iloc[i]:
                consecutive_count += 1
            else:
                consecutive_count = 0
            contraction_days.iloc[i] = consecutive_count

        # Expansion potential (inverse of current volatility percentile)
        expansion_potential = 100 - volatility_percentile

        # Breakout threshold (dynamic based on recent range)
        recent_range = (df['high'].rolling(5).max() - df['low'].rolling(5).min())
        breakout_threshold = recent_range * 0.5  # 50% of recent range

        return {
            'atr': atr,
            'price_volatility': price_volatility,
            'range_volatility': avg_range_volatility,
            'volatility_percentile': volatility_percentile,
            'is_contracted': is_contracted,
            'contraction_days': contraction_days,
            'expansion_potential': expansion_potential,
            'breakout_threshold': breakout_threshold
        }

    def _detect_narrow_range_patterns(self, df: pd.DataFrame) -> pd.Series:
        """Detect narrow range patterns (NR7, NR4, etc.)."""
        patterns = pd.Series('', index=df.index)

        # Calculate daily range
        daily_range = df['high'] - df['low']

        # NR7 - Narrowest range in 7 days
        for i in range(7, len(df)):
            current_range = daily_range.iloc[i]
            recent_ranges = daily_range.iloc[i-6:i]  # Previous 6 days

            if current_range == recent_ranges.min():
                patterns.iloc[i] = 'NR7'

        # NR4 - Narrowest range in 4 days
        for i in range(4, len(df)):
            current_range = daily_range.iloc[i]
            recent_ranges = daily_range.iloc[i-3:i]  # Previous 3 days

            if current_range == recent_ranges.min() and patterns.iloc[i] == '':
                patterns.iloc[i] = 'NR4'

        # Inside Day (ID) - Range inside previous day
        for i in range(1, len(df)):
            if (df['high'].iloc[i] < df['high'].iloc[i-1] and
                df['low'].iloc[i] > df['low'].iloc[i-1] and
                patterns.iloc[i] == ''):
                patterns.iloc[i] = 'ID'

        return patterns

    def _identify_contraction_periods(self, df: pd.DataFrame) -> pd.Series:
        """Identify volatility contraction periods ready for breakout."""
        contraction_signals = pd.Series(0, index=df.index)

        for i in range(len(df)):
            # Must have volatility contraction
            if not df['vb_is_contracted'].iloc[i]:
                continue

            # Must have minimum contraction days
            if df['vb_contraction_days'].iloc[i] < self.min_contraction_days:
                continue

            # Must have narrow range pattern
            if df['vb_nr_pattern'].iloc[i] == '':
                continue

            # High expansion potential
            if df['vb_expansion_potential'].iloc[i] < 60:  # Top 40% expansion potential
                continue

            contraction_signals.iloc[i] = 1

        return contraction_signals

    def _generate_breakout_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate breakout signals when price breaks out of contraction."""
        signals = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            # Must be in contraction setup
            if df['vb_contraction'].iloc[i-1] != 1:
                continue

            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            prev_high = df['high'].iloc[i-1]
            prev_low = df['low'].iloc[i-1]

            # Breakout threshold
            threshold = df['vb_breakout_threshold'].iloc[i]

            # Volume confirmation
            volume_ok = True
            if 'volume' in df.columns:
                avg_volume = df['volume'].rolling(20).mean().iloc[i]
                current_volume = df['volume'].iloc[i]
                volume_ok = current_volume > avg_volume * self.volume_threshold

            # Upside breakout
            if (current_high > prev_high + threshold and volume_ok):
                signals.iloc[i] = 1  # LONG

            # Downside breakout
            elif (current_low < prev_low - threshold and volume_ok):
                signals.iloc[i] = -1  # SHORT

        return signals

    def _calculate_confidence(self, df: pd.DataFrame) -> pd.Series:
        """Calculate confidence scores for signals."""
        confidence = pd.Series(0.0, index=df.index)

        signal_rows = df['vb_signal'] != 0

        for i in range(len(df)):
            if not signal_rows.iloc[i]:
                continue

            score = 0.3  # Base confidence

            # Volatility contraction strength
            volatility_percentile = df['vb_volatility_percentile'].iloc[i]
            if volatility_percentile < 10:  # Extreme contraction
                score += 0.3
            elif volatility_percentile < 25:
                score += 0.2

            # Contraction duration
            contraction_days = df['vb_contraction_days'].iloc[i-1] if i > 0 else 0
            if contraction_days >= 7:
                score += 0.2
            elif contraction_days >= 5:
                score += 0.1

            # Pattern quality
            pattern = df['vb_nr_pattern'].iloc[i-1] if i > 0 else ''
            if pattern == 'NR7':
                score += 0.15
            elif pattern == 'NR4':
                score += 0.1
            elif pattern == 'ID':
                score += 0.05

            # Expansion potential
            expansion_potential = df['vb_expansion_potential'].iloc[i]
            if expansion_potential > 80:
                score += 0.1
            elif expansion_potential > 60:
                score += 0.05

            # Volume confirmation
            if 'volume' in df.columns:
                avg_volume = df['volume'].rolling(20).mean().iloc[i]
                current_volume = df['volume'].iloc[i]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

                if volume_ratio > 2.0:
                    score += 0.1
                elif volume_ratio > 1.5:
                    score += 0.05

            confidence.iloc[i] = min(1.0, score)

        return confidence

    def _create_signal(self, row: pd.Series, df: pd.DataFrame) -> Optional[VolatilityBreakoutSignal]:
        """Create VolatilityBreakoutSignal from analysis row."""
        try:
            signal_value = row['vb_signal']
            direction = 'LONG' if signal_value > 0 else 'SHORT'

            # Entry price
            if direction == 'LONG':
                entry_price = row['high']
            else:
                entry_price = row['low']

            # Calculate target and stop loss
            recent_range = row['vb_atr'] if 'vb_atr' in row else (row['high'] - row['low'])
            target_distance = recent_range * self.expansion_multiplier

            if direction == 'LONG':
                target_price = entry_price + target_distance
                stop_loss = row['low'] - recent_range * 0.3  # 30% of range below low
            else:
                target_price = entry_price - target_distance
                stop_loss = row['high'] + recent_range * 0.3  # 30% of range above high

            # Volume confirmation
            volume_confirmation = True
            if 'volume' in df.columns:
                idx = df.index.get_loc(row.name)
                if idx > 0:
                    avg_volume = df['volume'].iloc[max(0, idx-19):idx+1].mean()
                    volume_confirmation = row['volume'] > avg_volume * self.volume_threshold

            # Get pattern info
            idx = df.index.get_loc(row.name)
            nr_pattern = df['vb_nr_pattern'].iloc[idx-1] if idx > 0 else ''
            contraction_days = df['vb_contraction_days'].iloc[idx-1] if idx > 0 else 0

            # Range expansion ratio
            if idx > 0:
                current_range = row['high'] - row['low']
                prev_range = df['high'].iloc[idx-1] - df['low'].iloc[idx-1]
                range_expansion_ratio = current_range / prev_range if prev_range > 0 else 1.0
            else:
                range_expansion_ratio = 1.0

            return VolatilityBreakoutSignal(
                timestamp=row.name,
                symbol=row.get('symbol', ''),
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                confidence=row['vb_confidence'],
                volatility_contraction_days=int(contraction_days),
                nr_pattern=nr_pattern,
                volume_confirmation=volume_confirmation,
                range_expansion_ratio=range_expansion_ratio
            )

        except Exception as e:
            print(f"Error creating volatility breakout signal: {e}")
            return None

    def get_pattern_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed pattern analysis for the current data."""
        df = self.analyze(data)

        if len(df) == 0:
            return {}

        latest = df.iloc[-1]

        # Current volatility state
        volatility_state = "NORMAL"
        if latest['vb_volatility_percentile'] < 25:
            volatility_state = "CONTRACTED"
        elif latest['vb_volatility_percentile'] > 75:
            volatility_state = "EXPANDED"

        # Pattern summary
        recent_patterns = df['vb_nr_pattern'].tail(5).value_counts()

        analysis = {
            'current_volatility_state': volatility_state,
            'volatility_percentile': latest['vb_volatility_percentile'],
            'contraction_days': latest['vb_contraction_days'],
            'expansion_potential': latest['vb_expansion_potential'],
            'current_pattern': latest['vb_nr_pattern'],
            'recent_patterns': recent_patterns.to_dict(),
            'breakout_ready': latest['vb_contraction'] == 1,
            'atr': latest['vb_atr'],
            'range_volatility': latest['vb_range_volatility']
        }

        return analysis

    def validate_setup(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate current volatility breakout setup."""
        analysis = self.get_pattern_analysis(data)

        validation = {
            'is_valid_setup': False,
            'score': 0.0,
            'factors': [],
            'warnings': []
        }

        # Check volatility contraction
        if analysis.get('volatility_percentile', 50) < 25:
            validation['score'] += 0.3
            validation['factors'].append('Low volatility (contracted)')
        else:
            validation['warnings'].append('Volatility not contracted')

        # Check contraction duration
        contraction_days = analysis.get('contraction_days', 0)
        if contraction_days >= 5:
            validation['score'] += 0.2
            validation['factors'].append(f'{contraction_days} days of contraction')
        elif contraction_days >= 3:
            validation['score'] += 0.1
            validation['factors'].append(f'{contraction_days} days of contraction')
        else:
            validation['warnings'].append('Insufficient contraction period')

        # Check narrow range pattern
        current_pattern = analysis.get('current_pattern', '')
        if current_pattern in ['NR7', 'NR4', 'ID']:
            validation['score'] += 0.2
            validation['factors'].append(f'{current_pattern} pattern')
        else:
            validation['warnings'].append('No narrow range pattern')

        # Check expansion potential
        expansion_potential = analysis.get('expansion_potential', 0)
        if expansion_potential > 70:
            validation['score'] += 0.2
            validation['factors'].append('High expansion potential')
        elif expansion_potential > 50:
            validation['score'] += 0.1
            validation['factors'].append('Moderate expansion potential')

        # Overall validation
        validation['is_valid_setup'] = (
            validation['score'] >= 0.5 and
            len(validation['warnings']) <= 1
        )

        return validation