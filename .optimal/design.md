# Design Overview

This design highlights the core data and signal flow for KR-ORB-Filter based on current requirements.

```mermaid
graph TD
    CLI[CLI Commands]
    API[Optional FastAPI]
    DataLoaders[Data Loaders]
    Features[Feature Pipelines]
    Screener[Daily Screener]
    Monitor[Intraday ORB Monitor]
    Backtest[Backtest Engine]
    Notify[Slack / Telegram Alerts]
    Store[SQLite / Parquet Store]

    CLI --> Screener
    CLI --> Monitor
    CLI --> Backtest
    API --> Screener
    API --> Monitor
    DataLoaders --> Features
    Features --> Screener
    Features --> Monitor
    Screener --> Store
    Monitor --> Notify
    Backtest --> Store
    Store --> Backtest
```

Key decisions:

- Keep data ingestion and feature calculation isolated to simplify unit testing and reuse.
- Route alerts through a shared notifier layer so delivery providers share throttling and logging logic.
- Persist all screen/backtest outputs to the store to support reproducible research and reporting.