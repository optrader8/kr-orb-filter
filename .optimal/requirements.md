# requirements.md ? EARS (Easy Approach to Requirements Syntax)

> Legend: **Ubiquitous** (general), **Event?Driven** (When ??, the system shall ??), **State?Driven** (While ??), **Unwanted** (If ??, the system shall prevent ??), **Optional** (Where ??, the system may ??).

## 1. Data Ingestion

* **U**: The system shall ingest **daily OHLCV** for KOSPI/KOSDAQ constituents.
* **U**: The system shall store raw daily data in **SQLite** and export to **Parquet**.
* **E**: When a daily download fails, the system shall **retry** up to 3 times with exponential backoff.
* **U**: The system shall record **data source, timestamp, and checksum** per batch.
* **E**: When symbols are **delisted or halted**, the system shall **exclude** them from screens.

## 2. Feature Engineering

* **U**: The system shall compute **Range = High ? Low** per day.
* **U**: The system shall label **NR7** when today??s Range is the **rolling 7?day minimum**.
* **U**: The system shall compute **Gap% = (Open ? PrevClose) / PrevClose**.
* **U**: The system shall compute **Move?off?Open = |Close ? Open| / Range**.
* **U**: The system shall compute **KOSPI 5/20MA slope** and **sector momentum** as **bias**.
* **O**: Where TA?Lib is installed, the system may compute **ATR(14)** and additional indicators.

## 3. Screening & Ranking

* **U**: The system shall apply **liquidity filter** using **daily trading value ?? MIN\_DAILY\_TRADING\_VALUE**.
* **U**: The system shall produce a **ranked list** combining NR7, Gap, MOO, and bias scores.
* **E**: When no symbols pass filters, the system shall **emit an empty report** and a **warning log**.
* **U**: The system shall persist **screen results** with parameters used.

## 4. Intraday ORB

* **U**: The system shall define the **Opening Range** over a configurable window (e.g., 09:00?09:15 KST).
* **E**: When price **crosses ORB High**, the system shall generate a **Long Breakout** signal.
* **E**: When price **crosses ORB Low**, the system shall generate a **Short Breakout** signal.
* **U**: The system shall **de?duplicate** alerts to prevent repeated notifications for the same symbol/direction.
* **S**: While market is **outside trading hours**, the system shall **suspend** ORB monitoring.
* **U**: The system shall support a **simulation mode** replaying intraday CSV.

## 5. Risk & Trade Rules (Signal Level)

* **U**: The system shall compute **ATR?based stop** = ATR ?? RISK\_ATR\_MULT for evaluation.
* **U**: The system shall evaluate **take?profit** via **Risk\:Reward (RR)** parameter.
* **U**: The system shall limit **MAX\_POSITIONS** concurrently flagged per run.
* **O**: Where sector correlation is high, the system may **throttle** multi?hits in the same sector.
* **U**: The system shall log **entry time, breakout price, stops/targets** for each signal.

## 6. Backtesting

* **U**: The system shall provide **vectorized backtests** for ORB/NR7 strategies.
* **U**: The system shall output **PnL, WinRate, AvgTrade, MDD, Sharpe, Exposure**.
* **E**: When parameters are invalid, the system shall **reject** the run with descriptive errors.
* **U**: The system shall allow **universe selection** (e.g., KOSPI200) and **date range**.
* **O**: Where fees/slippage are provided, the system may **apply** them to trades.

## 7. Notifications

* **U**: The system shall support **Slack webhook** and **Telegram bot** notifications.
* **E**: When an alert is sent, the system shall **record** status (success/failure, response code).
* **U**: The system shall implement **cooldown** per symbol to avoid spam.
* **U**: The system shall allow **message templates** including symbol, time, price, ORB metrics.

## 8. Configuration & Ops

* **U**: The system shall read configuration from **.env** and **config.py**.
* **U**: The system shall provide **CLI** commands: `screener`, `monitor`, `backtest`, `alert`.
* **U**: The system shall provide **logs** with **ISO timestamps** and **levels**.
* **E**: When an unrecoverable error occurs, the system shall **exit non?zero** and write a **crash report**.
* **S**: While network connectivity is lost, the system shall **queue** alerts and **flush** upon recovery.

## 9. Compliance & Safety

* **U**: The system shall not place trades; it shall produce **signals/alerts** only (MVP).
* **U**: The system shall include a **disclaimer** about financial risk.
* **U**: The system shall avoid storing **credentials** in code; secrets must be in env or key vaults.

## 10. Quality Targets

* **U**: The system shall run the **daily screen ?? 2 minutes** on a commodity laptop for 2,000 symbols.
* **U**: The system shall achieve **deterministic backtests** given fixed inputs and seed.
* **O**: Where Docker is available, the system may provide a **containerized** deployment recipe.

## 11. Dependency Notes

* **U**: The codebase shall rely on `pandas`, `numpy`, `pyarrow`, and `pydantic` for core data handling.
* **U**: Notification integrations shall use `requests` with timeouts configured.
* **O**: Optional providers such as `pykrx` may be installed to enable live data ingestion; otherwise the CSV fallback must remain operational.