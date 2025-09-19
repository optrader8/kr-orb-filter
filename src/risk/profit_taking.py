"""Profit taking framework implementing Linda Raschke's scale-out and trailing strategies."""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import datetime as dt

from src.config import get_risk_management_config


class ProfitTargetType(Enum):
    """Types of profit targets."""
    FIXED_RR = "fixed_risk_reward"
    SCALE_OUT = "scale_out"
    TRAILING = "trailing"
    TARGET_ZONE = "target_zone"
    TIME_EXIT = "time_exit"
    TECHNICAL = "technical"


@dataclass
class ProfitTarget:
    """Profit target with execution details."""
    symbol: str
    target_type: ProfitTargetType
    target_price: float
    target_percentage: float  # Percentage gain from entry
    quantity_percentage: float  # Percentage of position to exit
    priority: int
    reason: str
    timestamp: dt.datetime
    entry_price: float
    direction: str  # 'long' or 'short'
    risk_reward_ratio: float
    confidence: float


class ProfitTaker:
    """
    Profit taking system implementing Linda Raschke's scale-out methodology.

    Core principles:
    - Scale out: 1/3 at 1:1, 1/3 at 2:1, trail final 1/3
    - Move stop to breakeven after 1:1 target
    - Trail remaining position by ATR distance
    - Target zones: previous highs/lows, round numbers
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or get_risk_management_config()

        # Scale-out configuration
        self.first_target_rr = 1.0    # 1:1 risk/reward
        self.second_target_rr = 2.0   # 2:1 risk/reward
        self.first_exit_percentage = 0.33    # 1/3 of position
        self.second_exit_percentage = 0.33   # 1/3 of position
        self.final_exit_percentage = 0.34    # Remaining 1/3

        # Trailing configuration
        self.trail_after_rr = 1.0    # Start trailing after 1:1
        self.trail_atr_multiplier = 1.0
        self.breakeven_buffer = 0.01  # 1% buffer for breakeven stop

    def calculate_profit_targets(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        direction: str,
        entry_date: dt.datetime,
        data: pd.DataFrame,
        strategy_name: str = ""
    ) -> List[ProfitTarget]:
        """
        Calculate all profit targets for a position.

        Args:
            symbol: Trading symbol
            entry_price: Entry price per share
            stop_loss: Stop loss price
            direction: 'long' or 'short'
            entry_date: Entry timestamp
            data: OHLCV data for technical analysis
            strategy_name: Strategy name for context

        Returns:
            List of ProfitTarget objects sorted by priority
        """
        targets = []

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return targets

        # Scale-out targets
        scale_targets = self._calculate_scale_out_targets(
            symbol, entry_price, risk_per_share, direction, entry_date
        )
        targets.extend(scale_targets)

        # Technical targets
        technical_targets = self._calculate_technical_targets(
            symbol, entry_price, direction, data, entry_date
        )
        targets.extend(technical_targets)

        # Strategy-specific targets
        strategy_targets = self._calculate_strategy_targets(
            symbol, entry_price, direction, data, entry_date, strategy_name
        )
        targets.extend(strategy_targets)

        # Round number targets
        round_targets = self._calculate_round_number_targets(
            symbol, entry_price, direction, entry_date
        )
        targets.extend(round_targets)

        # Sort by priority and price proximity
        targets.sort(key=lambda x: (x.priority, abs(x.target_price - entry_price)))

        return targets

    def _calculate_scale_out_targets(
        self,
        symbol: str,
        entry_price: float,
        risk_per_share: float,
        direction: str,
        entry_date: dt.datetime
    ) -> List[ProfitTarget]:
        """Calculate Linda's scale-out targets (1:1, 2:1)."""
        targets = []

        # First target: 1:1 risk/reward
        if direction == 'long':
            first_target_price = entry_price + (risk_per_share * self.first_target_rr)
        else:
            first_target_price = entry_price - (risk_per_share * self.first_target_rr)

        first_target_percentage = abs(first_target_price - entry_price) / entry_price

        targets.append(ProfitTarget(
            symbol=symbol,
            target_type=ProfitTargetType.SCALE_OUT,
            target_price=first_target_price,
            target_percentage=first_target_percentage,
            quantity_percentage=self.first_exit_percentage,
            priority=1,
            reason=f"Scale-out 1/3 at 1:1 R/R ({first_target_price:.2f})",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            risk_reward_ratio=self.first_target_rr,
            confidence=0.9
        ))

        # Second target: 2:1 risk/reward
        if direction == 'long':
            second_target_price = entry_price + (risk_per_share * self.second_target_rr)
        else:
            second_target_price = entry_price - (risk_per_share * self.second_target_rr)

        second_target_percentage = abs(second_target_price - entry_price) / entry_price

        targets.append(ProfitTarget(
            symbol=symbol,
            target_type=ProfitTargetType.SCALE_OUT,
            target_price=second_target_price,
            target_percentage=second_target_percentage,
            quantity_percentage=self.second_exit_percentage,
            priority=2,
            reason=f"Scale-out 1/3 at 2:1 R/R ({second_target_price:.2f})",
            timestamp=entry_date,
            entry_price=entry_price,
            direction=direction,
            risk_reward_ratio=self.second_target_rr,
            confidence=0.8
        ))

        return targets

    def _calculate_technical_targets(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime
    ) -> List[ProfitTarget]:
        """Calculate technical targets based on support/resistance."""
        targets = []

        if len(data) < 20:
            return targets

        entry_idx = data.index.get_indexer([entry_date], method='nearest')[0]
        if entry_idx < 10:
            return targets

        # Look ahead and back for key levels
        lookback_data = data.iloc[max(0, entry_idx-50):entry_idx+1]

        if direction == 'long':
            # Find resistance levels above current price
            resistance_levels = self._find_resistance_targets(lookback_data, entry_price)
            for level, confidence in resistance_levels:
                target_percentage = (level - entry_price) / entry_price

                targets.append(ProfitTarget(
                    symbol=symbol,
                    target_type=ProfitTargetType.TECHNICAL,
                    target_price=level,
                    target_percentage=target_percentage,
                    quantity_percentage=0.5,  # Take profit on half position
                    priority=3,
                    reason=f"Technical resistance at {level:.2f} (confidence: {confidence:.2f})",
                    timestamp=entry_date,
                    entry_price=entry_price,
                    direction=direction,
                    risk_reward_ratio=target_percentage / 0.02,  # Assume 2% risk
                    confidence=confidence
                ))

        else:  # short
            # Find support levels below current price
            support_levels = self._find_support_targets(lookback_data, entry_price)
            for level, confidence in support_levels:
                target_percentage = (entry_price - level) / entry_price

                targets.append(ProfitTarget(
                    symbol=symbol,
                    target_type=ProfitTargetType.TECHNICAL,
                    target_price=level,
                    target_percentage=target_percentage,
                    quantity_percentage=0.5,  # Take profit on half position
                    priority=3,
                    reason=f"Technical support at {level:.2f} (confidence: {confidence:.2f})",
                    timestamp=entry_date,
                    entry_price=entry_price,
                    direction=direction,
                    risk_reward_ratio=target_percentage / 0.02,  # Assume 2% risk
                    confidence=confidence
                ))

        return targets

    def _find_resistance_targets(self, data: pd.DataFrame, entry_price: float) -> List[Tuple[float, float]]:
        """Find resistance levels above entry price."""
        resistances = []
        highs = data['high']

        # Previous highs
        for i in range(2, len(highs)-2):
            if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):

                level = highs.iloc[i]
                if level > entry_price:  # Only levels above entry
                    # Check strength of resistance
                    touches = sum(1 for high in highs if abs(high - level) / level < 0.01)
                    confidence = min(1.0, touches / 2.0)
                    resistances.append((level, confidence))

        # Recent high
        recent_high = highs.max()
        if recent_high > entry_price and recent_high not in [r[0] for r in resistances]:
            resistances.append((recent_high, 0.6))

        # Sort by proximity to entry price
        resistances.sort(key=lambda x: x[0])
        return resistances[:3]  # Closest 3 resistance levels

    def _find_support_targets(self, data: pd.DataFrame, entry_price: float) -> List[Tuple[float, float]]:
        """Find support levels below entry price."""
        supports = []
        lows = data['low']

        # Previous lows
        for i in range(2, len(lows)-2):
            if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):

                level = lows.iloc[i]
                if level < entry_price:  # Only levels below entry
                    # Check strength of support
                    touches = sum(1 for low in lows if abs(low - level) / level < 0.01)
                    confidence = min(1.0, touches / 2.0)
                    supports.append((level, confidence))

        # Recent low
        recent_low = lows.min()
        if recent_low < entry_price and recent_low not in [s[0] for s in supports]:
            supports.append((recent_low, 0.6))

        # Sort by proximity to entry price (descending for shorts)
        supports.sort(key=lambda x: x[0], reverse=True)
        return supports[:3]  # Closest 3 support levels

    def _calculate_strategy_targets(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        data: pd.DataFrame,
        entry_date: dt.datetime,
        strategy_name: str
    ) -> List[ProfitTarget]:
        """Calculate strategy-specific profit targets."""
        targets = []

        if strategy_name.lower() == 'anti_swing':
            # Anti-swing: target return to 5-period MA
            entry_idx = data.index.get_indexer([entry_date], method='nearest')[0]
            if entry_idx >= 5:
                ma5 = data['close'].rolling(5).mean().iloc[entry_idx]
                if not pd.isna(ma5):
                    target_percentage = abs(ma5 - entry_price) / entry_price

                    targets.append(ProfitTarget(
                        symbol=symbol,
                        target_type=ProfitTargetType.TECHNICAL,
                        target_price=ma5,
                        target_percentage=target_percentage,
                        quantity_percentage=0.75,  # Take most profit at MA
                        priority=2,
                        reason=f"Anti-swing MA5 target ({ma5:.2f})",
                        timestamp=entry_date,
                        entry_price=entry_price,
                        direction=direction,
                        risk_reward_ratio=target_percentage / 0.05,  # Assume 5% risk for mean reversion
                        confidence=0.8
                    ))

        elif strategy_name.lower() == 'volatility_breakout':
            # Volatility breakout: target 2-3x the narrow range
            # This would require additional data about the breakout range
            pass

        return targets

    def _calculate_round_number_targets(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        entry_date: dt.datetime
    ) -> List[ProfitTarget]:
        """Calculate round number profit targets."""
        targets = []

        # Find nearest round numbers
        if entry_price >= 100:
            increment = 10  # $10 increments for high-priced stocks
        elif entry_price >= 50:
            increment = 5   # $5 increments
        elif entry_price >= 10:
            increment = 1   # $1 increments
        else:
            increment = 0.5  # $0.50 increments

        if direction == 'long':
            # Find next round numbers above entry
            next_round = np.ceil(entry_price / increment) * increment
            if next_round <= entry_price:
                next_round += increment

            for i in range(3):  # Up to 3 round number targets
                round_price = next_round + (i * increment)
                target_percentage = (round_price - entry_price) / entry_price

                if target_percentage > 0.01:  # At least 1% profit
                    targets.append(ProfitTarget(
                        symbol=symbol,
                        target_type=ProfitTargetType.TARGET_ZONE,
                        target_price=round_price,
                        target_percentage=target_percentage,
                        quantity_percentage=0.25,  # Partial profit at round numbers
                        priority=4,
                        reason=f"Round number target ${round_price:.0f}",
                        timestamp=entry_date,
                        entry_price=entry_price,
                        direction=direction,
                        risk_reward_ratio=target_percentage / 0.02,
                        confidence=0.5
                    ))

        else:  # short
            # Find next round numbers below entry
            next_round = np.floor(entry_price / increment) * increment
            if next_round >= entry_price:
                next_round -= increment

            for i in range(3):  # Up to 3 round number targets
                round_price = next_round - (i * increment)
                if round_price > 0:
                    target_percentage = (entry_price - round_price) / entry_price

                    if target_percentage > 0.01:  # At least 1% profit
                        targets.append(ProfitTarget(
                            symbol=symbol,
                            target_type=ProfitTargetType.TARGET_ZONE,
                            target_price=round_price,
                            target_percentage=target_percentage,
                            quantity_percentage=0.25,  # Partial profit at round numbers
                            priority=4,
                            reason=f"Round number target ${round_price:.0f}",
                            timestamp=entry_date,
                            entry_price=entry_price,
                            direction=direction,
                            risk_reward_ratio=target_percentage / 0.02,
                            confidence=0.5
                        ))

        return targets

    def calculate_trailing_target(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        current_price: float,
        highest_profit: float,
        atr: float,
        entry_date: dt.datetime
    ) -> Optional[ProfitTarget]:
        """Calculate trailing profit target based on current price action."""
        # Only start trailing after reaching 1:1 profit
        if highest_profit < self.trail_after_rr:
            return None

        # Calculate trailing level
        if direction == 'long':
            trail_price = current_price - (atr * self.trail_atr_multiplier)
            # Ensure we don't trail below breakeven
            trail_price = max(trail_price, entry_price * (1 + self.breakeven_buffer))
        else:
            trail_price = current_price + (atr * self.trail_atr_multiplier)
            # Ensure we don't trail above breakeven
            trail_price = min(trail_price, entry_price * (1 - self.breakeven_buffer))

        target_percentage = abs(trail_price - entry_price) / entry_price

        return ProfitTarget(
            symbol=symbol,
            target_type=ProfitTargetType.TRAILING,
            target_price=trail_price,
            target_percentage=target_percentage,
            quantity_percentage=1.0,  # Trail entire remaining position
            priority=5,
            reason=f"Trailing target at {trail_price:.2f} (ATR trail)",
            timestamp=dt.datetime.now(),
            entry_price=entry_price,
            direction=direction,
            risk_reward_ratio=highest_profit,
            confidence=0.7
        )

    def is_target_hit(
        self,
        target: ProfitTarget,
        current_price: float,
        high_since_entry: float,
        low_since_entry: float
    ) -> bool:
        """Check if a profit target has been hit."""
        if target.direction == 'long':
            # For longs, check if high reached target
            return high_since_entry >= target.target_price
        else:
            # For shorts, check if low reached target
            return low_since_entry <= target.target_price

    def calculate_breakeven_stop(
        self,
        entry_price: float,
        direction: str,
        buffer_percentage: float = None
    ) -> float:
        """Calculate breakeven stop price with buffer."""
        buffer = buffer_percentage or self.breakeven_buffer

        if direction == 'long':
            return entry_price * (1 + buffer)
        else:
            return entry_price * (1 - buffer)

    def get_position_management_plan(
        self,
        targets: List[ProfitTarget],
        current_price: float,
        unrealized_profit: float
    ) -> Dict[str, any]:
        """Get current position management plan based on targets and profit."""
        plan = {
            'next_target': None,
            'targets_hit': [],
            'remaining_quantity': 1.0,
            'should_move_stop_to_breakeven': False,
            'should_start_trailing': False,
            'current_profit_percentage': unrealized_profit
        }

        # Find targets that have been hit
        targets_hit = []
        remaining_quantity = 1.0

        for target in sorted(targets, key=lambda x: x.priority):
            if target.direction == 'long':
                target_hit = current_price >= target.target_price
            else:
                target_hit = current_price <= target.target_price

            if target_hit:
                targets_hit.append(target)
                remaining_quantity -= target.quantity_percentage

        plan['targets_hit'] = targets_hit
        plan['remaining_quantity'] = max(0.0, remaining_quantity)

        # Check if we should move stop to breakeven (after 1:1 target)
        hit_first_target = any(t.risk_reward_ratio >= 1.0 for t in targets_hit)
        plan['should_move_stop_to_breakeven'] = hit_first_target

        # Check if we should start trailing (after 1:1 profit)
        plan['should_start_trailing'] = unrealized_profit >= self.trail_after_rr

        # Find next target
        remaining_targets = [t for t in targets if t not in targets_hit]
        if remaining_targets:
            plan['next_target'] = min(remaining_targets, key=lambda x: x.priority)

        return plan

    def calculate_profit_efficiency(
        self,
        targets_used: List[ProfitTarget],
        actual_exit_prices: List[float],
        quantities_sold: List[float]
    ) -> Dict[str, float]:
        """Calculate profit-taking efficiency metrics."""
        if not targets_used or not actual_exit_prices:
            return {}

        total_theoretical_profit = 0.0
        total_actual_profit = 0.0
        total_quantity = sum(quantities_sold)

        for target, exit_price, quantity in zip(targets_used, actual_exit_prices, quantities_sold):
            theoretical_profit = abs(target.target_price - target.entry_price) * quantity
            actual_profit = abs(exit_price - target.entry_price) * quantity

            total_theoretical_profit += theoretical_profit
            total_actual_profit += actual_profit

        efficiency = (total_actual_profit / total_theoretical_profit) if total_theoretical_profit > 0 else 0.0

        return {
            'profit_efficiency': efficiency,
            'total_theoretical_profit': total_theoretical_profit,
            'total_actual_profit': total_actual_profit,
            'average_slippage': (total_theoretical_profit - total_actual_profit) / total_quantity if total_quantity > 0 else 0.0
        }