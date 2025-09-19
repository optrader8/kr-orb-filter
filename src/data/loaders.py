"""Data ingestion utilities for KR-ORB-Filter."""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataLoaderError(RuntimeError):
    """Raised when a data loader fails to produce a dataframe."""


@dataclass
class DailyDataRequest:
    start: dt.date
    end: dt.date
    symbol: str


class DailyDataLoader:
    """Fetch daily OHLCV data via pykrx if available, otherwise CSV fallback."""

    def __init__(self, cache_dir: Optional[Path] = None, csv_fallback: Optional[Path] = None) -> None:
        self.cache_dir = cache_dir
        self.csv_fallback = csv_fallback
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, request: DailyDataRequest) -> pd.DataFrame:
        """Fetch OHLCV data with retry semantics and checksum logging."""
        attempts = 3
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                frame = self._fetch_via_pykrx(request)
                if frame is None and self.csv_fallback:
                    frame = self._fetch_via_csv(request)
                if frame is None:
                    raise DataLoaderError("No data provider succeeded")
                if frame.empty:
                    raise DataLoaderError("Received empty dataframe")
                return self._decorate(frame, request)
            except Exception as error:  # pylint: disable=broad-except
                last_error = error
                logger.warning("DailyDataLoader attempt %s failed: %s", attempt, error)
        raise DataLoaderError(f"Failed to load data after {attempts} attempts: {last_error}")

    def _fetch_via_pykrx(self, request: DailyDataRequest) -> Optional[pd.DataFrame]:
        try:
            from pykrx import stock  # type: ignore
        except ImportError:
            logger.debug("pykrx not installed; skipping API call")
            return None

        start_str = request.start.strftime("%Y%m%d")
        end_str = request.end.strftime("%Y%m%d")
        logger.info("Fetching pykrx OHLCV for %s from %s to %s", request.symbol, start_str, end_str)
        frame = stock.get_market_ohlcv_by_date(start_str, end_str, request.symbol)
        frame = frame.rename(
            columns={
                "시가": "open",
                "고가": "high",
                "저가": "low",
                "종가": "close",
                "거래량": "volume",
            }
        )
        frame.index = pd.to_datetime(frame.index)
        return frame

    def _fetch_via_csv(self, request: DailyDataRequest) -> Optional[pd.DataFrame]:
        csv_path = self.csv_fallback / f"{request.symbol}.csv" if self.csv_fallback else None
        if not csv_path or not csv_path.exists():
            logger.debug("CSV fallback missing for %s", request.symbol)
            return None
        logger.info("Loading OHLCV from CSV fallback: %s", csv_path)
        frame = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
        mask = (frame.index.date >= request.start) & (frame.index.date <= request.end)
        return frame.loc[mask]

    def _decorate(self, frame: pd.DataFrame, request: DailyDataRequest) -> pd.DataFrame:
        checksum = hashlib.sha256(frame.to_csv().encode("utf-8")).hexdigest()
        logger.info(
            "Loaded %s rows for %s (%s-%s) checksum=%s",
            len(frame),
            request.symbol,
            request.start,
            request.end,
            checksum,
        )
        if self.cache_dir:
            cache_file = self.cache_dir / f"{request.symbol}_{request.start}_{request.end}.parquet"
            frame.to_parquet(cache_file)
            logger.debug("Cached OHLCV to %s", cache_file)
        frame.attrs["checksum"] = checksum
        frame.attrs["requested_at"] = dt.datetime.utcnow()
        return frame