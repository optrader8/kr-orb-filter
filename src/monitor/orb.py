"""Intraday ORB monitoring with CSV replay support."""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, List, Optional


@dataclass
class ORBSettings:
    window_start: dt.time = dt.time(hour=9, minute=0)
    window_end: dt.time = dt.time(hour=9, minute=15)
    cooldown_seconds: int = 300


@dataclass
class ORBEvent:
    symbol: str
    direction: str
    breakout_time: dt.datetime
    orb_high: float
    orb_low: float
    price: float


class AlertThrottler:
    def __init__(self, cooldown: int) -> None:
        self.cooldown = dt.timedelta(seconds=cooldown)
        self._last_sent: dict[str, dt.datetime] = {}

    def allow(self, key: str, now: dt.datetime) -> bool:
        last = self._last_sent.get(key)
        if last is None or now - last >= self.cooldown:
            self._last_sent[key] = now
            return True
        return False


class ORBMonitor:
    def __init__(self, settings: ORBSettings, dispatch: Callable[[ORBEvent], None]) -> None:
        self.settings = settings
        self.dispatch = dispatch
        self._throttler = AlertThrottler(settings.cooldown_seconds)

    def run_csv(self, path: Path, symbol: str) -> List[ORBEvent]:
        events: List[ORBEvent] = []
        prices = list(self._iter_rows(path))
        orb_high, orb_low = self._compute_orb(prices)
        for timestamp, price in prices:
            if timestamp.time() <= self.settings.window_end:
                continue
            if price > orb_high:
                event = ORBEvent(symbol, "long", timestamp, orb_high, orb_low, price)
                if self._should_emit(event):
                    events.append(event)
            if price < orb_low:
                event = ORBEvent(symbol, "short", timestamp, orb_high, orb_low, price)
                if self._should_emit(event):
                    events.append(event)
        return events

    def _iter_rows(self, path: Path) -> Iterator[tuple[dt.datetime, float]]:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                timestamp = dt.datetime.fromisoformat(row["timestamp"])
                price = float(row["price"])
                yield timestamp, price

    def _compute_orb(self, prices: Iterable[tuple[dt.datetime, float]]) -> tuple[float, float]:
        highs: List[float] = []
        lows: List[float] = []
        for timestamp, price in prices:
            if self.settings.window_start <= timestamp.time() <= self.settings.window_end:
                highs.append(price)
                lows.append(price)
        if not highs or not lows:
            raise ValueError("ORB window contains no data")
        return max(highs), min(lows)

    def _should_emit(self, event: ORBEvent) -> bool:
        key = f"{event.symbol}:{event.direction}"
        if self._throttler.allow(key, event.breakout_time):
            self.dispatch(event)
            return True
        return False