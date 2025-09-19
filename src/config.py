"""Configuration management for KR-ORB-Filter."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    data_cache_dir: Path = Field(default=Path("data/cache"))
    storage_dir: Path = Field(default=Path("data/store"))
    slack_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    liquidity_min: float = 5_000_000_000

    class Config:
        env_prefix = "ORB_"
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.data_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings