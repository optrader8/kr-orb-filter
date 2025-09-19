"""Enhanced monitoring system for Linda Raschke strategies with real-time pattern detection."""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
import datetime as dt
from threading import Lock
import time

from src.monitor.orb import ORBMonitor, ORBEvent, ORBSettings  # Base ORB monitor
from src.strategies.linda.holy_grail import HolyGrailStrategy
from src.strategies.linda.turtle_soup import TurtleSoupStrategy
from src.strategies.linda.anti_swing import AntiSwingStrategy
from src.strategies.linda.volatility_breakout import VolatilityBreakoutStrategy
from src.strategies.linda.gap_fade import GapFadeStrategy
from src.risk.position_sizing import PositionSizer
from src.risk.stop_management import StopManager
from src.config import get_config_manager


@dataclass
class PatternAlert:
    """Real-time pattern detection alert."""
    symbol: str
    pattern_type: str  # 'holy_grail_setup', 'turtle_soup_ready', etc.
    timestamp: dt.datetime
    confidence: float
    message: str
    priority: int  # 1 = highest
    data: Dict[str, Any]


@dataclass
class PositionUpdate:
    """Position monitoring update."""
    symbol: str
    strategy: str
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    stop_triggered: bool
    target_hit: bool
    time_in_position: dt.timedelta
    next_action: str


