"""Enhanced notification system for Linda Raschke strategies with intelligent formatting and prioritization."""
from __future__ import annotations

import json
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
import datetime as dt
from enum import Enum
import time
from threading import Lock, Thread
import queue

from src.monitor.linda_monitor import PatternAlert, PositionUpdate
from src.screen.linda_screener import MultiStrategySignal
from src.config import get_config_manager


class NotificationChannel(Enum):
    """Available notification channels."""
    SLACK = "slack"
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertPriority(Enum):
    """Alert priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class NotificationConfig:
    """Configuration for a notification channel."""
    channel: NotificationChannel
    enabled: bool
    endpoint: str
    api_key: Optional[str] = None
    chat_id: Optional[str] = None
    priority_filter: List[AlertPriority] = None
    rate_limit_per_hour: int = 20
    template_override: Optional[str] = None


@dataclass
class FormattedMessage:
    """Formatted notification message."""
    title: str
    body: str
    formatted_text: str
    priority: AlertPriority
    metadata: Dict[str, Any]


class LindaNotificationManager:
    """
    Enhanced notification manager for Linda Raschke strategies.

    Features:
    - Strategy-specific message formatting
    - Intelligent prioritization
    - Rate limiting and throttling
    - Multi-channel support
    - Template customization
    """

    def __init__(self, config_manager: Optional[Any] = None):
        self.config_manager = config_manager or get_config_manager()
        self.config = self.config_manager.load_all_configs()

        # Initialize channels
        self.channels = self._initialize_channels()

        # Message formatting
        self.formatters = {
            'pattern_alert': self._format_pattern_alert,
            'position_update': self._format_position_update,
            'strategy_signal': self._format_strategy_signal,
            'risk_alert': self._format_risk_alert
        }

        # Rate limiting
        self.rate_limits = {}
        self.message_queue = queue.Queue()
        self._lock = Lock()

        # Start message processor
        self.processor_thread = Thread(target=self._process_message_queue, daemon=True)
        self.processor_thread.start()

    def _initialize_channels(self) -> Dict[str, NotificationConfig]:
        """Initialize notification channels from config."""
        channels = {}
        base_config = self.config.get('base', {})
        alert_config = base_config.get('alerts', {})

        # Slack
        slack_config = alert_config.get('channels', {}).get('slack', {})
        if slack_config.get('enabled', False):
            channels['slack'] = NotificationConfig(
                channel=NotificationChannel.SLACK,
                enabled=True,
                endpoint=slack_config.get('webhook_url', ''),
                rate_limit_per_hour=alert_config.get('max_per_hour', 20),
                priority_filter=[AlertPriority.CRITICAL, AlertPriority.HIGH]
            )

        # Telegram
        telegram_config = alert_config.get('channels', {}).get('telegram', {})
        if telegram_config.get('enabled', False):
            channels['telegram'] = NotificationConfig(
                channel=NotificationChannel.TELEGRAM,
                enabled=True,
                endpoint=f"https://api.telegram.org/bot{telegram_config.get('bot_token', '')}/sendMessage",
                chat_id=telegram_config.get('chat_id', ''),
                rate_limit_per_hour=alert_config.get('max_per_hour', 20),
                priority_filter=[AlertPriority.CRITICAL, AlertPriority.HIGH, AlertPriority.MEDIUM]
            )

        return channels

    def send_pattern_alert(self, alert: PatternAlert):
        """Send pattern detection alert."""
        priority = self._determine_pattern_priority(alert)
        message = self._format_pattern_alert(alert, priority)

        self._queue_message('pattern_alert', message, priority)

    def send_position_update(self, update: PositionUpdate):
        """Send position monitoring update."""
        priority = self._determine_position_priority(update)
        message = self._format_position_update(update, priority)

        self._queue_message('position_update', message, priority)

    def send_strategy_signal(self, signal: MultiStrategySignal):
        """Send strategy signal alert."""
        priority = self._determine_signal_priority(signal)
        message = self._format_strategy_signal(signal, priority)

        self._queue_message('strategy_signal', message, priority)

    def send_risk_alert(self, alert_type: str, data: Dict[str, Any]):
        """Send risk management alert."""
        priority = AlertPriority.CRITICAL if alert_type == 'portfolio_heat_exceeded' else AlertPriority.HIGH
        message = self._format_risk_alert(alert_type, data, priority)

        self._queue_message('risk_alert', message, priority)

    def _determine_pattern_priority(self, alert: PatternAlert) -> AlertPriority:
        """Determine priority for pattern alert."""
        if alert.confidence > 0.8 and alert.priority == 1:
            return AlertPriority.CRITICAL
        elif alert.confidence > 0.6 and alert.priority <= 2:
            return AlertPriority.HIGH
        elif alert.confidence > 0.4:
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW

    def _determine_position_priority(self, update: PositionUpdate) -> AlertPriority:
        """Determine priority for position update."""
        if update.stop_triggered or update.target_hit:
            return AlertPriority.HIGH
        elif abs(update.unrealized_pnl_percent) > 0.05:  # >5% move
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW

    def _determine_signal_priority(self, signal: MultiStrategySignal) -> AlertPriority:
        """Determine priority for strategy signal."""
        if signal.combined_confidence > 0.8 and len(signal.supporting_strategies) >= 1:
            return AlertPriority.CRITICAL
        elif signal.combined_confidence > 0.6:
            return AlertPriority.HIGH
        elif signal.combined_confidence > 0.4:
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW

    def _format_pattern_alert(self, alert: PatternAlert, priority: AlertPriority) -> FormattedMessage:
        """Format pattern detection alert."""
        # Priority emoji
        priority_emoji = {
            AlertPriority.CRITICAL: "🚨",
            AlertPriority.HIGH: "⚠️",
            AlertPriority.MEDIUM: "📊",
            AlertPriority.LOW: "ℹ️"
        }

        # Strategy emoji
        strategy_emoji = {
            'holy_grail': '🏆',
            'turtle_soup': '🐢',
            'anti_swing': '↩️',
            'enhanced_orb': '📈',
            'volatility_breakout': '💥',
            'gap_fade': '📉'
        }

        strategy = alert.pattern_type.split('_')[0] + '_' + alert.pattern_type.split('_')[1]
        emoji = strategy_emoji.get(strategy, '📈')

        title = f"{priority_emoji[priority]} {emoji} {alert.pattern_type.replace('_', ' ').title()}"

        # Detailed body
        body_parts = [
            f"Symbol: {alert.symbol}",
            f"Confidence: {alert.confidence:.1%}",
            f"Time: {alert.timestamp.strftime('%H:%M:%S')}"
        ]

        # Add strategy-specific details
        if 'adx' in alert.data:
            body_parts.append(f"ADX: {alert.data['adx']:.1f}")
        if 'rsi' in alert.data:
            body_parts.append(f"RSI: {alert.data['rsi']:.1f}")
        if 'rsi2' in alert.data:
            body_parts.append(f"RSI2: {alert.data['rsi2']:.1f}")

        body = '\n'.join(body_parts)

        # Formatted text for different channels
        slack_text = f"*{title}*\n```{body}```"
        telegram_text = f"<b>{title}</b>\n<pre>{body}</pre>"

        return FormattedMessage(
            title=title,
            body=body,
            formatted_text=slack_text,  # Default to Slack format
            priority=priority,
            metadata={
                'alert_type': 'pattern',
                'symbol': alert.symbol,
                'pattern': alert.pattern_type,
                'confidence': alert.confidence,
                'slack_format': slack_text,
                'telegram_format': telegram_text
            }
        )

    def _format_position_update(self, update: PositionUpdate, priority: AlertPriority) -> FormattedMessage:
        """Format position monitoring update."""
        if update.stop_triggered:
            title = f"🛑 Stop Loss Triggered - {update.symbol}"
            action = "STOP TRIGGERED"
        elif update.target_hit:
            title = f"🎯 Target Hit - {update.symbol}"
            action = "TARGET HIT"
        elif update.unrealized_pnl_percent > 0.02:
            title = f"📈 Strong Profit - {update.symbol}"
            action = "MONITOR"
        elif update.unrealized_pnl_percent < -0.02:
            title = f"📉 Drawdown Alert - {update.symbol}"
            action = "REVIEW"
        else:
            title = f"📊 Position Update - {update.symbol}"
            action = "HOLD"

        # Format P&L
        pnl_sign = "+" if update.unrealized_pnl > 0 else ""
        pnl_color = "🟢" if update.unrealized_pnl > 0 else "🔴" if update.unrealized_pnl < 0 else "⚪"

        body = f"""Strategy: {update.strategy}
