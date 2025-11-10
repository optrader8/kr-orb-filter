"""Position sizing engine implementing Linda Raschke's 2% rule and portfolio heat management."""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from src.config import get_risk_management_config


class PositionSizeMethod(Enum):
    """Available position sizing methods."""
    FIXED_RISK = "fixed_risk"
    FIXED_AMOUNT = "fixed_amount"
    KELLY = "kelly"
    OPTIMAL_F = "optimal_f"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


@dataclass
class PositionSizeCalculation:
    """Result of position size calculation."""
    symbol: str
    position_size: float  # Position size as percentage of account
    shares: int  # Number of shares/units
    dollar_amount: float  # Dollar amount of position
    risk_amount: float  # Dollar amount at risk
    risk_percentage: float  # Risk as percentage of account
    method_used: str
    confidence_adjustment: float
    volatility_adjustment: float
    correlation_adjustment: float
    portfolio_heat_adjustment: float
    max_position_allowed: bool


class PositionSizer:
    """
    Position sizing engine implementing Linda Raschke's risk management principles.

    Core principles:
    - Never risk more than 2% of account per trade
    - Maximum portfolio heat of 6-8%
    - Reduce position size for correlated instruments
    - Adjust for volatility and market conditions
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or get_risk_management_config()

        # Risk parameters
        self.base_risk_per_trade = getattr(self.config, 'max_risk_per_trade', 0.02)
        self.max_risk_per_trade = min(0.025, self.base_risk_per_trade * 1.25)  # 25% higher max
        self.max_portfolio_heat = getattr(self.config, 'max_portfolio_heat', 0.08)
        self.correlation_threshold = 0.7

        # Position size limits
        self.min_position_size = 0.001  # 0.1%
        self.max_position_size = 0.05   # 5%

        # Current portfolio state
        self.current_positions: Dict[str, float] = {}  # symbol -> risk amount
        self.current_correlations: Dict[Tuple[str, str], float] = {}

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        account_value: float,
        strategy_name: str = "",
        confidence: float = 1.0,
        volatility_adjustment: float = 1.0,
        method: PositionSizeMethod = PositionSizeMethod.FIXED_RISK
    ) -> PositionSizeCalculation:
        """
        Calculate optimal position size based on Linda's risk management rules.

        Args:
            symbol: Trading symbol
            entry_price: Entry price per share
            stop_loss: Stop loss price per share
            account_value: Total account value
            strategy_name: Name of strategy generating signal
            confidence: Signal confidence (0-1)
            volatility_adjustment: Volatility adjustment factor
            method: Position sizing method

        Returns:
            PositionSizeCalculation with all relevant metrics
        """
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return self._zero_position(symbol, "Invalid risk per share")

        # Base risk calculation
        base_risk_amount = account_value * self.base_risk_per_trade

        # Apply adjustments
        adjusted_risk = self._apply_adjustments(
            base_risk_amount, symbol, strategy_name, confidence, volatility_adjustment
        )

        # Calculate position size
        shares = int(adjusted_risk / risk_per_share)
        if shares <= 0:
            return self._zero_position(symbol, "Calculated shares <= 0")

        # Calculate actual amounts
        dollar_amount = shares * entry_price
        actual_risk = shares * risk_per_share
        position_percentage = dollar_amount / account_value
        risk_percentage = actual_risk / account_value

        # Validate against limits
        if position_percentage > self.max_position_size:
            # Scale down to max position size
            shares = int((self.max_position_size * account_value) / entry_price)
            dollar_amount = shares * entry_price
            actual_risk = shares * risk_per_share
            position_percentage = dollar_amount / account_value
            risk_percentage = actual_risk / account_value

        if position_percentage < self.min_position_size:
            return self._zero_position(symbol, "Position too small")

        # Check portfolio heat
        max_position_allowed = self._check_portfolio_heat(actual_risk)

        return PositionSizeCalculation(
            symbol=symbol,
            position_size=position_percentage,
            shares=shares,
            dollar_amount=dollar_amount,
            risk_amount=actual_risk,
            risk_percentage=risk_percentage,
            method_used=method.value,
            confidence_adjustment=confidence,
            volatility_adjustment=volatility_adjustment,
            correlation_adjustment=self._get_correlation_adjustment(symbol),
            portfolio_heat_adjustment=self._get_portfolio_heat_ratio(),
            max_position_allowed=max_position_allowed
        )

    def _apply_adjustments(
        self,
        base_risk: float,
        symbol: str,
        strategy_name: str,
        confidence: float,
        volatility_adjustment: float
    ) -> float:
        """Apply various adjustments to base risk amount."""
        adjusted_risk = base_risk

        # Confidence adjustment (scale down for low confidence)
        confidence_factor = 0.5 + (confidence * 0.5)  # 0.5 to 1.0 range
        adjusted_risk *= confidence_factor

        # Volatility adjustment
        # High volatility = smaller position, Low volatility = larger position
        vol_factor = 1.0 / max(0.5, min(2.0, volatility_adjustment))
        adjusted_risk *= vol_factor

        # Strategy-specific adjustments
        strategy_factor = self._get_strategy_risk_factor(strategy_name)
        adjusted_risk *= strategy_factor

        # Correlation adjustment
        correlation_factor = self._get_correlation_adjustment(symbol)
        adjusted_risk *= correlation_factor

        # Portfolio heat adjustment
        heat_factor = self._get_portfolio_heat_factor()
        adjusted_risk *= heat_factor

        return adjusted_risk

    def _get_strategy_risk_factor(self, strategy_name: str) -> float:
        """Get risk adjustment factor for specific strategy."""
        strategy_factors = {
            'holy_grail': 1.0,      # Normal risk for trend following
            'turtle_soup': 0.8,     # Lower risk for counter-trend
            'anti_swing': 0.8,      # Lower risk for mean reversion
            'enhanced_orb': 1.0,    # Normal risk for breakouts
            'volatility_breakout': 1.2,  # Higher risk for momentum
            'gap_fade': 0.7,        # Lower risk for gap fading
        }

        return strategy_factors.get(strategy_name.lower(), 1.0)

    def _get_correlation_adjustment(self, symbol: str) -> float:
        """Calculate correlation adjustment factor."""
        # Check correlation with existing positions
        total_correlated_risk = 0.0

        for existing_symbol, existing_risk in self.current_positions.items():
            correlation = self.current_correlations.get((symbol, existing_symbol), 0.0)
            if abs(correlation) > self.correlation_threshold:
                total_correlated_risk += existing_risk * abs(correlation)

        # Reduce position size if high correlation
        if total_correlated_risk > 0:
            # Scale down by correlation factor
            max_correlated_risk = self.max_portfolio_heat * 0.5  # 50% of max heat
            if total_correlated_risk > max_correlated_risk:
                return max_correlated_risk / total_correlated_risk
            else:
                return 1.0 - (total_correlated_risk / max_correlated_risk) * 0.3

        return 1.0

    def _get_portfolio_heat_factor(self) -> float:
        """Get portfolio heat adjustment factor."""
        current_heat = sum(self.current_positions.values())
        heat_ratio = current_heat / self.max_portfolio_heat

        if heat_ratio > 0.8:  # Above 80% of max heat
            return 0.5  # Reduce new positions by 50%
        elif heat_ratio > 0.6:  # Above 60% of max heat
            return 0.7  # Reduce new positions by 30%
        else:
            return 1.0  # Normal position sizing

    def _get_portfolio_heat_ratio(self) -> float:
        """Get current portfolio heat ratio."""
        current_heat = sum(self.current_positions.values())
        return current_heat / self.max_portfolio_heat

    def _check_portfolio_heat(self, additional_risk: float) -> bool:
        """Check if adding this position would exceed portfolio heat limit."""
        current_heat = sum(self.current_positions.values())
        return (current_heat + additional_risk) <= self.max_portfolio_heat

    def _zero_position(self, symbol: str, reason: str) -> PositionSizeCalculation:
        """Return zero position with reason."""
        return PositionSizeCalculation(
            symbol=symbol,
            position_size=0.0,
            shares=0,
            dollar_amount=0.0,
            risk_amount=0.0,
            risk_percentage=0.0,
            method_used="zero_position",
            confidence_adjustment=0.0,
            volatility_adjustment=0.0,
            correlation_adjustment=0.0,
            portfolio_heat_adjustment=0.0,
            max_position_allowed=False
        )

    def update_portfolio(self, symbol: str, risk_amount: float):
        """Update current portfolio with new or modified position."""
        if risk_amount > 0:
            self.current_positions[symbol] = risk_amount
        else:
            self.current_positions.pop(symbol, None)

    def update_correlations(self, correlations: Dict[Tuple[str, str], float]):
        """
        Update correlation matrix for position sizing.

        Args:
            correlations: Dictionary with (symbol1, symbol2) tuples as keys and correlation values

        Example:
            correlations = {
                ('AAPL', 'MSFT'): 0.85,
                ('AAPL', 'GOOGL'): 0.72,
                ('MSFT', 'GOOGL'): 0.80
            }
            position_sizer.update_correlations(correlations)
        """
        self.current_correlations.update(correlations)

    def load_correlations_from_calculator(self, correlation_analysis):
        """
        Load correlations from CorrelationAnalysis object.

        Args:
            correlation_analysis: CorrelationAnalysis object from correlation.py
        """
        from src.risk.correlation import convert_correlations_to_position_sizer_format

        correlations = convert_correlations_to_position_sizer_format(correlation_analysis)
        self.update_correlations(correlations)

    def calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion optimal position size.

        Formula: f = (bp - q) / b
        Where:
        - f = fraction of capital to wager
        - b = odds received (avg_win / avg_loss)
        - p = probability of win
        - q = probability of loss (1 - p)
        """
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        # Cap Kelly at 25% for safety (quarter Kelly)
        return max(0.0, min(0.25, kelly_fraction))

    def calculate_optimal_f(
        self,
        trade_results: List[float]
    ) -> float:
        """
        Calculate Optimal F position sizing.

        Optimal F maximizes geometric growth rate.
        """
        if not trade_results or len(trade_results) < 10:
            return self.base_risk_per_trade

        # Find the largest loss (negative number)
        largest_loss = min(trade_results)
        if largest_loss >= 0:
            return self.base_risk_per_trade

        # Calculate TWR (Terminal Wealth Relative) for different f values
        best_f = 0.0
        best_twr = 0.0

        for f in np.arange(0.01, 0.5, 0.01):  # Test f from 1% to 50%
            twr = 1.0

            for result in trade_results:
                # Convert result to relative gain/loss
                relative_result = result / abs(largest_loss)
                new_equity = 1.0 + (f * relative_result)

                if new_equity <= 0:  # Ruin
                    twr = 0.0
                    break

                twr *= new_equity

            if twr > best_twr:
                best_twr = twr
                best_f = f

        # Cap Optimal F at 20% for safety
        return min(0.20, best_f)

    def calculate_volatility_adjusted_size(
        self,
        base_size: float,
        current_volatility: float,
        average_volatility: float
    ) -> float:
        """Calculate volatility-adjusted position size."""
        if average_volatility <= 0:
            return base_size

        # Inverse volatility scaling
        vol_ratio = current_volatility / average_volatility
        adjustment_factor = 1.0 / max(0.5, min(2.0, vol_ratio))

        return base_size * adjustment_factor

    def get_portfolio_summary(self) -> Dict[str, float]:
        """Get current portfolio risk summary."""
        total_risk = sum(self.current_positions.values())

        return {
            'total_positions': len(self.current_positions),
            'total_risk_amount': total_risk,
            'portfolio_heat_ratio': total_risk / self.max_portfolio_heat,
            'remaining_heat': self.max_portfolio_heat - total_risk,
            'max_new_position_risk': min(
                self.max_risk_per_trade,
                self.max_portfolio_heat - total_risk
            )
        }

    def validate_position_limits(
        self,
        calculation: PositionSizeCalculation,
        account_value: float
    ) -> Tuple[bool, List[str]]:
        """Validate position against all risk limits."""
        violations = []

        # Check individual position risk
        if calculation.risk_percentage > self.max_risk_per_trade:
            violations.append(f"Position risk {calculation.risk_percentage:.2%} exceeds max {self.max_risk_per_trade:.2%}")

        # Check position size
        if calculation.position_size > self.max_position_size:
            violations.append(f"Position size {calculation.position_size:.2%} exceeds max {self.max_position_size:.2%}")

        # Check portfolio heat
        current_heat = sum(self.current_positions.values())
        total_heat = current_heat + calculation.risk_amount
        if total_heat > self.max_portfolio_heat * account_value:
            violations.append(f"Total portfolio heat would exceed limit")

        # Check minimum position
        if calculation.position_size < self.min_position_size and calculation.position_size > 0:
            violations.append(f"Position size {calculation.position_size:.2%} below minimum {self.min_position_size:.2%}")

        return len(violations) == 0, violations