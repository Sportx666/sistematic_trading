"""Backward adjustment for splits and cash dividends.

The formula is specified in ``docs/data.md``. Adjusted levels are anchored so
that a bar with no later corporate action keeps its raw prices. Returns
between two sessions depend only on actions whose ex-date is inside the
window, so a later split does not change a return-based signal.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

from systrade.data.model import (
    AdjustmentError,
    CorporateAction,
    DailyBar,
    SymbolHistory,
    check_symbol,
)


def build_history(
    symbol: str,
    bars: Sequence[DailyBar],
    actions: Sequence[CorporateAction],
) -> SymbolHistory:
    """Sort raw bars and actions, then attach the adjusted series."""
    check_symbol(symbol)
    ordered = tuple(sorted(bars, key=lambda bar: bar.session))
    ordered_actions = tuple(
        sorted(actions, key=lambda action: (action.session, action.kind, action.amount))
    )
    adjusted = adjust_bars(ordered, ordered_actions)
    return SymbolHistory(
        symbol=symbol,
        bars=ordered,
        adjusted=adjusted,
        actions=ordered_actions,
    )


def adjust_bars(
    bars: Sequence[DailyBar],
    actions: Sequence[CorporateAction],
) -> tuple[DailyBar, ...]:
    """Return split- and dividend-adjusted bars aligned with ``bars``.

    ``bars`` must already be sorted and free of duplicate sessions. Prices are
    divided by later split ratios. Volume is multiplied by those ratios.
    Dividends scale prices only.
    """
    ordered = tuple(bars)
    if not ordered:
        return ()
    sessions = [bar.session for bar in ordered]
    if sessions != sorted(sessions) or len(set(sessions)) != len(sessions):
        raise AdjustmentError("bars must be sorted and have unique sessions")

    splits: list[tuple[date, float]] = []
    dividend_cash: dict[date, float] = {}
    for action in actions:
        _check_action(action)
        if action.kind == "split":
            splits.append((action.session, action.amount))
        else:
            dividend_cash[action.session] = dividend_cash.get(action.session, 0.0) + action.amount

    price_scale = [_split_price_scale(session, splits) for session in sessions]
    dividend_factor = _dividend_factors(ordered, price_scale, dividend_cash, splits)

    adjusted: list[DailyBar] = []
    for index, bar in enumerate(ordered):
        factor = price_scale[index] * dividend_factor[index]
        volume_factor = 1.0 / price_scale[index]
        adjusted.append(
            DailyBar(
                session=bar.session,
                open=bar.open * factor,
                high=bar.high * factor,
                low=bar.low * factor,
                close=bar.close * factor,
                volume=bar.volume * volume_factor,
            )
        )
    return tuple(adjusted)


def _check_action(action: CorporateAction) -> None:
    if action.kind not in ("split", "dividend"):
        raise AdjustmentError(f"unknown corporate action: {action.kind}")
    if not math.isfinite(action.amount) or action.amount <= 0:
        raise AdjustmentError(
            f"{action.kind} on {action.session.isoformat()} must be a positive finite amount"
        )


def _split_product(
    session: date, splits: Sequence[tuple[date, float]], *, inclusive: bool
) -> float:
    product = 1.0
    for split_session, ratio in splits:
        if split_session > session or (inclusive and split_session == session):
            product *= ratio
    return product


def _split_price_scale(session: date, splits: Sequence[tuple[date, float]]) -> float:
    """Divide raw prices by split ratios whose ex-date is strictly later."""
    return 1.0 / _split_product(session, splits, inclusive=False)


def _dividend_factors(
    bars: Sequence[DailyBar],
    price_scale: Sequence[float],
    dividend_cash: dict[date, float],
    splits: Sequence[tuple[date, float]],
) -> list[float]:
    """Price multipliers from cash distributions, on top of ``price_scale``.

    The base price is the split-adjusted previous close, not a close that
    already includes later dividends. Same-day and later splits rescale the
    cash amount into those units.
    """
    factors = [1.0] * len(bars)
    sessions = [bar.session for bar in bars]
    for ex_date, amount in dividend_cash.items():
        cash = amount / _split_product(ex_date, splits, inclusive=True)
        previous = _last_before(sessions, ex_date)
        if previous is None:
            continue
        base = bars[previous].close * price_scale[previous]
        if not math.isfinite(base) or base <= cash:
            raise AdjustmentError(
                f"dividend {amount} on {ex_date.isoformat()} is not below the previous close"
            )
        factor = (base - cash) / base
        for index in range(previous + 1):
            factors[index] *= factor
    return factors


def _last_before(sessions: Sequence[date], ex_date: date) -> int | None:
    previous: int | None = None
    for index, session in enumerate(sessions):
        if session < ex_date:
            previous = index
            continue
        break
    return previous
