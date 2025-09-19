# Design Overview - Linda Raschke Integration

This design extends the core KR-ORB-Filter system to incorporate Linda Raschke's proven trading methodologies while maintaining the existing architecture's modularity and performance.

```mermaid
graph TD
    CLI[CLI Commands]
    API[Optional FastAPI]
    DataLoaders[Enhanced Data Loaders]

    %% Core Features
    BaseFeatures[Base Features<br/>NR7, Gap, MOO, Bias]
    LindaFeatures[Linda Features<br/>ADX/DMI, RSI2, Stochastic, MAs]

    %% Strategy Engines
    BaseScreener[Base Daily Screener]
    LindaScreener[Linda Strategy Screener<br/>HG, Turtle Soup, Anti-Swing]

    BaseMonitor[Base ORB Monitor]
    LindaMonitor[Enhanced ORB Monitor<br/>Volume, Gap Analysis, MA Bias]

    %% Risk & Management
    BaseRisk[Base Risk Management]
    LindaRisk[Linda Risk Framework<br/>2% Rule, Scale-out, Trailing Stops]

    %% Strategy Specific Components
    HolyGrail[Holy Grail Setup Engine]
    TurtleSoup[Turtle Soup Engine]
    AntiSwing[Anti-Swing Engine]
    VolBreakout[Volatility Breakout Engine]
    GapFade[Gap Fade Engine]

    %% Backtesting & Analytics
    BaseBacktest[Base Backtest Engine]
    LindaBacktest[Linda Strategy Backtester<br/>Multiple Timeframes, Performance Metrics]

    %% Infrastructure
    Notify[Enhanced Notifications<br/>Strategy-specific Alerts]
    Store[Enhanced Store<br/>Strategy Parameters, Performance Logs]

    %% Market Psychology
    Sentiment[Market Psychology Module<br/>VIX, Put/Call, FII Flows]

    CLI --> BaseScreener
    CLI --> LindaScreener
    CLI --> BaseMonitor
    CLI --> LindaMonitor
    CLI --> BaseBacktest
    CLI --> LindaBacktest

    API --> BaseScreener
    API --> LindaScreener
    API --> BaseMonitor
    API --> LindaMonitor

    DataLoaders --> BaseFeatures
    DataLoaders --> LindaFeatures
    DataLoaders --> Sentiment

    BaseFeatures --> BaseScreener
    BaseFeatures --> BaseMonitor

    LindaFeatures --> LindaScreener
    LindaFeatures --> LindaMonitor
    LindaFeatures --> HolyGrail
    LindaFeatures --> TurtleSoup
    LindaFeatures --> AntiSwing
    LindaFeatures --> VolBreakout
    LindaFeatures --> GapFade

    HolyGrail --> LindaScreener
    TurtleSoup --> LindaScreener
    AntiSwing --> LindaScreener
    VolBreakout --> LindaMonitor
    GapFade --> LindaMonitor

    BaseScreener --> Store
    LindaScreener --> Store

    BaseMonitor --> BaseRisk
    LindaMonitor --> LindaRisk

    BaseRisk --> Notify
    LindaRisk --> Notify

    LindaBacktest --> Store
    BaseBacktest --> Store
    Store --> LindaBacktest
    Store --> BaseBacktest

    Sentiment --> LindaScreener
    Sentiment --> LindaMonitor
```

## Key Design Decisions

### 1. Modular Strategy Integration
- **Parallel Architecture**: Linda strategies run alongside existing base strategies without interference
- **Shared Infrastructure**: Leverage existing data loaders, storage, and notification systems
- **Strategy Isolation**: Each Linda strategy (HG, Turtle Soup, etc.) is implemented as a separate module
- **Configuration Driven**: All Linda parameters configurable via environment and config files

### 2. Enhanced Feature Pipeline
```mermaid
graph LR
    Raw[Raw OHLCV Data] --> Base[Base Features<br/>NR7, Gap, MOO]
    Raw --> Technical[Technical Indicators<br/>ADX, RSI2, Stochastic, EMAs]
    Raw --> Psychology[Market Psychology<br/>VIX, Put/Call, FII]

    Base --> Scoring[Enhanced Scoring Engine]
    Technical --> Scoring
    Psychology --> Scoring

    Scoring --> Signals[Multi-Strategy Signals]
```

### 3. Risk Management Enhancement
```mermaid
graph TD
    Entry[Signal Entry] --> Size[Position Sizing<br/>2% Rule, Correlation Check]
    Size --> Stop[Stop Loss<br/>Technical, Volatility, Time, Money]
    Stop --> Management[Trade Management<br/>Scale-out 1/3, 1/3, 1/3]
    Management --> Trail[Trailing Stops<br/>ATR-based, Breakeven]
    Trail --> Exit[Exit Strategies<br/>Target Zones, Time Exits]
```

### 4. Strategy-Specific Components

