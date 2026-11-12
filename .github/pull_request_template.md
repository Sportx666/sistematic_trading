## Summary
<!-- What does this PR change and why? -->

Part of / Closes #

## Changes
-

## Testing
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` passes locally
- [ ] New or changed logic has tests (hermetic: no network, no real data)

## Research and safety checklist
- [ ] No credentials, API keys, account numbers or `.env` files
- [ ] No live-order code; `LIVE_TRADING_ALLOWED` unchanged
- [ ] No market data or large generated files committed
- [ ] Signal and fill timing is explicit and look-ahead is checked (if strategy/backtest code)
- [ ] Strategy code matches an approved spec in `strategies/` (if applicable)
- [ ] Journal / progress tracker updated (if applicable)
