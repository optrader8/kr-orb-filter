# Operations Runbook

## Daily Screener
- Ensure `.env` is populated (see `.env.example`).
- Activate the virtual environment and run `python -m src.cli screener daily` (CLI scaffolding pending; invoke `DailyScreener` directly in notebooks/tests meanwhile).
- Check output parquet files under `data/store` for the `daily_screener_*` artifacts.

## Intraday ORB Monitor
- Prepare intraday CSV with `timestamp,price` headers using ISO timestamps.
- Run `ORBMonitor` via a small driver script: `python scripts/run_orb.py --symbol 005930 --csv intraday.csv` (script forthcoming).
- Verify Slack/Telegram credentials before enabling live alerts; otherwise run in dry-run mode by swapping dispatch with a logger.

## Backtests
- Generate signals via research notebooks or CLI and call `run_backtest` with `BacktestParams`.
- Persist results using `ResultStore.save_dataframe` and attach summary metrics from `summarize`.
- Archive metrics JSON alongside parquet outputs for traceability.

## Alerting
- Rotate Slack and Telegram secrets quarterly; store them in your vault and export to environment variables before execution.
- Monitor notifier logs for non-2xx responses and retry manually if needed.

## Incident Response
- If data ingestion fails three times, inspect provider availability and switch to CSV fallback until resolved.
- For ORB alert floods, adjust `cooldown_seconds` in `ORBSettings` and redeploy monitoring service.
- Capture failures in the run log and open issues tagged with `ops` for follow-up.