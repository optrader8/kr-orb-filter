# Phase 5: Advanced Linda Raschke Strategies

This document summarizes the implementation of Phase 5 advanced strategies in the KR-ORB-Filter system.

## Implemented Strategies

### 1. Volatility Breakout Strategy

**File**: `src/strategies/linda/volatility_breakout.py`

**Purpose**: Detects volatility contraction periods followed by expansion breakouts

**Key Features**:
- Volatility percentile ranking (20-period lookback)
- Narrow Range pattern detection (NR4, NR7, NR10)
- Volume confirmation requirements
- Dynamic target calculation (2.5x ATR expansion)
- Minimum 3-day contraction period requirement

**Configuration** (`config/linda_strategies.yaml`):
```yaml
volatility_breakout:
  enabled: true
  volatility_lookback: 20
  contraction_threshold: 25    # percentile threshold
  expansion_multiplier: 2.5
  volume_threshold: 1.2
  min_contraction_days: 3
```

**Signal Conditions**:
1. Volatility percentile < 25% (bottom quartile)
2. Minimum 3 consecutive contraction days
3. Narrow Range pattern present (NR7, NR4, or Inside Day)
4. Breakout with volume confirmation (>1.2x average)
5. Target: 2.5x recent ATR from breakout point

**Portfolio Allocation**: 15% of portfolio, maximum 3 positions

### 2. Gap Fade Strategy

**File**: `src/strategies/linda/gap_fade.py`

**Purpose**: Trades gap fills (mean reversion) when gaps occur without fundamental news

**Key Features**:
- Gap size filtering (0.5% - 3.0% of price)
- ATR-based gap significance (0.5x - 2.0x ATR)
- Volume profile analysis (avoid high-volume news gaps)
- Market context awareness (avoid strong trends)
- Korean market timing (2-hour entry window)

**Configuration** (`config/linda_strategies.yaml`):
```yaml
gap_fade:
  enabled: true
  min_gap_percent: 0.5         # 0.5% minimum gap
  max_gap_percent: 3.0         # 3% maximum gap
  min_gap_atr_multiple: 0.5    # 0.5x ATR minimum
  max_gap_atr_multiple: 2.0    # 2x ATR maximum
  low_volume_threshold: 0.7    # Low volume ratio
  high_volume_threshold: 1.5   # High volume ratio
  max_entry_time: 120          # 2 hours after open
```

**Signal Conditions**:
1. Gap size: 0.5% - 3.0% of previous close
2. Gap size: 0.5x - 2.0x ATR
3. Normal or low volume (avoid news-driven gaps)
4. Range-bound or weak trend market context
5. Entry: when price moves back toward gap
6. Target: previous day's close (gap fill)

**Portfolio Allocation**: 7% of portfolio, maximum 2 positions

## Pattern Detection Module

**File**: `src/features/linda/patterns.py`

**Purpose**: Unified pattern detection for all Linda strategies

**Implemented Patterns**:
- Narrow Range (NR4, NR7, NR10, NR20)
- Inside Days
- Outside Days
- Key Reversals

**Usage**: Shared by volatility breakout and other strategies requiring pattern analysis

## Integration Points

### 1. Multi-Strategy Screener
- **File**: `src/screen/linda_screener.py`
- **Integration**: Both strategies added to strategy dictionary
- **Priority**: volatility_breakout (3), gap_fade (6)

### 2. Multi-Strategy Coordinator
- **File**: `src/screen/multi_strategy.py`
- **Portfolio Allocation**:
  - Volatility Breakout: 15%
  - Gap Fade: 7%
- **Conflict Resolution**: Included in priority hierarchy

### 3. Enhanced Monitoring
- **File**: `src/monitor/linda_monitor.py`
- **Integration**: Real-time pattern detection for both strategies
- **Alerts**: Pattern formation and signal generation

### 4. Notification System
- **File**: `src/notify/linda_notifications.py`
- **Emojis**:
  - Volatility Breakout: 💥
  - Gap Fade: 📉
- **Templates**: Automatic formatting for both strategies

## Risk Management

Both strategies integrate with the existing risk management framework:

### Position Sizing
- 2% risk rule application
- Portfolio heat management
- Correlation-based adjustments

### Stop Loss Management
- Volatility Breakout: 30% of ATR below/above pattern extreme
- Gap Fade: 0.5% beyond recent high/low
- Technical, volatility, and time-based stops

### Profit Taking
- Scale-out methodology (1/3 at 1:1, 1/3 at 2:1, trail final 1/3)
- Target-based exits with dynamic adjustment

## Performance Characteristics

### Expected Win Rates
- Volatility Breakout: 60-70% (trend following nature)
- Gap Fade: 40-50% (mean reversion nature)

### Risk/Reward Profile
- Volatility Breakout: 2.5:1 average R/R
- Gap Fade: 1.5-2:1 average R/R

### Market Conditions
- Volatility Breakout: Best in trending markets after consolidation
- Gap Fade: Best in range-bound or weak trend environments

## Configuration Management

All strategy parameters are centrally managed in `config/linda_strategies.yaml` with fallback defaults in `src/config.py`.

Strategy enable/disable is controlled via:
```yaml
volatility_breakout:
  enabled: true  # Set to false to disable

gap_fade:
  enabled: true  # Set to false to disable
```

## Next Steps (Phase 6+)

The strategies are ready for:
1. **Backtesting**: Historical performance analysis
2. **Live Testing**: Paper trading validation
3. **Parameter Optimization**: Fine-tuning based on Korean market characteristics
4. **Additional Patterns**: Integration with more complex Linda patterns

## Summary

Phase 5 successfully implements two advanced Linda Raschke strategies:
- **Volatility Breakout**: Captures range expansion after contraction
- **Gap Fade**: Exploits mean reversion in gap situations

Both strategies are fully integrated into the existing system architecture with proper risk management, monitoring, and notification capabilities.