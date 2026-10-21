# Instructions for Claude Code (and other AI agents)

This is a research and backtesting project for long-only, daily, swing-trading strategies on US stocks and liquid ETFs. Read `README.md` and `docs/research_standards.md` before you change any code.

## Hard rules (never break these)

- **Never place, enable or wire up live orders.** Don't change `LIVE_TRADING_ALLOWED` in `src/systrade/safety.py`, and don't add broker order endpoints, unless an issue explicitly approved by the repository owner asks for it.
- **Never commit credentials**: no API keys, broker logins, account numbers or tokens, not even fake-looking ones. Use `.env` (gitignored) and point to `.env.example`.
- **Never merge PRs, enable auto-merge, or deploy.** The owner merges manually after review.
- **Never commit market data** or large generated files. `data/` is gitignored.
- **Never skip, delete or weaken tests** to make CI pass.

## Workflow

- One issue → one branch named `claude/issue-<n>-<slug>` → one small PR (preferably under ~400 changed lines) that references the issue.
- Before you push, run: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`.
- Tests must be hermetic. Use synthetic data fixtures, and never access the network in tests.
- Strategy code requires an approved spec in `strategies/` first.
- Any backtest code must state its timing explicitly (signal at the close on *t*, fill at *t+1* or later) and include a look-ahead test.

## Style

- Python ≥ 3.11, type-annotated (mypy strict), ruff for lint and formatting.
- Prefer pure functions over pandas DataFrames for signals and metrics; keep I/O at the edges.
