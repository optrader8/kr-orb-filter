# Toby Crabel Trading Principles

Toby Crabel is a renowned short-term trader and author of *Day Trading with Short-Term Price Patterns & Opening Range Breakout (ORB)*. His research anchors the KR-ORB-Filter project, emphasizing volatility regimes, breakout mechanics, and strict risk controls.

---

## Snapshot

- Founder of Crabel Capital Management, noted for decades of positive performance.
- Specialist in short-term futures and equity index trading.
- Core publication released in 1990 focusing on ORB and price pattern edges.

---

## Core Concepts

### Opening Range Breakout (ORB)
- Define the opening range as the first X minutes after the market opens (commonly 5, 15, or 30 minutes).
- Breakout triggers:
  - **Long** when price clears the ORB high.
  - **Short** when price breaks the ORB low.
- Rationale: the opening captures liquidity, positioning, and directional bias for the session.

### Short-Term Price Patterns
- Study relationships between open, high, low, and close.
- Key filters: move-off-open (MOO), gap magnitude, and inside/outside day structures.
- Patterns confirm whether an ORB signal reflects genuine momentum.

### Volatility Contraction -> Expansion
- Markets cycle between quiet and volatile phases.
- Edge: anticipate expansion following extreme contraction.
- Toolbox: NR7 (narrowest range in seven sessions) and multi-day narrow-range scans.

### NR7 Implementation
- Compute daily range = high - low.
- Tag NR7 when the current range is the smallest of the previous seven days.
- Monitor the next session for a breakout through the NR7 boundaries, ideally aligned with ORB triggers and volume upticks.

### Bias & Context Filters
- Avoid trading signals in isolation.
- Add environmental bias via index trend, sector momentum, macro catalysts, and liquidity screens.
- Improves selectivity and reduces false positives.

### Risk Management
- Stops: opposite ORB boundary or ATR-based multiplier.
- Targets: fixed risk:reward (e.g., 1:2) or session close.
- Position sizing: fixed-fraction or volatility-adjusted exposure; reduce size after drawdowns.
- Discipline: limit trades to the highest-scoring setups.

---

## Trade Workflow
1. **Pre-market**: shortlist instruments showing NR7 or narrow-range clusters.
2. **Opening window**: record high/low for the chosen ORB duration.
3. **Signal check**: confirm breakout aligns with broader bias filters before triggering.
4. **Execution**: enter, apply stop/target rules, and monitor position through the session.
5. **Review**: log trade metrics and update performance dashboards end-of-day.

---

## Strengths vs. Weaknesses

| Strengths                                                   | Weaknesses                                                |
| ----------------------------------------------------------- | --------------------------------------------------------- |
| Quantitative structure limits emotional decisions.          | False breakouts can produce frequent small losses.        |
| Works across equities, futures, and commodities.            | Transaction costs can erode gains in thin instruments.    |
| Exploits recurring contraction/expansion dynamics.          | Underperforms in choppy, directionless regimes.           |
| Clear entry, stop, and exit rules support automation.       | Requires strict discipline; discretionary overrides hurt. |

---

## Applying to Korean Markets
- Set the ORB window for KST (e.g., 09:00-09:15).
- Run NR7 scans on KOSPI/KOSDAQ universes and enforce liquidity thresholds (>= 5e9 KRW).
- Track foreign flow-driven gaps and sector momentum (semiconductor, bio, finance, etc.).
- Combine ORB alerts with KR-ORB-Filter scoring to prioritize tradeable symbols.

---

## References
- Crabel, T. (1990). *Day Trading with Short-Term Price Patterns & Opening Range Breakout*.
- Crabel Capital Management performance disclosures.
- Public write-ups on NR7 and ORB from Quantified Strategies, GFF Brokers, and OxfordStrat.

> DISCLAIMER: Educational summary only. Trading involves risk; past results do not guarantee future performance.