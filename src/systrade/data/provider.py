"""Data-provider seam and the yfinance adapter.

``DataProvider.fetch_daily`` returns raw (as-traded) bars plus splits and
cash distributions. Adjusted prices are computed later by ``adjust.py``,
not taken from the vendor's adjusted close.

Yahoo's ``history(auto_adjust=False)`` OHLC and volume are already
split-adjusted. This adapter reverses that with the split column, and passes
dividend amounts through as Yahoo reports them. See ``docs/data.md`` for the
spot-check that assumption needs before any result depends on it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

import pandas as pd

from systrade.data.model import CorporateAction, DailyBar, ProviderError, check_symbol

_NY = ZoneInfo("America/New_York")
_REQUIRED = ("Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits")


class DataProvider(Protocol):
    """A source of daily raw bars and corporate actions.

    ``start`` is inclusive and ``end`` is exclusive. Implementations may use
    the network. Tests must not call a live provider.
    """

    @property
    def name(self) -> str: ...

    def fetch_daily(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> tuple[tuple[DailyBar, ...], tuple[CorporateAction, ...]]: ...


class YFinanceProvider:
    """Free Yahoo Finance history via :mod:`yfinance`.

    Regular session only (``prepost=False``). ``repair`` is off so bad prints
    stay visible to the validator. ``auto_adjust`` is off so splits and
    dividends stay in their own columns.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "yfinance"

    def fetch_daily(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> tuple[tuple[DailyBar, ...], tuple[CorporateAction, ...]]:
        check_symbol(symbol)
        if end <= start:
            raise ValueError("end must be after start")
        frame = self._download(symbol, start, end)
        if frame.empty:
            raise ProviderError(f"{symbol}: yfinance returned no rows for {start}..{end}")
        bars, actions = parse_yfinance_frame(frame)
        if not bars:
            raise ProviderError(f"{symbol}: yfinance rows had no usable OHLC")
        return bars, actions

    def _download(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ProviderError(
                "yfinance is not installed; install the project dependencies to download"
            ) from exc
        ticker = yf.Ticker(symbol)
        try:
            downloaded = ticker.history(
                start=start.isoformat(),
                end=end.isoformat(),
                interval="1d",
                auto_adjust=False,
                back_adjust=False,
                actions=True,
                prepost=False,
                repair=False,
                rounding=False,
                timeout=self.timeout,
                raise_errors=True,
            )
        except Exception as exc:
            raise ProviderError(f"{symbol}: yfinance request failed") from exc
        if not isinstance(downloaded, pd.DataFrame):
            raise ProviderError(f"{symbol}: yfinance returned {type(downloaded).__name__}")
        return downloaded


def parse_yfinance_frame(
    frame: pd.DataFrame,
) -> tuple[tuple[DailyBar, ...], tuple[CorporateAction, ...]]:
    """Turn a yfinance history frame into raw bars and actions.

    Does not call the network. Rows with missing OHLC are dropped. Split and
    dividend values on those rows are still kept when the session date is
    readable. Capital-gains cash is added to the dividend on that session.
    """
    if isinstance(frame.columns, pd.MultiIndex):
        raise ProviderError("yfinance frame has unexpected multi-level columns")
    missing = [name for name in _REQUIRED if name not in frame.columns]
    if missing:
        raise ProviderError("yfinance frame is missing columns: " + ", ".join(missing))

    opens = _column(frame, "Open")
    highs = _column(frame, "High")
    lows = _column(frame, "Low")
    closes = _column(frame, "Close")
    volumes = _column(frame, "Volume")
    dividends = _column(frame, "Dividends")
    capital_gains = _column(frame, "Capital Gains")
    splits = _column(frame, "Stock Splits")
    labels = list(frame.index)

    parsed: list[_Row] = []
    for index, label in enumerate(labels):
        session = _as_session(label)
        dividend = _amount(dividends[index], "dividend") + _amount(capital_gains[index], "dividend")
        split = _amount(splits[index], "split")
        ohlc = (opens[index], highs[index], lows[index], closes[index], volumes[index])
        parsed.append(_Row(session, ohlc, dividend, split))

    sessions = [row.session for row in parsed]
    if len(set(sessions)) != len(sessions):
        raise ProviderError("yfinance frame has duplicate sessions")

    split_ratios = [(row.session, row.split) for row in parsed if row.split > 0]
    actions: list[CorporateAction] = [
        CorporateAction(session, "split", ratio) for session, ratio in split_ratios
    ]
    actions.extend(
        CorporateAction(row.session, "dividend", row.dividend) for row in parsed if row.dividend > 0
    )

    bars: list[DailyBar] = []
    for row in parsed:
        open_, high, low, close, volume = row.ohlc
        if open_ is None or high is None or low is None or close is None or volume is None:
            continue
        product = _later_split_product(row.session, split_ratios)
        bars.append(
            DailyBar(
                session=row.session,
                open=open_ * product,
                high=high * product,
                low=low * product,
                close=close * product,
                volume=volume / product,
            )
        )
    bars.sort(key=lambda bar: bar.session)
    actions.sort(key=lambda action: (action.session, action.kind, action.amount))
    return tuple(bars), tuple(actions)


class _Row:
    def __init__(
        self,
        session: date,
        ohlc: tuple[float | None, float | None, float | None, float | None, float | None],
        dividend: float,
        split: float,
    ) -> None:
        self.session = session
        self.ohlc = ohlc
        self.dividend = dividend
        self.split = split


def _later_split_product(session: date, splits: Sequence[tuple[date, float]]) -> float:
    product = 1.0
    for split_session, ratio in splits:
        if split_session > session:
            product *= ratio
    return product


def _column(frame: pd.DataFrame, name: str) -> list[float | None]:
    if name not in frame.columns:
        return [None] * len(frame)
    series = frame[name]
    return [_as_float(item) for item in series.tolist()]


def _amount(value: float | None, label: str) -> float:
    if value is None or value == 0:
        return 0.0
    if value < 0:
        raise ProviderError(f"negative {label} amount")
    return value


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _as_session(value: object) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(_NY).date()
        return value.date()
    if isinstance(value, date):
        return value
    raise ProviderError(f"unrecognised session label: {value!r}")
