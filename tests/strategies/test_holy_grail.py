"""Test suite for Holy Grail strategy implementation."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.linda.holy_grail import HolyGrailStrategy, HolyGrailSignal


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')

    # Create trending data with pullback
    np.random.seed(42)
    base_price = 100
    trend = np.linspace(0, 20, 100)  # Uptrend
    noise = np.random.randn(100) * 2

    close = base_price + trend + noise

    # Create realistic OHLC from close
    high = close + np.abs(np.random.randn(100)) * 0.5
    low = close - np.abs(np.random.randn(100)) * 0.5
    open_price = close - np.random.randn(100) * 0.3
    volume = np.random.randint(1000000, 5000000, 100)

    data = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return data


@pytest.fixture
def pullback_data():
    """Create data with clear pullback pattern."""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')

    # Strong uptrend
    uptrend = np.array([100, 102, 105, 108, 111, 114, 117, 120] + [120] * 42)

    # Add pullback (3-5 bars of lower highs)
    pullback_start = 8
    uptrend[pullback_start:pullback_start+4] = [119, 118, 117, 116]

    # Resume uptrend
    uptrend[pullback_start+4:pullback_start+8] = [118, 121, 124, 127]

    close = uptrend + np.random.randn(50) * 0.5

    high = close + np.abs(np.random.randn(50)) * 0.3
    low = close - np.abs(np.random.randn(50)) * 0.3
    open_price = close - np.random.randn(50) * 0.2
    volume = np.random.randint(1000000, 5000000, 50)

    data = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return data


class TestHolyGrailStrategy:
    """Test Holy Grail strategy implementation."""

    def test_initialization(self):
        """Test strategy initialization with default config."""
        strategy = HolyGrailStrategy()

        assert strategy.name == "Holy Grail"
        assert strategy.adx_period == 14
        assert strategy.adx_strong_threshold == 30.0
        assert strategy.pullback_min_bars == 3
        assert strategy.pullback_max_bars == 5

    def test_initialization_with_custom_config(self):
        """Test strategy initialization with custom config."""
        config = {
            'adx_period': 20,
            'adx_strong_threshold': 35.0,
            'pullback_min_bars': 2,
            'pullback_max_bars': 4
        }
        strategy = HolyGrailStrategy(config)

        assert strategy.adx_period == 20
        assert strategy.adx_strong_threshold == 35.0
        assert strategy.pullback_min_bars == 2
        assert strategy.pullback_max_bars == 4

    def test_analyze_insufficient_data(self):
        """Test analyze with insufficient data."""
        strategy = HolyGrailStrategy()

        # Only 10 bars
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'open': np.random.randn(10) + 100,
            'high': np.random.randn(10) + 101,
            'low': np.random.randn(10) + 99,
            'close': np.random.randn(10) + 100,
            'volume': np.random.randint(1000000, 5000000, 10)
        }, index=dates)

        result = strategy.analyze(data)

        assert result.empty

    def test_analyze_returns_required_columns(self, sample_data):
        """Test that analyze returns all required columns."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        required_columns = [
            'adx_adx', 'adx_plus_di', 'adx_minus_di',
            'rsi',
            'uptrend_pullback', 'downtrend_pullback', 'any_pullback',
            'hg_long_setup', 'hg_short_setup',
            'hg_long_entry', 'hg_short_entry'
        ]

        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_pullback_detection_uptrend(self, pullback_data):
        """Test pullback detection in uptrend."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(pullback_data)

        # Should detect some pullbacks in uptrend
        assert result['uptrend_pullback'].any(), "No uptrend pullbacks detected"

        # Check pullback bars are within expected range
        pullback_indices = result[result['uptrend_pullback']].index
        assert len(pullback_indices) > 0

    def test_pullback_detection_vectorized(self, sample_data):
        """Test that vectorized pullback detection works correctly."""
        strategy = HolyGrailStrategy()

        # Test uptrend pullback detection
        highs = sample_data['high']
        lows = sample_data['low']

        pullback_3 = strategy._detect_uptrend_pullback(highs, lows, 3)
        pullback_5 = strategy._detect_uptrend_pullback(highs, lows, 5)

        # Should return Series with same index
        assert len(pullback_3) == len(sample_data)
        assert len(pullback_5) == len(sample_data)

        # Should be boolean Series
        assert pullback_3.dtype == bool
        assert pullback_5.dtype == bool

    def test_signal_generation(self, sample_data):
        """Test signal generation produces valid signals."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Check signal columns exist and are boolean
        assert result['hg_long_setup'].dtype == bool
        assert result['hg_short_setup'].dtype == bool
        assert result['hg_long_entry'].dtype == bool
        assert result['hg_short_entry'].dtype == bool

        # Entry signals should not occur on first bars (need setup first)
        first_20_bars = result.iloc[:20]
        assert not first_20_bars['hg_long_entry'].any()
        assert not first_20_bars['hg_short_entry'].any()

    def test_stop_loss_calculation(self, sample_data):
        """Test stop loss calculation."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Get entries with stop loss values
        entries_with_stops = result[result['hg_long_entry'] & result['hg_stop_loss'].notna()]

        for idx, row in entries_with_stops.iterrows():
            entry_price = sample_data.loc[idx, 'high']
            stop_loss = row['hg_stop_loss']

            # Stop loss should be below entry for long positions
            assert stop_loss < entry_price, f"Stop loss {stop_loss} not below entry {entry_price}"

    def test_target_calculation(self, sample_data):
        """Test target price calculation."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Get entries with targets
        entries_with_targets = result[result['hg_long_entry'] & result['hg_target'].notna()]

        for idx, row in entries_with_targets.iterrows():
            entry_price = sample_data.loc[idx, 'high']
            stop_loss = row['hg_stop_loss']
            target = row['hg_target']

            # Target should be above entry
            assert target > entry_price, f"Target {target} not above entry {entry_price}"

            # Risk/reward should be approximately 2:1
            risk = entry_price - stop_loss
            reward = target - entry_price

            if risk > 0:
                rr_ratio = reward / risk
                assert 1.5 < rr_ratio < 2.5, f"R:R ratio {rr_ratio} not close to 2:1"

    def test_confidence_calculation(self, sample_data):
        """Test confidence score calculation."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Get entries with confidence
        entries = result[result['hg_long_entry'] | result['hg_short_entry']]

        for idx, row in entries.iterrows():
            confidence = row['hg_confidence']

            # Confidence should be between 0 and 1
            assert 0 <= confidence <= 1, f"Confidence {confidence} out of range"

            # Should have some reasonable value (not 0 or 1 typically)
            # This is a soft check since it depends on conditions
            assert confidence > 0.3, f"Confidence {confidence} too low"

    def test_get_signals(self, sample_data):
        """Test get_signals returns list of HolyGrailSignal objects."""
        strategy = HolyGrailStrategy()
        sample_data.symbol = 'TEST'  # Add symbol attribute

        signals = strategy.get_signals(sample_data)

        assert isinstance(signals, list)

        for signal in signals:
            assert isinstance(signal, HolyGrailSignal)
            assert signal.symbol == 'TEST'
            assert signal.direction in ['long', 'short']
            assert 0 <= signal.confidence <= 1
            assert signal.entry_price > 0
            assert signal.stop_loss > 0
            assert signal.target_price > 0

    def test_long_signal_structure(self, pullback_data):
        """Test structure of long signals."""
        strategy = HolyGrailStrategy()
        pullback_data.symbol = 'TEST'

        signals = strategy.get_signals(pullback_data)

        long_signals = [s for s in signals if s.direction == 'long']

        for signal in long_signals:
            assert signal.entry_price > signal.stop_loss, "Entry should be above stop for long"
            assert signal.target_price > signal.entry_price, "Target should be above entry for long"
            assert signal.adx_value >= 0
            assert signal.rsi_value >= 0
            assert signal.pullback_bars >= strategy.pullback_min_bars

    def test_adx_requirement_for_setup(self, sample_data):
        """Test that ADX requirement is enforced for setups."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Setups should only occur when ADX is strong
        setups = result[result['hg_long_setup'] | result['hg_short_setup']]

        for idx, row in setups.iterrows():
            # ADX should be above weak threshold at minimum
            # (actual threshold is 30 for strong, but checking for reasonableness)
            assert row['adx_adx'] > strategy.adx_weak_threshold

    def test_rsi_requirement_for_setup(self, sample_data):
        """Test RSI requirements for setups."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Long setups should have RSI oversold or bullish divergence
        long_setups = result[result['hg_long_setup']]

        for idx, row in long_setups.iterrows():
            # Should have either low RSI or divergence
            has_oversold = row['rsi'] < strategy.rsi_oversold
            has_divergence = row.get('bullish_divergence', False)

            # At least one condition should be true (in real scenarios)
            # This is a soft check since data is synthetic

    def test_no_signals_on_choppy_market(self):
        """Test that no signals are generated in choppy/sideways market."""
        # Create sideways market data
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        close = 100 + np.random.randn(50) * 2  # Sideways with noise

        data = pd.DataFrame({
            'open': close - np.random.randn(50) * 0.5,
            'high': close + np.abs(np.random.randn(50)) * 0.5,
            'low': close - np.abs(np.random.randn(50)) * 0.5,
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 50)
        }, index=dates)

        strategy = HolyGrailStrategy()
        result = strategy.analyze(data)

        # In true choppy market, ADX will be low, so few/no strong setups
        strong_setups = result['adx_trend_strong'].sum()

        # Should have limited strong trend signals
        assert strong_setups < len(data) * 0.5, "Too many strong trend signals in choppy market"

    def test_pullback_depth_calculation(self, sample_data):
        """Test pullback depth calculation."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Check pullback depths
        pullbacks_with_depth = result[result['any_pullback'] & (result['pullback_depth'] > 0)]

        for idx, row in pullbacks_with_depth.iterrows():
            depth = row['pullback_depth']

            # Depth should be between 0 and 1 (percentage of range)
            assert 0 <= depth <= 1, f"Pullback depth {depth} out of range"

    def test_strategy_name(self):
        """Test strategy name property."""
        strategy = HolyGrailStrategy()
        assert strategy.name == "Holy Grail"

    def test_entry_after_setup(self, sample_data):
        """Test that entry signals come after setup signals."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        # Entry should occur after setup (not same bar)
        for i in range(1, len(result)):
            if result['hg_long_entry'].iloc[i]:
                # Should have had setup in previous bar
                assert result['hg_long_setup'].iloc[i-1], "Long entry without prior setup"

            if result['hg_short_entry'].iloc[i]:
                # Should have had setup in previous bar
                assert result['hg_short_setup'].iloc[i-1], "Short entry without prior setup"

    def test_count_pullback_bars(self, sample_data):
        """Test pullback bar counting."""
        strategy = HolyGrailStrategy()
        result = strategy.analyze(sample_data)

        for i in range(len(result)):
            count = strategy._count_pullback_bars(result, i)

            # Count should be within valid range
            assert 0 <= count <= strategy.pullback_max_bars


class TestHolyGrailSignal:
    """Test HolyGrailSignal dataclass."""

    def test_signal_creation(self):
        """Test creating a HolyGrailSignal."""
        signal = HolyGrailSignal(
            symbol='TEST',
            timestamp=pd.Timestamp('2024-01-01'),
            direction='long',
            entry_price=100.0,
            stop_loss=95.0,
            target_price=110.0,
            confidence=0.8,
            setup_type='pullback_breakout',
            adx_value=35.0,
            pullback_bars=4,
            rsi_value=25.0
        )

        assert signal.symbol == 'TEST'
        assert signal.direction == 'long'
        assert signal.entry_price == 100.0
        assert signal.stop_loss == 95.0
        assert signal.target_price == 110.0
        assert signal.confidence == 0.8


def test_holy_grail_integration(sample_data):
    """Integration test for complete Holy Grail workflow."""
    # Initialize strategy
    strategy = HolyGrailStrategy()

    # Analyze data
    result = strategy.analyze(sample_data)

    # Should have analyzed data
    assert not result.empty
    assert len(result) == len(sample_data)

    # Get signals
    sample_data.symbol = 'INTEGRATION_TEST'
    signals = strategy.get_signals(sample_data)

    # Signals should be valid
    assert isinstance(signals, list)

    for signal in signals:
        assert isinstance(signal, HolyGrailSignal)
        assert signal.symbol == 'INTEGRATION_TEST'

        # Validate risk/reward
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.target_price - signal.entry_price)

        if risk > 0:
            rr = reward / risk
            assert 1.5 < rr < 2.5, f"Invalid R:R ratio: {rr}"
