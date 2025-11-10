"""Business logic services for API endpoints."""
from typing import List, Optional, Dict
import datetime as dt
import logging

from src.api import models
from src.risk.position_sizing import PositionSizer
from src.risk.correlation import CorrelationCalculator
from src.features.shared_indicators import SharedIndicatorManager

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service layer for dashboard operations.

    Manages state and coordinates between different components.
    """

    def __init__(self):
        self.position_sizer = PositionSizer()
        self.correlation_calculator = CorrelationCalculator()
        self.indicator_manager = SharedIndicatorManager()

        # In-memory storage (would use database in production)
        self.positions: Dict[str, Dict] = {}
        self.signals_history: List[Dict] = []
        self.performance_cache: Dict[str, Dict] = {}

    def initialize(self):
        """Initialize service on startup."""
        logger.info("Initializing DashboardService")
        # Load any saved state, connect to databases, etc.

    def cleanup(self):
        """Cleanup on shutdown."""
        logger.info("Cleaning up DashboardService")
        # Save state, close connections, etc.

    def get_positions(self) -> List[models.PositionResponse]:
        """Get all current positions."""
        positions = []

        for symbol, pos_data in self.positions.items():
            try:
                position = models.PositionResponse(
                    symbol=symbol,
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data.get('current_price', pos_data['entry_price']),
                    quantity=pos_data['quantity'],
                    direction=pos_data['direction'],
                    entry_date=pos_data['entry_date'],
                    pnl=pos_data.get('pnl', 0.0),
                    pnl_percent=pos_data.get('pnl_percent', 0.0),
                    risk_amount=pos_data['risk_amount'],
                    stop_loss=pos_data['stop_loss'],
                    target=pos_data.get('target'),
                    strategy=pos_data['strategy']
                )
                positions.append(position)
            except Exception as e:
                logger.error(f"Error processing position {symbol}: {e}")

        return positions

    def get_position_detail(self, symbol: str) -> Optional[models.PositionDetail]:
        """Get detailed position information."""
        if symbol not in self.positions:
            return None

        pos_data = self.positions[symbol]

        # Get indicators for symbol
        indicators = self.indicator_manager.get_indicators(symbol)
        indicator_values = {}
        if indicators:
            summary = indicators.get_indicator_summary()
            indicator_values = {
                'adx': summary.get('adx', 0),
                'rsi14': summary.get('rsi14', 0),
                'atr': summary.get('atr', 0)
            }

        detail = models.PositionDetail(
            symbol=symbol,
            entry_price=pos_data['entry_price'],
            current_price=pos_data.get('current_price', pos_data['entry_price']),
            quantity=pos_data['quantity'],
            direction=pos_data['direction'],
            entry_date=pos_data['entry_date'],
            pnl=pos_data.get('pnl', 0.0),
            pnl_percent=pos_data.get('pnl_percent', 0.0),
            risk_amount=pos_data['risk_amount'],
            stop_loss=pos_data['stop_loss'],
            target=pos_data.get('target'),
            strategy=pos_data['strategy'],
            indicators=indicator_values,
            signal_confidence=pos_data.get('confidence', 0.5),
            days_held=(dt.datetime.now() - pos_data['entry_date']).days,
            max_favorable_excursion=pos_data.get('mfe', 0.0),
            max_adverse_excursion=pos_data.get('mae', 0.0)
        )

        return detail

    def get_portfolio_summary(self) -> models.PortfolioSummary:
        """Get portfolio summary with risk metrics."""
        total_value = sum(p['quantity'] * p.get('current_price', p['entry_price'])
                         for p in self.positions.values())
        total_pnl = sum(p.get('pnl', 0.0) for p in self.positions.values())

        portfolio_summary = self.position_sizer.get_portfolio_summary()

        summary = models.PortfolioSummary(
            total_positions=len(self.positions),
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_percent=(total_pnl / total_value * 100) if total_value > 0 else 0.0,
            portfolio_heat=portfolio_summary['total_risk_amount'],
            max_portfolio_heat=self.position_sizer.max_portfolio_heat * 100000,  # Assume 100k account
            remaining_capacity=portfolio_summary['remaining_heat'],
            diversification_score=0.75,  # Would calculate from actual correlations
            timestamp=dt.datetime.now()
        )

        return summary

    def get_signals(
        self,
        strategy: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 20
    ) -> List[models.SignalResponse]:
        """Get recent signals with optional filtering."""
        signals = []

        # Filter signals from history
        for signal_data in self.signals_history[-100:]:  # Last 100 signals
            if strategy and signal_data.get('strategy') != strategy:
                continue
            if min_confidence and signal_data.get('confidence', 0) < min_confidence:
                continue

            try:
                signal = models.SignalResponse(
                    symbol=signal_data['symbol'],
                    strategy=signal_data['strategy'],
                    direction=signal_data['direction'],
                    confidence=signal_data['confidence'],
                    entry_price=signal_data['entry_price'],
                    stop_loss=signal_data['stop_loss'],
                    target=signal_data['target'],
                    position_size_pct=signal_data.get('position_size', 0.02),
                    risk_reward_ratio=signal_data.get('rr_ratio', 2.0),
                    timestamp=signal_data['timestamp'],
                    market_conditions=signal_data.get('market_conditions')
                )
                signals.append(signal)
            except Exception as e:
                logger.error(f"Error processing signal: {e}")

        # Sort by timestamp descending
        signals.sort(key=lambda s: s.timestamp, reverse=True)

        return signals[:limit]

    def get_strategies(self) -> List[models.StrategyInfo]:
        """Get information about all strategies."""
        strategies = [
            models.StrategyInfo(
                name="holy_grail",
                enabled=True,
                description="Linda Raschke's signature pullback strategy in strong trends",
                parameters={"adx_threshold": 30, "pullback_bars": "3-5"},
                total_signals=len([s for s in self.signals_history if s.get('strategy') == 'holy_grail']),
                win_rate=0.58
            ),
            models.StrategyInfo(
                name="turtle_soup",
                enabled=True,
                description="Fade false breakouts with volume confirmation",
                parameters={"lookback": 20, "false_breakout_pct": 0.5},
                total_signals=len([s for s in self.signals_history if s.get('strategy') == 'turtle_soup']),
                win_rate=0.52
            ),
            models.StrategyInfo(
                name="anti_swing",
                enabled=True,
                description="Mean reversion on RSI2 extremes",
                parameters={"rsi2_oversold": 10, "rsi2_overbought": 90},
                total_signals=len([s for s in self.signals_history if s.get('strategy') == 'anti_swing']),
                win_rate=0.65
            ),
            models.StrategyInfo(
                name="volatility_breakout",
                enabled=True,
                description="Trade ATR expansion after contraction",
                parameters={"nr7_required": True, "volume_confirm": True},
                total_signals=len([s for s in self.signals_history if s.get('strategy') == 'volatility_breakout']),
                win_rate=0.55
            ),
            models.StrategyInfo(
                name="gap_fade",
                enabled=True,
                description="Fade large gaps with pullback confirmation",
                parameters={"gap_threshold": 0.02, "pullback_required": True},
                total_signals=len([s for s in self.signals_history if s.get('strategy') == 'gap_fade']),
                win_rate=0.60
            )
        ]

        return strategies

    def get_strategy_performance(self, strategy_name: str) -> Optional[models.StrategyPerformance]:
        """Get performance metrics for a strategy."""
        # Filter trades for this strategy
        strategy_trades = [s for s in self.signals_history if s.get('strategy') == strategy_name]

        if not strategy_trades:
            return None

        # Calculate metrics (simplified)
        total_trades = len(strategy_trades)
        winning_trades = len([t for t in strategy_trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades

        wins = [t['pnl'] for t in strategy_trades if t.get('pnl', 0) > 0]
        losses = [abs(t['pnl']) for t in strategy_trades if t.get('pnl', 0) < 0]

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 1
        profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if losing_trades > 0 else 0

        performance = models.StrategyPerformance(
            strategy_name=strategy_name,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=winning_trades / total_trades if total_trades > 0 else 0,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=None,  # Would calculate with actual returns
            max_drawdown=0.0,  # Would calculate from equity curve
            total_pnl=sum(t.get('pnl', 0) for t in strategy_trades),
            avg_holding_period=5.0  # Days
        )

        return performance

    def get_market_psychology(self) -> models.MarketPsychologyResponse:
        """Get market psychology indicators."""
        # Would fetch from MarketPsychologyLoader
        psychology = models.MarketPsychologyResponse(
            vix=15.5,
            put_call_ratio=0.85,
            fii_flows=1500000000,  # 15억
            sentiment="neutral",
            recommendation="Normal market conditions - follow strategy signals",
            timestamp=dt.datetime.now()
        )

        return psychology

    def get_correlations(self, threshold: float) -> models.CorrelationResponse:
        """Get correlation analysis."""
        # Would use actual correlation data
        pairs = [
            models.CorrelationPair(symbol1='005930', symbol2='000660', correlation=0.75),
            models.CorrelationPair(symbol1='005930', symbol2='035420', correlation=0.82),
        ]

        response = models.CorrelationResponse(
            high_correlations=pairs,
            clusters={
                '005930': ['000660', '035420'],
                '000660': ['005930']
            },
            diversification_score=0.68,
            timestamp=dt.datetime.now()
        )

        return response

    async def run_screening(self, request: models.ScreeningRequest) -> models.ScreeningResult:
        """Run multi-strategy screening."""
        # Would use actual LindaScreener
        logger.info(f"Running screening on {len(request.symbols)} symbols")

        # Mock result
        result = models.ScreeningResult(
            signals=[],
            screened_symbols=len(request.symbols),
            signals_generated=0,
            top_opportunities=[],
            timestamp=dt.datetime.now()
        )

        return result

    async def run_backtest(
        self,
        strategy_name: str,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> models.BacktestResult:
        """Run backtest for a strategy."""
        # Would use actual backtesting engine
        logger.info(f"Running backtest: {strategy_name} on {symbol}")

        result = models.BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_trades=25,
            win_rate=0.60,
            profit_factor=1.8,
            total_return=0.15,
            sharpe_ratio=1.2,
            max_drawdown=-0.08,
            trades=[]
        )

        return result

    def get_indicators(self, symbol: str) -> Optional[models.IndicatorSummary]:
        """Get technical indicators for a symbol."""
        indicators = self.indicator_manager.get_indicators(symbol)

        if not indicators:
            return None

        summary_dict = indicators.get_indicator_summary()

        indicator_summary = models.IndicatorSummary(
            symbol=symbol,
            timestamp=dt.datetime.now(),
            close_price=summary_dict.get('close', 0.0),
            adx=summary_dict.get('adx', 0.0),
            rsi14=summary_dict.get('rsi14', 0.0),
            rsi2=summary_dict.get('rsi2', 0.0),
            atr=summary_dict.get('atr', 0.0),
            atr_percent=summary_dict.get('atr_percent', 0.0),
            trend="uptrend" if summary_dict.get('adx', 0) > 30 else "sideways",
            volatility="normal"
        )

        return indicator_summary
