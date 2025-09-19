"""Price pattern detection for Linda Raschke strategies.

Implements various chart patterns including narrow range patterns,
inside days, and other price formations used in Linda's methodology.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class PatternSignal:
    """Pattern detection signal."""
    pattern_type: str
    timestamp: pd.Timestamp
    strength: float  # 0-1 pattern strength
    details: Dict[str, Any]


class NarrowRangePattern:
    """
    Narrow Range Pattern Detector.

    Detects NR4, NR7, NR10 and other narrow range patterns
    that indicate volatility contraction before potential breakouts.
    """

    def __init__(self):
        self.patterns = ['NR4', 'NR7', 'NR10', 'NR20']

    def detect_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Detect narrow range patterns in OHLC data.

        Args:
            data: OHLC DataFrame

        Returns:
            DataFrame with pattern detection columns
        """
        df = data.copy()

        # Calculate daily range
        df['daily_range'] = df['high'] - df['low']

        # Detect each pattern type
        for pattern in self.patterns:
            period = int(pattern[2:])  # Extract number from pattern name
            df[f'is_{pattern.lower()}'] = self._detect_nr_pattern(df, period)

        # Combined narrow range signal
        df['narrow_range_signal'] = self._combine_nr_signals(df)

        return df

    def _detect_nr_pattern(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Detect narrow range pattern for specific period."""
        nr_signals = pd.Series(False, index=df.index)

        for i in range(period, len(df)):
            current_range = df['daily_range'].iloc[i]
            recent_ranges = df['daily_range'].iloc[i-period+1:i]  # Previous (period-1) days

            # Current day has narrowest range in the period
            if current_range == recent_ranges.min():
                nr_signals.iloc[i] = True

        return nr_signals

    def _combine_nr_signals(self, df: pd.DataFrame) -> pd.Series:
        """Combine multiple NR signals with priority."""
        combined = pd.Series('', index=df.index)

        # Priority order: NR20 > NR10 > NR7 > NR4
        pattern_priority = ['NR20', 'NR10', 'NR7', 'NR4']

        for pattern in pattern_priority:
            column = f'is_{pattern.lower()}'
            if column in df.columns:
                mask = df[column] == True
                combined.loc[mask] = pattern

        return combined

    def get_pattern_strength(self, data: pd.DataFrame, pattern_type: str = 'NR7') -> pd.Series:
        """
        Calculate pattern strength based on range compression.

        Args:
            data: OHLC DataFrame
            pattern_type: Type of NR pattern to analyze

        Returns:
            Series with pattern strength values (0-1)
        """
        df = data.copy()
        period = int(pattern_type[2:])

        strength = pd.Series(0.0, index=df.index)
        daily_range = df['high'] - df['low']

        for i in range(period, len(df)):
            current_range = daily_range.iloc[i]
            recent_ranges = daily_range.iloc[i-period+1:i]

            if len(recent_ranges) > 0:
                min_range = recent_ranges.min()
                max_range = recent_ranges.max()

                if max_range > min_range:
                    # Strength based on how much smaller current range is
                    range_compression = 1 - (current_range - min_range) / (max_range - min_range)
                    strength.iloc[i] = max(0.0, min(1.0, range_compression))

        return strength


class InsideDayPattern:
    """
    Inside Day Pattern Detector.

    Detects inside days where the entire range is within
    the previous day's high-low range.
    """

    def detect_inside_days(self, data: pd.DataFrame) -> pd.DataFrame:
        """Detect inside day patterns."""
        df = data.copy()

        df['is_inside_day'] = False
        df['inside_day_strength'] = 0.0

        for i in range(1, len(df)):
            prev_high = df['high'].iloc[i-1]
            prev_low = df['low'].iloc[i-1]
            curr_high = df['high'].iloc[i]
            curr_low = df['low'].iloc[i]

            # Inside day: current high < prev high AND current low > prev low
            if curr_high < prev_high and curr_low > prev_low:
                df.iloc[i, df.columns.get_loc('is_inside_day')] = True

                # Calculate strength based on how much inside the range is
                prev_range = prev_high - prev_low
                curr_range = curr_high - curr_low

                if prev_range > 0:
                    strength = 1.0 - (curr_range / prev_range)
                    df.iloc[i, df.columns.get_loc('inside_day_strength')] = max(0.0, min(1.0, strength))

        return df


class OutsideDayPattern:
    """
    Outside Day Pattern Detector.

    Detects outside days where the range encompasses
    the previous day's range.
    """

    def detect_outside_days(self, data: pd.DataFrame) -> pd.DataFrame:
        """Detect outside day patterns."""
        df = data.copy()

        df['is_outside_day'] = False
        df['outside_day_type'] = ''  # 'bullish' or 'bearish'
        df['outside_day_strength'] = 0.0

        for i in range(1, len(df)):
            prev_high = df['high'].iloc[i-1]
            prev_low = df['low'].iloc[i-1]
            curr_high = df['high'].iloc[i]
            curr_low = df['low'].iloc[i]
            curr_close = df['close'].iloc[i]

            # Outside day: current high > prev high AND current low < prev low
            if curr_high > prev_high and curr_low < prev_low:
                df.iloc[i, df.columns.get_loc('is_outside_day')] = True

                # Determine bullish or bearish based on close
                prev_mid = (prev_high + prev_low) / 2
                if curr_close > prev_mid:
                    df.iloc[i, df.columns.get_loc('outside_day_type')] = 'bullish'
                else:
                    df.iloc[i, df.columns.get_loc('outside_day_type')] = 'bearish'

                # Calculate strength based on range expansion
                prev_range = prev_high - prev_low
                curr_range = curr_high - curr_low

                if prev_range > 0:
                    expansion_ratio = curr_range / prev_range
                    strength = min(1.0, expansion_ratio / 2.0)  # Cap at 2x expansion = 1.0 strength
                    df.iloc[i, df.columns.get_loc('outside_day_strength')] = strength

        return df


class KeyReversalPattern:
    """
    Key Reversal Pattern Detector.

    Detects key reversal days that often mark short-term turning points.
    """

    def detect_key_reversals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Detect key reversal patterns."""
        df = data.copy()

        df['is_key_reversal'] = False
        df['reversal_type'] = ''  # 'bullish' or 'bearish'
        df['reversal_strength'] = 0.0

        for i in range(1, len(df)):
            prev_close = df['close'].iloc[i-1]
            curr_open = df['open'].iloc[i]
            curr_high = df['high'].iloc[i]
            curr_low = df['low'].iloc[i]
            curr_close = df['close'].iloc[i]

            # Bullish Key Reversal
            if (curr_open < prev_close and  # Gap down open
                curr_close > prev_close and  # Close above previous close
                curr_low < df['low'].iloc[i-1]):  # Lower low than previous day

                df.iloc[i, df.columns.get_loc('is_key_reversal')] = True
                df.iloc[i, df.columns.get_loc('reversal_type')] = 'bullish'

                # Strength based on range and reversal magnitude
                daily_range = curr_high - curr_low
                reversal_magnitude = curr_close - curr_low
                if daily_range > 0:
                    strength = reversal_magnitude / daily_range
                    df.iloc[i, df.columns.get_loc('reversal_strength')] = strength

            # Bearish Key Reversal
            elif (curr_open > prev_close and  # Gap up open
                  curr_close < prev_close and  # Close below previous close
                  curr_high > df['high'].iloc[i-1]):  # Higher high than previous day

                df.iloc[i, df.columns.get_loc('is_key_reversal')] = True
                df.iloc[i, df.columns.get_loc('reversal_type')] = 'bearish'

                # Strength based on range and reversal magnitude
                daily_range = curr_high - curr_low
                reversal_magnitude = curr_high - curr_close
                if daily_range > 0:
                    strength = reversal_magnitude / daily_range
                    df.iloc[i, df.columns.get_loc('reversal_strength')] = strength

        return df


class PatternDetector:
    """
    Main pattern detection coordinator.

    Combines all pattern detection methods and provides
    a unified interface for pattern analysis.
    """

    def __init__(self):
        self.nr_detector = NarrowRangePattern()
        self.inside_detector = InsideDayPattern()
        self.outside_detector = OutsideDayPattern()
        self.reversal_detector = KeyReversalPattern()

    def detect_all_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Detect all patterns in OHLC data.

        Args:
            data: OHLC DataFrame

        Returns:
            DataFrame with all pattern detection columns
        """
        df = data.copy()

        # Detect narrow range patterns
        df = self.nr_detector.detect_patterns(df)

        # Detect inside days
        df = self.inside_detector.detect_inside_days(df)

        # Detect outside days
        df = self.outside_detector.detect_outside_days(df)

        # Detect key reversals
        df = self.reversal_detector.detect_key_reversals(df)

        # Add combined pattern signal
        df['pattern_signal'] = self._create_combined_signal(df)

        return df

    def _create_combined_signal(self, df: pd.DataFrame) -> pd.Series:
        """Create combined pattern signal prioritizing different patterns."""
        combined = pd.Series('', index=df.index)

        # Priority order for pattern signals
        for i in range(len(df)):
            # Key reversals have highest priority
            if df['is_key_reversal'].iloc[i]:
                reversal_type = df['reversal_type'].iloc[i]
                combined.iloc[i] = f"KEY_REVERSAL_{reversal_type.upper()}"

            # Outside days
            elif df['is_outside_day'].iloc[i]:
                outside_type = df['outside_day_type'].iloc[i]
                combined.iloc[i] = f"OUTSIDE_DAY_{outside_type.upper()}"

            # Narrow range patterns
            elif df['narrow_range_signal'].iloc[i] != '':
                combined.iloc[i] = df['narrow_range_signal'].iloc[i]

            # Inside days
            elif df['is_inside_day'].iloc[i]:
                combined.iloc[i] = "INSIDE_DAY"

        return combined

    def get_pattern_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get summary of patterns in the data."""
        df = self.detect_all_patterns(data)

        # Count pattern occurrences
        pattern_counts = {}

        # Narrow range patterns
        for pattern in ['NR4', 'NR7', 'NR10', 'NR20']:
            column = f'is_{pattern.lower()}'
            if column in df.columns:
                pattern_counts[pattern] = df[column].sum()

        # Other patterns
        pattern_counts['inside_days'] = df['is_inside_day'].sum()
        pattern_counts['outside_days'] = df['is_outside_day'].sum()
        pattern_counts['key_reversals'] = df['is_key_reversal'].sum()

        # Recent patterns (last 10 days)
        recent_patterns = []
        recent_data = df.tail(10)

        for idx, row in recent_data.iterrows():
            if row['pattern_signal'] != '':
                recent_patterns.append({
                    'date': idx,
                    'pattern': row['pattern_signal'],
                    'strength': self._get_pattern_strength_for_row(row)
                })

        return {
            'pattern_counts': pattern_counts,
            'recent_patterns': recent_patterns,
            'total_patterns': sum(pattern_counts.values())
        }

    def _get_pattern_strength_for_row(self, row: pd.Series) -> float:
        """Get pattern strength for a specific row."""
        pattern = row['pattern_signal']

        if 'KEY_REVERSAL' in pattern:
            return row.get('reversal_strength', 0.0)
        elif 'OUTSIDE_DAY' in pattern:
            return row.get('outside_day_strength', 0.0)
        elif 'INSIDE_DAY' in pattern:
            return row.get('inside_day_strength', 0.0)
        elif pattern in ['NR4', 'NR7', 'NR10', 'NR20']:
            # Would need to calculate NR strength here
            return 0.5  # Default moderate strength
        else:
            return 0.0