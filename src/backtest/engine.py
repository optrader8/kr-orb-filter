"""Backtest utilities for KR-ORB-Filter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import numpy as np
import pandas as pd


@dataclass
class BacktestParams:
    atr_mult: float = 1.0
    risk_reward: float = 2.0
    hold_minutes: int = 240


def run_backtest(prices: pd.DataFrame, signals: pd.Series, params: BacktestParams | None = None) -> pd.DataFrame:
    params = params or BacktestParams()
    frame = prices.copy()
    frame["signal"] = signals
    frame["return"] = frame["close"].pct_change().fillna(0)
    frame["strategy_return"] = frame["return"] * frame["signal"].shift().fillna(0)
    frame["equity_curve"] = (1 + frame["strategy_return"]).cumprod()
    return frame


def summarize(result: pd.DataFrame) -> Dict[str, float]:
    strat_returns = result["strategy_return"]
    total_return = strat_returns.add(1).prod() - 1
    win_rate = (strat_returns > 0).mean()
    avg_trade = strat_returns.mean()
    drawdown = (result["equity_curve"].cummax() - result["equity_curve"]) / result["equity_curve"].cummax()
    mdd = drawdown.max()
    sharpe = np.sqrt(252) * strat_returns.mean() / (strat_returns.std() + 1e-9)
    exposure = strat_returns.ne(0).mean()
    return {
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "avg_trade": float(avg_trade),
        "mdd": float(mdd),
        "sharpe": float(sharpe),
        "exposure": float(exposure),
    }