#### Holy Grail Setup Engine
- **Trend Detection**: ADX > 30 filter with ±DI confirmation
- **Pullback Identification**: 3-5 bar retracement detection
- **Momentum Divergence**: RSI oversold/overbought in pullback
- **Entry Confirmation**: Break of pullback high/low

#### Turtle Soup Engine
- **20-Day Range Tracking**: Rolling high/low calculation
- **Failed Breakout Detection**: Break above/below with close failure
- **Reversal Confirmation**: Next day trade through opposite level
- **Risk Management**: Stop beyond failed breakout level

#### Anti-Swing Engine
- **Extreme Condition Detection**: 2-day RSI < 10 or > 90
- **Counter-Trend Setup**: After 2-3 days strong directional move
- **Entry Timing**: Stochastic crossover confirmation
- **Mean Reversion Target**: 5-period moving average

### 5. Enhanced ORB Monitor
```mermaid
graph TD
    Market[Market Open] --> Window[30-min ORB Window<br/>09:00-09:30 KST]
    Window --> Volume[Volume Analysis<br/>> 20-day Average]
    Window --> Gap[Gap Classification<br/>Small/Medium/Large]
    Window --> Bias[Market Bias<br/>KOSPI Direction]

    Volume --> Signal[ORB Signal Generation]
    Gap --> Signal
    Bias --> Signal

    Signal --> Risk[Enhanced Risk Calc<br/>1.5x ORB or Prev Day]
    Risk --> Alert[Strategy-specific Alerts]
```

### 6. Performance Metrics Integration
```mermaid
graph LR
    Trades[Trade Results] --> Metrics[Performance Metrics]

    Metrics --> WinRate[Win Rate Targets<br/>Trend: 60-65%<br/>Mean Rev: 40-45%]
    Metrics --> RiskReward[Risk/Reward<br/>Min 1:1.5]
    Metrics --> Drawdown[Max Drawdown<br/>≤ 15-20%]
    Metrics --> Sharpe[Sharpe Ratio<br/>> 1.5]

    WinRate --> Dashboard[Strategy Dashboard]
    RiskReward --> Dashboard
    Drawdown --> Dashboard
    Sharpe --> Dashboard
```

## Data Flow Architecture

### 1. Pre-Market Analysis (Pre-09:00 KST)
1. **Data Ingestion**: Download overnight data, foreign market results
2. **Feature Calculation**: Compute all technical indicators and Linda features
3. **Screening**: Run both base and Linda strategy screens
4. **Bias Determination**: Assess overall market direction using multiple timeframes
5. **Alert Preparation**: Queue potential setups for intraday monitoring

### 2. Trading Session (09:00-15:30 KST)
1. **Opening Analysis**: Monitor gaps, volume, and ORB formation
2. **Pattern Recognition**: Real-time detection of HG, Turtle Soup, Anti-Swing setups
3. **Signal Generation**: Coordinate multiple strategy signals with priority weighting
4. **Risk Management**: Apply Linda's risk framework to all generated signals
5. **Alert Distribution**: Send strategy-specific notifications via Slack/Telegram

### 3. Post-Market Analysis (Post-15:30 KST)
1. **Trade Journaling**: Log all signals, entries, exits, and reasoning
2. **Performance Review**: Calculate strategy-specific metrics and comparisons
3. **Strategy Adjustment**: Analyze market conditions for parameter optimization
4. **Reporting**: Generate daily/weekly/monthly performance summaries

## Technical Implementation Strategy

### 1. Backward Compatibility
- Existing base system functionality remains unchanged
- New Linda features are additive, not replacements
- Configuration allows selective enabling/disabling of Linda strategies
- Existing users can gradually adopt Linda enhancements

### 2. Performance Optimization
- Vectorized calculations for all Linda indicators using NumPy/Pandas
- Efficient caching of expensive computations (ADX, EMAs)
- Parallel processing for multiple strategy evaluations
- Memory-efficient handling of multi-timeframe data

### 3. Configuration Management
```python
# Enhanced config structure
LINDA_STRATEGIES = {
    'holy_grail': {
        'enabled': True,
        'adx_threshold': 30,
        'pullback_bars': [3, 4, 5],
        'rsi_oversold': 30,
        'rsi_overbought': 70
    },
    'turtle_soup': {
        'enabled': True,
        'lookback_days': 20,
        'confirmation_required': True
    },
    'anti_swing': {
        'enabled': True,
        'rsi2_oversold': 10,
        'rsi2_overbought': 90,
        'target_ma_period': 5
    }
}
```

### 4. Testing Strategy
- Unit tests for each Linda strategy component
- Integration tests for multi-strategy coordination
- Backtesting validation against known historical patterns
- Performance benchmarking against base system
- A/B testing framework for strategy comparison

This design ensures Linda Raschke's methodologies are seamlessly integrated while maintaining the system's reliability, performance, and extensibility.