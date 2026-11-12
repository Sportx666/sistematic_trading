"""Hand-built bars. Not market data."""

from __future__ import annotations

from datetime import date

from systrade.data.model import CorporateAction, DailyBar


def bar(
    session: str,
    close: float,
    *,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
    volume: float = 1_000.0,
) -> DailyBar:
    return DailyBar(
        session=date.fromisoformat(session),
        open=close if open_ is None else open_,
        high=close if high is None else high,
        low=close if low is None else low,
        close=close,
        volume=volume,
    )


def known_split_dividend() -> tuple[tuple[DailyBar, ...], tuple[CorporateAction, ...]]:
    """A 4-for-1 split and a later $1 dividend, with the adjusted closes written out.

    Raw closes are as traded. The split ex-date (2020-08-31) is already on the
    new share count. The dividend is cash per post-split share.

    Split-adjusted closes before the dividend factor: 100, 124, 125, 126, 126, 127.
    The dividend uses P = 126, so earlier prices scale by 125/126.
    From the dividend ex-date onward, adjusted OHLC equals raw OHLC.
    """
    bars = (
        bar("2020-08-27", 400, volume=1_000),
        bar("2020-08-28", 496, volume=1_100),
        bar("2020-08-31", 125, volume=4_000),
        bar("2020-09-01", 126, volume=4_100),
        bar("2020-09-02", 126, volume=4_200),
        bar("2020-09-03", 127, volume=4_300),
    )
    actions = (
        CorporateAction(date(2020, 8, 31), "split", 4.0),
        CorporateAction(date(2020, 9, 2), "dividend", 1.0),
    )
    return bars, actions
