"""Gap Fade Strategy - Linda Raschke.

Identifies gap openings and trades for gap fill (mean reversion).
Focuses on gaps that occur without fundamental news and are likely to be filled.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import datetime as dt

from src.config import get_linda_strategy_config


@dataclass
class GapFadeSignal:
    """Gap fade signal."""
    timestamp: pd.Timestamp
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    target_price: float  # Gap fill target
    confidence: float
    gap_type: str  # 'up_gap', 'down_gap'
    gap_size_percent: float
    gap_size_atr_multiple: float
    volume_profile: str  # 'low', 'normal', 'high'
    market_context: str  # 'trend', 'range', 'reversal'


@dataclass
class GapAnalysis:
    """Gap analysis metrics."""
    has_gap: bool
    gap_type: str
    gap_size: float
    gap_size_percent: float
    gap_size_atr_multiple: float
    previous_close: float
    current_open: float
    gap_fill_target: float
    is_tradeable: bool
    fade_probability: float


class GapFadeStrategy:
    """
    Gap Fade Strategy.

    Strategy Logic:
    1. Identify significant gaps at market open
    2. Filter out gaps with fundamental news
    3. Determine gap fade probability based on:
       - Gap size relative to ATR
       - Market context (trend vs range)
       - Volume characteristics
       - Time of day effects
    4. Enter counter-gap position targeting gap fill
    5. Use tight stops beyond gap extreme
    """

    def __init__(self):
        self.config = get_linda_strategy_config('gap_fade')

        # Strategy parameters
        self.min_gap_percent = self.config.parameters.get('min_gap_percent', 0.5)  # 0.5%
        self.max_gap_percent = self.config.parameters.get('max_gap_percent', 3.0)  # 3%
        self.min_gap_atr_multiple = self.config.parameters.get('min_gap_atr_multiple', 0.5)
        self.max_gap_atr_multiple = self.config.parameters.get('max_gap_atr_multiple', 2.0)

        # Volume thresholds
        self.low_volume_threshold = self.config.parameters.get('low_volume_threshold', 0.7)
        self.high_volume_threshold = self.config.parameters.get('high_volume_threshold', 1.5)

        # Timing parameters
        self.max_entry_time = self.config.parameters.get('max_entry_time', 120)  # 2 hours after open

        # Korean market specific
        self.market_open_time = dt.time(9, 0)  # KST 09:00
        self.market_close_time = dt.time(15, 30)  # KST 15:30

    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze gaps and generate fade signals.

        Args:
            data: OHLCV DataFrame

        Returns:
            DataFrame with gap analysis and signals
        """
        df = data.copy()

        # Calculate ATR for gap sizing
        df['atr'] = self._calculate_atr(df)

        # Identify gaps
        gap_analysis = self._identify_gaps(df)

        # Add gap analysis columns
        for key, values in gap_analysis.items():
            df[f'gf_{key}'] = values

        # Determine tradeable gaps
        tradeable = self._filter_tradeable_gaps(df)
        df['gf_tradeable'] = tradeable

        # Generate fade signals
        signals = self._generate_fade_signals(df)
        df['gf_signal'] = signals

        # Calculate confidence
        confidence = self._calculate_confidence(df)
        df['gf_confidence'] = confidence

        return df

    def get_signals(self, data: pd.DataFrame) -> List[GapFadeSignal]:
        """
        Get gap fade signals.

        Args:
            data: OHLCV DataFrame

        Returns:
            List of GapFadeSignal objects
        """
        df = self.analyze(data)
        signals = []

        # Find signal rows
        signal_rows = df[df['gf_signal'].notna() & (df['gf_signal'] != 0)]

        for idx, row in signal_rows.iterrows():
            try:
                signal = self._create_signal(row, df)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"Error creating gap fade signal: {e}")
                continue

        return signals

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(period).mean()

        return atr

    def _identify_gaps(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Identify and analyze gaps."""
        # Gap detection
        has_gap = pd.Series(False, index=df.index)
        gap_type = pd.Series('', index=df.index)
        gap_size = pd.Series(0.0, index=df.index)
        gap_size_percent = pd.Series(0.0, index=df.index)
        gap_size_atr_multiple = pd.Series(0.0, index=df.index)
        previous_close = pd.Series(0.0, index=df.index)
        current_open = pd.Series(0.0, index=df.index)
        gap_fill_target = pd.Series(0.0, index=df.index)

        for i in range(1, len(df)):
            prev_close = df['close'].iloc[i-1]
            curr_open = df['open'].iloc[i]
            curr_atr = df['atr'].iloc[i]

            # Calculate gap size
            gap_amount = curr_open - prev_close
            gap_percent = abs(gap_amount / prev_close) * 100
            gap_atr_multiple = abs(gap_amount / curr_atr) if curr_atr > 0 else 0

            # Store values
            previous_close.iloc[i] = prev_close
            current_open.iloc[i] = curr_open
            gap_size.iloc[i] = gap_amount
            gap_size_percent.iloc[i] = gap_percent
            gap_size_atr_multiple.iloc[i] = gap_atr_multiple

            # Check if significant gap
            if gap_percent >= self.min_gap_percent:
                has_gap.iloc[i] = True

                if gap_amount > 0:
                    gap_type.iloc[i] = 'up_gap'
                    gap_fill_target.iloc[i] = prev_close  # Fill down to previous close
                else:
                    gap_type.iloc[i] = 'down_gap'
                    gap_fill_target.iloc[i] = prev_close  # Fill up to previous close

        return {
            'has_gap': has_gap,
            'gap_type': gap_type,
            'gap_size': gap_size,
            'gap_size_percent': gap_size_percent,
            'gap_size_atr_multiple': gap_size_atr_multiple,
            'previous_close': previous_close,
            'current_open': current_open,
            'gap_fill_target': gap_fill_target
        }

    def _filter_tradeable_gaps(self, df: pd.DataFrame) -> pd.Series:
        """Filter for tradeable gaps based on criteria."""
        tradeable = pd.Series(False, index=df.index)

        for i in range(len(df)):
            if not df['gf_has_gap'].iloc[i]:
                continue

            gap_percent = df['gf_gap_size_percent'].iloc[i]
            gap_atr_multiple = df['gf_gap_size_atr_multiple'].iloc[i]

            # Gap size filters
            if gap_percent < self.min_gap_percent or gap_percent > self.max_gap_percent:
                continue

            if gap_atr_multiple < self.min_gap_atr_multiple or gap_atr_multiple > self.max_gap_atr_multiple:
                continue

            # Volume analysis
            volume_profile = self._analyze_volume_profile(df, i)

            # Only trade gaps with normal or low volume (avoid news-driven gaps)
            if volume_profile == 'high':
                continue

            # Market context analysis
            market_context = self._analyze_market_context(df, i)

            # Avoid gaps in strong trending markets
            if market_context == 'strong_trend':
                continue

            tradeable.iloc[i] = True

        return tradeable

    def _analyze_volume_profile(self, df: pd.DataFrame, idx: int) -> str:
        """Analyze volume profile for gap assessment."""
        if 'volume' not in df.columns or idx == 0:
            return 'normal'

        current_volume = df['volume'].iloc[idx]

        # Calculate average volume (20-day)
        start_idx = max(0, idx - 19)
        avg_volume = df['volume'].iloc[start_idx:idx].mean()

        if avg_volume == 0:
            return 'normal'

        volume_ratio = current_volume / avg_volume

        if volume_ratio < self.low_volume_threshold:
            return 'low'
        elif volume_ratio > self.high_volume_threshold:
            return 'high'
        else:
            return 'normal'

    def _analyze_market_context(self, df: pd.DataFrame, idx: int) -> str:
        """Analyze market context for gap assessment."""
        if idx < 20:
            return 'range'

        # Calculate trend indicators
        close_prices = df['close'].iloc[idx-19:idx+1]

        # Simple trend analysis using moving averages
        sma_5 = close_prices.tail(5).mean()
        sma_20 = close_prices.mean()

        current_price = df['close'].iloc[idx]

        # Trend strength
        if current_price > sma_5 > sma_20:
            # Check trend strength
            trend_slope = (sma_5 - sma_20) / sma_20
            if trend_slope > 0.02:  # 2% slope
                return 'strong_trend'
            else:
                return 'trend'
        elif current_price < sma_5 < sma_20:
            # Check trend strength
            trend_slope = (sma_20 - sma_5) / sma_20
            if trend_slope > 0.02:  # 2% slope
                return 'strong_trend'
            else:
                return 'trend'
        else:
            return 'range'

    def _generate_fade_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate gap fade signals."""
        signals = pd.Series(0, index=df.index)

        for i in range(len(df)):
            if not df['gf_tradeable'].iloc[i]:
                continue

            gap_type = df['gf_gap_type'].iloc[i]

            # Entry conditions based on gap type
            if gap_type == 'up_gap':
                # Fade up gaps (go short)
                # Enter if price moves back toward gap
                current_price = df['close'].iloc[i]
                open_price = df['gf_current_open'].iloc[i]

                # Price should be moving back down from open
                if current_price < open_price:
                    signals.iloc[i] = -1  # SHORT

            elif gap_type == 'down_gap':
                # Fade down gaps (go long)
                # Enter if price moves back toward gap
                current_price = df['close'].iloc[i]
                open_price = df['gf_current_open'].iloc[i]

                # Price should be moving back up from open
                if current_price > open_price:
                    signals.iloc[i] = 1  # LONG

        return signals

    def _calculate_confidence(self, df: pd.DataFrame) -> pd.Series:
        """Calculate confidence scores for gap fade signals."""
        confidence = pd.Series(0.0, index=df.index)

        signal_rows = df['gf_signal'] != 0

        for i in range(len(df)):
            if not signal_rows.iloc[i]:
                continue

            score = 0.3  # Base confidence

            # Gap size scoring (moderate gaps fade better)
            gap_percent = df['gf_gap_size_percent'].iloc[i]
            if 0.5 <= gap_percent <= 1.5:  # Sweet spot
                score += 0.25
            elif 1.5 < gap_percent <= 2.5:
                score += 0.15
            elif gap_percent > 2.5:
                score += 0.05  # Large gaps less likely to fade quickly

            # Volume scoring (low volume = higher fade probability)
            volume_profile = self._analyze_volume_profile(df, i)
            if volume_profile == 'low':
                score += 0.2
            elif volume_profile == 'normal':
                score += 0.1

            # Market context scoring
            market_context = self._analyze_market_context(df, i)
            if market_context == 'range':
                score += 0.2
            elif market_context == 'trend':
                score += 0.1

            # ATR multiple scoring
            atr_multiple = df['gf_gap_size_atr_multiple'].iloc[i]
            if 0.5 <= atr_multiple <= 1.0:
                score += 0.15
            elif 1.0 < atr_multiple <= 1.5:
                score += 0.1

            # Price action confirmation
            gap_type = df['gf_gap_type'].iloc[i]
            signal = df['gf_signal'].iloc[i]

            if gap_type == 'up_gap' and signal == -1:
                # Check if price is already moving back toward gap
                open_price = df['gf_current_open'].iloc[i]
                close_price = df['close'].iloc[i]
                fade_progress = (open_price - close_price) / open_price

                if fade_progress > 0.002:  # 0.2% fade
                    score += 0.1

            elif gap_type == 'down_gap' and signal == 1:
                # Check if price is already moving back toward gap
                open_price = df['gf_current_open'].iloc[i]
                close_price = df['close'].iloc[i]
                fade_progress = (close_price - open_price) / abs(open_price)

                if fade_progress > 0.002:  # 0.2% fade
                    score += 0.1

            confidence.iloc[i] = min(1.0, score)

        return confidence

    def _create_signal(self, row: pd.Series, df: pd.DataFrame) -> Optional[GapFadeSignal]:
        """Create GapFadeSignal from analysis row."""
        try:
            signal_value = row['gf_signal']
            direction = 'LONG' if signal_value > 0 else 'SHORT'
            gap_type = row['gf_gap_type']

            # Entry price (current close)
            entry_price = row['close']

            # Target price (gap fill)
            target_price = row['gf_gap_fill_target']

            # Stop loss
            if direction == 'LONG':
                # Stop below recent low
                stop_loss = row['low'] * 0.995  # 0.5% below low
            else:
                # Stop above recent high
                stop_loss = row['high'] * 1.005  # 0.5% above high

            # Volume profile
            idx = df.index.get_loc(row.name)
            volume_profile = self._analyze_volume_profile(df, idx)

            # Market context
            market_context = self._analyze_market_context(df, idx)

            return GapFadeSignal(
                timestamp=row.name,
                symbol=row.get('symbol', ''),
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                confidence=row['gf_confidence'],
                gap_type=gap_type,
                gap_size_percent=row['gf_gap_size_percent'],
                gap_size_atr_multiple=row['gf_gap_size_atr_multiple'],
                volume_profile=volume_profile,
                market_context=market_context
            )

        except Exception as e:
            print(f"Error creating gap fade signal: {e}")
            return None

    def get_gap_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed gap analysis for current data."""
        df = self.analyze(data)

        if len(df) == 0:
            return {}

        # Find recent gaps
        recent_gaps = df[df['gf_has_gap'] == True].tail(5)

        analysis = {
            'recent_gaps_count': len(recent_gaps),
            'recent_gaps': [],
            'current_gap_opportunity': None
        }

        # Analyze recent gaps
        for idx, row in recent_gaps.iterrows():
            gap_info = {
                'timestamp': idx,
                'gap_type': row['gf_gap_type'],
                'gap_size_percent': row['gf_gap_size_percent'],
                'gap_size_atr_multiple': row['gf_gap_size_atr_multiple'],
                'is_tradeable': row['gf_tradeable'],
                'has_signal': row['gf_signal'] != 0
            }
            analysis['recent_gaps'].append(gap_info)

        # Check current opportunity
        latest = df.iloc[-1]
        if latest['gf_tradeable']:
            analysis['current_gap_opportunity'] = {
                'gap_type': latest['gf_gap_type'],
                'gap_size_percent': latest['gf_gap_size_percent'],
                'entry_signal': latest['gf_signal'] != 0,
                'confidence': latest['gf_confidence']
            }

        return analysis

    def validate_gap_trade(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate current gap trading opportunity."""
        analysis = self.get_gap_analysis(data)

        validation = {
            'has_opportunity': False,
            'score': 0.0,
            'factors': [],
            'warnings': []
        }

        current_opportunity = analysis.get('current_gap_opportunity')
        if not current_opportunity:
            validation['warnings'].append('No current gap opportunity')
            return validation

        # Gap size validation
        gap_size = current_opportunity['gap_size_percent']
        if 0.5 <= gap_size <= 2.0:
            validation['score'] += 0.3
            validation['factors'].append(f'Optimal gap size: {gap_size:.2f}%')
        elif gap_size > 3.0:
            validation['warnings'].append(f'Large gap ({gap_size:.2f}%) - lower fade probability')
        else:
            validation['warnings'].append(f'Small gap ({gap_size:.2f}%) - may not be significant')

        # Entry signal validation
        if current_opportunity['entry_signal']:
            validation['score'] += 0.3
            validation['factors'].append('Entry signal confirmed')
        else:
            validation['warnings'].append('No entry signal yet')

        # Confidence validation
        confidence = current_opportunity['confidence']
        if confidence > 0.7:
            validation['score'] += 0.2
            validation['factors'].append(f'High confidence: {confidence:.2f}')
        elif confidence > 0.5:
            validation['score'] += 0.1
            validation['factors'].append(f'Moderate confidence: {confidence:.2f}')

        validation['has_opportunity'] = validation['score'] >= 0.5

        return validation