Entry: {update.entry_price:.2f}
Current: {update.current_price:.2f}
P&L: {pnl_color} {pnl_sign}{update.unrealized_pnl:.2f} ({pnl_sign}{update.unrealized_pnl_percent:.1%})
Time: {update.time_in_position}
Action: {action}"""

        return FormattedMessage(
            title=title,
            body=body,
            formatted_text=f"*{title}*\n```{body}```",
            priority=priority,
            metadata={
                'alert_type': 'position',
                'symbol': update.symbol,
                'strategy': update.strategy,
                'pnl_percent': update.unrealized_pnl_percent
            }
        )

    def _format_strategy_signal(self, signal: MultiStrategySignal, priority: AlertPriority) -> FormattedMessage:
        """Format strategy signal alert."""
        direction_emoji = "📈" if signal.primary_direction == "long" else "📉"
        confidence_emoji = "🔥" if signal.combined_confidence > 0.8 else "⭐" if signal.combined_confidence > 0.6 else "📊"

        title = f"{confidence_emoji} {direction_emoji} {signal.primary_strategy.replace('_', ' ').title()} - {signal.symbol}"

        # Risk/Reward calculation
        risk = abs(signal.primary_entry_price - signal.primary_stop_loss)
        reward = abs(signal.primary_target - signal.primary_entry_price)
        rr_ratio = reward / risk if risk > 0 else 0

        body = f"""Direction: {signal.primary_direction.upper()}