class LindaMonitor:
    """
    Enhanced monitoring system for Linda Raschke strategies.

    Features:
    - Real-time pattern detection
    - Position monitoring
    - Risk management alerts
    - Performance tracking
    - Market condition monitoring
    """

    def __init__(self, config_manager: Optional[Any] = None):
        self.config_manager = config_manager or get_config_manager()
        self.config = self.config_manager.load_all_configs()

        # Initialize strategies for pattern detection
        self.strategies = {
            'holy_grail': HolyGrailStrategy(),
            'turtle_soup': TurtleSoupStrategy(),
            'anti_swing': AntiSwingStrategy(),
            'volatility_breakout': VolatilityBreakoutStrategy(),
            'gap_fade': GapFadeStrategy(),
        }

        # Initialize risk management
        self.position_sizer = PositionSizer()
        self.stop_manager = StopManager()

        # Enhanced ORB settings (30 minutes)
        orb_config = self.config.get('linda_strategies', {}).get('enhanced_orb', {})
        self.orb_settings = ORBSettings(
            window_start=dt.time(hour=9, minute=0),
            window_end=dt.time(hour=9, minute=30),
            cooldown_seconds=orb_config.get('cooldown_seconds', 1800)  # 30 minutes
        )

        # Monitoring state
        self.active_positions: Dict[str, Dict] = {}
        self.pattern_cache: Dict[str, List] = {}
        self.last_update: Dict[str, dt.datetime] = {}
        self.alert_history: List[PatternAlert] = []

        # Thread safety
        self._lock = Lock()

        # Callbacks for alerts
        self.alert_callbacks: List[Callable[[PatternAlert], None]] = []
        self.position_callbacks: List[Callable[[PositionUpdate], None]] = []

    def add_alert_callback(self, callback: Callable[[PatternAlert], None]):
        """Add callback for pattern alerts."""
        self.alert_callbacks.append(callback)

    def add_position_callback(self, callback: Callable[[PositionUpdate], None]):
        """Add callback for position updates."""
        self.position_callbacks.append(callback)

    def start_monitoring(self, symbols: List[str], data_feed_callback: Callable[[str], pd.DataFrame]):
        """
        Start real-time monitoring of symbols.

        Args:
            symbols: List of symbols to monitor
            data_feed_callback: Function to get latest data for a symbol
        """
        print(f"Starting Linda monitoring for {len(symbols)} symbols")

        # Initialize monitoring for each symbol
        for symbol in symbols:
            self.last_update[symbol] = dt.datetime.now()
            self.pattern_cache[symbol] = []

        # Main monitoring loop (in production, this would be event-driven)
        while True:
            try:
                for symbol in symbols:
                    # Get latest data
                    latest_data = data_feed_callback(symbol)
                    if latest_data is None or latest_data.empty:
                        continue

                    # Update monitoring
                    self._update_symbol_monitoring(symbol, latest_data)

                # Check position updates
                self._update_position_monitoring(data_feed_callback)

                # Sleep between updates (adjust based on data feed frequency)
                time.sleep(10)  # 10 seconds

            except KeyboardInterrupt:
                print("Monitoring stopped by user")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def _update_symbol_monitoring(self, symbol: str, data: pd.DataFrame):
        """Update monitoring for a specific symbol."""
        with self._lock:
            current_time = dt.datetime.now()

            # Skip if data is too old
            if len(data) < 50:
                return

            latest_timestamp = data.index[-1]
            if isinstance(latest_timestamp, str):
                latest_timestamp = pd.to_datetime(latest_timestamp)

            # Pattern detection
            patterns_detected = self._detect_patterns(symbol, data, current_time)

            # Enhanced ORB monitoring during market hours
            if self._is_orb_time(current_time):
                orb_alerts = self._monitor_enhanced_orb(symbol, data, current_time)
                patterns_detected.extend(orb_alerts)

            # Process new patterns
            for pattern in patterns_detected:
                self._process_pattern_alert(pattern)

            # Update cache
            self.pattern_cache[symbol] = patterns_detected
            self.last_update[symbol] = current_time

    def _detect_patterns(self, symbol: str, data: pd.DataFrame, current_time: dt.datetime) -> List[PatternAlert]:
        """Detect Linda strategy patterns in real-time."""
        patterns = []

        for strategy_name, strategy in self.strategies.items():
            try:
                # Get latest analysis
                analysis = strategy.analyze(data)
                if analysis.empty:
                    continue

                # Check for setup conditions
                latest_idx = -1
                latest_analysis = analysis.iloc[latest_idx]

                # Holy Grail setup detection
                if strategy_name == 'holy_grail':
                    if latest_analysis.get('hg_long_setup', False) or latest_analysis.get('hg_short_setup', False):
                        direction = 'long' if latest_analysis.get('hg_long_setup', False) else 'short'
                        confidence = latest_analysis.get('adx_adx', 0) / 50.0  # Normalize ADX

                        patterns.append(PatternAlert(
                            symbol=symbol,
                            pattern_type=f'holy_grail_{direction}_setup',
                            timestamp=current_time,
                            confidence=min(1.0, confidence),
                            message=f"Holy Grail {direction} setup detected on {symbol} (ADX: {latest_analysis.get('adx_adx', 0):.1f})",
                            priority=1,
                            data={
                                'adx': latest_analysis.get('adx_adx', 0),
                                'rsi': latest_analysis.get('rsi', 0),
                                'pullback_detected': True
                            }
                        ))

                # Turtle Soup setup detection
                elif strategy_name == 'turtle_soup':
                    if latest_analysis.get('ts_long_setup', False) or latest_analysis.get('ts_short_setup', False):
                        direction = 'long' if latest_analysis.get('ts_long_setup', False) else 'short'
                        breakout_level = latest_analysis.get('high_20' if direction == 'short' else 'low_20', 0)

                        patterns.append(PatternAlert(
                            symbol=symbol,
                            pattern_type=f'turtle_soup_{direction}_setup',
                            timestamp=current_time,
                            confidence=0.8,
                            message=f"Turtle Soup {direction} setup - failed breakout on {symbol}",
                            priority=2,
                            data={
                                'breakout_level': breakout_level,
                                'failed_breakout': True
                            }
                        ))

                # Anti-Swing setup detection
                elif strategy_name == 'anti_swing':
                    if latest_analysis.get('as_long_setup', False) or latest_analysis.get('as_short_setup', False):
                        direction = 'long' if latest_analysis.get('as_long_setup', False) else 'short'
                        rsi2_value = latest_analysis.get('rsi2', 50)

                        patterns.append(PatternAlert(
                            symbol=symbol,
                            pattern_type=f'anti_swing_{direction}_setup',
                            timestamp=current_time,
                            confidence=0.7,
                            message=f"Anti-Swing {direction} setup on {symbol} (RSI2: {rsi2_value:.1f})",
                            priority=3,
                            data={
                                'rsi2': rsi2_value,
                                'extreme_condition': True,
                                'target_ma': latest_analysis.get('target_ma', 0)
                            }
                        ))

            except Exception as e:
                print(f"Error detecting {strategy_name} patterns for {symbol}: {e}")

        return patterns

    def _monitor_enhanced_orb(self, symbol: str, data: pd.DataFrame, current_time: dt.datetime) -> List[PatternAlert]:
        """Monitor enhanced ORB patterns during opening hours."""
        patterns = []

        if not self._is_orb_time(current_time):
            return patterns

        try:
            # Calculate ORB range
            orb_start = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
            orb_end = current_time.replace(hour=9, minute=30, second=0, microsecond=0)

            # Get ORB data
            orb_data = data[data.index >= orb_start.strftime('%Y-%m-%d %H:%M:%S')]
            if orb_data.empty:
                return patterns

            orb_high = orb_data['high'].max()
            orb_low = orb_data['low'].min()
            current_price = data['close'].iloc[-1]

            # Volume analysis
            volume_analysis = self._analyze_orb_volume(data, current_time)

            # Gap analysis
            gap_analysis = self._analyze_gap(data)

            # Check for ORB breakout
            if current_time > orb_end:
                if current_price > orb_high:
                    confidence = 0.8
                    if volume_analysis['above_average']:
                        confidence += 0.1
                    if gap_analysis['favorable']:
                        confidence += 0.1

                    patterns.append(PatternAlert(
                        symbol=symbol,
                        pattern_type='enhanced_orb_long_breakout',
                        timestamp=current_time,
                        confidence=min(1.0, confidence),
                        message=f"Enhanced ORB long breakout on {symbol} - price {current_price:.2f} above ORB high {orb_high:.2f}",
                        priority=1,
                        data={
                            'orb_high': orb_high,
                            'orb_low': orb_low,
                            'current_price': current_price,
                            'volume_confirmation': volume_analysis['above_average'],
                            'gap_favorable': gap_analysis['favorable']
                        }
                    ))

                elif current_price < orb_low:
                    confidence = 0.8
                    if volume_analysis['above_average']:
                        confidence += 0.1
                    if gap_analysis['favorable']:
                        confidence += 0.1

                    patterns.append(PatternAlert(
                        symbol=symbol,
                        pattern_type='enhanced_orb_short_breakout',
                        timestamp=current_time,
                        confidence=min(1.0, confidence),
                        message=f"Enhanced ORB short breakout on {symbol} - price {current_price:.2f} below ORB low {orb_low:.2f}",
                        priority=1,
                        data={
                            'orb_high': orb_high,
                            'orb_low': orb_low,
                            'current_price': current_price,
                            'volume_confirmation': volume_analysis['above_average'],
                            'gap_favorable': gap_analysis['favorable']
                        }
                    ))

        except Exception as e:
            print(f"Error monitoring enhanced ORB for {symbol}: {e}")

        return patterns

    def _analyze_orb_volume(self, data: pd.DataFrame, current_time: dt.datetime) -> Dict[str, Any]:
        """Analyze volume during ORB period."""
        if 'volume' not in data.columns:
            return {'above_average': False, 'volume_ratio': 1.0}

        try:
            # Get 20-day average volume
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]

            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

            return {
                'above_average': volume_ratio > 1.5,  # 50% above average
                'volume_ratio': volume_ratio,
                'current_volume': current_volume,
                'avg_volume': avg_volume
            }
        except Exception:
            return {'above_average': False, 'volume_ratio': 1.0}

    def _analyze_gap(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze gap characteristics."""
        try:
            if len(data) < 2:
                return {'favorable': False, 'gap_percent': 0.0}

            prev_close = data['close'].iloc[-2]
            current_open = data['open'].iloc[-1]
            gap_percent = (current_open - prev_close) / prev_close

            # Small to medium gaps are favorable for continuation
            favorable = 0.005 < abs(gap_percent) < 0.02  # 0.5% to 2%

            return {
                'favorable': favorable,
                'gap_percent': gap_percent,
                'gap_size': 'small' if abs(gap_percent) < 0.01 else 'medium' if abs(gap_percent) < 0.02 else 'large'
            }
        except Exception:
            return {'favorable': False, 'gap_percent': 0.0}

    def _is_orb_time(self, current_time: dt.datetime) -> bool:
        """Check if current time is within ORB monitoring window."""
        market_open = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
        orb_end = current_time.replace(hour=9, minute=45, second=0, microsecond=0)  # Monitor 15 min after ORB

        return market_open <= current_time <= orb_end

    def _process_pattern_alert(self, alert: PatternAlert):
        """Process and dispatch pattern alert."""
        # Add to history
        self.alert_history.append(alert)

        # Keep only recent alerts (last 100)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]

        # Dispatch to callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")

        # Log alert
        print(f"[{alert.timestamp.strftime('%H:%M:%S')}] {alert.message} (Confidence: {alert.confidence:.2f})")

    def _update_position_monitoring(self, data_feed_callback: Callable[[str], pd.DataFrame]):
        """Update monitoring for active positions."""
        if not self.active_positions:
            return

        for symbol, position_info in list(self.active_positions.items()):
            try:
                # Get latest data
                latest_data = data_feed_callback(symbol)
                if latest_data is None or latest_data.empty:
                    continue

                current_price = latest_data['close'].iloc[-1]

                # Calculate P&L
                entry_price = position_info['entry_price']
                direction = position_info['direction']

                if direction == 'long':
                    unrealized_pnl = current_price - entry_price
                else:
                    unrealized_pnl = entry_price - current_price

                unrealized_pnl_percent = unrealized_pnl / entry_price

                # Check stops and targets
                stop_triggered = self._check_stop_triggered(position_info, current_price, latest_data)
                target_hit = self._check_target_hit(position_info, current_price, latest_data)

                # Time in position
                entry_time = position_info['entry_time']
                time_in_position = dt.datetime.now() - entry_time

                # Determine next action
                next_action = self._determine_next_action(position_info, current_price, stop_triggered, target_hit)

                # Create position update
                update = PositionUpdate(
                    symbol=symbol,
                    strategy=position_info['strategy'],
                    entry_price=entry_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent,
                    stop_triggered=stop_triggered,
                    target_hit=target_hit,
                    time_in_position=time_in_position,
                    next_action=next_action
                )

                # Dispatch update
                for callback in self.position_callbacks:
                    try:
                        callback(update)
                    except Exception as e:
                        print(f"Error in position callback: {e}")

                # Handle stop/target hits
                if stop_triggered or target_hit:
                    self._handle_position_exit(symbol, update)

            except Exception as e:
                print(f"Error updating position monitoring for {symbol}: {e}")

    def _check_stop_triggered(self, position_info: Dict, current_price: float, data: pd.DataFrame) -> bool:
        """Check if stop loss has been triggered."""
        stop_price = position_info.get('stop_loss')
        if not stop_price:
            return False

        direction = position_info['direction']

        if direction == 'long':
            return current_price <= stop_price
        else:
            return current_price >= stop_price

    def _check_target_hit(self, position_info: Dict, current_price: float, data: pd.DataFrame) -> bool:
        """Check if profit target has been hit."""
        target_price = position_info.get('target_price')
        if not target_price:
            return False

        direction = position_info['direction']

        if direction == 'long':
            return current_price >= target_price
        else:
            return current_price <= target_price

    def _determine_next_action(self, position_info: Dict, current_price: float, stop_triggered: bool, target_hit: bool) -> str:
        """Determine next action for position."""
        if stop_triggered:
            return "EXIT_STOP_TRIGGERED"
        elif target_hit:
            return "EXIT_TARGET_HIT"
        else:
            # Check if we should trail stop or take partial profits
            entry_price = position_info['entry_price']
            direction = position_info['direction']

            if direction == 'long':
                profit_percent = (current_price - entry_price) / entry_price
            else:
                profit_percent = (entry_price - current_price) / entry_price

            if profit_percent > 0.02:  # 2% profit
                return "CONSIDER_TRAILING_STOP"
            elif profit_percent > 0.01:  # 1% profit
                return "MOVE_STOP_TO_BREAKEVEN"
            else:
                return "HOLD"

    def _handle_position_exit(self, symbol: str, update: PositionUpdate):
        """Handle position exit."""
        print(f"Position exit: {symbol} - {update.next_action}")

        # Remove from active positions
        if symbol in self.active_positions:
            del self.active_positions[symbol]

    def add_position(self, symbol: str, strategy: str, direction: str, entry_price: float,
                    stop_loss: float, target_price: float, entry_time: dt.datetime = None):
        """Add position to monitoring."""
        with self._lock:
            self.active_positions[symbol] = {
                'strategy': strategy,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'entry_time': entry_time or dt.datetime.now()
            }

    def remove_position(self, symbol: str):
        """Remove position from monitoring."""
        with self._lock:
            self.active_positions.pop(symbol, None)

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        with self._lock:
            return {
                'active_positions': len(self.active_positions),
                'symbols_monitored': len(self.pattern_cache),
                'alerts_today': len([a for a in self.alert_history
                                   if a.timestamp.date() == dt.date.today()]),
                'last_update': max(self.last_update.values()) if self.last_update else None,
                'pattern_cache_size': sum(len(patterns) for patterns in self.pattern_cache.values())
            }