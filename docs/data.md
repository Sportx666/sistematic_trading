# Market data

Daily bars for the starting universe, stored on disk, with splits and dividends kept as their own records. This is milestone M2. Nothing here places an order or runs a backtest.

## Which series to use

Every cached session has two price series and a corporate-action table.

| Series | Fields | Use for |
|---|---|---|
| Raw (as traded) | `open_raw`, `high_raw`, `low_raw`, `close_raw`, `volume_raw` | **Fills and P&L.** These are the prices that printed and the shares that traded. A fill is the raw open of day *t+1* (or later). P&L applies the action table: a split changes the share count, a dividend is cash received. |
| Adjusted | `open_adj`, `high_adj`, `low_adj`, `close_adj`, `volume_adj` | **Signals and indicators.** Backward-adjusted for splits and cash dividends, so a split is not a crash and a dividend is not a price gap. `volume_adj` is split-adjusted only; dividends do not change the share count. |

Do not fill at adjusted prices. An adjusted price is a scaling of history, not a quote.

Adjusted **levels** depend on later corporate actions. The series is anchored so that a bar with no later action keeps its raw OHLC. Adjusted **returns** between two sessions depend only on actions whose ex-date sits inside that window. A return-based signal computed at the close of day *t* does not change if a split or dividend is inserted after *t*. A rule that uses a dollar level ("stop at $100", a moving average in dollars) must not use the adjusted level.

M4 (the backtest) has to follow this contract. M2 only stores the series and checks them.

## Adjustment

Worked from the raw series, newest action first in effect:

1. **Splits.** `amount` is new shares per old share: 4.0 for a 4-for-1, 0.5 for a 1-for-2 reverse. For an ex-date *S*, OHLC on sessions before *S* is divided by that ratio and volume is multiplied by it. The ex-date bar itself is already in post-split units and is left alone.
2. **Cash.** `amount` is cash per share in the same units as the previous session's raw close (the amount that was paid, not a split-adjusted reprint). Splits with an ex-date on or after the cash ex-date rescale that cash into split-adjusted units. Same-day cash amounts are summed first. Let *P* be the split-adjusted close of the last session before the ex-date. OHLC on earlier sessions is multiplied by *(P − cash) / P*. Volume is unchanged.
3. The adjusted return across an ex-date is *P_ex / (P − cash) − 1*. That equals the total return *(P_ex − P + cash) / P* only when the price drops by exactly the cash amount. The difference is the overnight move. This is a backward adjustment, not a total-return index that reinvests the cash.

A dividend greater than or equal to the previous close is rejected. A non-positive split ratio is rejected.

## Provider

`DataProvider.fetch_daily(symbol, start, end)` returns raw bars and actions. `start` is inclusive, `end` is exclusive. `YFinanceProvider` is the only implementation. Another vendor can replace it without changing the cache, the adjustment, or the validator.

The adapter calls `Ticker.history` with `auto_adjust=False`, `actions=True`, `prepost=False`, `repair=False`. Regular-session bars only. Yahoo's repair is left off so a bad print shows up in the validation report instead of being rewritten.

Yahoo's OHLC and volume in that mode are **already split-adjusted**, not the prices that traded. The adapter rebuilds raw OHLC by multiplying by later split ratios, and raw volume by dividing by those ratios. Dividend figures are passed through as Yahoo reports them. A `Capital Gains` column, when present, is added to that session's dividend: both are cash that gaps the price, and this store does not model tax character.

That reconstruction is the fragile part of this feed. Before a research result depends on it, spot-check one name:

- AAPL 2020-08-31 was a 4-for-1. The raw close on 2020-08-28 should be about four times Yahoo's published "Close" for that day.
- AAPL's 2020-05-08 dividend was $0.82 per pre-split share. The stored dividend should be about 0.82, not 0.205, and the previous raw close should be the pre-split price (about $300, not about $75).

Adjusted columns are computed in this repository from the raw bars and the action table. Yahoo's `Adj Close` is not stored.

Further limits of this free feed:

- Listed names only. No delisted tape, so any long history of the stock list is a survivor history.
- Yahoo can revise old bars. The manifest says when a file was downloaded; `snapshot_id` identifies the logical content. A later download is a new snapshot.
- No point-in-time index membership, no auction flag, no borrow, no official total-return series.
- Missing sessions, wrong dividends and scaled prices (100× errors) occur. Validate before using a file.
- Share classes use Yahoo's ticker (`BRK-B`, not `BRK.B`). The starting universe has none.
- The request can be rate-limited or the columns can change. A frame without OHLC, `Dividends` or `Stock Splits` fails rather than being stored as raw prices.

