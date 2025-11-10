"""Test suite for Position Sizing implementation."""
import pytest
import pandas as pd
import numpy as np

from src.risk.position_sizing import (
    PositionSizer, PositionSizeMethod, PositionSizeCalculation
)


class TestPositionSizer:
    """Test PositionSizer implementation."""

    def test_initialization(self):
        """Test position sizer initialization."""
        sizer = PositionSizer()

        assert sizer.base_risk_per_trade == 0.02
        assert sizer.max_portfolio_heat == 0.08
        assert len(sizer.current_positions) == 0

    def test_calculate_position_size_basic(self):
        """Test basic position size calculation."""
        sizer = PositionSizer()

        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=100000.0,
            confidence=1.0
        )

        assert isinstance(result, PositionSizeCalculation)
        assert result.symbol == 'TEST'
        assert result.shares > 0
        assert result.risk_percentage <= sizer.max_risk_per_trade
        assert result.position_size <= sizer.max_position_size

    def test_two_percent_rule(self):
        """Test Linda's 2% rule is enforced."""
        sizer = PositionSizer()
        account_value = 100000.0

        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=95.0,  # 5% risk per share
            account_value=account_value,
            confidence=1.0
        )

        # Risk should be approximately 2% of account
        expected_risk = account_value * 0.02
        assert abs(result.risk_amount - expected_risk) < expected_risk * 0.5

    def test_zero_position_invalid_risk(self):
        """Test zero position on invalid risk."""
        sizer = PositionSizer()

        # Stop loss above entry (invalid)
        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=105.0,  # Above entry!
            account_value=100000.0
        )

        assert result.shares == 0
        assert result.risk_amount == 0.0

    def test_confidence_adjustment(self):
        """Test position size adjustment based on confidence."""
        sizer = PositionSizer()
        account_value = 100000.0

        # High confidence
        high_conf = sizer.calculate_position_size(
            symbol='TEST1',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            confidence=1.0
        )

        # Low confidence
        low_conf = sizer.calculate_position_size(
            symbol='TEST2',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            confidence=0.5
        )

        # High confidence should have larger position
        assert high_conf.shares > low_conf.shares
        assert high_conf.risk_amount > low_conf.risk_amount

    def test_volatility_adjustment(self):
        """Test position size adjustment based on volatility."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Low volatility (larger position)
        low_vol = sizer.calculate_position_size(
            symbol='TEST1',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            volatility_adjustment=0.5  # Low volatility
        )

        # High volatility (smaller position)
        high_vol = sizer.calculate_position_size(
            symbol='TEST2',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            volatility_adjustment=2.0  # High volatility
        )

        # Low volatility should have larger position
        assert low_vol.shares > high_vol.shares

    def test_strategy_risk_factors(self):
        """Test strategy-specific risk factors."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Trend following (normal risk)
        trend = sizer.calculate_position_size(
            symbol='TEST1',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            strategy_name='holy_grail',
            confidence=1.0,
            volatility_adjustment=1.0
        )

        # Counter-trend (reduced risk)
        counter = sizer.calculate_position_size(
            symbol='TEST2',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            strategy_name='turtle_soup',
            confidence=1.0,
            volatility_adjustment=1.0
        )

        # Trend following should have larger position
        assert trend.shares > counter.shares

    def test_portfolio_heat_management(self):
        """Test portfolio heat limits."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Add existing positions to approach heat limit
        sizer.update_portfolio('POS1', 3000)  # 3% risk
        sizer.update_portfolio('POS2', 3000)  # 3% risk
        sizer.update_portfolio('POS3', 1500)  # 1.5% risk
        # Total: 7.5% (close to 8% limit)

        # Try to add another position
        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            confidence=1.0
        )

        # Position should be reduced due to high portfolio heat
        assert result.portfolio_heat_adjustment < 1.0

    def test_max_position_size_limit(self):
        """Test maximum position size limit."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Very tight stop (would create large position)
        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=99.5,  # Only 0.5% risk per share
            account_value=account_value,
            confidence=1.0
        )

        # Position size should be capped at max (5%)
        assert result.position_size <= sizer.max_position_size

    def test_min_position_size_filter(self):
        """Test minimum position size filter."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Very wide stop (would create tiny position)
        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=10.0,  # 90% risk per share!
            account_value=account_value,
            confidence=1.0
        )

        # Should return zero position (too small)
        assert result.shares == 0

    def test_correlation_adjustment(self):
        """Test position size adjustment for correlated positions."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Add existing position
        sizer.update_portfolio('AAPL', 2000)

        # Add correlations
        correlations = {
            ('TEST', 'AAPL'): 0.85  # High correlation
        }
        sizer.update_correlations(correlations)

        # Calculate position for correlated symbol
        result = sizer.calculate_position_size(
            symbol='TEST',
            entry_price=100.0,
            stop_loss=95.0,
            account_value=account_value,
            confidence=1.0
        )

        # Should have correlation adjustment
        assert result.correlation_adjustment < 1.0

    def test_portfolio_summary(self):
        """Test portfolio summary generation."""
        sizer = PositionSizer()

        sizer.update_portfolio('POS1', 2000)
        sizer.update_portfolio('POS2', 1500)
        sizer.update_portfolio('POS3', 1000)

        summary = sizer.get_portfolio_summary()

        assert summary['total_positions'] == 3
        assert summary['total_risk_amount'] == 4500
        assert 0 <= summary['portfolio_heat_ratio'] <= 1
        assert summary['remaining_heat'] > 0

    def test_validate_position_limits(self):
        """Test position limits validation."""
        sizer = PositionSizer()
        account_value = 100000.0

        # Valid position
        valid_calc = PositionSizeCalculation(
            symbol='TEST',
            position_size=0.03,  # 3%
            shares=300,
            dollar_amount=3000,
            risk_amount=150,
            risk_percentage=0.015,  # 1.5%
            method_used='fixed_risk',
            confidence_adjustment=1.0,
            volatility_adjustment=1.0,
            correlation_adjustment=1.0,
            portfolio_heat_adjustment=1.0,
            max_position_allowed=True
        )

        is_valid, violations = sizer.validate_position_limits(valid_calc, account_value)
        assert is_valid
        assert len(violations) == 0

    def test_kelly_criterion(self):
        """Test Kelly Criterion calculation."""
        sizer = PositionSizer()

        kelly_fraction = sizer.calculate_kelly_criterion(
            win_rate=0.55,
            avg_win=150,
            avg_loss=100
        )

        # Kelly should be positive for profitable system
        assert kelly_fraction > 0

        # Should be capped at 25% (quarter Kelly)
        assert kelly_fraction <= 0.25

    def test_optimal_f(self):
        """Test Optimal F calculation."""
        sizer = PositionSizer()

        # Sample trade results
        trade_results = [100, -50, 150, -75, 200, -100, 80, -60, 120, -40]

        optimal_f = sizer.calculate_optimal_f(trade_results)

        # Should return reasonable value
        assert 0 < optimal_f <= 0.20  # Capped at 20%

    def test_volatility_adjusted_size(self):
        """Test volatility-adjusted position sizing."""
        sizer = PositionSizer()

        base_size = 0.02

        # Low volatility = larger position
        low_vol_size = sizer.calculate_volatility_adjusted_size(
            base_size=base_size,
            current_volatility=0.15,
            average_volatility=0.20
        )

        # High volatility = smaller position
        high_vol_size = sizer.calculate_volatility_adjusted_size(
            base_size=base_size,
            current_volatility=0.30,
            average_volatility=0.20
        )

        assert low_vol_size > base_size
        assert high_vol_size < base_size

    def test_update_portfolio(self):
        """Test updating portfolio positions."""
        sizer = PositionSizer()

        # Add position
        sizer.update_portfolio('TEST1', 1000)
        assert 'TEST1' in sizer.current_positions
        assert sizer.current_positions['TEST1'] == 1000

        # Update position
        sizer.update_portfolio('TEST1', 1500)
        assert sizer.current_positions['TEST1'] == 1500

        # Remove position
        sizer.update_portfolio('TEST1', 0)
        assert 'TEST1' not in sizer.current_positions

    def test_load_correlations_from_calculator(self):
        """Test loading correlations from CorrelationAnalysis."""
        from src.risk.correlation import CorrelationAnalysis
        import datetime as dt

        sizer = PositionSizer()

        # Create mock correlation analysis
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.8, 0.3],
            'B': [0.8, 1.0, 0.4],
            'C': [0.3, 0.4, 1.0]
        }, index=['A', 'B', 'C'])

        analysis = CorrelationAnalysis(
            correlation_matrix=corr_matrix,
            high_correlations=[('A', 'B', 0.8)],
            clustered_symbols={'A': ['B'], 'B': ['A'], 'C': []},
            diversification_score=0.6,
            calculated_at=dt.datetime.now()
        )

        sizer.load_correlations_from_calculator(analysis)

        # Should have correlations loaded
        assert len(sizer.current_correlations) > 0
        assert ('A', 'B') in sizer.current_correlations or ('B', 'A') in sizer.current_correlations


