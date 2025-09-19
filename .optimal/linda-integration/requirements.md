# requirements.md – EARS (Easy Approach to Requirements Syntax)
# Linda Raschke Trading Strategies Integration

> Legend: **Ubiquitous** (general), **Event‐Driven** (When ??, the system shall ??), **State‐Driven** (While ??), **Unwanted** (If ??, the system shall prevent ??), **Optional** (Where ??, the system may ??).

## 1. Holy Grail Setup (HG) Integration

* **U**: The system shall compute **ADX(14)** and **±DI** indicators for trend strength assessment.
* **U**: The system shall identify **strong trends** when ADX > 30.
* **S**: While ADX < 20, the system shall **avoid breakout strategies** and **prefer mean reversion**.
* **U**: The system shall detect **pullbacks** lasting 3-5 bars in trending markets.
* **E**: When +DI > -DI and ADX > 30, the system shall **prioritize long setups**.
* **E**: When -DI > +DI and ADX > 30, the system shall **prioritize short setups**.
* **U**: The system shall compute **RSI(2)** for momentum divergence detection.
* **E**: When RSI shows oversold/overbought during pullback, the system shall **flag Holy Grail candidate**.

## 2. Turtle Soup Strategy

* **U**: The system shall track **20-day rolling highs and lows** for each symbol.
* **E**: When price breaks above 20-day high but **closes below**, the system shall **flag failed breakout**.
* **E**: When next day price trades **below previous day's low** after failed breakout, the system shall **generate short signal**.
* **E**: When price breaks below 20-day low but **closes above**, the system shall **flag failed breakdown**.
* **E**: When next day price trades **above previous day's high** after failed breakdown, the system shall **generate long signal**.
* **U**: The system shall set **stop loss beyond failed breakout level**.

## 3. Anti-Swing Setup

* **U**: The system shall compute **2-day RSI** for counter-trend identification.
* **E**: When 2-day RSI < 10 after 2-3 days strong decline, the system shall **flag oversold bounce candidate**.
* **E**: When 2-day RSI > 90 after 2-3 days strong rally, the system shall **flag overbought fade candidate**.
* **U**: The system shall compute **Stochastic %K and %D** for entry timing.
* **E**: When Stochastic %K crosses above %D in oversold, the system shall **confirm long entry**.
* **E**: When Stochastic %K crosses below %D in overbought, the system shall **confirm short entry**.
* **U**: The system shall target **return to 5-period moving average**.

## 4. Enhanced Opening Range Breakout (Linda's Version)

* **U**: The system shall extend ORB window to **first 30 minutes** (09:00-09:30 KST).
* **U**: The system shall compute **20-day average volume** for volume filter.
* **E**: When ORB breakout occurs with **volume > 20-day average**, the system shall **prioritize signal**.
* **U**: The system shall classify gaps as **small (<1%), medium (1-2%), large (>2%)**.
* **E**: When gap is small (<1%) and breakout occurs, the system shall **favor continuation**.
* **E**: When gap is large (>2%) against trend, the system shall **consider gap fade**.
* **U**: The system shall align ORB signals with **KOSPI index direction**.
* **U**: The system shall set risk at **1.5 × opening range** or previous day's high/low.

## 5. Moving Average Integration

* **U**: The system shall compute **20 EMA and 50 EMA** for crossover signals.
* **E**: When 20 EMA crosses above 50 EMA with volume expansion, the system shall **generate long bias**.
* **E**: When 20 EMA crosses below 50 EMA, the system shall **generate short bias**.
* **U**: The system shall compute **3-period moving average** for short-term entries.
* **E**: When price is above 3-period MA in uptrend, the system shall **confirm long entry**.
* **U**: The system shall set **tight stops 2-3 points below 3-period MA**.

## 6. Risk Management Framework

* **U**: The system shall implement **2% rule**: never risk more than 2% of account per trade.
* **U**: The system shall limit **total portfolio heat** to 6-8% across all open positions.
* **U**: The system shall **reduce position size** when trading correlated instruments.
* **U**: The system shall implement **volatility stops** at 1.5-2 × ATR.
* **U**: The system shall implement **time stops** for positions showing no movement.
* **E**: When stop loss is hit, the system shall **immediately close position**.

