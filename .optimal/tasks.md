# Work Tasks

- Finalize data ingestion pipelines: implement pykrx daily fetches, retries, and checksum logging.
- Build feature modules for NR7, gap, move-off-open, and bias calculations with deterministic tests.
- Implement daily screener workflow wiring feature scores into ranking and persistence.
- Create intraday ORB monitor supporting replay CSVs, breakout detection, and alert throttling.
- Extend notification layer with Slack webhook and Telegram bot adapters plus status logging.
- Deliver vectorized backtest engine with configurable strategies, metrics, and universe filters.
- Harden configuration handling: env loading, validation via Pydantic, and secure secret usage.
- Establish pytest suite covering data loaders, features, screening, ORB monitor, and backtesting.
- Document operational runbooks and update `.env.example` and requirements notes for new dependencies.