def test_position_sizing_integration():
    """Integration test for position sizing workflow."""
    sizer = PositionSizer()
    account_value = 100000.0

    # Scenario: Building a 3-position portfolio
    positions = []

    # Position 1: High confidence, low volatility
    pos1 = sizer.calculate_position_size(
        symbol='TECH1',
        entry_price=150.0,
        stop_loss=145.0,
        account_value=account_value,
        strategy_name='holy_grail',
        confidence=0.9,
        volatility_adjustment=0.8
    )
    positions.append(pos1)
    sizer.update_portfolio('TECH1', pos1.risk_amount)

    # Position 2: Medium confidence, normal volatility
    pos2 = sizer.calculate_position_size(
        symbol='TECH2',
        entry_price=80.0,
        stop_loss=77.0,
        account_value=account_value,
        strategy_name='anti_swing',
        confidence=0.7,
        volatility_adjustment=1.0
    )
    positions.append(pos2)
    sizer.update_portfolio('TECH2', pos2.risk_amount)

    # Position 3: Lower confidence due to portfolio heat
    pos3 = sizer.calculate_position_size(
        symbol='TECH3',
        entry_price=120.0,
        stop_loss=115.0,
        account_value=account_value,
        strategy_name='volatility_breakout',
        confidence=0.8,
        volatility_adjustment=1.2
    )
    positions.append(pos3)

    # Validate portfolio
    summary = sizer.get_portfolio_summary()
    assert summary['total_positions'] == 2  # Only 2 added so far
    assert summary['total_risk_amount'] <= account_value * sizer.max_portfolio_heat

    # All positions should be valid
    for pos in positions:
        assert pos.shares > 0 or not pos.max_position_allowed
        assert pos.risk_percentage <= sizer.max_risk_per_trade
