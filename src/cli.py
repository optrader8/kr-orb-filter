"""Command line entrypoints for KR-ORB-Filter."""
from __future__ import annotations

import argparse
import datetime as dt
import logging
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd

from src.backtest import BacktestParams, run_backtest, summarize
from src.config import get_settings
from src.data import DailyDataLoader, DailyDataRequest
from src.monitor import ORBMonitor, ORBSettings
from src.notify import NotificationError, SlackNotifier, TelegramNotifier
from src.screen import DailyScreener, ScreenerSettings
from src.store import ResultStore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_symbols(raw: str | None, file_path: Path | None) -> List[str]:
    if raw:
        return [symbol.strip() for symbol in raw.split(",") if symbol.strip()]
    if file_path:
        return [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    raise ValueError("symbols or symbols-file must be provided")


def load_series_from_csv(path: Path, value_column: str = "close") -> pd.Series:
    frame = pd.read_csv(path, parse_dates=["date"])
    if value_column not in frame.columns:
        raise ValueError(f"{value_column} column missing in {path}")
    series = pd.Series(frame[value_column].values, index=pd.to_datetime(frame["date"]))
    return series.sort_index()


def prepare_daily_dataset(symbols: Sequence[str], start: dt.date, end: dt.date, loader: DailyDataLoader) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for symbol in symbols:
        request = DailyDataRequest(start=start, end=end, symbol=symbol)
        df = loader.fetch(request)
        frames.append(df)
    combined = pd.concat(frames, keys=symbols, names=["symbol", "date"])
    return combined


def build_dispatch(settings) -> callable:
    notifiers: List[callable] = []
    if settings.slack_webhook_url:
        notifiers.append(SlackNotifier(settings.slack_webhook_url).send)
    if settings.telegram_bot_token and settings.telegram_chat_id:
        telegram = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
        notifiers.append(telegram.send)

    def dispatch(event) -> None:
        message = (
            f"{event.symbol} {event.direction.upper()} breakout at {event.breakout_time.isoformat()} "
            f"(H:{event.orb_high} L:{event.orb_low} P:{event.price})"
        )
        logger.info(message)
        for send in notifiers:
            try:
                send(message)
            except NotificationError as error:
                logger.error("Notification send failed: %s", error)

    return dispatch


def run_screener(args: argparse.Namespace) -> None:
    settings = get_settings()
    loader = DailyDataLoader(cache_dir=settings.data_cache_dir, csv_fallback=args.csv_dir)
    symbols = parse_symbols(args.symbols, args.symbols_file)
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    data = prepare_daily_dataset(symbols, start, end, loader)
    market_series = load_series_from_csv(args.market_csv)
    sector_series = load_series_from_csv(args.sector_csv)
    screener = DailyScreener(ResultStore(settings.storage_dir), ScreenerSettings(liquidity_min=settings.liquidity_min))
    ranked = screener.run(data, market_series, sector_series)
    print(ranked[["score", "gap_pct", "moo", "kospi_bias", "sector_momentum", "liquidity"]])


def run_monitor(args: argparse.Namespace) -> None:
    settings = get_settings()
    dispatch = build_dispatch(settings)
    monitor = ORBMonitor(
        ORBSettings(
            cooldown_seconds=args.cooldown,
        ),
        dispatch,
    )
    events = monitor.run_csv(args.csv, args.symbol)
    print(f"Generated {len(events)} breakout events")


def run_backtest_cli(args: argparse.Namespace) -> None:
    prices = pd.read_csv(args.prices, parse_dates=["date"])
    signals = pd.read_csv(args.signals, parse_dates=["date"])
    merged = prices.merge(signals, on="date", how="left")
    merged["signal"] = merged["signal"].fillna(0)
    merged = merged.sort_values("date")
    frame = merged.set_index("date")[["close"]]
    signal_series = merged.set_index("date")["signal"]
    params = BacktestParams(atr_mult=args.atr_mult, risk_reward=args.risk_reward, hold_minutes=args.hold_minutes)
    result = run_backtest(frame, signal_series, params)
    metrics = summarize(result)
    print(pd.Series(metrics))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KR-ORB-Filter CLI")
    subparsers = parser.add_subparsers(dest="command")

    screener_parser = subparsers.add_parser("screener", help="Run screeners")
    screener_sub = screener_parser.add_subparsers(dest="screener_command")
    daily_parser = screener_sub.add_parser("daily", help="Run daily screener")
    daily_parser.add_argument("--symbols", help="Comma-separated list of symbols")
    daily_parser.add_argument("--symbols-file", type=Path, help="File containing symbols, one per line")
    daily_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    daily_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    daily_parser.add_argument("--market-csv", type=Path, required=True, help="Market index CSV with date, close")
    daily_parser.add_argument("--sector-csv", type=Path, required=True, help="Sector index CSV with date, close")
    daily_parser.add_argument("--csv-dir", type=Path, required=True, help="Directory with per-symbol CSV fallback data")
    daily_parser.set_defaults(func=run_screener)

    monitor_parser = subparsers.add_parser("monitor", help="Run ORB monitor")
    monitor_parser.add_argument("--symbol", required=True, help="Symbol identifier")
    monitor_parser.add_argument("--csv", type=Path, required=True, help="Intraday CSV with timestamp,price")
    monitor_parser.add_argument("--cooldown", type=int, default=300, help="Cooldown seconds between alerts")
    monitor_parser.set_defaults(func=run_monitor)

    backtest_parser = subparsers.add_parser("backtest", help="Run backtests")
    backtest_parser.add_argument("--prices", type=Path, required=True, help="CSV with date, close")
    backtest_parser.add_argument("--signals", type=Path, required=True, help="CSV with date, signal")
    backtest_parser.add_argument("--atr-mult", type=float, default=1.0)
    backtest_parser.add_argument("--risk-reward", type=float, default=2.0)
    backtest_parser.add_argument("--hold-minutes", type=int, default=240)
    backtest_parser.set_defaults(func=run_backtest_cli)

    return parser


def main(argv: Iterable[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()