"""FastAPI main application for KR-ORB-Filter web dashboard."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict
import datetime as dt
import logging

from src.api import models, services
from src.config import get_config_manager

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="KR-ORB-Filter Dashboard",
    description="Real-time monitoring and analysis dashboard for Korean equity trading strategies",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
config_manager = get_config_manager()
dashboard_service = services.DashboardService()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard homepage."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KR-ORB-Filter Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .api-link {
                display: inline-block;
                margin: 10px 10px 10px 0;
                padding: 10px 20px;
                background: #0066cc;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            .api-link:hover {
                background: #0052a3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 KR-ORB-Filter Dashboard</h1>
            <p>Welcome to the Korean equity trading system dashboard.</p>

            <h2>Quick Links</h2>
            <a href="/docs" class="api-link">📚 API Documentation</a>
            <a href="/api/v1/health" class="api-link">💚 Health Check</a>
            <a href="/api/v1/positions" class="api-link">💼 Positions</a>
            <a href="/api/v1/strategies" class="api-link">📊 Strategies</a>

            <h2>Features</h2>
            <ul>
                <li>Real-time position monitoring</li>
                <li>Multi-strategy signal analysis (5 Linda Raschke strategies)</li>
                <li>Portfolio risk management (2% rule + portfolio heat)</li>
                <li>Performance analytics and backtesting</li>
                <li>Correlation analysis for diversification</li>
            </ul>
        </div>
    </body>
    </html>
    """


@app.get("/api/v1/health", response_model=models.HealthResponse)
async def health_check():
    """Health check endpoint."""
    return models.HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=dt.datetime.now()
    )


@app.get("/api/v1/positions", response_model=List[models.PositionResponse])
async def get_positions():
    """
    Get current open positions.

    Returns list of all open positions with risk metrics.
    """
    try:
        positions = dashboard_service.get_positions()
        return positions
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/positions/{symbol}", response_model=models.PositionDetail)
async def get_position_detail(symbol: str):
    """
    Get detailed information for a specific position.

    Args:
        symbol: Trading symbol (e.g., '005930')
    """
    try:
        position = dashboard_service.get_position_detail(symbol)
        if not position:
            raise HTTPException(status_code=404, detail=f"Position {symbol} not found")
        return position
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position detail for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/portfolio/summary", response_model=models.PortfolioSummary)
async def get_portfolio_summary():
    """
    Get portfolio summary with risk metrics.

    Includes total positions, portfolio heat, and risk allocation.
    """
    try:
        summary = dashboard_service.get_portfolio_summary()
        return summary
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/signals", response_model=List[models.SignalResponse])
async def get_signals(
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of signals")
):
    """
    Get recent trading signals from all strategies.

    Query parameters:
    - strategy: Filter by strategy name (holy_grail, turtle_soup, etc.)
    - min_confidence: Minimum confidence threshold (0-1)
    - limit: Maximum number of signals to return
    """
    try:
        signals = dashboard_service.get_signals(
            strategy=strategy,
            min_confidence=min_confidence,
            limit=limit
        )
        return signals
    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/strategies", response_model=List[models.StrategyInfo])
async def get_strategies():
    """
    Get information about all available strategies.

    Returns configuration and status for each Linda Raschke strategy.
    """
    try:
        strategies = dashboard_service.get_strategies()
        return strategies
    except Exception as e:
        logger.error(f"Error fetching strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/strategies/{strategy_name}/performance", response_model=models.StrategyPerformance)
async def get_strategy_performance(strategy_name: str):
    """
    Get performance metrics for a specific strategy.

    Args:
        strategy_name: Strategy identifier (holy_grail, turtle_soup, etc.)
    """
    try:
        performance = dashboard_service.get_strategy_performance(strategy_name)
        if not performance:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_name} not found")
        return performance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/market/psychology", response_model=models.MarketPsychologyResponse)
async def get_market_psychology():
    """
    Get current market psychology indicators.

    Includes VIX, Put/Call ratio, FII flows, and sentiment metrics.
    """
    try:
        psychology = dashboard_service.get_market_psychology()
        return psychology
    except Exception as e:
        logger.error(f"Error fetching market psychology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/correlations", response_model=models.CorrelationResponse)
async def get_correlations(
    threshold: float = Query(0.7, ge=0, le=1, description="Correlation threshold")
):
    """
    Get correlation analysis for current positions.

    Query parameters:
    - threshold: Minimum correlation to report (0-1)
    """
    try:
        correlations = dashboard_service.get_correlations(threshold)
        return correlations
    except Exception as e:
        logger.error(f"Error fetching correlations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/screen", response_model=models.ScreeningResult)
async def run_screening(request: models.ScreeningRequest):
    """
    Run multi-strategy screening on specified symbols.

    Request body:
    - symbols: List of trading symbols to screen
    - strategies: List of strategies to use (empty = all)
    - account_value: Total account value for position sizing
    """
    try:
        result = await dashboard_service.run_screening(request)
        return result
    except Exception as e:
        logger.error(f"Error running screening: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/backtest/{strategy_name}", response_model=models.BacktestResult)
async def run_backtest(
    strategy_name: str,
    symbol: str = Query(..., description="Trading symbol"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """
    Run backtest for a strategy on a specific symbol.

    Args:
        strategy_name: Strategy to backtest
        symbol: Trading symbol
        start_date: Backtest start date
        end_date: Backtest end date
    """
    try:
        result = await dashboard_service.run_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        return result
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/indicators/{symbol}", response_model=models.IndicatorSummary)
async def get_indicators(symbol: str):
    """
    Get current technical indicators for a symbol.

    Args:
        symbol: Trading symbol
    """
    try:
        indicators = dashboard_service.get_indicators(symbol)
        if not indicators:
            raise HTTPException(status_code=404, detail=f"No data for symbol {symbol}")
        return indicators
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching indicators for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting KR-ORB-Filter Dashboard API")
    try:
        dashboard_service.initialize()
        logger.info("Dashboard service initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down KR-ORB-Filter Dashboard API")
    try:
        dashboard_service.cleanup()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
