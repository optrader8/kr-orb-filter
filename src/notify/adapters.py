"""Notification adapters for Slack and Telegram."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class NotificationError(RuntimeError):
    """Raised when a notifier cannot deliver a message."""


@dataclass
class SlackNotifier:
    webhook_url: str
    timeout: int = 5

    def send(self, message: str, extra: Optional[Dict[str, str]] = None) -> bool:
        payload = {"text": message}
        if extra:
            payload.update(extra)
        logger.info("Sending Slack alert")
        response = requests.post(self.webhook_url, json=payload, timeout=self.timeout)
        if response.status_code // 100 != 2:
            logger.error("Slack send failed: %s %s", response.status_code, response.text)
            raise NotificationError(response.text)
        return True


@dataclass
class TelegramNotifier:
    bot_token: str
    chat_id: str
    timeout: int = 5

    def send(self, message: str) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        logger.info("Sending Telegram alert")
        response = requests.post(url, json=payload, timeout=self.timeout)
        if response.status_code // 100 != 2:
            logger.error("Telegram send failed: %s %s", response.status_code, response.text)
            raise NotificationError(response.text)
        return True