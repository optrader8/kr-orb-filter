# Project Structure - Linda Raschke Integration

This document outlines the enhanced project structure incorporating Linda Raschke's trading strategies while maintaining the existing codebase organization.

## Enhanced Directory Structure

```
kr-orb-filter/
├── src/
│   ├── config.py                      # Enhanced env, constants, Linda parameters
│   ├── data/
│   │   ├── loaders.py                 # Base pykrx, CSV, broker API adapters
│   │   ├── intraday.py                # Enhanced ORB window, real-time handlers
│   │   └── market_psychology.py       # NEW: VIX, put/call, FII flow data
│   ├── features/
│   │   ├── nr7.py                     # Base NR7, narrow-range features
│   │   ├── orb.py                     # Enhanced opening range calc, breakout logic
│   │   ├── bias.py                    # Enhanced market/sector bias, gaps, move-off-open
│   │   ├── technical.py               # NEW: ADX/DMI, RSI2, Stochastic, EMAs
│   │   └── linda/                     # NEW: Linda-specific feature modules
│   │       ├── __init__.py
│   │       ├── adx_system.py          # ADX/DMI calculations and trend detection
│   │       ├── momentum.py            # RSI2, Stochastic calculations
│   │       ├── moving_averages.py     # EMA crossovers, 3-period MA
│   │       └── volatility.py          # ATR calculations, volatility analysis
│   ├── strategies/                    # NEW: Strategy-specific implementations
│   │   ├── __init__.py
│   │   ├── base/
│   │   │   ├── __init__.py
│   │   │   ├── nr7_orb.py            # Original NR7 + ORB strategy
│   │   │   └── momentum_screen.py     # Original momentum screening
│   │   └── linda/
│   │       ├── __init__.py
│   │       ├── holy_grail.py         # Holy Grail setup detection and signals
│   │       ├── turtle_soup.py        # Turtle Soup false breakout strategy
│   │       ├── anti_swing.py         # Anti-Swing counter-trend strategy
│   │       ├── enhanced_orb.py       # Linda's enhanced ORB with volume/gap analysis
│   │       ├── volatility_breakout.py # Volatility contraction/expansion strategy
│   │       ├── gap_fade.py           # Gap fade strategy implementation
│   │       └── ma_crossover.py       # Moving average crossover strategies
│   ├── screen/
│   │   ├── screener.py               # Enhanced daily screening & ranking
│   │   ├── filters.py                # Enhanced liquidity, price bands, exclusions
│   │   ├── linda_screener.py         # NEW: Linda strategy coordinator
│   │   └── multi_strategy.py         # NEW: Multi-strategy signal coordination
│   ├── monitor/                      # RENAMED from intraday monitoring
│   │   ├── __init__.py
│   │   ├── base_monitor.py           # Original ORB monitoring
│   │   ├── linda_monitor.py          # NEW: Enhanced ORB monitoring with Linda features
│   │   ├── pattern_detector.py       # NEW: Real-time pattern detection
│   │   └── signal_coordinator.py     # NEW: Multi-strategy signal management
│   ├── risk/                         # NEW: Enhanced risk management
│   │   ├── __init__.py
│   │   ├── base_risk.py              # Original risk calculations
│   │   ├── linda_risk.py             # Linda's risk management framework
│   │   ├── position_sizing.py        # 2% rule, correlation-based sizing
│   │   ├── stop_management.py        # Technical, volatility, time, money stops
│   │   └── profit_taking.py          # Scale-out strategies, trailing stops
│   ├── backtest/
│   │   ├── engine.py                 # Enhanced vectorized backtests
│   │   ├── metrics.py                # Enhanced PnL, winrate, MDD, Sharpe
│   │   ├── linda_engine.py           # NEW: Linda strategy backtesting
│   │   ├── strategy_comparison.py    # NEW: Multi-strategy performance comparison
│   │   └── optimization.py           # NEW: Parameter optimization framework
│   ├── notify/
│   │   ├── slack.py                  # Enhanced Slack integration
│   │   ├── telegram.py               # Enhanced Telegram integration
│   │   ├── formatters.py             # NEW: Strategy-specific message formatting
│   │   └── priority_manager.py       # NEW: Alert prioritization and throttling
│   ├── store/
│   │   ├── db.py                     # Enhanced SQLite/Postgres ORM models
│   │   ├── io.py                     # Enhanced parquet/csv snapshots
│   │   ├── strategy_logs.py          # NEW: Strategy-specific logging
│   │   └── performance_tracking.py   # NEW: Performance metrics storage
│   ├── analysis/                     # NEW: Analysis and reporting tools
│   │   ├── __init__.py
│   │   ├── performance_analyzer.py   # Strategy performance analysis
│   │   ├── market_regime.py          # Market regime detection
│   │   ├── correlation_analysis.py   # Cross-strategy correlation analysis
│   │   └── reporting.py              # Automated report generation
│   ├── utils/                        # NEW: Utility functions
│   │   ├── __init__.py
│   │   ├── validators.py             # Data validation utilities
│   │   ├── time_utils.py             # Korean market time handling
│   │   ├── math_utils.py             # Mathematical calculations
│   │   └── logging_utils.py          # Enhanced logging utilities
│   ├── cli.py                        # Enhanced CLI entrypoints
│   └── app.py                        # Enhanced FastAPI (optional)
├── tests/                            # NEW: Comprehensive test suite
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_features/
│   │   ├── test_strategies/
│   │   ├── test_risk/
│   │   └── test_utils/
│   ├── integration/
│   │   ├── test_workflows/
│   │   ├── test_backtesting/
│   │   └── test_monitoring/
│   ├── fixtures/
│   │   ├── sample_data.py
│   │   └── mock_responses.py
│   └── conftest.py
├── config/                           # NEW: Configuration management
│   ├── base.yaml                     # Base configuration
│   ├── linda_strategies.yaml         # Linda strategy parameters
│   ├── risk_management.yaml          # Risk management settings
│   └── market_hours.yaml             # Market timing configurations
├── notebooks/
│   ├── EDA.ipynb
│   ├── backtest_examples.ipynb
│   ├── linda_strategy_analysis.ipynb # NEW: Linda strategy research
│   ├── performance_comparison.ipynb  # NEW: Strategy comparison analysis
│   └── market_regime_analysis.ipynb  # NEW: Market regime studies
├── docs/                             # NEW: Documentation
│   ├── README.md
│   ├── strategy_guides/
│   │   ├── linda_strategies.md
│   │   ├── risk_management.md
│   │   └── backtesting_guide.md
│   ├── api_reference/
│   └── deployment_guide.md
├── scripts/                          # NEW: Utility scripts
│   ├── data_validation.py
│   ├── performance_report.py
│   ├── strategy_optimization.py
│   └── market_analysis.py
├── .optimal/
│   ├── requirements.md               # Original EARS requirements
│   ├── design.md                     # Original design
│   ├── tasks.md                      # Original tasks
│   └── linda-integration/            # NEW: Linda integration docs
│       ├── requirements.md           # Linda EARS requirements
│       ├── design.md                 # Linda design overview
│       ├── structure.md              # This file
│       └── tasks.md                  # Linda implementation tasks
├── .env.example                      # Enhanced environment template
├── .gitignore
├── README.md                         # Enhanced with Linda strategies
├── PRD.md
├── requirements.txt                  # Enhanced dependencies
├── requirements.md                   # Original EARS
└── linda.md                          # Linda strategy documentation
```

