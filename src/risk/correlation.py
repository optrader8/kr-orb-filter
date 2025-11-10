"""Correlation matrix calculation and portfolio risk management.

This module provides correlation analysis for position sizing and portfolio heat management,
implementing Linda Raschke's principle of reducing position sizes for highly correlated instruments.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import datetime as dt


@dataclass
class CorrelationAnalysis:
    """Result of correlation analysis for a group of symbols."""
    correlation_matrix: pd.DataFrame
    high_correlations: List[Tuple[str, str, float]]  # (symbol1, symbol2, correlation)
    clustered_symbols: Dict[str, List[str]]  # symbol -> list of correlated symbols
    diversification_score: float  # 0-1, higher is more diversified
    calculated_at: dt.datetime


class CorrelationCalculator:
    """
    Calculate and manage correlation matrices for portfolio risk management.

    Usage:
        calculator = CorrelationCalculator()

        # Calculate correlations from price data
        correlation_matrix = calculator.calculate_returns_correlation(data_dict, lookback=60)

        # Get high correlations for risk management
        high_corr = calculator.get_high_correlations(correlation_matrix, threshold=0.7)

        # Use in position sizing
        position_sizer.update_correlations(high_corr)
    """

    def __init__(self, lookback_period: int = 60, min_data_points: int = 30):
        """
        Initialize correlation calculator.

        Args:
            lookback_period: Number of days to use for correlation calculation
            min_data_points: Minimum data points required for reliable correlation
        """
        self.lookback_period = lookback_period
        self.min_data_points = min_data_points
        self._cache: Optional[CorrelationAnalysis] = None

    def calculate_returns_correlation(
        self,
        data_dict: Dict[str, pd.DataFrame],
        lookback: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix based on daily returns.

        Args:
            data_dict: Dictionary of symbol -> OHLCV DataFrame
            lookback: Lookback period in days (None = use self.lookback_period)

        Returns:
            Correlation matrix as DataFrame
        """
        lookback = lookback or self.lookback_period

        # Extract close prices for all symbols
        returns_dict = {}

        for symbol, data in data_dict.items():
            if 'close' not in data.columns or len(data) < self.min_data_points:
                continue

            # Calculate returns
            returns = data['close'].pct_change()

            # Use only recent lookback period
            returns_dict[symbol] = returns.iloc[-lookback:]

        if len(returns_dict) < 2:
            # Need at least 2 symbols for correlation
            return pd.DataFrame()

        # Combine all returns into DataFrame
        returns_df = pd.DataFrame(returns_dict)

        # Drop rows with any NaN values
        returns_df = returns_df.dropna()

        if len(returns_df) < self.min_data_points:
            return pd.DataFrame()

        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()

        return correlation_matrix

    def calculate_price_correlation(
        self,
        data_dict: Dict[str, pd.DataFrame],
        lookback: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix based on normalized prices.

        Useful when you want to capture long-term co-movement patterns.

        Args:
            data_dict: Dictionary of symbol -> OHLCV DataFrame
            lookback: Lookback period in days (None = use self.lookback_period)

        Returns:
            Correlation matrix as DataFrame
        """
        lookback = lookback or self.lookback_period

        # Extract and normalize close prices
        normalized_prices = {}

        for symbol, data in data_dict.items():
            if 'close' not in data.columns or len(data) < self.min_data_points:
                continue

            # Get recent prices
            prices = data['close'].iloc[-lookback:]

            # Normalize to start at 100
            normalized = (prices / prices.iloc[0]) * 100
            normalized_prices[symbol] = normalized

        if len(normalized_prices) < 2:
            return pd.DataFrame()

        # Combine into DataFrame
        prices_df = pd.DataFrame(normalized_prices)
        prices_df = prices_df.dropna()

        if len(prices_df) < self.min_data_points:
            return pd.DataFrame()

        # Calculate correlation
        correlation_matrix = prices_df.corr()

        return correlation_matrix

    def get_high_correlations(
        self,
        correlation_matrix: pd.DataFrame,
        threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        """
        Extract pairs with correlation above threshold.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            threshold: Correlation threshold (0-1)

        Returns:
            List of (symbol1, symbol2, correlation) tuples
        """
        if correlation_matrix.empty:
            return []

        high_correlations = []
        symbols = correlation_matrix.columns.tolist()

        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i >= j:  # Skip diagonal and duplicates
                    continue

                corr = correlation_matrix.loc[sym1, sym2]

                if abs(corr) >= threshold:
                    high_correlations.append((sym1, sym2, corr))

        # Sort by absolute correlation (descending)
        high_correlations.sort(key=lambda x: abs(x[2]), reverse=True)

        return high_correlations

    def get_correlations_for_symbol(
        self,
        symbol: str,
        correlation_matrix: pd.DataFrame,
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        Get all symbols correlated with given symbol above threshold.

        Args:
            symbol: Target symbol
            correlation_matrix: Correlation matrix DataFrame
            threshold: Correlation threshold

        Returns:
            List of (correlated_symbol, correlation) tuples
        """
        if correlation_matrix.empty or symbol not in correlation_matrix.columns:
            return []

        correlations = correlation_matrix[symbol]
        high_corr = correlations[abs(correlations) >= threshold]

        # Remove self-correlation
        high_corr = high_corr[high_corr.index != symbol]

        # Convert to list of tuples
        result = [(sym, corr) for sym, corr in high_corr.items()]

        # Sort by absolute correlation
        result.sort(key=lambda x: abs(x[1]), reverse=True)

        return result

    def cluster_correlated_symbols(
        self,
        correlation_matrix: pd.DataFrame,
        threshold: float = 0.7
    ) -> Dict[str, List[str]]:
        """
        Group symbols into correlation clusters.

        Each symbol is mapped to its list of highly correlated symbols.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            threshold: Correlation threshold

        Returns:
            Dictionary mapping symbol -> list of correlated symbols
        """
        if correlation_matrix.empty:
            return {}

        clusters = {}

        for symbol in correlation_matrix.columns:
            correlated = self.get_correlations_for_symbol(symbol, correlation_matrix, threshold)
            clusters[symbol] = [sym for sym, _ in correlated]

        return clusters

    def calculate_diversification_score(self, correlation_matrix: pd.DataFrame) -> float:
        """
        Calculate portfolio diversification score (0-1).

        Lower average correlation = higher diversification score.

        Args:
            correlation_matrix: Correlation matrix DataFrame

        Returns:
            Diversification score (0 = fully correlated, 1 = no correlation)
        """
        if correlation_matrix.empty or len(correlation_matrix) < 2:
            return 1.0  # Single asset is perfectly "diversified"

        # Get upper triangle of correlation matrix (excluding diagonal)
        upper_triangle = np.triu(correlation_matrix.values, k=1)

        # Count non-zero elements (number of pairs)
        n = len(correlation_matrix)
        num_pairs = n * (n - 1) // 2

        if num_pairs == 0:
            return 1.0

        # Calculate average absolute correlation
        total_corr = np.sum(np.abs(upper_triangle))
        avg_corr = total_corr / num_pairs

        # Convert to diversification score (1 - avg_corr)
        diversification = 1.0 - avg_corr

        return max(0.0, min(1.0, diversification))

    def analyze_correlations(
        self,
        data_dict: Dict[str, pd.DataFrame],
        lookback: Optional[int] = None,
        threshold: float = 0.7
    ) -> CorrelationAnalysis:
        """
        Perform complete correlation analysis.

        Args:
            data_dict: Dictionary of symbol -> OHLCV DataFrame
            lookback: Lookback period in days
            threshold: Correlation threshold for clustering

        Returns:
            CorrelationAnalysis object with all results
        """
        # Calculate correlation matrix
        correlation_matrix = self.calculate_returns_correlation(data_dict, lookback)

        if correlation_matrix.empty:
            return CorrelationAnalysis(
                correlation_matrix=correlation_matrix,
                high_correlations=[],
                clustered_symbols={},
                diversification_score=1.0,
                calculated_at=dt.datetime.now()
            )

        # Get high correlations
        high_corrs = self.get_high_correlations(correlation_matrix, threshold)

        # Cluster symbols
        clusters = self.cluster_correlated_symbols(correlation_matrix, threshold)

        # Calculate diversification score
        div_score = self.calculate_diversification_score(correlation_matrix)

        analysis = CorrelationAnalysis(
            correlation_matrix=correlation_matrix,
            high_correlations=high_corrs,
            clustered_symbols=clusters,
            diversification_score=div_score,
            calculated_at=dt.datetime.now()
        )

        # Cache for later use
        self._cache = analysis

        return analysis

    def get_correlation_adjustment_factors(
        self,
        analysis: CorrelationAnalysis,
        symbols: List[str],
        existing_positions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate position size adjustment factors based on correlations.

        For each symbol, reduce position size if correlated with existing positions.

        Args:
            analysis: CorrelationAnalysis object
            symbols: List of symbols to calculate adjustments for
            existing_positions: Dict of symbol -> risk amount for existing positions

        Returns:
            Dict of symbol -> adjustment factor (0-1)
        """
        adjustments = {}

        for symbol in symbols:
            # Start with no adjustment
            adjustment = 1.0

            # Check correlations with existing positions
            total_correlated_risk = 0.0

            for existing_symbol, existing_risk in existing_positions.items():
                if existing_symbol == symbol:
                    continue

                # Get correlation
                if symbol in analysis.correlation_matrix.columns and \
                   existing_symbol in analysis.correlation_matrix.columns:
                    corr = abs(analysis.correlation_matrix.loc[symbol, existing_symbol])

                    if corr > 0.7:  # High correlation
                        total_correlated_risk += existing_risk * corr

            # Calculate adjustment factor
            # Higher correlated risk = lower adjustment = smaller position
            if total_correlated_risk > 0:
                # Scale down by correlation factor (max 70% reduction)
                max_reduction = 0.7
                reduction = min(max_reduction, total_correlated_risk / 0.1)  # Normalize
                adjustment = 1.0 - reduction

            adjustments[symbol] = max(0.3, adjustment)  # Min 30% of normal size

        return adjustments

    def format_correlation_matrix(self, correlation_matrix: pd.DataFrame, decimals: int = 2) -> str:
        """Format correlation matrix for display."""
        if correlation_matrix.empty:
            return "No correlation data available"

        return correlation_matrix.round(decimals).to_string()

    def export_to_dict(self, analysis: CorrelationAnalysis) -> Dict:
        """Export correlation analysis to dictionary for serialization."""
        return {
            'correlation_matrix': analysis.correlation_matrix.to_dict(),
            'high_correlations': [
                {'symbol1': s1, 'symbol2': s2, 'correlation': round(c, 3)}
                for s1, s2, c in analysis.high_correlations
            ],
            'clustered_symbols': analysis.clustered_symbols,
            'diversification_score': round(analysis.diversification_score, 3),
            'calculated_at': analysis.calculated_at.isoformat()
        }


def convert_correlations_to_position_sizer_format(
    analysis: CorrelationAnalysis
) -> Dict[Tuple[str, str], float]:
    """
    Convert CorrelationAnalysis to format expected by PositionSizer.

    PositionSizer expects: Dict[Tuple[str, str], float]

    Args:
        analysis: CorrelationAnalysis object

    Returns:
        Dictionary with (symbol1, symbol2) tuples as keys and correlation as values
    """
    result = {}

    if analysis.correlation_matrix.empty:
        return result

    symbols = analysis.correlation_matrix.columns.tolist()

    for i, sym1 in enumerate(symbols):
        for j, sym2 in enumerate(symbols):
            if i == j:
                continue  # Skip self-correlation

            corr = analysis.correlation_matrix.loc[sym1, sym2]
            result[(sym1, sym2)] = corr

    return result
