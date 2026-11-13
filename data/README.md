# Local data cache

Everything in this directory except this README is gitignored. Market data is downloaded and validated by `systrade.data` (M2, [#2](https://github.com/Sportx666/sistematic_trading/issues/2)), and can always be re-created from code. See [docs/data.md](../docs/data.md).

`systrade.data` writes the cache under `data/cache/`:

```
data/cache/
  ohlcv/{SYMBOL}.parquet     raw and adjusted daily bars
  actions/{SYMBOL}.parquet   splits and cash distributions
  manifest.jsonl             one record per download (source, time, parameters)
```

Never commit data files, broker statements or account exports.
