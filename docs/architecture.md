# Architecture

The pipeline flows one way. Each stage is a separate sub-package of `systrade` with a narrow interface, so every stage can be tested on synthetic data.

```
 data ──► strategies ──► risk ──► backtest ──► validation
  (M2)       (M3)        (M6)       (M4)          (M5)
                           │
                           └────► paper (M7): same signals and risk checks, forward in time
```

| Stage | Input | Output | Key rule |
|---|---|---|---|
| `data` | provider + symbols + dates | validated OHLCV (raw + adjusted) | signals use adjusted prices; fills and P&L use raw prices plus the action table ([data](data.md)) |
| `strategies` | OHLCV up to day *t* | target signal per symbol at close *t* | pure function; no future data |
| `risk` | signals, portfolio state | sized and approved orders, or rejections | same checks in backtest and paper trading |
| `backtest` | orders, next-day prices, cost model | fills, positions, equity curve, trades | fill at *t+1* open or later; costs always on |
| `validation` | strategy + parameter grid + periods | walk-forward / OOS / robustness reports | locked hold-out; every trial logged |
| `paper` | latest data | order file, simulated ledger, reconciliation | no broker order API |

## Cross-cutting

- `config.py`: programme scope and account defaults (€2,000, EUR base, USD instruments, ≤1% risk per trade, no leverage).
- `safety.py`: live-trading guard. Every runnable entry point calls `assert_paper_only()`.

## Timing convention

All bars are daily. A signal computed from data up to and including the **close of day *t*** may only be filled at the **open of day *t+1*** or later. Every engine and strategy test checks this.