## Key Structural Decisions

### 1. Strategy Organization

#### Base Strategies (`src/strategies/base/`)
- **Isolation**: Original strategies remain unchanged and isolated
- **Backward Compatibility**: Existing functionality preserved
- **Independent Operation**: Can run without Linda enhancements

#### Linda Strategies (`src/strategies/linda/`)
- **Modular Design**: Each strategy is a separate module
- **Common Interface**: All strategies implement standard interfaces
- **Parameter Driven**: Configuration-based behavior modification

### 2. Feature Pipeline Enhancement

#### Original Features (`src/features/`)
- **Enhanced**: Existing modules extended with additional functionality
- **Preserved**: Original calculations remain intact
- **Extended**: New Linda-specific calculations added

#### Linda Features (`src/features/linda/`)
- **Specialized**: Linda-specific technical indicators
- **Reusable**: Common calculations shared across strategies
- **Optimized**: Vectorized implementations for performance

### 3. Risk Management Framework (`src/risk/`)

#### Modular Risk Components
- **Position Sizing**: 2% rule, correlation-based adjustments
- **Stop Management**: Multiple stop types (technical, volatility, time, money)
- **Profit Taking**: Scale-out strategies, trailing stops
- **Portfolio Heat**: Total exposure monitoring

### 4. Monitoring and Analysis

#### Enhanced Monitoring (`src/monitor/`)
- **Real-time**: Pattern detection during market hours
- **Multi-strategy**: Coordinated signal management
- **Priority-based**: Alert prioritization and throttling

#### Analysis Framework (`src/analysis/`)
- **Performance Tracking**: Strategy-specific metrics
- **Market Regime**: Environment-based adaptation
- **Correlation Analysis**: Cross-strategy relationships
- **Reporting**: Automated performance reports

### 5. Configuration Management

#### Hierarchical Configuration
```
config/
├── base.yaml                 # Core system settings
├── linda_strategies.yaml     # Strategy-specific parameters
├── risk_management.yaml      # Risk framework settings
└── market_hours.yaml         # Timing configurations
```

#### Environment Integration
- **Development**: Local development settings
- **Testing**: Test environment configurations
- **Production**: Live trading parameters

### 6. Testing Strategy

#### Test Organization
```
tests/
├── unit/                     # Component-level tests
├── integration/              # System integration tests
├── fixtures/                 # Test data and mocks
└── conftest.py              # Pytest configuration
```

#### Coverage Requirements
- **Unit Tests**: >90% coverage for all strategy modules
- **Integration Tests**: End-to-end workflow validation
- **Performance Tests**: Backtesting accuracy verification

### 7. Data Flow Architecture

#### Input Sources
1. **Market Data**: OHLCV, volume, fundamentals
2. **Market Psychology**: VIX, sentiment indicators
3. **Foreign Flows**: FII investment data
4. **Configuration**: Strategy parameters, risk settings

#### Processing Pipeline
1. **Data Ingestion**: Multi-source data collection
2. **Feature Engineering**: Technical indicator calculations
3. **Strategy Evaluation**: Multi-strategy signal generation
4. **Risk Assessment**: Position sizing and risk evaluation
5. **Signal Coordination**: Priority-based signal management
6. **Execution Planning**: Trade preparation and alert generation

#### Output Destinations
1. **Alerts**: Slack/Telegram notifications
2. **Storage**: Database and file persistence
3. **Analysis**: Performance tracking and reporting
4. **Logs**: Detailed audit trails

### 8. Deployment Considerations

#### Development Environment
- **Local Development**: Full-featured development setup
- **Testing**: Isolated test environment with mock data
- **Staging**: Production-like environment for validation

#### Production Environment
- **Containerized**: Docker-based deployment
- **Scalable**: Cloud-native architecture
- **Monitored**: Comprehensive logging and alerting
- **Backed Up**: Regular data and configuration backups

This structure ensures Linda Raschke's strategies are seamlessly integrated while maintaining clear separation of concerns, testability, and maintainability of the existing codebase.