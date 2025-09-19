# Operations Runbook

## Daily Screener
- Populate `.env` (see `.env.example`) and activate the virtual environment.
- Prepare historical OHLCV CSVs per symbol under a directory and create market/sector index CSVs (columns: `date,close`).
- Execute `python -m src.cli screener daily --symbols 005930,000660 --start 2024-01-01 --end 2024-02-01 --market-csv data/kospi.csv --sector-csv data/sector.csv --csv-dir data/ohlcv`.
- Review output parquet and JSON artifacts in `data/store` prefixed `daily_screener_*`.

## Intraday ORB Monitor
- Compile intraday CSVs with `timestamp,price` headers (ISO 8601 timestamps).
- Run `python -m src.cli monitor --symbol 005930 --csv data/intraday/005930.csv --cooldown 300`.
- Confirm Slack/Telegram credentials are set via environment variables before live runs; otherwise monitor console output for simulated dispatches.

## Backtests
- Prepare `prices.csv` (`date,close`) and `signals.csv` (`date,signal`).
- Execute `python -m src.cli backtest --prices data/prices.csv --signals data/signals.csv --atr-mult 1.0 --risk-reward 2.0`.
- Persist results using `ResultStore.save_dataframe` as needed and store metrics JSON for traceability.

## Alerting
- Rotate Slack and Telegram secrets quarterly; load them into the environment (see `.env.example`).
- Monitor notifier logs for non-2xx responses and retry manually when required.

## Incident Response
- If data ingestion fails three times, verify provider availability and switch to CSV fallback until resolved.
- For ORB alert floods, raise `cooldown_seconds` in `ORBSettings` and redeploy the monitoring process.
- Record failures in run logs and open issues tagged `ops` for follow-up.