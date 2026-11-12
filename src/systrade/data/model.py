"""Shared types for daily bars, corporate actions and cache provenance.

Raw and adjusted series, and which one a later stage may use, are specified in
``docs/data.md``. This module does not download or adjust anything.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

ActionKind = Literal["split", "dividend"]

_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")


class DataError(Exception):
    """Base error for acquisition, cache and adjustment failures."""


class ProviderError(DataError):
    """The data provider failed or returned nothing usable."""


class CacheMissError(DataError):
    """One or more symbols are not in the local cache."""


class AdjustmentError(DataError):
    """Splits or dividends could not be applied."""


def _as_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a number")
    return float(value)


def check_symbol(symbol: str) -> str:
    """Return ``symbol`` if it is a safe cache key (no paths, uppercase)."""
    if _SYMBOL_RE.fullmatch(symbol) is None:
        raise ValueError(f"invalid symbol: {symbol!r}")
    return symbol


def parameter_pairs(parameters: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Sorted ``(key, value)`` pairs so a download record is deterministic."""
    pairs: list[tuple[str, str]] = []
    for key, value in parameters.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("download parameters must be strings")
        pairs.append((key, value))
    return tuple(sorted(pairs))


@dataclass(frozen=True)
class DailyBar:
    """One regular-session daily bar.

    ``volume`` is a share count. On the raw series it is shares that traded
    that day. On the adjusted series it is split-adjusted into the latest
    share units. Prices are floats, not decimal currency. Integers are
    accepted and stored as floats.
    """

    session: date
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "open", _as_number(self.open, "open"))
        object.__setattr__(self, "high", _as_number(self.high, "high"))
        object.__setattr__(self, "low", _as_number(self.low, "low"))
        object.__setattr__(self, "close", _as_number(self.close, "close"))
        object.__setattr__(self, "volume", _as_number(self.volume, "volume"))


@dataclass(frozen=True)
class CorporateAction:
    """A split or a cash distribution.

    ``kind="split"``: ``amount`` is new shares per old share (4.0 for a
    4-for-1, 0.5 for a 1-for-2 reverse). It applies to sessions before
    ``session``.

    ``kind="dividend"``: ``amount`` is cash per share, in the same units as
    the previous session's raw close. Capital-gains distributions are stored
    with this kind because they gap the price the same way. Same-day cash
    amounts are summed before the adjustment factor is applied.
    """

    session: date
    kind: ActionKind
    amount: float


@dataclass(frozen=True)
class SymbolHistory:
    """Raw bars, backward-adjusted bars, and the actions that link them.

    ``bars`` and ``adjusted`` cover the same sessions in the same order.
    """

    symbol: str
    bars: tuple[DailyBar, ...]
    adjusted: tuple[DailyBar, ...]
    actions: tuple[CorporateAction, ...]


@dataclass(frozen=True)
class DownloadRecord:
    """Provenance for one cache write."""

    symbol: str
    source: str
    downloaded_at: datetime
    parameters: tuple[tuple[str, str], ...]
    row_count: int
    action_count: int

    def __post_init__(self) -> None:
        if self.downloaded_at.tzinfo is None:
            raise ValueError("downloaded_at must be timezone-aware")
        if self.row_count < 0 or self.action_count < 0:
            raise ValueError("row_count and action_count must be non-negative")


@dataclass(frozen=True)
class UniverseData:
    """Histories loaded together, plus an id for the logical content."""

    symbols: tuple[str, ...]
    histories: tuple[SymbolHistory, ...]
    snapshot_id: str

    def __post_init__(self) -> None:
        loaded = tuple(history.symbol for history in self.histories)
        if loaded != self.symbols:
            raise ValueError("histories must follow symbols, in the same order")

    def __getitem__(self, symbol: str) -> SymbolHistory:
        for history in self.histories:
            if history.symbol == symbol:
                return history
        raise KeyError(symbol)
