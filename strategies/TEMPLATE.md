# SPEC-NNN: <Strategy name>

| Field | Value |
|---|---|
| Status | draft |
| Author | |
| Created | YYYY-MM-DD |
| Issue | #n |
| Implementation | `systrade.strategies.<module>` |

## 1. Hypothesis
What market behaviour does this strategy exploit, and why might it persist? (one paragraph)

## 2. Universe
Symbols or selection rule, the date range, and the minimum liquidity filter (e.g. 20-day average dollar volume ≥ $X). Known survivorship/selection biases.

## 3. Data
Provider, which fields are used, and whether signals use adjusted or raw prices. Fills always use raw (unadjusted) prices.

## 4. Signal rules
Exact, unambiguous definitions, written so that two people would implement them identically.
- **Indicators:** (e.g. `SMA_n(close)` = mean of the last *n* closes, including today)
- **Entry:**
- **Exit:**
- **Stop loss:**

## 5. Timing and execution
- Signal computed at: close of day *t*
- Order type and fill: e.g. market-on-open at *t+1* (filled at the *t+1* open plus slippage)
- What happens with gaps through the stop, halts, or missing data

## 6. Position sizing and risk
- Risk per trade (% of equity), and how the stop distance converts it into a number of shares
- Maximum number of positions, maximum weight per position, and the cash buffer
- Minimum position size given commissions

## 7. Parameters
| Name | Default | Allowed range | Rationale |
|---|---|---|---|
| | | | |

Keep this to ≤ 4 free parameters.

## 8. Costs assumed
Commission (fixed / % / minimum), spread, slippage, FX.

## 9. Evaluation plan (pre-registered)
- In-sample period, validation period, locked hold-out period
- Benchmark(s)
- **Pass criteria** (e.g. net Sharpe on the out-of-sample segments > benchmark, max drawdown < X%, ≥ N trades)
- **Reject criteria**

## 10. Known risks and failure modes

## Changelog
| Date | Change | Reason | Seen results before change? |
|---|---|---|---|
