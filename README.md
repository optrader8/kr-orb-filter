# KR·ORB·Filter

**Toby Crabel** 스타일의 **NR7**, **변동성 수축 → 확장**, **Opening Range Breakout (ORB)** 신호를 사용하여 **한국 주식(KOSPI/KOSDAQ)**을 스크리닝하는 Python 시스템입니다. 일일 스크리너, 장중 ORB 모니터, 백테스터, 알림 기능(Slack/Telegram)을 포함합니다.

> 참고: 이 프로젝트는 한국 표준시(KST, Asia/Seoul)와 정규 장 시간(09:00–15:30)을 기준으로 합니다. 선물/연장 세션 사용 시 시간을 조정하세요.

---

## 🔍 주요 기능

* **일일 스크리너**: NR7 / 좁은 범위 패턴 감지 + 유동성 필터
* **장중 ORB 모니터**: 시가 범위(설정 가능: 예. 09:00–09:15) 계산 및 실시간 돌파 추적
* **신호 & 스코어링**: NR7, 갭 바이어스, 시가 대비 움직임, 시장/섹터 바이어스를 단일 점수로 결합
* **백테스팅**: ORB/NR7에 대한 간단한 벡터화된 백테스트 (ATR 기반 리스크)
* **알림**: 필터를 통과한 ORB 돌파에 대한 Slack/Telegram 알림
* **저장소**: 플러그형 영속성 (기본값: SQLite). Postgres 옵션

---

## 🛠️ 기술 스택

* **Python 3.11+**
* **데이터**: `pykrx` (일일), 장중용 브로커 API 또는 웹소켓; CSV/Parquet 가져오기 지원
* **핵심**: `pandas`, `numpy`, `TA-Lib` (선택), `pydantic`, `sqlalchemy`
* **스케줄링**: `APScheduler`
* **API**: 대시보드 & 웹훅용 `FastAPI` (선택)
* **알림**: Slack Webhook / Telegram Bot API

---

## 📁 저장소 구조

```
kr-orb-filter/
├── src/
│  ├── config.py              # env, constants
│  ├── data/
│  │  ├── loaders.py          # pykrx, CSV, broker API adapters
│  │  ├── intraday.py         # ORB window, real-time handlers
│  ├── features/
│  │  ├── nr7.py              # NR7, narrow-range features
│  │  ├── orb.py              # opening range calc, breakout logic
│  │  ├── bias.py             # market/sector bias, gaps, move-off-open
│  ├── screen/
│  │  ├── screener.py         # daily screening & ranking
│  │  ├── filters.py          # liquidity, price bands, exclusions
│  ├── backtest/
│  │  ├── engine.py           # vectorized backtests
│  │  ├── metrics.py          # PnL, winrate, MDD, Sharpe
│  ├── notify/
│  │  ├── slack.py            # Slack integration
│  │  ├── telegram.py         # Telegram integration
│  ├── store/
│  │  ├── db.py               # SQLite/Postgres ORM models
│  │  ├── io.py               # parquet/csv snapshots
│  ├── cli.py                 # CLI entrypoints
│  ├── app.py                 # FastAPI (optional)
├── notebooks/
│  ├── EDA.ipynb
│  ├── backtest_examples.ipynb
├── .env.example
├── README.md
├── PRD.md
├── requirements.md           # EARS
```

---

## ⚙️ 설정

`.env.example`에서 `.env` 파일을 생성하세요:

```
TZ=Asia/Seoul
DATA_PROVIDER=pykrx
INTRADAY_PROVIDER=dummy   # or your broker adapter key
MIN_DAILY_TRADING_VALUE=5000000000  # 50억 KRW
ORB_WINDOW_MIN=15         # 5|15|30
RISK_ATR_MULT=1.0
TAKE_PROFIT_RR=2.0
MAX_POSITIONS=10
SLACK_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DB_URL=sqlite:///./kr_orb.db
```

전략 튜닝 (`config.py`에서):

```python
ORB_WINDOW = ("09:00", "09:15")
NR_WINDOW = 7
GAP_THRESHOLD = 0.5 / 100  # 0.5%
LIQUIDITY_MIN_VALUE = 5e9  # 50억
RISK_ATR_MULT = 1.0
TAKE_PROFIT_RR = 2.0
TIME_EXIT_MIN = 240        # 4h; or use EOD
```

---

## 🚀 빠른 시작

```bash
# 1) 가상환경 생성
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# 2) 설치
pip install -U pip wheel
pip install -r requirements.txt

# 3) 환경설정
cp .env.example .env && edit .env

# 4) 일일 스크리너 실행
python -m src.cli screener daily

# 5) 장중 ORB 모니터 실행 (시뮬레이션 / 실제)
python -m src.cli monitor --provider intraday --simulate

# 6) 백테스트 예제
python -m src.cli backtest --strategy orb_nr7 --universe KOSPI200
```

---

## 📊 신호 (요약)

* **NR7**: `range_t = high_t - low_t`가 7일 롤링 최소값과 같음
* **갭**: `(open_t - close_{t-1}) / close_{t-1}`이 임계값을 초과
* **시가 대비 움직임 (MOO)**: `abs(close_t - open_t) / range_t`
* **ORB 돌파**: 장중 가격이 윈도우 후 ORB 고점/저점을 돌파
* **바이어스 필터**: KOSPI 5/20MA 기울기; 섹터 모멘텀

결합 스코어링 예제 (의사코드):

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

## 📈 백테스팅

최소 예제:

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

PnL, 승률, 평균거래, MDD, 샤프, 노출도를 출력합니다.

---

## 🔔 알림

* Slack: 수신 웹훅
* Telegram: 봇 토큰 + 채팅 ID

```bash
python -m src.cli alert test
```

---

## 📝 참고사항 및 면책조항

* 시장은 변합니다. **백테스트 ≠ 미래 결과.** 수수료, 슬리피지, 세금을 포함하세요.
* 브로커 및 현지 규정 준수를 확인하세요.

---

## 💡 한국어 요약

* 이 프로젝트는 **NR7 + ORB 신호 + 시장성 필터 + 바이어스** 조합으로 한국 주식 스크리닝을 자동화하고, 실시간 모니터 및 **알림**을 제공합니다. 백테스트/튜닝을 통해 자신에게 맞는 파라미터를 찾아 보세요.

---