## 7. Profit Taking Strategy

* **U**: The system shall implement **scale-out strategy**: 1/3 at 1:1, 1/3 at 2:1, trail final 1/3.
* **U**: The system shall identify **target zones** at previous highs/lows and round numbers.
* **E**: When position reaches 1:1 R:R, the system shall **move stop to breakeven**.
* **U**: The system shall trail stops by **ATR distance** for remaining position.

## 8. Market Psychology Integration

* **U**: The system shall monitor **VIX equivalent** (KOSPI200 volatility) for sentiment.
* **U**: The system shall track **put/call ratios** for contrarian signals.
* **E**: When sentiment indicators show **extreme readings**, the system shall **flag reversal potential**.
* **U**: The system shall identify **optimal trading times**: 10:30-11:30 and 14:30-15:30 KST.
* **U**: The system shall account for **end-of-month/quarter rebalancing** effects.

## 9. Volatility Breakout Enhancement

* **U**: The system shall compute **5-day ATR** for volatility contraction/expansion.
* **E**: When 5-day ATR expands after contraction, the system shall **prioritize breakout signals**.
* **E**: When narrow range (NR7) coincides with ATR expansion, the system shall **increase signal weight**.
* **U**: The system shall target **2-3 × narrow range measurement** for breakouts.

## 10. Gap Fade Strategy

* **U**: The system shall identify **large gaps >2%** opposite to overall trend.
* **E**: When price fills **50% of gap**, the system shall **enter fade direction**.
* **U**: The system shall set risk **beyond gap extreme**.
* **E**: When gap fade occurs in **strong trending stock**, the system shall **prioritize signal**.

## 11. Korean Market Adaptations

* **U**: The system shall adjust for **Korean market hours** (09:00-15:30 KST).
* **U**: The system shall monitor **US market close impact** on Korean gap patterns.
* **U**: The system shall focus on **semiconductor, shipbuilding, biotech cycles**.
* **U**: The system shall track **Foreign Institutional Investor (FII) flows**.
* **O**: Where **KOSPI200 futures** data is available, the system may use for broad market exposure.

## 12. Performance Metrics Integration

* **U**: The system shall target **60-65% win rate** for trend following strategies.
* **U**: The system shall target **40-45% win rate** for mean reversion strategies.
* **U**: The system shall maintain **minimum 1:1.5 risk/reward** across all trades.
* **U**: The system shall limit **maximum drawdown** to 15-20% of peak equity.
* **U**: The system shall target **Sharpe ratio >1.5** for risk-adjusted returns.

## 13. Trade Management Workflow

* **U**: The system shall perform **pre-market analysis**: overnight news, futures, foreign markets.
* **U**: The system shall scan for **ADX, volume, and pattern criteria** before market open.
* **U**: The system shall determine **market bias** using index analysis.
* **E**: During trading session, the system shall **monitor gaps, volume, and ORB formation**.
* **E**: When HG, Turtle Soup, or Anti-Swing setup appears, the system shall **generate alerts**.
* **U**: The system shall log **entry reason, exit reason, and lessons learned**.

## 14. Configuration & Safety

* **U**: The system shall allow **strategy parameter adjustment** for changing volatility regimes.
* **E**: When market conditions are **unfavorable**, the system shall **recommend standing aside**.
* **U**: The system shall **scale position size** based on market environment.
* **U**: The system shall maintain **detailed strategy performance logs**.
* **U**: The system shall provide **educational disclaimers** about trading risks.

## 15. Quality Targets

* **U**: The system shall process **Linda strategy signals ≤ 5 minutes** for 2,000 symbols.
* **U**: The system shall provide **deterministic backtests** for Linda strategies.
* **U**: The system shall achieve **≥95% uptime** during market hours.
* **O**: Where advanced charting is needed, the system may integrate with **professional platforms**.