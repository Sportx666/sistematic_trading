# Research standards

Backtests are easy to fool yourself with. These rules apply to every experiment in this repository.

## 1. Specify before you test
Write the strategy spec (`strategies/TEMPLATE.md`) **before** looking at backtest results. That includes the hypothesis, the rules, the parameters and their allowed ranges, and the pass/fail criteria. If you change the spec after seeing results, note the change in the spec's changelog and in the journal.

## 2. No look-ahead bias
- Signals at the close on *t* → fills at the open on *t+1* or later.
- Indicators use only past and current bars (no centred windows, no `shift(-1)` in signal code).
- Universe membership, corporate-action adjustments and fundamental data must be *as known at the time*. Where free data can't guarantee this, say so.
- Test: changing data after *t* must not change any decision made at or before *t*.

## 3. Realistic costs, always on
Commission (including minimum ticket fees, which matter a lot for a €2,000 account), half-spread, slippage, and FX conversion from EUR to USD. Report results gross **and** net, and run a test with costs doubled.

## 4. Out-of-sample discipline
- Split the data into in-sample, validation and a **locked hold-out**. The hold-out is used once, and that use is logged.
- Use walk-forward analysis for any parameter choice.
- Count and log every configuration tried. More trials make a good result more likely to be luck.

## 5. Robustness over peak performance
Prefer parameter plateaus to sharp peaks, and few parameters to many. A strategy that only works with one specific lookback is not a strategy.

## 6. Benchmark everything
Compare against buy-and-hold SPY (and an equal-weight universe benchmark) over the same period, with the same costs where relevant.

## 7. Reproducibility
Every reported result must be traceable to a commit hash, a config, and a data-snapshot identifier. Results that exist only in a notebook don't count.

## 8. Known biases to state explicitly
Survivorship bias (today's tickers), selection bias (universe chosen in hindsight), data-snooping (many trials), and regime dependence (tested mostly on a long bull market).
