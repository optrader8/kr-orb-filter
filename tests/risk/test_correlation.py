"""Test suite for Correlation calculation."""
import pytest
import pandas as pd
import numpy as np

from src.risk.correlation import (
    CorrelationCalculator, CorrelationAnalysis,
    convert_correlations_to_position_sizer_format
)


class TestCorrelationCalculator:
    """Test CorrelationCalculator implementation."""

    def test_initialization(self):
        """Test calculator initialization."""
        calc = CorrelationCalculator()
        assert calc.lookback_period == 60
        assert calc.min_data_points == 30

    def test_calculate_returns_correlation(self):
        """Test returns-based correlation calculation."""
        calc = CorrelationCalculator()

        # Create correlated price data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        base = np.cumsum(np.random.randn(100))

        data_dict = {
            'A': pd.DataFrame({'close': 100 + base + np.random.randn(100) * 0.5}, index=dates),
            'B': pd.DataFrame({'close': 50 + base * 0.8 + np.random.randn(100) * 0.5}, index=dates),
            'C': pd.DataFrame({'close': 200 + np.random.randn(100) * 2}, index=dates)  # Uncorrelated
        }

        corr_matrix = calc.calculate_returns_correlation(data_dict)

        assert not corr_matrix.empty
        assert list(corr_matrix.columns) == ['A', 'B', 'C']
        assert corr_matrix.loc['A', 'A'] == pytest.approx(1.0, abs=0.01)

    def test_get_high_correlations(self):
        """Test extracting high correlation pairs."""
        calc = CorrelationCalculator()

        # Create correlation matrix
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.85, 0.3],
            'B': [0.85, 1.0, 0.4],
            'C': [0.3, 0.4, 1.0]
        }, index=['A', 'B', 'C'])

        high_corrs = calc.get_high_correlations(corr_matrix, threshold=0.7)

        assert len(high_corrs) > 0
        assert ('A', 'B', 0.85) in high_corrs

    def test_diversification_score(self):
        """Test diversification score calculation."""
        calc = CorrelationCalculator()

        # Highly correlated portfolio
        high_corr_matrix = pd.DataFrame({
            'A': [1.0, 0.9, 0.85],
            'B': [0.9, 1.0, 0.88],
            'C': [0.85, 0.88, 1.0]
        }, index=['A', 'B', 'C'])

        low_div = calc.calculate_diversification_score(high_corr_matrix)
        assert 0 <= low_div <= 1
        assert low_div < 0.3  # Low diversification

        # Uncorrelated portfolio
        low_corr_matrix = pd.DataFrame({
            'A': [1.0, 0.1, 0.05],
            'B': [0.1, 1.0, 0.08],
            'C': [0.05, 0.08, 1.0]
        }, index=['A', 'B', 'C'])

        high_div = calc.calculate_diversification_score(low_corr_matrix)
        assert high_div > 0.8  # High diversification

    def test_cluster_correlated_symbols(self):
        """Test symbol clustering by correlation."""
        calc = CorrelationCalculator()

        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.85, 0.3],
            'B': [0.85, 1.0, 0.4],
            'C': [0.3, 0.4, 1.0]
        }, index=['A', 'B', 'C'])

        clusters = calc.cluster_correlated_symbols(corr_matrix, threshold=0.7)

        assert 'A' in clusters
        assert 'B' in clusters['A']  # A and B are correlated
        assert 'A' in clusters['B']


def test_convert_correlations_to_position_sizer_format():
    """Test conversion to PositionSizer format."""
    import datetime as dt

    corr_matrix = pd.DataFrame({
        'A': [1.0, 0.8],
        'B': [0.8, 1.0]
    }, index=['A', 'B'])

    analysis = CorrelationAnalysis(
        correlation_matrix=corr_matrix,
        high_correlations=[('A', 'B', 0.8)],
        clustered_symbols={'A': ['B'], 'B': ['A']},
        diversification_score=0.6,
        calculated_at=dt.datetime.now()
    )

    result = convert_correlations_to_position_sizer_format(analysis)

    assert isinstance(result, dict)
    assert ('A', 'B') in result or ('B', 'A') in result
