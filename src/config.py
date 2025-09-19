"""Enhanced configuration management for KR-ORB-Filter with Linda integration."""
from __future__ import annotations

import yaml
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Legacy settings for backward compatibility."""
    data_cache_dir: Path = Field(default=Path("data/cache"))
    storage_dir: Path = Field(default=Path("data/store"))
    slack_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    liquidity_min: float = 5_000_000_000

    class Config:
        env_prefix = "ORB_"
        env_file = ".env"


@dataclass
class LindaStrategyConfig:
    """Configuration for Linda Raschke strategies."""
    enabled: bool = True
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class RiskManagementConfig:
    """Risk management configuration."""
    max_risk_per_trade: float = 0.02
    max_portfolio_heat: float = 0.08
    position_sizing_method: str = "2_percent_rule"
    stop_methods: Dict[str, bool] = None

    def __post_init__(self):
        if self.stop_methods is None:
            self.stop_methods = {
                "technical": True,
                "volatility": True,
                "time": True,
                "money_management": True
            }


class ConfigurationManager:
    """Enhanced configuration manager supporting YAML files and Linda strategies."""

    def __init__(self, config_dir: Path = Path("config")):
        self.config_dir = config_dir
        self._base_config: Optional[Dict[str, Any]] = None
        self._linda_config: Optional[Dict[str, Any]] = None
        self._risk_config: Optional[Dict[str, Any]] = None
        self._market_hours_config: Optional[Dict[str, Any]] = None

    def load_all_configs(self) -> Dict[str, Any]:
        """Load all configuration files."""
        configs = {}

        # Load base configuration
        configs['base'] = self.load_base_config()
        configs['linda_strategies'] = self.load_linda_config()
        configs['risk_management'] = self.load_risk_config()
        configs['market_hours'] = self.load_market_hours_config()

        return configs

    def load_base_config(self) -> Dict[str, Any]:
        """Load base configuration."""
        if self._base_config is None:
            config_path = self.config_dir / "base.yaml"
            self._base_config = self._load_yaml_config(config_path, self._get_default_base_config())
        return self._base_config

    def load_linda_config(self) -> Dict[str, Any]:
        """Load Linda strategy configuration."""
        if self._linda_config is None:
            config_path = self.config_dir / "linda_strategies.yaml"
            self._linda_config = self._load_yaml_config(config_path, self._get_default_linda_config())
        return self._linda_config

    def load_risk_config(self) -> Dict[str, Any]:
        """Load risk management configuration."""
        if self._risk_config is None:
            config_path = self.config_dir / "risk_management.yaml"
            self._risk_config = self._load_yaml_config(config_path, self._get_default_risk_config())
        return self._risk_config

    def load_market_hours_config(self) -> Dict[str, Any]:
        """Load market hours configuration."""
        if self._market_hours_config is None:
            config_path = self.config_dir / "market_hours.yaml"
            self._market_hours_config = self._load_yaml_config(config_path, self._get_default_market_hours_config())
        return self._market_hours_config

    def _load_yaml_config(self, config_path: Path, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Load YAML configuration with fallback to defaults."""
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config if config is not None else default_config
            except Exception as e:
                print(f"Warning: Failed to load {config_path}: {e}")
                print(f"Using default configuration for {config_path.name}")
                return default_config
        else:
            print(f"Warning: {config_path} not found, using defaults")
            return default_config

    def get_strategy_config(self, strategy_name: str) -> LindaStrategyConfig:
        """Get configuration for a specific Linda strategy."""
        linda_config = self.load_linda_config()
        strategy_config = linda_config.get(strategy_name, {})

        return LindaStrategyConfig(
            enabled=strategy_config.get('enabled', True),
            parameters=strategy_config
        )

    def get_risk_management_config(self) -> RiskManagementConfig:
        """Get risk management configuration."""
        risk_config = self.load_risk_config()
        position_sizing = risk_config.get('position_sizing', {})

        return RiskManagementConfig(
            max_risk_per_trade=position_sizing.get('base_risk_per_trade', 0.02),
            max_portfolio_heat=position_sizing.get('max_total_exposure', 0.08),
            position_sizing_method=position_sizing.get('method', '2_percent_rule'),
            stop_methods=risk_config.get('stop_loss', {}).get('stop_priority', {})
        )

    def _get_default_base_config(self) -> Dict[str, Any]:
        """Get default base configuration."""
        return {
            'system': {
                'name': 'KR-ORB-Filter with Linda Integration',
                'version': '2.0.0',
                'timezone': 'Asia/Seoul'
            },
            'data': {
                'cache': {'directory': 'data/cache'},
                'storage': {'directory': 'data/store'}
            }
        }

    def _get_default_linda_config(self) -> Dict[str, Any]:
        """Get default Linda strategy configuration."""
        return {
            'holy_grail': {'enabled': True, 'adx_threshold': 30.0},
            'turtle_soup': {'enabled': True, 'lookback_period': 20},
            'anti_swing': {'enabled': True, 'rsi2_oversold': 10, 'rsi2_overbought': 90},
            'enhanced_orb': {'enabled': True, 'window_minutes': 30},
            'volatility_breakout': {'enabled': True, 'target_multiplier': 2.0},
            'gap_fade': {'enabled': True, 'large_gap_threshold': 0.02}
        }

    def _get_default_risk_config(self) -> Dict[str, Any]:
        """Get default risk management configuration."""
        return {
            'position_sizing': {
                'base_risk_per_trade': 0.02,
                'max_total_exposure': 0.08,
                'method': '2_percent_rule'
            },
            'stop_loss': {
                'stop_priority': ['technical', 'volatility', 'money_management', 'time']
            }
        }

    def _get_default_market_hours_config(self) -> Dict[str, Any]:
        """Get default market hours configuration."""
        return {
            'market_sessions': {
                'kospi': {
                    'timezone': 'Asia/Seoul',
                    'regular_hours': {'start': '09:00', 'end': '15:30'}
                }
            },
            'trading_windows': {
                'opening_range': {'start': '09:00', 'end': '09:30'}
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """Get legacy settings for backward compatibility."""
    settings = Settings()
    settings.data_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings


@lru_cache()
def get_config_manager() -> ConfigurationManager:
    """Get the configuration manager instance."""
    return ConfigurationManager()


def get_linda_strategy_config(strategy_name: str) -> LindaStrategyConfig:
    """Get configuration for a specific Linda strategy."""
    config_manager = get_config_manager()
    return config_manager.get_strategy_config(strategy_name)


def get_risk_management_config() -> RiskManagementConfig:
    """Get risk management configuration."""
    config_manager = get_config_manager()
    return config_manager.get_risk_management_config()