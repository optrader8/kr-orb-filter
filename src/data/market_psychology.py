"""Market psychology data ingestion for sentiment analysis."""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class MarketPsychologyError(RuntimeError):
    """Raised when market psychology data loading fails."""


@dataclass
class PsychologyDataRequest:
    start: dt.date
    end: dt.date
    indicator: str  # 'vix', 'put_call_ratio', 'fii_flows'


class MarketPsychologyLoader:
    """Load market psychology indicators for sentiment analysis."""

    def __init__(self, cache_dir: Optional[Path] = None, data_dir: Optional[Path] = None) -> None:
        self.cache_dir = cache_dir
        self.data_dir = data_dir or Path("data/psychology")
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_vix_equivalent(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Fetch Korean market volatility index (KOSPI200 volatility)."""
        try:
            # Try to fetch KOSPI200 volatility index
            # For now, use a placeholder implementation
            # In production, this would connect to Korean data providers
            return self._fetch_placeholder_vix(request)
        except Exception as error:
            logger.warning("Failed to fetch VIX equivalent: %s", error)
            return self._generate_fallback_vix(request)

    def fetch_put_call_ratio(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Fetch put/call ratio for KOSPI options."""
        csv_path = self.data_dir / "put_call_ratio.csv"
        if csv_path.exists():
            return self._load_from_csv(csv_path, request)

        logger.warning("Put/call ratio data not available, using synthetic data")
        return self._generate_fallback_put_call(request)

    def fetch_fii_flows(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Fetch Foreign Institutional Investor flow data."""
        try:
            # This would typically connect to Korean financial data providers
            # For now, use CSV fallback
            csv_path = self.data_dir / "fii_flows.csv"
            if csv_path.exists():
                return self._load_from_csv(csv_path, request)

            logger.warning("FII flows data not available, using synthetic data")
            return self._generate_fallback_fii(request)
        except Exception as error:
            logger.error("Failed to fetch FII flows: %s", error)
            raise MarketPsychologyError(f"FII flows loading failed: {error}")

    def _fetch_placeholder_vix(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Placeholder VIX implementation - replace with real data source."""
        # In production, this would connect to:
        # - KRX KOSPI200 volatility index
        # - Alternative volatility measures
        logger.info("Using placeholder VIX data for %s to %s", request.start, request.end)

        date_range = pd.date_range(start=request.start, end=request.end, freq='D')
        # Generate realistic VIX-like data (10-40 range, mean around 20)
        import numpy as np
        np.random.seed(42)  # For reproducible testing
        vix_values = 20 + 10 * np.random.randn(len(date_range)) + 5 * np.sin(np.arange(len(date_range)) * 0.1)
        vix_values = np.clip(vix_values, 10, 40)

        return pd.DataFrame({
            'vix': vix_values,
            'date': date_range
        }).set_index('date')

    def _generate_fallback_vix(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Generate fallback VIX data when real data unavailable."""
        return self._fetch_placeholder_vix(request)

    def _generate_fallback_put_call(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Generate fallback put/call ratio data."""
        date_range = pd.date_range(start=request.start, end=request.end, freq='D')
        import numpy as np
        np.random.seed(123)
        # Normal put/call ratio around 0.8-1.2
        ratios = 1.0 + 0.3 * np.random.randn(len(date_range))
        ratios = np.clip(ratios, 0.5, 2.0)

        return pd.DataFrame({
            'put_call_ratio': ratios,
            'date': date_range
        }).set_index('date')

    def _generate_fallback_fii(self, request: PsychologyDataRequest) -> pd.DataFrame:
        """Generate fallback FII flows data."""
        date_range = pd.date_range(start=request.start, end=request.end, freq='D')
        import numpy as np
        np.random.seed(456)
        # FII flows in billions KRW
        flows = np.random.randn(len(date_range)) * 100  # +/- 100B KRW

        return pd.DataFrame({
            'fii_net_flows': flows,
            'fii_cumulative': flows.cumsum(),
            'date': date_range
        }).set_index('date')

    def _load_from_csv(self, csv_path: Path, request: PsychologyDataRequest) -> pd.DataFrame:
        """Load psychology data from CSV file."""
        logger.info("Loading psychology data from %s", csv_path)
        try:
            frame = pd.read_csv(csv_path, parse_dates=['date'], index_col='date')
            mask = (frame.index.date >= request.start) & (frame.index.date <= request.end)
            return frame.loc[mask]
        except Exception as error:
            logger.error("Failed to load CSV %s: %s", csv_path, error)
            raise MarketPsychologyError(f"CSV loading failed: {error}")

    def get_sentiment_indicators(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        """Get all sentiment indicators for the given period."""
        indicators = {}

        try:
            vix_req = PsychologyDataRequest(start, end, 'vix')
            vix_data = self.fetch_vix_equivalent(vix_req)
            indicators['vix'] = vix_data['vix']
        except Exception as error:
            logger.warning("Failed to load VIX data: %s", error)

        try:
            pc_req = PsychologyDataRequest(start, end, 'put_call_ratio')
            pc_data = self.fetch_put_call_ratio(pc_req)
            indicators['put_call_ratio'] = pc_data['put_call_ratio']
        except Exception as error:
            logger.warning("Failed to load put/call ratio: %s", error)

        try:
            fii_req = PsychologyDataRequest(start, end, 'fii_flows')
            fii_data = self.fetch_fii_flows(fii_req)
            indicators['fii_net_flows'] = fii_data['fii_net_flows']
            indicators['fii_cumulative'] = fii_data['fii_cumulative']
        except Exception as error:
            logger.warning("Failed to load FII flows: %s", error)

        if not indicators:
            raise MarketPsychologyError("No sentiment indicators could be loaded")

        # Combine all indicators into single DataFrame
        result = pd.DataFrame(indicators)
        result.index.name = 'date'

        logger.info("Loaded %d sentiment indicators for %d days", len(result.columns), len(result))
        return result


def analyze_sentiment_extremes(sentiment_data: pd.DataFrame,
                             vix_high_threshold: float = 30.0,
                             vix_low_threshold: float = 15.0,
                             pc_high_threshold: float = 1.3,
                             pc_low_threshold: float = 0.7) -> pd.DataFrame:
    """Analyze sentiment data for extreme readings that may signal reversals."""
    extremes = pd.DataFrame(index=sentiment_data.index)

    if 'vix' in sentiment_data.columns:
        extremes['vix_extreme_high'] = sentiment_data['vix'] > vix_high_threshold
        extremes['vix_extreme_low'] = sentiment_data['vix'] < vix_low_threshold

    if 'put_call_ratio' in sentiment_data.columns:
        extremes['pc_extreme_high'] = sentiment_data['put_call_ratio'] > pc_high_threshold
        extremes['pc_extreme_low'] = sentiment_data['put_call_ratio'] < pc_low_threshold

    if 'fii_cumulative' in sentiment_data.columns:
        # Use rolling z-score for FII flow extremes
        fii_zscore = (sentiment_data['fii_cumulative'] - sentiment_data['fii_cumulative'].rolling(20).mean()) / sentiment_data['fii_cumulative'].rolling(20).std()
        extremes['fii_extreme_positive'] = fii_zscore > 2.0
        extremes['fii_extreme_negative'] = fii_zscore < -2.0

    # Overall sentiment extreme (any extreme reading)
    extreme_cols = [col for col in extremes.columns if 'extreme' in col]
    extremes['any_extreme'] = extremes[extreme_cols].any(axis=1)

    return extremes