Entry: {signal.primary_entry_price:.2f}
Stop: {signal.primary_stop_loss:.2f}
Target: {signal.primary_target:.2f}
R/R: {rr_ratio:.1f}:1
Confidence: {signal.combined_confidence:.1%}
Position Size: {signal.position_size_recommendation:.1%}
Risk Level: {signal.risk_assessment}"""

        if signal.supporting_strategies:
            body += f"\nSupporting: {', '.join(signal.supporting_strategies)}"

        return FormattedMessage(
            title=title,
            body=body,
            formatted_text=f"*{title}*\n```{body}```",
            priority=priority,
            metadata={
                'alert_type': 'signal',
                'symbol': signal.symbol,
                'strategy': signal.primary_strategy,
                'direction': signal.primary_direction,
                'confidence': signal.combined_confidence
            }
        )

    def _format_risk_alert(self, alert_type: str, data: Dict[str, Any], priority: AlertPriority) -> FormattedMessage:
        """Format risk management alert."""
        risk_emoji = {
            'portfolio_heat_exceeded': '🚨',
            'position_size_large': '⚠️',
            'correlation_high': '🔗',
            'drawdown_warning': '📉'
        }

        emoji = risk_emoji.get(alert_type, '⚠️')
        title = f"{emoji} Risk Alert: {alert_type.replace('_', ' ').title()}"

        body_parts = []
        for key, value in data.items():
            if isinstance(value, float):
                if 'percent' in key or 'ratio' in key:
                    body_parts.append(f"{key.replace('_', ' ').title()}: {value:.1%}")
                else:
                    body_parts.append(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                body_parts.append(f"{key.replace('_', ' ').title()}: {value}")

        body = '\n'.join(body_parts)

        return FormattedMessage(
            title=title,
            body=body,
            formatted_text=f"*{title}*\n```{body}```",
            priority=priority,
            metadata={
                'alert_type': 'risk',
                'risk_type': alert_type,
                'data': data
            }
        )

    def _queue_message(self, message_type: str, message: FormattedMessage, priority: AlertPriority):
        """Queue message for processing."""
        with self._lock:
            self.message_queue.put({
                'type': message_type,
                'message': message,
                'priority': priority,
                'timestamp': dt.datetime.now()
            })

    def _process_message_queue(self):
        """Process queued messages."""
        while True:
            try:
                # Get message from queue (blocking)
                item = self.message_queue.get(timeout=1)

                # Check rate limits
                if not self._check_rate_limits(item['priority']):
                    print(f"Rate limit exceeded, skipping message: {item['message'].title}")
                    continue

                # Send to all enabled channels
                self._send_to_channels(item['message'], item['priority'])

                # Mark task as done
                self.message_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing message queue: {e}")
                time.sleep(1)

    def _check_rate_limits(self, priority: AlertPriority) -> bool:
        """Check if message can be sent based on rate limits."""
        current_hour = dt.datetime.now().replace(minute=0, second=0, microsecond=0)

        # Critical messages always go through
        if priority == AlertPriority.CRITICAL:
            return True

        # Check hourly limits
        hour_key = current_hour.isoformat()
        if hour_key not in self.rate_limits:
            self.rate_limits[hour_key] = {'total': 0, 'by_priority': {}}

        hour_data = self.rate_limits[hour_key]

        # Check total limit
        max_per_hour = max(channel.rate_limit_per_hour for channel in self.channels.values() if channel.enabled)
        if hour_data['total'] >= max_per_hour:
            return False

        # Update counters
        hour_data['total'] += 1
        hour_data['by_priority'][priority.name] = hour_data['by_priority'].get(priority.name, 0) + 1

        # Clean up old hour data
        cutoff = current_hour - dt.timedelta(hours=24)
        old_keys = [k for k in self.rate_limits.keys() if dt.datetime.fromisoformat(k) < cutoff]
        for old_key in old_keys:
            del self.rate_limits[old_key]

        return True

    def _send_to_channels(self, message: FormattedMessage, priority: AlertPriority):
        """Send message to all appropriate channels."""
        for channel_name, config in self.channels.items():
            if not config.enabled:
                continue

            # Check priority filter
            if config.priority_filter and priority not in config.priority_filter:
                continue

            try:
                if config.channel == NotificationChannel.SLACK:
                    self._send_slack(message, config)
                elif config.channel == NotificationChannel.TELEGRAM:
                    self._send_telegram(message, config)

            except Exception as e:
                print(f"Error sending to {channel_name}: {e}")

    def _send_slack(self, message: FormattedMessage, config: NotificationConfig):
        """Send message to Slack."""
        if not config.endpoint:
            return

        payload = {
            "text": message.metadata.get('slack_format', message.formatted_text),
            "username": "Linda Trader",
            "icon_emoji": ":chart_with_upwards_trend:"
        }

        response = requests.post(config.endpoint, json=payload, timeout=10)
        response.raise_for_status()

    def _send_telegram(self, message: FormattedMessage, config: NotificationConfig):
        """Send message to Telegram."""
        if not config.endpoint or not config.chat_id:
            return

        payload = {
            "chat_id": config.chat_id,
            "text": message.metadata.get('telegram_format', message.formatted_text),
            "parse_mode": "HTML"
        }

        response = requests.post(config.endpoint, json=payload, timeout=10)
        response.raise_for_status()

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        current_hour = dt.datetime.now().replace(minute=0, second=0, microsecond=0)
        hour_key = current_hour.isoformat()

        hour_data = self.rate_limits.get(hour_key, {'total': 0, 'by_priority': {}})

        return {
            'channels_enabled': len([c for c in self.channels.values() if c.enabled]),
            'messages_this_hour': hour_data['total'],
            'queue_size': self.message_queue.qsize(),
            'by_priority': hour_data['by_priority'],
            'rate_limits': {name: config.rate_limit_per_hour for name, config in self.channels.items()}
        }

    def test_notifications(self):
        """Test all notification channels."""
        test_message = FormattedMessage(
            title="🧪 Test Notification",
            body="This is a test message from Linda Trader",
            formatted_text="*🧪 Test Notification*\n```This is a test message from Linda Trader```",
            priority=AlertPriority.LOW,
            metadata={'alert_type': 'test'}
        )

        self._send_to_channels(test_message, AlertPriority.LOW)
        print("Test notifications sent to all enabled channels")