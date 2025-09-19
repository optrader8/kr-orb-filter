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
        frame = self._ensure_multiindex(daily_data)
        featured = frame.groupby(level="symbol", group_keys=False).apply(self._apply_symbol_features)
        dates = featured.index.get_level_values("date")
        featured["kospi_bias"] = kospi_bias(market_index).reindex(dates).values
        featured["sector_momentum"] = sector_momentum(sector_index).reindex(dates).values
        featured["score"] = featured.apply(self._score_row, axis=1)
        latest = featured.groupby(level="symbol").tail(1)
        screened = latest[latest["liquidity"] >= self.settings.liquidity_min]
        ranked = screened.sort_values("score", ascending=False)
        self.store.save_dataframe(ranked.reset_index(), "daily_screener")
        self.store.save_metadata(self._metadata(ranked), "daily_screener_meta")
        return ranked

    def _apply_symbol_features(self, group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_index()
        if "prev_close" not in group.columns:
            group["prev_close"] = group["close"].shift(1)
        if "liquidity" not in group.columns:
            volume = group.get("volume", pd.Series(0, index=group.index))
            group["liquidity"] = group["close"] * volume
        group["nr7"] = nr7_flag(group["high"], group["low"])
        group["gap_pct"] = gap_percent(group["open"], group["prev_close"])
        group["moo"] = move_off_open(group["open"], group["close"], group["high"], group["low"])
        return group.dropna(subset=["prev_close"])

    def _ensure_multiindex(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        if not isinstance(result.index, pd.MultiIndex):
            if "symbol" not in result.columns:
                raise ValueError("daily_data must include a symbol level or column")
            result = result.set_index("symbol", append=True)
            result = result.reorder_levels(["symbol", result.index.name or "index"]).sort_index()
        result.index = result.index.set_names(["symbol", "date"])
        return result

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