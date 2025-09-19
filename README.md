# README.md ? KR?ORB?Filter

A Python system to screen **Korean equities (KOSPI/KOSDAQ)** using **Toby Crabel** style signals: **NR7**, **volatility contraction �� expansion**, and **Opening Range Breakout (ORB)**. Includes daily screener, intraday ORB monitor, backtester, and alerting (Slack/Telegram).

> Note: This project targets Korea Standard Time (KST, Asia/Seoul) and standard market hours (09:00?15:30). Adjust times if using futures/extended sessions.

---

## ? Features

* **Daily Screener**: Detect NR7 / narrow-range patterns + liquidity filters.
* **Intraday ORB Monitor**: Computes opening range (configurable: e.g., 09:00?09:15) and tracks breakouts in real time.
* **Signals & Scoring**: Combines NR7, gap bias, move?off?open, market/sectors bias into a single score.
* **Backtesting**: Simple vectorized backtests for ORB/NR7 with ATR?based risk.
* **Alerts**: Slack/Telegram notifications on ORB breakouts passing filters.
* **Storage**: Pluggable persistence (SQLite by default). Optional Postgres.

---

## ?? Tech Stack

* **Python 3.11+**
* **Data**: `pykrx` (daily), broker APIs or websockets for intraday; fallback CSV/Parquet import.
* **Core**: `pandas`, `numpy`, `TA?Lib` (optional), `pydantic`, `sqlalchemy`
* **Scheduling**: `APScheduler`
* **API**: `FastAPI` for dashboards & webhooks (optional)
* **Alerts**: Slack Webhook / Telegram Bot API

---

## ?? Repository Layout

```
kr-orb-filter/
���� src/
��  ���� config.py              # env, constants
��  ���� data/
��  ��  ���� loaders.py          # pykrx, CSV, broker API adapters
��  ��  ���� intraday.py         # ORB window, real-time handlers
��  ���� features/
��  ��  ���� nr7.py              # NR7, narrow-range features
��  ��  ���� orb.py              # opening range calc, breakout logic
��  ��  ���� bias.py             # market/sector bias, gaps, move-off-open
��  ���� screen/
��  ��  ���� screener.py         # daily screening & ranking
��  ��  ���� filters.py          # liquidity, price bands, exclusions
��  ���� backtest/
��  ��  ���� engine.py           # vectorized backtests
��  ��  ���� metrics.py          # PnL, winrate, MDD, Sharpe
��  ���� notify/
��  ��  ���� slack.py            # Slack integration
��  ��  ���� telegram.py         # Telegram integration
��  ���� store/
��  ��  ���� db.py               # SQLite/Postgres ORM models
��  ��  ���� io.py               # parquet/csv snapshots
��  ���� cli.py                 # CLI entrypoints
��  ���� app.py                 # FastAPI (optional)
���� notebooks/
��  ���� EDA.ipynb
��  ���� backtest_examples.ipynb
���� .env.example
���� README.md
���� PRD.md
���� requirements.md           # EARS
```

---

## ?? Configuration

Create `.env` from `.env.example`:

```
TZ=Asia/Seoul
DATA_PROVIDER=pykrx
INTRADAY_PROVIDER=dummy   # or your broker adapter key
MIN_DAILY_TRADING_VALUE=5000000000  # 50�� KRW
ORB_WINDOW_MIN=15         # 5|15|30
RISK_ATR_MULT=1.0
TAKE_PROFIT_RR=2.0
MAX_POSITIONS=10
SLACK_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DB_URL=sqlite:///./kr_orb.db
```

Strategy tuning (in `config.py`):

```python
ORB_WINDOW = ("09:00", "09:15")
NR_WINDOW = 7
GAP_THRESHOLD = 0.5 / 100  # 0.5%
LIQUIDITY_MIN_VALUE = 5e9  # 50��
RISK_ATR_MULT = 1.0
TAKE_PROFIT_RR = 2.0
TIME_EXIT_MIN = 240        # 4h; or use EOD
```

---

## ?? Quickstart

```bash
# 1) create venv
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# 2) install
pip install -U pip wheel
pip install -r requirements.txt

# 3) env
cp .env.example .env && edit .env

# 4) run daily screener
python -m src.cli screener daily

# 5) run intraday ORB monitor (sim / real)
python -m src.cli monitor --provider intraday --simulate

# 6) backtest examples
python -m src.cli backtest --strategy orb_nr7 --universe KOSPI200
```

---

## ?? Signals (Summary)

* **NR7**: `range_t = high_t - low_t` equals rolling 7?day minimum
* **Gap**: `(open_t - close_{t-1}) / close_{t-1}` exceeds ��threshold
* **Move?off?Open (MOO)**: `abs(close_t - open_t) / range_t`
* **ORB Breakout**: intraday price crosses ORB high/low after the window
* **Bias Filters**: KOSPI 5/20MA slope; sector momentum

Combined scoring example (pseudocode):

```python
score = 0
if nr7: score += 2
if gap > +GAP_THRESHOLD: score += 1
if moo > 0.6: score += 1
if kospi_trend_up: score += 1
if sector_momentum_up: score += 1
return score
```

---

## ?? Backtesting

Minimal example:

```python
from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize

res = run_backtest(
    universe="KOSPI200",
    strategy="orb_nr7",
    start="2016-01-01",
    end="2025-09-01",
    params={"orb_min": 15, "atr_mult": 1.0, "rr": 2.0}
)
print(summarize(res))
```

Outputs PnL, WinRate, AvgTrade, MDD, Sharpe, Exposure.

---

## ?? Alerts

* Slack: incoming webhook
* Telegram: bot token + chat ID

```bash
python -m src.cli alert test
```

---

## ?? Notes & Disclaimers

* Markets change. **Backtest �� Future results.** Include fees, slippage, and tax.
* Confirm compliance with your broker and local regulations.

---

## ???? �ѱ��� ���

* �� ������Ʈ�� **NR7 + ORB ���� + ������ ���� + ���̾** �������� �ѱ� �ֽ� �ĺ��� �����ϰ�, �ǽð� ���� �� **�˸�**�� �����մϴ�. ���׽�Ʈ/Ʃ���� ���� �ڽſ��� �´� �Ķ���͸� ã�� ���� �����մϴ�.

---

