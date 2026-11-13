"""Starting research universe.

A current list of liquid US-listed ETFs and large-cap stocks. It is not a
point-in-time membership list. Limits are written up in ``docs/data.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

InstrumentKind = Literal["etf", "stock"]

# Far enough back to include 2008, and late enough that most of these ETFs exist.
# XLRE (2015) and XLC (2018) still start later; the panel is not a rectangle.
SUGGESTED_HISTORY_START = date(2005, 1, 1)


@dataclass(frozen=True)
class Instrument:
    """One name in the starting universe."""

    symbol: str
    name: str
    kind: InstrumentKind


_ETFS: tuple[tuple[str, str], ...] = (
    ("SPY", "SPDR S&P 500 ETF Trust"),
    ("QQQ", "Invesco QQQ Trust"),
    ("IWM", "iShares Russell 2000 ETF"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF"),
    ("XLK", "Technology Select Sector SPDR"),
    ("XLF", "Financial Select Sector SPDR"),
    ("XLE", "Energy Select Sector SPDR"),
    ("XLV", "Health Care Select Sector SPDR"),
    ("XLI", "Industrial Select Sector SPDR"),
    ("XLY", "Consumer Discretionary Select Sector SPDR"),
    ("XLP", "Consumer Staples Select Sector SPDR"),
    ("XLU", "Utilities Select Sector SPDR"),
    ("XLB", "Materials Select Sector SPDR"),
    ("XLRE", "Real Estate Select Sector SPDR"),
    ("XLC", "Communication Services Select Sector SPDR"),
    ("TLT", "iShares 20+ Year Treasury Bond ETF"),
    ("GLD", "SPDR Gold Shares"),
)

# Large and liquid today, spread across sectors. Still a survivor list.
_STOCKS: tuple[tuple[str, str], ...] = (
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("AMZN", "Amazon"),
    ("JPM", "JPMorgan Chase"),
    ("JNJ", "Johnson & Johnson"),
    ("XOM", "Exxon Mobil"),
)


def _instruments(rows: tuple[tuple[str, str], ...], kind: InstrumentKind) -> tuple[Instrument, ...]:
    return tuple(Instrument(symbol, name, kind) for symbol, name in rows)


STARTING_UNIVERSE: tuple[Instrument, ...] = _instruments(_ETFS, "etf") + _instruments(
    _STOCKS, "stock"
)


def starting_symbols(kind: InstrumentKind | None = None) -> tuple[str, ...]:
    """Symbols in universe order, optionally restricted to ETFs or stocks."""
    if kind is None:
        return tuple(item.symbol for item in STARTING_UNIVERSE)
    return tuple(item.symbol for item in STARTING_UNIVERSE if item.kind == kind)
