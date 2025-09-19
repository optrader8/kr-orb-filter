"""Daily screener workflow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from src.features import gap_percent, kospi_bias, move_off_open, nr7_flag, sector_momentum
from src.store import ResultStore


@dataclass
class ScreenerSettings:
    nr7_weight: int = 2
    gap_threshold: float = 0.005
    moo_threshold: float = 0.6
    bias_weight: int = 1
    liquidity_min: float = 5_000_000_000


class DailyScreener:
    def __init__(self, store: ResultStore, settings: ScreenerSettings | None = None) -> None:
        self.store = store
        self.settings = settings or ScreenerSettings()

    def run(self, daily_data: pd.DataFrame, market_index: pd.Series, sector_index: pd.Series) -> pd.DataFrame:
        """Compute features, score securities, persist results, and return ranked frame."""
        frame = daily_data.copy()
        frame["nr7"] = nr7_flag(frame["high"], frame["low"])
        frame["gap_pct"] = gap_percent(frame["open"], frame["prev_close"])
        frame["moo"] = move_off_open(frame["open"], frame["close"], frame["high"], frame["low"])
        frame["kospi_bias"] = kospi_bias(market_index).reindex(frame.index)
        frame["sector_momentum"] = sector_momentum(sector_index).reindex(frame.index)
        frame["score"] = frame.apply(self._score_row, axis=1)
        screened = frame[frame["liquidity"] >= self.settings.liquidity_min]
        ranked = screened.sort_values("score", ascending=False)
        self.store.save_dataframe(ranked, "daily_screener")
        self.store.save_metadata(self._metadata(ranked), "daily_screener_meta")
        return ranked

    def _score_row(self, row: pd.Series) -> int:
        score = 0
        if row.get("nr7"):
            score += self.settings.nr7_weight
        if row.get("gap_pct", 0) > self.settings.gap_threshold:
            score += 1
        if row.get("moo", 0) > self.settings.moo_threshold:
            score += 1
        if row.get("kospi_bias", 0) > 0:
            score += self.settings.bias_weight
        if row.get("sector_momentum", 0) > 0:
            score += self.settings.bias_weight
        return score

    def _metadata(self, frame: pd.DataFrame) -> Dict[str, List[str] | int]:
        return {
            "columns": list(frame.columns),
            "index_len": len(frame),
        }