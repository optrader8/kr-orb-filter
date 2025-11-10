"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime


class PositionResponse(BaseModel):
    """Position information."""
    symbol: str
    entry_price: float
    current_price: float
    quantity: int
    direction: str  # 'long' or 'short'
    entry_date: datetime
    pnl: float
    pnl_percent: float
    risk_amount: float
    stop_loss: float
    target: Optional[float] = None
    strategy: str


class PositionDetail(PositionResponse):
    """Detailed position information."""
    indicators: Dict[str, float]
    signal_confidence: float
    days_held: int
    max_favorable_excursion: float
    max_adverse_excursion: float


class PortfolioSummary(BaseModel):
    """Portfolio summary with risk metrics."""
    total_positions: int
    total_value: float
    total_pnl: float
    total_pnl_percent: float
    portfolio_heat: float
    max_portfolio_heat: float
    remaining_capacity: float
    diversification_score: float
    timestamp: datetime


class SignalResponse(BaseModel):
    """Trading signal."""
    symbol: str
    strategy: str
    direction: str
    confidence: float
    entry_price: float
    stop_loss: float
    target: float
    position_size_pct: float
    risk_reward_ratio: float
    timestamp: datetime
    market_conditions: Optional[Dict] = None


class StrategyInfo(BaseModel):
    """Strategy information."""
    name: str
    enabled: bool
    description: str
    parameters: Dict[str, any]
    total_signals: int
    win_rate: Optional[float] = None


class StrategyPerformance(BaseModel):
    """Strategy performance metrics."""
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: float
    total_pnl: float
    avg_holding_period: float


class MarketPsychologyResponse(BaseModel):
    """Market psychology indicators."""
    vix: Optional[float] = None
    put_call_ratio: Optional[float] = None
    fii_flows: Optional[float] = None
    sentiment: str  # 'fearful', 'neutral', 'greedy'
    recommendation: str
    timestamp: datetime


class CorrelationPair(BaseModel):
    """Correlation between two symbols."""
    symbol1: str
    symbol2: str
    correlation: float


class CorrelationResponse(BaseModel):
    """Correlation analysis."""
    high_correlations: List[CorrelationPair]
    clusters: Dict[str, List[str]]
    diversification_score: float
    timestamp: datetime


class ScreeningRequest(BaseModel):
    """Screening request."""
    symbols: List[str] = Field(..., min_items=1)
    strategies: List[str] = Field(default_factory=list)
    account_value: float = Field(100000000, gt=0)  # 1억원 default


class ScreeningResult(BaseModel):
    """Screening result."""
    signals: List[SignalResponse]
    screened_symbols: int
    signals_generated: int
    top_opportunities: List[SignalResponse]
    timestamp: datetime


class BacktestResult(BaseModel):
    """Backtest result."""
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    total_trades: int
    win_rate: float
    profit_factor: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[Dict]


class IndicatorSummary(BaseModel):
    """Technical indicator summary."""
    symbol: str
    timestamp: datetime
    close_price: float
    adx: float
    rsi14: float
    rsi2: float
    atr: float
    atr_percent: float
    trend: str  # 'uptrend', 'downtrend', 'sideways'
    volatility: str  # 'low', 'normal', 'high'
