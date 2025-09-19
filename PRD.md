# PRD.md ? KR?ORB?Filter

## 1. Goal & Non?Goals

**Goal**: Korean equities screener + intraday ORB breakout alerting with backtests, to operationalize Crabel?style short?term opportunity detection.
**Non?Goals**: Full broker execution platform; portfolio optimizer; exotic derivatives integrations.

## 2. Personas

* **Discretionary Trader (D?T)**: Wants curated daily list + timely intraday alerts.
* **Quant Tinkerer (Q?T)**: Needs editable code, reproducible backtests, CSV exports.
* **Risk?Aware PM (R?PM)**: Focus on stability, risk metrics, audit logs.

## 3. Use Cases

1. Daily open plan: NR7 candidates with scores & liquidity filters.
2. Intraday watch: ORB windows, gap bias; push alerts on valid breakouts.
3. Post?session review: EOD signals, hit?rate, exceptions.
4. Research: Parameter sweep, universes (KOSPI200, thematics), factors.

## 4. Scope

* **MVP**

  * Data: pykrx daily; intraday via simulated replay (CSV) + simple adapter
  * Features: NR7, ORB, Gap, MOO, KOSPI/sector bias
  * Screener + ranker; backtest engine; Slack/Telegram alerts
  * Storage: SQLite; exports (CSV/Parquet)
* **Phase 2**

  * Live intraday via broker APIs; dashboard (FastAPI + simple UI)
  * Multi?universe & sector models; advanced risk (vol targeting)
* **Phase 3**

  * Portfolio rules; execution hooks; Postgres; Docker deploy

## 5. KPIs

* Coverage: �� 90% of KOSPI200, top?liquidity KOSDAQ
* Alert Latency: �� 5s from breakout detection (sim/live)
* Data Freshness: Daily EOD by 18:00 KST
* System Reliability: 99% uptime during market hours (MVP target: 97%)
* Backtest Reproducibility: Same seed �� identical results

## 6. Functional Requirements (high level)

* Import daily OHLCV; compute NR7 & bias; output ranked list.
* Intraday: compute ORB window; detect first valid breakout; de?dupe alerts.
* Risk checks: liquidity, price bands, exclude halts/special treatments.
* Backtests: vectorized, paramizable; output metrics & trade logs.
* Notifications: Slack/Telegram; throttle & cooldown per symbol.
* Configuration via `.env` & `config.py`.

## 7. Non?Functional Requirements

* **Performance**: Daily screen �� 2 min for 2,000+ symbols on laptop.
* **Reliability**: Retry data sources, failover to cache.
* **Observability**: Structured logs; alert send result codes.
* **Security**: Secrets in env; minimal scopes; no PII.
* **Portability**: Linux/Windows dev; Dockerfile in Phase 3.

## 8. Architecture (MVP)

```
            +-------------------+
            |   CLI / API       |
            +---------+---------+
                      |
           +----------v----------+
           |  Screener (daily)   |<---+   Bias (KOSPI/sector)
           +----------+----------+    |
                      |               |
             +--------v--------+      |
             |  Feature Calc   |------+
             +--------+--------+
                      |
           +----------v----------+
           |    Data Loaders     |  (pykrx / CSV / broker adapter)
           +----------+----------+
                      |
             +--------v--------+
             |   Storage DB    |  SQLite / Parquet
             +--------+--------+
                      |
           +----------v----------+
           |  Backtest Engine    |
           +----------+----------+
                      |
             +--------v--------+
             |  Notifiers      |
             +-----------------+
```

## 9. Risks & Mitigations

* **Intraday data quality / latency** �� Start with replay/sim; broker adapter behind feature flag.
* **False breakouts** �� Require confirm filters (min volume since open, bias alignment).
* **Overfitting** �� Cross?validation by regime; out?of?sample tests.
* **Costs** �� Include fees/slippage in backtests; add realistic order sizing.

## 10. Milestones

* **M0 (Week 1)**: Repo scaffold, loaders (daily), NR7 feature, basic screener.
* **M1 (Week 2)**: ORB calc + simulated intraday; Slack alerts.
* **M2 (Week 3)**: Backtest engine + metrics; CLI UX & docs.
* **M3 (Week 4)**: Bias filters; ranking model; Telegram; stability pass.
* **M4 (Phase 2)**: Live intraday adapter; FastAPI dashboard.

---

