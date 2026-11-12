"""Safety guard: this project never places live orders without explicit approval.

Every entry point that could act on a signal (backtest runner, paper trader) must call
:func:`assert_paper_only` first. Live trading is off by default. Turning it on requires
a separate, owner-approved issue and code change; setting an environment variable is
not enough.
"""

from __future__ import annotations

import os

LIVE_TRADING_ENV_VAR = "LIVE_TRADING_ENABLED"

# Hard-coded off. Changing this constant requires an owner-approved issue and PR.
LIVE_TRADING_ALLOWED = False

_TRUTHY = {"1", "true", "yes", "on"}


class LiveTradingDisabledError(RuntimeError):
    """Raised when something tries to enable live trading."""


def live_trading_requested(environ: dict[str, str] | None = None) -> bool:
    """Return True if the environment asks for live trading."""
    env = os.environ if environ is None else environ
    return env.get(LIVE_TRADING_ENV_VAR, "false").strip().lower() in _TRUTHY


def assert_paper_only(environ: dict[str, str] | None = None) -> None:
    """Raise if live trading is requested while it is not allowed in code."""
    if live_trading_requested(environ) and not LIVE_TRADING_ALLOWED:
        raise LiveTradingDisabledError(
            f"{LIVE_TRADING_ENV_VAR} is set, but live trading is disabled in this "
            "repository. Enabling it requires an explicit, owner-approved issue and PR."
        )
