"""Persistence helpers for screener and backtest outputs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd


@dataclass
class ResultStore:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save_dataframe(self, frame: pd.DataFrame, name: str) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        path = self.root / f"{name}_{timestamp}.parquet"
        frame.to_parquet(path)
        return path

    def save_metadata(self, data: Dict[str, Any], name: str) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        path = self.root / f"{name}_{timestamp}.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path