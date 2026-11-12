# sistematic_trading

A Python environment for learning and backtesting systematic trading strategies, built to support a **12-week structured training programme**.

| Scope | |
|---|---|
| Instruments | US stocks and liquid ETFs |
| Direction | Long only (no shorting, no leverage) |
| Timeframe | Daily bars |
| Style | Swing trading (holding periods of days to weeks) |
| Eventual account | €2,000 risk capital, **only after** the go/no-go checklist is passed |

> **This is a research project.** Nothing here is financial advice. The code does
> backtests and paper trading only and **cannot place live orders**.

## Safety policy

1. **No live orders.** Live trading is hard-disabled in `src/systrade/safety.py`. Setting `LIVE_TRADING_ENABLED=true` makes the program refuse to start; it does not enable anything. Changing this requires a dedicated issue with explicit written approval from the repository owner.
2. **No credentials in the repository.** Broker keys, passwords and account numbers never go in code, config, notebooks, issues or PRs. `.env` is gitignored, and `.env.example` holds placeholders only.
3. **No automatic merging or deployment.** Every change is a small PR, reviewed by a person and merged manually.
4. **Market data stays out of git.** `data/` is gitignored; data is re-downloadable and documented.

## Quick start

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Sportx666/sistematic_trading.git
cd sistematic_trading
uv sync --all-extras          # creates .venv from uv.lock (reproducible)
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format --check .  # formatting
uv run mypy                   # type check
```

Without uv: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`. This resolves dependency versions fresh, so it is less reproducible than `uv.lock`.

## Repository layout

```
src/systrade/          Python package
  config.py            programme scope and account defaults (€2,000, 1% risk/trade)
  safety.py            live-trading guard
  data/                data acquisition, validation, corporate actions     (M2)
  strategies/          strategy implementations (spec required)            (M3)
  backtest/            backtest engine, costs, sizing                      (M4)
  validation/          out-of-sample and walk-forward analysis             (M5)
  risk/                risk limits, pre-trade checks                       (M6)
  paper/               paper-trading simulation, reconciliation            (M7)
tests/                 pytest suite (hermetic: no network, no real data)
strategies/            strategy specifications (written before code)
journal/               daily research journal
progress/              12-week progress tracker
docs/                  architecture, research standards, workflow
notebooks/             exploratory notebooks (results never cited without code)
data/                  local data cache (gitignored)
```

## Milestones

| # | Milestone | Issue |
|---|---|---|
| M1 | Repository foundation and reproducible Python environment | [#1](https://github.com/Sportx666/sistematic_trading/issues/1) |
| M2 | Historical data acquisition, validation, corporate actions | [#2](https://github.com/Sportx666/sistematic_trading/issues/2) |
| M3 | First fully specified trend-following strategy | [#3](https://github.com/Sportx666/sistematic_trading/issues/3) |
| M4 | Backtesting engine: costs, slippage, sizing, no look-ahead | [#4](https://github.com/Sportx666/sistematic_trading/issues/4) |
| M5 | Out-of-sample and walk-forward validation | [#5](https://github.com/Sportx666/sistematic_trading/issues/5) |
| M6 | Risk management and portfolio constraints | [#6](https://github.com/Sportx666/sistematic_trading/issues/6) |
| M7 | Paper-trading simulation and reconciliation | [#7](https://github.com/Sportx666/sistematic_trading/issues/7) |
| M8 | 12-week curriculum and daily journal | [#8](https://github.com/Sportx666/sistematic_trading/issues/8) |
| M9 | CI tests and research-quality checks | [#9](https://github.com/Sportx666/sistematic_trading/issues/9) |
| M10 | Claude Code issue-to-PR workflow | [#10](https://github.com/Sportx666/sistematic_trading/issues/10) |

## Documentation

- [Architecture](docs/architecture.md)
- [Market data](docs/data.md): cache, adjustments, survivorship, free-data limits
- [Research standards](docs/research_standards.md): how to avoid fooling yourself
- [Development workflow](docs/workflow.md): issue → PR → review
- [Strategy specs](strategies/README.md) · [Journal](journal/README.md) · [Progress tracker](progress/TRACKER.md)
