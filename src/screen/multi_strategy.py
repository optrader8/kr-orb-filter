"""Multi-strategy coordination and conflict resolution system."""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from src.screen.linda_screener import MultiStrategySignal, LindaScreener
from src.screen.screener import DailyScreener  # Base screener
from src.config import get_config_manager


class ConflictResolution(Enum):
    """Methods for resolving strategy conflicts."""
    HIGHEST_CONFIDENCE = "highest_confidence"
    STRATEGY_PRIORITY = "strategy_priority"
    RISK_ADJUSTED = "risk_adjusted"
    ENSEMBLE_VOTING = "ensemble_voting"


@dataclass
class StrategyAllocation:
    """Portfolio allocation across strategies."""
    strategy_name: str
    allocation_percentage: float
    max_positions: int
    current_positions: int
    available_capacity: float


class MultiStrategyCoordinator:
    """
    Coordinates multiple trading strategies and resolves conflicts.

    Functions:
    - Strategy conflict resolution
    - Portfolio allocation management
    - Risk budget distribution
    - Performance tracking by strategy
    """

    def __init__(self, config_manager: Optional[Any] = None):
        self.config_manager = config_manager or get_config_manager()
        self.config = self.config_manager.load_all_configs()

        # Initialize screeners
        self.linda_screener = LindaScreener(config_manager)
        self.base_screener = DailyScreener(None)  # Will need proper initialization

        # Strategy allocation settings
        self.strategy_allocations = self._initialize_strategy_allocations()
        self.conflict_resolution_method = ConflictResolution.HIGHEST_CONFIDENCE

        # Performance tracking
        self.strategy_performance = {}
        self.correlation_matrix = {}

    def coordinate_strategies(
        self,
        symbols: List[str],
        data_dict: Dict[str, pd.DataFrame],
        market_index: pd.Series,
        sector_index: pd.Series,
        account_value: float,
        current_positions: Dict[str, float] = None
    ) -> List[MultiStrategySignal]:
        """
        Coordinate all strategies and return prioritized signals.

        Args:
            symbols: List of symbols to analyze
            data_dict: OHLCV data per symbol
            market_index: Market index data
            sector_index: Sector index data
            account_value: Total account value
            current_positions: Current position risks

        Returns:
            Coordinated list of signals
        """
        all_signals = []

        # Get Linda strategy signals
        linda_signals = self.linda_screener.screen_market(
            symbols, data_dict, account_value, current_positions
        )
        all_signals.extend(linda_signals)

        # Get base strategy signals (if enabled)
        if self._is_base_strategy_enabled():
            base_signals = self._get_base_strategy_signals(
                symbols, data_dict, market_index, sector_index
            )
            all_signals.extend(base_signals)

        # Resolve conflicts and coordinate
        coordinated_signals = self._resolve_conflicts(all_signals)

        # Apply portfolio allocation constraints
        final_signals = self._apply_allocation_constraints(coordinated_signals, account_value)

        # Update strategy performance tracking
        self._update_performance_tracking(final_signals)

        return final_signals

    def _initialize_strategy_allocations(self) -> Dict[str, StrategyAllocation]:
        """Initialize strategy allocation settings."""
        base_config = self.config.get('base', {})
        linda_config = self.config.get('linda_strategies', {})

        allocations = {}

        # Base strategies
        if base_config.get('default_strategies', {}).get('base_enabled', True):
            allocations['base_nr7_orb'] = StrategyAllocation(
                strategy_name='base_nr7_orb',
                allocation_percentage=0.3,  # 30% of portfolio
                max_positions=5,
                current_positions=0,
                available_capacity=1.0
            )

        # Linda strategies
        linda_enabled = base_config.get('default_strategies', {}).get('linda_enabled', True)
        if linda_enabled:
            # Holy Grail - highest allocation (trend following)
            allocations['holy_grail'] = StrategyAllocation(
                strategy_name='holy_grail',
                allocation_percentage=0.25,  # 25% of portfolio
                max_positions=4,
                current_positions=0,
                available_capacity=1.0
            )

            # Enhanced ORB
            allocations['enhanced_orb'] = StrategyAllocation(
                strategy_name='enhanced_orb',
                allocation_percentage=0.20,  # 20% of portfolio
                max_positions=3,
                current_positions=0,
                available_capacity=1.0
            )

            # Turtle Soup (counter-trend)
            allocations['turtle_soup'] = StrategyAllocation(
                strategy_name='turtle_soup',
                allocation_percentage=0.15,  # 15% of portfolio
                max_positions=3,
                current_positions=0,
                available_capacity=1.0
            )

            # Volatility Breakout
            allocations['volatility_breakout'] = StrategyAllocation(
                strategy_name='volatility_breakout',
                allocation_percentage=0.15,  # 15% of portfolio
                max_positions=3,
                current_positions=0,
                available_capacity=1.0
            )

            # Anti-Swing (mean reversion)
            allocations['anti_swing'] = StrategyAllocation(
                strategy_name='anti_swing',
                allocation_percentage=0.08,  # 8% of portfolio
                max_positions=2,
                current_positions=0,
                available_capacity=1.0
            )

            # Gap Fade (mean reversion)
            allocations['gap_fade'] = StrategyAllocation(
                strategy_name='gap_fade',
                allocation_percentage=0.07,  # 7% of portfolio
                max_positions=2,
                current_positions=0,
                available_capacity=1.0
            )

        return allocations

    def _is_base_strategy_enabled(self) -> bool:
        """Check if base strategies are enabled."""
        return self.config.get('base', {}).get('default_strategies', {}).get('base_enabled', True)

    def _get_base_strategy_signals(
        self,
        symbols: List[str],
        data_dict: Dict[str, pd.DataFrame],
        market_index: pd.Series,
        sector_index: pd.Series
    ) -> List[MultiStrategySignal]:
        """Get signals from base strategies and convert to MultiStrategySignal format."""
        base_signals = []

        # This would integrate with the existing base screener
        # For now, we'll return empty list as the base screener needs adaptation
        # TODO: Integrate with existing screener.py

        return base_signals

    def _resolve_conflicts(self, signals: List[MultiStrategySignal]) -> List[MultiStrategySignal]:
        """Resolve conflicts between strategies."""
        if not signals:
            return signals

        # Group signals by symbol
        symbol_signals = {}
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)

        resolved_signals = []

        for symbol, symbol_signal_list in symbol_signals.items():
            if len(symbol_signal_list) == 1:
                # No conflict
                resolved_signals.extend(symbol_signal_list)
            else:
                # Resolve conflict
                resolved_signal = self._resolve_symbol_conflict(symbol_signal_list)
                if resolved_signal:
                    resolved_signals.append(resolved_signal)

        return resolved_signals

    def _resolve_symbol_conflict(self, signals: List[MultiStrategySignal]) -> Optional[MultiStrategySignal]:
        """Resolve conflict for a specific symbol."""
        if not signals:
            return None

        if self.conflict_resolution_method == ConflictResolution.HIGHEST_CONFIDENCE:
            return max(signals, key=lambda s: s.combined_confidence)

        elif self.conflict_resolution_method == ConflictResolution.STRATEGY_PRIORITY:
            # Use predefined strategy priority
            priority_order = ['holy_grail', 'enhanced_orb', 'volatility_breakout', 'turtle_soup', 'anti_swing', 'gap_fade']
            for strategy in priority_order:
                for signal in signals:
                    if signal.primary_strategy == strategy:
                        return signal
            return signals[0]  # Fallback

        elif self.conflict_resolution_method == ConflictResolution.RISK_ADJUSTED:
            # Choose signal with best risk-adjusted return potential
            best_signal = None
            best_score = -1

            for signal in signals:
                # Calculate risk-adjusted score
                risk_penalty = {'LOW': 0, 'MODERATE': 0.1, 'HIGH': 0.2, 'VERY_HIGH': 0.3}
                penalty = risk_penalty.get(signal.risk_assessment, 0.3)
                score = signal.combined_confidence * (1 - penalty)

                if score > best_score:
                    best_score = score
                    best_signal = signal

            return best_signal

        elif self.conflict_resolution_method == ConflictResolution.ENSEMBLE_VOTING:
            # Create ensemble signal
            return self._create_ensemble_signal(signals)

        return signals[0]  # Default fallback

    def _create_ensemble_signal(self, signals: List[MultiStrategySignal]) -> MultiStrategySignal:
        """Create an ensemble signal from conflicting signals."""
        if not signals:
            return None

        # Use the highest confidence signal as base
        base_signal = max(signals, key=lambda s: s.combined_confidence)

        # Calculate ensemble confidence
        confidence_values = [s.combined_confidence for s in signals]
        ensemble_confidence = np.mean(confidence_values) + (np.std(confidence_values) * 0.1)  # Diversity bonus

        # Combine supporting strategies
        all_supporting = []
        for signal in signals:
            all_supporting.extend(signal.supporting_strategies)
            if signal != base_signal:
                all_supporting.append(signal.primary_strategy)

        # Create ensemble signal
        ensemble_signal = MultiStrategySignal(
            symbol=base_signal.symbol,
            timestamp=base_signal.timestamp,
            primary_strategy=base_signal.primary_strategy,
            primary_direction=base_signal.primary_direction,
            primary_confidence=base_signal.primary_confidence,
            primary_entry_price=base_signal.primary_entry_price,
            primary_stop_loss=base_signal.primary_stop_loss,
            primary_target=base_signal.primary_target,
            supporting_strategies=list(set(all_supporting)),  # Remove duplicates
            combined_confidence=min(1.0, ensemble_confidence),
            position_size_recommendation=base_signal.position_size_recommendation,
            risk_assessment=base_signal.risk_assessment,
            market_conditions=base_signal.market_conditions
        )

        return ensemble_signal

    def _apply_allocation_constraints(
        self,
        signals: List[MultiStrategySignal],
        account_value: float
    ) -> List[MultiStrategySignal]:
        """Apply portfolio allocation constraints to signals."""
        constrained_signals = []

        # Sort signals by combined confidence
        sorted_signals = sorted(signals, key=lambda s: s.combined_confidence, reverse=True)

        # Track allocation usage
        strategy_usage = {name: 0.0 for name in self.strategy_allocations.keys()}
        strategy_positions = {name: 0 for name in self.strategy_allocations.keys()}

        for signal in sorted_signals:
            strategy = signal.primary_strategy
            allocation = self.strategy_allocations.get(strategy)

            if not allocation:
                continue  # Strategy not in allocation plan

            # Check position limit
            if strategy_positions[strategy] >= allocation.max_positions:
                continue

            # Check allocation limit
            signal_allocation = signal.position_size_recommendation
            total_strategy_allocation = strategy_usage[strategy] + signal_allocation

            max_strategy_allocation = allocation.allocation_percentage
            if total_strategy_allocation > max_strategy_allocation:
                # Reduce signal size to fit allocation
                available_allocation = max_strategy_allocation - strategy_usage[strategy]
                if available_allocation > 0.001:  # At least 0.1%
                    signal.position_size_recommendation = available_allocation
                else:
                    continue  # Skip signal

            # Accept signal
            constrained_signals.append(signal)
            strategy_usage[strategy] += signal.position_size_recommendation
            strategy_positions[strategy] += 1

        return constrained_signals

    def _update_performance_tracking(self, signals: List[MultiStrategySignal]):
        """Update strategy performance tracking."""
        for signal in signals:
            strategy = signal.primary_strategy

            if strategy not in self.strategy_performance:
                self.strategy_performance[strategy] = {
                    'signals_generated': 0,
                    'avg_confidence': 0.0,
                    'allocation_used': 0.0
                }

            perf = self.strategy_performance[strategy]
            perf['signals_generated'] += 1

            # Update running average confidence
            prev_avg = perf['avg_confidence']
            new_count = perf['signals_generated']
            perf['avg_confidence'] = ((prev_avg * (new_count - 1)) + signal.combined_confidence) / new_count

            perf['allocation_used'] += signal.position_size_recommendation

    def get_strategy_allocation_summary(self) -> Dict[str, Any]:
        """Get current strategy allocation summary."""
        summary = {}

        for strategy_name, allocation in self.strategy_allocations.items():
            performance = self.strategy_performance.get(strategy_name, {})

            summary[strategy_name] = {
                'max_allocation': allocation.allocation_percentage,
                'current_usage': performance.get('allocation_used', 0.0),
                'available_capacity': max(0.0, allocation.allocation_percentage - performance.get('allocation_used', 0.0)),
                'max_positions': allocation.max_positions,
                'current_positions': allocation.current_positions,
                'signals_generated': performance.get('signals_generated', 0),
                'avg_confidence': performance.get('avg_confidence', 0.0)
            }

        return summary

    def rebalance_allocations(self, performance_data: Dict[str, Dict[str, float]]):
        """Rebalance strategy allocations based on performance."""
        if not performance_data:
            return

        # Calculate performance scores
        strategy_scores = {}
        for strategy, data in performance_data.items():
            # Simple scoring: (win_rate * avg_return) - (max_drawdown * 0.5)
            win_rate = data.get('win_rate', 0.5)
            avg_return = data.get('avg_return', 0.0)
            max_drawdown = data.get('max_drawdown', 0.1)

            score = (win_rate * avg_return) - (max_drawdown * 0.5)
            strategy_scores[strategy] = max(0.0, score)

        # Rebalance allocations based on scores
        total_score = sum(strategy_scores.values())
        if total_score > 0:
            for strategy, allocation in self.strategy_allocations.items():
                if strategy in strategy_scores:
                    new_percentage = (strategy_scores[strategy] / total_score) * 0.8  # 80% based on performance
                    base_percentage = allocation.allocation_percentage * 0.2  # 20% base allocation

                    allocation.allocation_percentage = new_percentage + base_percentage

    def get_correlation_matrix(self) -> pd.DataFrame:
        """Get strategy correlation matrix."""
        if not self.correlation_matrix:
            return pd.DataFrame()

        strategies = list(self.correlation_matrix.keys())
        n = len(strategies)
        correlation_data = np.zeros((n, n))

        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies):
                if i == j:
                    correlation_data[i, j] = 1.0
                else:
                    correlation_data[i, j] = self.correlation_matrix.get(strategy1, {}).get(strategy2, 0.0)

        return pd.DataFrame(correlation_data, index=strategies, columns=strategies)

    def update_correlations(self, returns_data: Dict[str, pd.Series]):
        """Update strategy correlation matrix."""
        if len(returns_data) < 2:
            return

        strategies = list(returns_data.keys())
        self.correlation_matrix = {}

        for strategy1 in strategies:
            self.correlation_matrix[strategy1] = {}
            for strategy2 in strategies:
                if strategy1 == strategy2:
                    correlation = 1.0
                else:
                    # Calculate correlation between strategy returns
                    returns1 = returns_data[strategy1]
                    returns2 = returns_data[strategy2]

                    # Align series
                    aligned_returns = pd.DataFrame({strategy1: returns1, strategy2: returns2}).dropna()

                    if len(aligned_returns) > 10:
                        correlation = aligned_returns[strategy1].corr(aligned_returns[strategy2])
                    else:
                        correlation = 0.0

                self.correlation_matrix[strategy1][strategy2] = correlation

    def get_portfolio_diversification_score(self) -> float:
        """Calculate portfolio diversification score based on strategy correlations."""
        if not self.correlation_matrix:
            return 1.0  # Perfect diversification if no correlation data

        correlations = []
        strategies = list(self.correlation_matrix.keys())

        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies[i+1:], i+1):
                correlation = self.correlation_matrix.get(strategy1, {}).get(strategy2, 0.0)
                correlations.append(abs(correlation))

        if not correlations:
            return 1.0

        # Diversification score: 1 - average absolute correlation
        avg_correlation = np.mean(correlations)
        diversification_score = 1.0 - avg_correlation

        return max(0.0, min(1.0, diversification_score))