Stooq was not used. It does not provide a split and dividend history this code can apply, so it cannot meet the corporate-action requirement.

## Cache

`data/` is gitignored except `data/README.md`. The cache lives at `data/cache/`:

```
data/cache/
  ohlcv/{SYMBOL}.parquet
  actions/{SYMBOL}.parquet
  manifest.jsonl
```

Each manifest line is one download: `symbol`, `source`, `downloaded_at` (UTC), `parameters` (`start`, `end`, `interval`, `price_basis`, `adjustment`), `row_count`, `action_count`. Rewriting a symbol appends a line; it does not edit the old one.

`load_universe(cache)` reads the whole starting universe from disk and does not download. It raises if any symbol is missing, and it returns `snapshot_id` (sha256 of the logical bars, adjusted bars and actions). Record that id next to a result. The id does not cover the manifest, so a rewrite that stores the same numbers keeps the same id and still adds a provenance line.

`refresh_history(...)` is the call that hits the provider. Tests use a fake provider. They do not call Yahoo.

Loading does not mean the bars passed validation. Call `validate_history` or `validate_universe` and read the report.

## Universe

Seventeen liquid US-listed ETFs and six large-cap stocks:

- Broad: SPY, QQQ, IWM, DIA
- Sector SPDRs: XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC
- Bonds and gold: TLT, GLD
- Stocks: AAPL, MSFT, AMZN, JPM, JNJ, XOM

`SUGGESTED_HISTORY_START` is 2005-01-01. XLRE listed in 2015 and XLC in 2018, so a download from 2005 is not a rectangle. Validation looks for missing sessions only between a symbol's first and last stored bar, so a late listing is not reported as a hole before the first bar.

## Survivorship and selection

This list is a snapshot of names that are large and liquid now. It is not the membership of any index on any past date.

- Stocks that were delisted, acquired or went to zero are absent. Results on these six names overstate what a stock picker would have earned.
- The six were chosen because they are familiar, liquid and spread across sectors, not because a rule picked them in 2005. That choice is hindsight.
- The ETFs are fewer and have not been replaced as often as single stocks, but the choice of these ETFs is still a choice made today. XLRE and XLC did not exist for the whole sample. Sector funds that closed are not here.
- There is no point-in-time universe file in this repository. Free Yahoo data does not provide one. Until that exists, a backtest on `STARTING_UNIVERSE` cannot support a claim about "stocks" or "the market" in general. It can describe these names only, and the write-up has to say so.

## Validation

`validate_history` flags:

| Code | What it means |
|---|---|
| `missing_session` | An NYSE session between the first and last bar has no row |
| `unexpected_session` | A row falls on a weekend or a holiday in this calendar |
| `duplicate_date` | The same session appears twice |
| `non_positive_price` | Open, high, low or close is not a positive finite number (either series) |
| `high_below_low` | High is below low |
| `close_outside_range` | Close is outside [low, high] |
| `open_outside_range` | Open is outside [low, high]. Included because fills use the open |
| `zero_volume` | Raw volume is 0 |
| `invalid_volume` | Raw volume is negative or not finite |
| `extreme_return` | Absolute adjusted close-to-close return is above 50% (configurable) |
| `date_mismatch` | Raw and adjusted series do not cover the same sessions |
| `empty` | No bars |

The extreme-return check uses the **adjusted** close. A raw 4-for-1 gap is not, by itself, a bad print. Fifty percent is a review threshold. A single stock can exceed it on an earnings day; the report names the session and does not delete the bar.

## Calendar

Sessions are weekdays that are not standard NYSE full-day holidays: New Year's Day, Martin Luther King Jr. Day (from 1998), Washington's Birthday, Good Friday, Memorial Day, Juneteenth (from 2022), Independence Day, Labor Day, Thanksgiving and Christmas. A Saturday holiday is observed on Friday, a Sunday holiday on Monday. The day after Thanksgiving is a session (it is an early close, not a closure).

Not in this calendar: one-off closures such as 11–14 September 2001, Hurricane Sandy (29–30 October 2012), or a national day of mourning. A download that is otherwise complete can still raise `missing_session` on those dates. That flag means "not in this rule set". It is not automatic proof that the vendor dropped a trading day.

## What this milestone does not do

No strategy, no position sizing, no fills, no broker client. `LIVE_TRADING_ALLOWED` stays `False`. Market data files stay out of git.
