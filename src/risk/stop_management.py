"""Stop loss management system implementing Linda Raschke's multiple stop methodologies."""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import datetime as dt

from src.features.linda.volatility import enhanced_atr
from src.config import get_risk_management_config


class StopType(Enum):
    """Types of stop losses."""
    TECHNICAL = "technical"
    VOLATILITY = "volatility"
    TIME = "time"
    MONEY_MANAGEMENT = "money_management"
    PATTERN_INVALIDATION = "pattern_invalidation"
    TRAILING = "trailing"


@dataclass
class StopLevel:
    """Stop loss level with metadata."""
    symbol: str
    stop_type: StopType
    stop_price: float
    stop_percentage: float  # Percentage from entry
    priority: int  # 1 = highest priority
    reason: str
    timestamp: dt.datetime
    entry_price: float
    direction: str  # 'long' or 'short'
    confidence: float


class StopManager:
    """
    Stop loss management system implementing Linda Raschke's methodologies.

    Multiple stop types with priority system:
    1. Technical stops (support/resistance)
    2. Volatility stops (ATR-based)
    3. Money management stops (2% rule)
    4. Time stops (position duration)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or get_risk_management_config()

        # Stop configuration
        self.atr_multiplier = 1.5
        self.technical_buffer = 0.01  # 1% buffer beyond S/R
        self.max_time_in_trade = 5  # Days
        self.max_money_management_risk = 0.02  # 2%

        # Priority order (lower number = higher priority)
        self.stop_priority = {
            StopType.MONEY_MANAGEMENT: 1,
            StopType.TECHNICAL: 2,
            StopType.VOLATILITY: 3,
            StopType.TIME: 4,
            StopType.PATTERN_INVALIDATION: 5,
            StopType.TRAILING: 6
        }

    def calculate_all_stops(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime,
        account_value: float,
        position_size: float,
        strategy_name: str = ""
    ) -> List[StopLevel]:
        """
        Calculate all applicable stop levels for a position.

        Args:
            symbol: Trading symbol
            entry_price: Entry price per share
            direction: 'long' or 'short'
            data: OHLCV data for technical analysis
            entry_date: Entry timestamp
            account_value: Total account value
            position_size: Position size in shares
            strategy_name: Name of strategy for context

        Returns:
            List of StopLevel objects sorted by priority
        """
        stops = []

        # Money management stop (always calculated)
        money_stop = self._calculate_money_management_stop(
            symbol, entry_price, direction, account_value, position_size, entry_date
        )
        if money_stop:
            stops.append(money_stop)

        # Technical stops
        technical_stops = self._calculate_technical_stops(
            symbol, entry_price, direction, data, entry_date
        )
        stops.extend(technical_stops)

        # Volatility stops
        volatility_stop = self._calculate_volatility_stop(
            symbol, entry_price, direction, data, entry_date
        )
        if volatility_stop:
            stops.append(volatility_stop)

        # Time stops
        time_stop = self._calculate_time_stop(
            symbol, entry_price, direction, entry_date
        )
        if time_stop:
            stops.append(time_stop)

        # Pattern invalidation stops (strategy-specific)
        pattern_stop = self._calculate_pattern_invalidation_stop(
            symbol, entry_price, direction, data, entry_date, strategy_name
        )
        if pattern_stop:
            stops.append(pattern_stop)

        # Sort by priority
        stops.sort(key=lambda x: self.stop_priority.get(x.stop_type, 999))

        return stops

    def _calculate_money_management_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        account_value: float,
        position_size: float,
        entry_date: dt.datetime
    ) -> Optional[StopLevel]:
        """Calculate money management stop based on 2% rule."""
        max_loss = account_value * self.max_money_management_risk
        loss_per_share = max_loss / position_size if position_size > 0 else 0

        if direction == 'long':
            stop_price = entry_price - loss_per_share
        else:
            stop_price = entry_price + loss_per_share

        if stop_price <= 0:
            return None

        stop_percentage = abs(stop_price - entry_price) / entry_price

        return StopLevel(
            symbol=symbol,
            stop_type=StopType.MONEY_MANAGEMENT,
            stop_price=stop_price,
            stop_percentage=stop_percentage,
            priority=1,
            reason=f"2% money management rule: max ${max_loss:.0f} loss",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            confidence=1.0
        )

    def _calculate_technical_stops(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime
    ) -> List[StopLevel]:
        """Calculate technical stops based on support/resistance levels."""
        stops = []

        if len(data) < 20:
            return stops

        entry_idx = data.index.get_indexer([entry_date], method='nearest')[0]
        if entry_idx < 10:
            return stops

        # Look back for support/resistance levels
        lookback_data = data.iloc[max(0, entry_idx-20):entry_idx+1]

        if direction == 'long':
            # Find support levels
            support_levels = self._find_support_levels(lookback_data)
            for level, confidence in support_levels:
                if level < entry_price:  # Only valid support below entry
                    stop_price = level * (1 - self.technical_buffer)
                    stop_percentage = (entry_price - stop_price) / entry_price

                    stops.append(StopLevel(
                        symbol=symbol,
                        stop_type=StopType.TECHNICAL,
                        stop_price=stop_price,
                        stop_percentage=stop_percentage,
                        priority=2,
                        reason=f"Technical support at {level:.2f} (confidence: {confidence:.2f})",
                        timestamp=entry_date,
                        entry_price=entry_price,
                        direction=direction,
                        confidence=confidence
                    ))

        else:  # short
            # Find resistance levels
            resistance_levels = self._find_resistance_levels(lookback_data)
            for level, confidence in resistance_levels:
                if level > entry_price:  # Only valid resistance above entry
                    stop_price = level * (1 + self.technical_buffer)
                    stop_percentage = (stop_price - entry_price) / entry_price

                    stops.append(StopLevel(
                        symbol=symbol,
                        stop_type=StopType.TECHNICAL,
                        stop_price=stop_price,
                        stop_percentage=stop_percentage,
                        priority=2,
                        reason=f"Technical resistance at {level:.2f} (confidence: {confidence:.2f})",
                        timestamp=entry_date,
                        entry_price=entry_price,
                        direction=direction,
                        confidence=confidence
                    ))

        return stops

    def _find_support_levels(self, data: pd.DataFrame) -> List[Tuple[float, float]]:
        """Find support levels in price data."""
        supports = []

        # Swing lows
        lows = data['low']
        for i in range(2, len(lows)-2):
            if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):

                # Check how many times this level was tested
                level = lows.iloc[i]
                touches = sum(1 for low in lows if abs(low - level) / level < 0.02)
                confidence = min(1.0, touches / 3.0)  # Max confidence at 3+ touches

                supports.append((level, confidence))

        # Recent lows
        recent_low = lows.min()
        if recent_low not in [s[0] for s in supports]:
            supports.append((recent_low, 0.5))

        # Sort by confidence
        supports.sort(key=lambda x: x[1], reverse=True)
        return supports[:3]  # Top 3 support levels

    def _find_resistance_levels(self, data: pd.DataFrame) -> List[Tuple[float, float]]:
        """Find resistance levels in price data."""
        resistances = []

        # Swing highs
        highs = data['high']
        for i in range(2, len(highs)-2):
            if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):

                # Check how many times this level was tested
                level = highs.iloc[i]
                touches = sum(1 for high in highs if abs(high - level) / level < 0.02)
                confidence = min(1.0, touches / 3.0)  # Max confidence at 3+ touches

                resistances.append((level, confidence))

        # Recent highs
        recent_high = highs.max()
        if recent_high not in [r[0] for r in resistances]:
            resistances.append((recent_high, 0.5))

        # Sort by confidence
        resistances.sort(key=lambda x: x[1], reverse=True)
        return resistances[:3]  # Top 3 resistance levels

    def _calculate_volatility_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime
    ) -> Optional[StopLevel]:
        """Calculate volatility-based stop using ATR."""
        if len(data) < 14:
            return None

        entry_idx = data.index.get_indexer([entry_date], method='nearest')[0]
        if entry_idx < 14:
            return None

        # Calculate ATR
        atr_data = enhanced_atr(data['high'], data['low'], data['close'])
        current_atr = atr_data['atr'].iloc[entry_idx]

        if pd.isna(current_atr) or current_atr <= 0:
            return None

        # Calculate stop distance
        stop_distance = current_atr * self.atr_multiplier

        if direction == 'long':
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance

        if stop_price <= 0:
            return None

        stop_percentage = abs(stop_price - entry_price) / entry_price

        return StopLevel(
            symbol=symbol,
            stop_type=StopType.VOLATILITY,
            stop_price=stop_price,
            stop_percentage=stop_percentage,
            priority=3,
            reason=f"ATR stop: {self.atr_multiplier}x ATR ({current_atr:.2f})",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            confidence=0.8
        )

    def _calculate_time_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        entry_date: dt.datetime
    ) -> Optional[StopLevel]:
        """Calculate time-based stop."""
        exit_date = entry_date + dt.timedelta(days=self.max_time_in_trade)

        return StopLevel(
            symbol=symbol,
            stop_type=StopType.TIME,
            stop_price=entry_price,  # Exit at market price
            stop_percentage=0.0,
            priority=4,
            reason=f"Time stop: {self.max_time_in_trade} days maximum hold",
            timestamp=exit_date,
            entry_price=entry_price,
            direction=direction,
            confidence=0.3
        )

    def _calculate_pattern_invalidation_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime,
        strategy_name: str
    ) -> Optional[StopLevel]:
        """Calculate pattern invalidation stops based on strategy."""
        if not strategy_name:
            return None

        entry_idx = data.index.get_indexer([entry_date], method='nearest')[0]

        if strategy_name.lower() == 'holy_grail':
            # Holy Grail: stop if price breaks back below/above the pullback range
            return self._holy_grail_invalidation_stop(
                symbol, entry_price, direction, data, entry_date, entry_idx
            )
        elif strategy_name.lower() == 'turtle_soup':
            # Turtle Soup: stop if price re-enters the original breakout range
            return self._turtle_soup_invalidation_stop(
                symbol, entry_price, direction, data, entry_date, entry_idx
            )
        elif strategy_name.lower() == 'anti_swing':
            # Anti-Swing: stop if momentum reverses (RSI extreme reversal)
            return self._anti_swing_invalidation_stop(
                symbol, entry_price, direction, data, entry_date, entry_idx
            )

        return None

    def _holy_grail_invalidation_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime,
        entry_idx: int
    ) -> Optional[StopLevel]:
        """Calculate Holy Grail pattern invalidation stop."""
        if entry_idx < 5:
            return None

        # Look at recent pullback range
        pullback_data = data.iloc[max(0, entry_idx-5):entry_idx]

        if direction == 'long':
            # Stop below the pullback low
            pullback_low = pullback_data['low'].min()
            stop_price = pullback_low * 0.98  # 2% buffer
        else:
            # Stop above the pullback high
            pullback_high = pullback_data['high'].max()
            stop_price = pullback_high * 1.02  # 2% buffer

        if stop_price <= 0:
            return None

        stop_percentage = abs(stop_price - entry_price) / entry_price

        return StopLevel(
            symbol=symbol,
            stop_type=StopType.PATTERN_INVALIDATION,
            stop_price=stop_price,
            stop_percentage=stop_percentage,
            priority=5,
            reason="Holy Grail pattern invalidation",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            confidence=0.9
        )

    def _turtle_soup_invalidation_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime,
        entry_idx: int
    ) -> Optional[StopLevel]:
        """Calculate Turtle Soup pattern invalidation stop."""
        if entry_idx < 20:
            return None

        # Find the 20-day breakout level that failed
        lookback_data = data.iloc[max(0, entry_idx-20):entry_idx]

        if direction == 'long':
            # Stop below the failed breakdown level
            twenty_day_low = lookback_data['low'].min()
            stop_price = twenty_day_low * 0.98
        else:
            # Stop above the failed breakout level
            twenty_day_high = lookback_data['high'].max()
            stop_price = twenty_day_high * 1.02

        if stop_price <= 0:
            return None

        stop_percentage = abs(stop_price - entry_price) / entry_price

        return StopLevel(
            symbol=symbol,
            stop_type=StopType.PATTERN_INVALIDATION,
            stop_price=stop_price,
            stop_percentage=stop_percentage,
            priority=5,
            reason="Turtle Soup pattern invalidation",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            confidence=0.8
        )

    def _anti_swing_invalidation_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime,
        entry_idx: int
    ) -> Optional[StopLevel]:
        """Calculate Anti-Swing pattern invalidation stop."""
        # For Anti-Swing, use a percentage-based stop since it's mean reversion
        if direction == 'long':
            stop_price = entry_price * 0.95  # 5% stop
        else:
            stop_price = entry_price * 1.05  # 5% stop

        stop_percentage = abs(stop_price - entry_price) / entry_price

        return StopLevel(
            symbol=symbol,
            stop_type=StopType.PATTERN_INVALIDATION,
            stop_price=stop_price,
            stop_percentage=stop_percentage,
            priority=5,
            reason="Anti-Swing momentum reversal",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            confidence=0.7
        )

    def get_active_stop(self, stops: List[StopLevel]) -> Optional[StopLevel]:
        """Get the active (highest priority) stop from a list of stops."""
        if not stops:
            return None

        # Filter out expired time stops
        current_time = dt.datetime.now()
        valid_stops = [s for s in stops if s.stop_type != StopType.TIME or s.timestamp > current_time]

        if not valid_stops:
            return None

        # Return highest priority stop
        return min(valid_stops, key=lambda x: self.stop_priority.get(x.stop_type, 999))

    def update_trailing_stop(
        self,
        current_stop: StopLevel,
        current_price: float,
        high_since_entry: float,
        low_since_entry: float,
        atr: float
    ) -> Optional[StopLevel]:
        """Update trailing stop based on current price action."""
        if current_stop.direction == 'long':
            # Trail stop up for long positions
            new_stop_price = high_since_entry - (atr * self.atr_multiplier)
            if new_stop_price > current_stop.stop_price:
                return StopLevel(
                    symbol=current_stop.symbol,
                    stop_type=StopType.TRAILING,
                    stop_price=new_stop_price,
                    stop_percentage=abs(new_stop_price - current_stop.entry_price) / current_stop.entry_price,
                    priority=6,
                    reason=f"Trailing stop moved to {new_stop_price:.2f}",
                    timestamp=dt.datetime.now(),
                    entry_price=current_stop.entry_price,
                    direction=current_stop.direction,
                    confidence=0.8
                )
        else:
            # Trail stop down for short positions
            new_stop_price = low_since_entry + (atr * self.atr_multiplier)
            if new_stop_price < current_stop.stop_price:
                return StopLevel(
                    symbol=current_stop.symbol,
                    stop_type=StopType.TRAILING,
                    stop_price=new_stop_price,
                    stop_percentage=abs(new_stop_price - current_stop.entry_price) / current_stop.entry_price,
                    priority=6,
                    reason=f"Trailing stop moved to {new_stop_price:.2f}",
                    timestamp=dt.datetime.now(),
                    entry_price=current_stop.entry_price,
                    direction=current_stop.direction,
                    confidence=0.8
                )

        return None

    def is_stop_triggered(
        self,
        stop: StopLevel,
        current_price: float,
        current_time: dt.datetime
    ) -> bool:
        """Check if a stop loss has been triggered."""
        if stop.stop_type == StopType.TIME:
            return current_time >= stop.timestamp

        if stop.direction == 'long':
            return current_price <= stop.stop_price
        else:
            return current_price >= stop.stop_price

    def calculate_stop_effectiveness(
        self,
        stops_used: List[StopLevel],
        actual_exit_price: float,
        actual_exit_reason: str
    ) -> Dict[str, float]:
        """Calculate effectiveness of different stop types."""
        effectiveness = {}

        for stop in stops_used:
            if stop.direction == 'long':
                theoretical_loss = stop.entry_price - stop.stop_price
                actual_loss = stop.entry_price - actual_exit_price
            else:
                theoretical_loss = stop.stop_price - stop.entry_price
                actual_loss = actual_exit_price - stop.entry_price

            if theoretical_loss > 0:
                effectiveness[stop.stop_type.value] = actual_loss / theoretical_loss
            else:
                effectiveness[stop.stop_type.value] = 0.0

        return effectiveness