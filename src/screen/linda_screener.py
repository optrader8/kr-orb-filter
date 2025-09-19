"""Multi-strategy screener integrating Linda Raschke strategies with base system."""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import datetime as dt

from src.strategies.linda.holy_grail import HolyGrailStrategy
from src.strategies.linda.turtle_soup import TurtleSoupStrategy
from src.strategies.linda.anti_swing import AntiSwingStrategy
from src.strategies.linda.volatility_breakout import VolatilityBreakoutStrategy
from src.strategies.linda.gap_fade import GapFadeStrategy
from src.data.market_psychology import MarketPsychologyLoader
from src.risk.position_sizing import PositionSizer
from src.config import get_linda_strategy_config, get_config_manager


@dataclass
class MultiStrategySignal:
    """Combined signal from multiple strategies."""
    symbol: str
    timestamp: pd.Timestamp
    primary_strategy: str
    primary_direction: str
    primary_confidence: float
    primary_entry_price: float
    primary_stop_loss: float
    primary_target: float
    supporting_strategies: List[str]
    combined_confidence: float
    position_size_recommendation: float
    risk_assessment: str
    market_conditions: Dict[str, Any]


class LindaScreener:
    """
    Multi-strategy screener coordinating Linda Raschke strategies.

    Integrates:
    - Holy Grail Setup
    - Turtle Soup
    - Anti-Swing
    - Market psychology
    - Risk management
    """

    def __init__(self, config_manager: Optional[Any] = None):
        self.config_manager = config_manager or get_config_manager()
        self.config = self.config_manager.load_linda_config()

        # Initialize strategies
        self.strategies = {
            'holy_grail': HolyGrailStrategy(),
            'turtle_soup': TurtleSoupStrategy(),
            'anti_swing': AntiSwingStrategy(),
            'volatility_breakout': VolatilityBreakoutStrategy(),
            'gap_fade': GapFadeStrategy(),
        }

        # Initialize components
        self.psychology_loader = MarketPsychologyLoader()
        self.position_sizer = PositionSizer()

        # Strategy priority (lower number = higher priority)
        self.strategy_priority = {
            'holy_grail': 1,
            'enhanced_orb': 2,
            'volatility_breakout': 3,
            'turtle_soup': 4,
            'anti_swing': 5,
            'gap_fade': 6
        }

        # Maximum strategies per symbol
        self.max_strategies_per_symbol = self.config.get('strategy_combination', {}).get('max_strategies_per_symbol', 2)

    def screen_market(
        self,
        symbols: List[str],
        data_dict: Dict[str, pd.DataFrame],
        account_value: float,
        current_positions: Dict[str, float] = None
    ) -> List[MultiStrategySignal]:
        """
        Screen entire market using multiple Linda strategies.

        Args:
            symbols: List of symbols to screen
            data_dict: Dictionary of OHLCV data per symbol
            account_value: Total account value for position sizing
            current_positions: Current positions for portfolio heat management

        Returns:
            List of MultiStrategySignal objects ranked by combined confidence
        """
        all_signals = []

        # Get market psychology data
        market_psychology = self._get_market_psychology()

        # Update position sizer with current positions
        if current_positions:
            for symbol, risk_amount in current_positions.items():
                self.position_sizer.update_portfolio(symbol, risk_amount)

        # Screen each symbol
        for symbol in symbols:
            if symbol not in data_dict or data_dict[symbol].empty:
                continue

            data = data_dict[symbol]
            if len(data) < 50:  # Need sufficient data
                continue

            # Get signals from each strategy
            strategy_signals = self._get_strategy_signals(symbol, data)

            if not strategy_signals:
                continue

            # Combine and prioritize signals
            combined_signals = self._combine_strategy_signals(
                symbol, strategy_signals, data, market_psychology, account_value
            )

            all_signals.extend(combined_signals)

        # Rank and filter signals
        ranked_signals = self._rank_and_filter_signals(all_signals)

        return ranked_signals

    def _get_strategy_signals(self, symbol: str, data: pd.DataFrame) -> Dict[str, List]:
        """Get signals from all enabled strategies for a symbol."""
        strategy_signals = {}

        for strategy_name, strategy in self.strategies.items():
            strategy_config = get_linda_strategy_config(strategy_name)
            if not strategy_config.enabled:
                continue

            try:
                signals = strategy.get_signals(data)
                if signals:
                    strategy_signals[strategy_name] = signals
            except Exception as e:
                print(f"Error getting {strategy_name} signals for {symbol}: {e}")
                continue

        return strategy_signals

    def _combine_strategy_signals(
        self,
        symbol: str,
        strategy_signals: Dict[str, List],
        data: pd.DataFrame,
        market_psychology: Dict[str, Any],
        account_value: float
    ) -> List[MultiStrategySignal]:
        """Combine signals from multiple strategies for a symbol."""
        combined_signals = []

        # Group signals by timestamp and direction
        signal_groups = self._group_signals_by_time_and_direction(strategy_signals)

        for (timestamp, direction), signals in signal_groups.items():
            if len(signals) == 0:
                continue

            # Find primary strategy (highest priority)
            primary_signal = min(signals, key=lambda s: self.strategy_priority.get(s['strategy'], 999))

            # Find supporting strategies
            supporting_strategies = [s['strategy'] for s in signals if s['strategy'] != primary_signal['strategy']]

            # Calculate combined confidence
            combined_confidence = self._calculate_combined_confidence(signals, market_psychology)

            # Calculate position size
            position_size = self._calculate_position_size(
                symbol, primary_signal, combined_confidence, account_value
            )

            # Assess market conditions
            market_conditions = self._assess_market_conditions(data, market_psychology, timestamp)

            # Create combined signal
            combined_signal = MultiStrategySignal(
                symbol=symbol,
                timestamp=timestamp,
                primary_strategy=primary_signal['strategy'],
                primary_direction=direction,
                primary_confidence=primary_signal['signal'].confidence,
                primary_entry_price=primary_signal['signal'].entry_price,
                primary_stop_loss=primary_signal['signal'].stop_loss,
                primary_target=primary_signal['signal'].target_price,
                supporting_strategies=supporting_strategies,
                combined_confidence=combined_confidence,
                position_size_recommendation=position_size.position_size if position_size else 0.0,
                risk_assessment=self._assess_risk_level(combined_confidence, len(supporting_strategies)),
                market_conditions=market_conditions
            )

            combined_signals.append(combined_signal)

        return combined_signals

    def _group_signals_by_time_and_direction(self, strategy_signals: Dict[str, List]) -> Dict[Tuple[pd.Timestamp, str], List]:
        """Group signals by timestamp and direction."""
        signal_groups = {}

        for strategy_name, signals in strategy_signals.items():
            for signal in signals:
                key = (signal.timestamp, signal.direction)
                if key not in signal_groups:
                    signal_groups[key] = []

                signal_groups[key].append({
                    'strategy': strategy_name,
                    'signal': signal
                })

        return signal_groups

    def _calculate_combined_confidence(
        self,
        signals: List[Dict],
        market_psychology: Dict[str, Any]
    ) -> float:
        """Calculate combined confidence from multiple strategy signals."""
        if len(signals) == 1:
            base_confidence = signals[0]['signal'].confidence
        else:
            # Weighted average based on strategy priority
            total_weight = 0
            weighted_confidence = 0

            for signal_data in signals:
                strategy_name = signal_data['strategy']
                priority = self.strategy_priority.get(strategy_name, 5)
                weight = 1.0 / priority  # Higher priority = higher weight

                weighted_confidence += signal_data['signal'].confidence * weight
                total_weight += weight

            base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5

        # Apply market psychology adjustment
        psychology_adjustment = self._get_psychology_adjustment(market_psychology)

        # Multiple strategy bonus
        multi_strategy_bonus = min(0.2, (len(signals) - 1) * 0.1)  # Up to 20% bonus

        combined_confidence = base_confidence * psychology_adjustment + multi_strategy_bonus

        return min(1.0, combined_confidence)

    def _get_psychology_adjustment(self, market_psychology: Dict[str, Any]) -> float:
        """Get market psychology adjustment factor."""
        if not market_psychology:
            return 1.0

        adjustment = 1.0

        # VIX adjustment
        vix_data = market_psychology.get('vix')
        if vix_data is not None and len(vix_data) > 0:
            current_vix = vix_data.iloc[-1] if hasattr(vix_data, 'iloc') else vix_data
            if current_vix > 30:  # High fear
                adjustment *= 0.9  # Slightly reduce confidence
            elif current_vix < 15:  # Low fear/complacency
                adjustment *= 0.95  # Slightly reduce confidence

        # Put/Call ratio adjustment
        pc_data = market_psychology.get('put_call_ratio')
        if pc_data is not None and len(pc_data) > 0:
            current_pc = pc_data.iloc[-1] if hasattr(pc_data, 'iloc') else pc_data
            if current_pc > 1.3:  # Extreme bearishness
                adjustment *= 1.05  # Slight boost for contrarian signals
            elif current_pc < 0.7:  # Extreme bullishness
                adjustment *= 1.05  # Slight boost for contrarian signals

        return adjustment

    def _calculate_position_size(
        self,
        symbol: str,
        primary_signal: Dict,
        combined_confidence: float,
        account_value: float
    ) -> Optional[Any]:
        """Calculate position size for the combined signal."""
        signal = primary_signal['signal']

        try:
            position_calc = self.position_sizer.calculate_position_size(
                symbol=symbol,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                account_value=account_value,
                strategy_name=primary_signal['strategy'],
                confidence=combined_confidence
            )
            return position_calc
        except Exception as e:
            print(f"Error calculating position size for {symbol}: {e}")
            return None

    def _assess_market_conditions(
        self,
        data: pd.DataFrame,
        market_psychology: Dict[str, Any],
        timestamp: pd.Timestamp
    ) -> Dict[str, Any]:
        """Assess current market conditions."""
        conditions = {}

        # Trend assessment
        if len(data) >= 50:
            sma20 = data['close'].rolling(20).mean()
            sma50 = data['close'].rolling(50).mean()

            latest_idx = data.index.get_indexer([timestamp], method='nearest')[0]
            if latest_idx >= 0:
                current_price = data['close'].iloc[latest_idx]
                current_sma20 = sma20.iloc[latest_idx]
                current_sma50 = sma50.iloc[latest_idx]

                if current_price > current_sma20 > current_sma50:
                    conditions['trend'] = 'uptrend'
                elif current_price < current_sma20 < current_sma50:
                    conditions['trend'] = 'downtrend'
                else:
                    conditions['trend'] = 'sideways'

        # Volatility assessment
        if len(data) >= 20:
            returns = data['close'].pct_change()
            volatility = returns.rolling(20).std() * np.sqrt(252)
            latest_vol = volatility.iloc[-1] if not volatility.empty else 0

            if latest_vol > 0.4:
                conditions['volatility'] = 'high'
            elif latest_vol < 0.15:
                conditions['volatility'] = 'low'
            else:
                conditions['volatility'] = 'normal'

        # Market psychology
        conditions['psychology'] = market_psychology

        return conditions

    def _assess_risk_level(self, confidence: float, supporting_strategies: int) -> str:
        """Assess overall risk level of the signal."""
        if confidence > 0.8 and supporting_strategies >= 1:
            return "LOW"
        elif confidence > 0.6 and supporting_strategies >= 0:
            return "MODERATE"
        elif confidence > 0.4:
            return "HIGH"
        else:
            return "VERY_HIGH"

    def _rank_and_filter_signals(self, signals: List[MultiStrategySignal]) -> List[MultiStrategySignal]:
        """Rank and filter signals based on combined criteria."""
        if not signals:
            return []

        # Sort by combined confidence (descending)
        signals.sort(key=lambda s: s.combined_confidence, reverse=True)

        # Filter by risk level and position size
        filtered_signals = []
        symbols_used = set()

        for signal in signals:
            # Skip if symbol already has a signal (prevent duplicates)
            if signal.symbol in symbols_used:
                continue

            # Skip very high risk signals unless confidence is exceptional
            if signal.risk_assessment == "VERY_HIGH" and signal.combined_confidence < 0.7:
                continue

            # Skip if position size too small
            if signal.position_size_recommendation < 0.001:  # Less than 0.1%
                continue

            filtered_signals.append(signal)
            symbols_used.add(signal.symbol)

            # Limit total number of signals
            if len(filtered_signals) >= 20:  # Top 20 signals
                break

        return filtered_signals

    def _get_market_psychology(self) -> Dict[str, Any]:
        """Get current market psychology data."""
        try:
            end_date = dt.date.today()
            start_date = end_date - dt.timedelta(days=30)

            psychology_data = self.psychology_loader.get_sentiment_indicators(start_date, end_date)

            return {
                'vix': psychology_data.get('vix'),
                'put_call_ratio': psychology_data.get('put_call_ratio'),
                'fii_flows': psychology_data.get('fii_net_flows'),
                'data_date': end_date
            }
        except Exception as e:
            print(f"Error loading market psychology data: {e}")
            return {}

    def validate_signal_quality(self, signal: MultiStrategySignal, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate signal quality and provide detailed assessment."""
        validation = {
            'is_valid': True,
            'warnings': [],
            'quality_score': 0.0,
            'technical_factors': {},
            'risk_factors': {}
        }

        # Check technical factors
        latest_data = data.iloc[-1]

        # Volume validation
        if 'volume' in data.columns:
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = latest_data['volume']

            if current_volume < avg_volume * 0.5:
                validation['warnings'].append("Low volume - signal reliability reduced")
                validation['quality_score'] -= 0.1
            elif current_volume > avg_volume * 1.5:
                validation['quality_score'] += 0.1

            validation['technical_factors']['volume_ratio'] = current_volume / avg_volume

        # Price action validation
        range_20 = (data['high'].rolling(20).max() - data['low'].rolling(20).min()).iloc[-1]
        current_range = latest_data['high'] - latest_data['low']

        validation['technical_factors']['range_ratio'] = current_range / range_20

        # Risk factor assessment
        if signal.position_size_recommendation > 0.03:  # > 3%
            validation['warnings'].append("Large position size - consider reducing")

        if signal.risk_assessment in ["HIGH", "VERY_HIGH"]:
            validation['warnings'].append(f"Risk level: {signal.risk_assessment}")

        # Calculate overall quality score
        base_score = signal.combined_confidence
        technical_score = validation['technical_factors'].get('volume_ratio', 1.0) * 0.1
        risk_penalty = len(validation['warnings']) * 0.05

        validation['quality_score'] = max(0.0, base_score + technical_score - risk_penalty)
        validation['is_valid'] = validation['quality_score'] > 0.3  # Minimum threshold

        return validation