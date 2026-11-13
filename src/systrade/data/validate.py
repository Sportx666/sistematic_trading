"""Data-quality checks for a symbol's raw and adjusted bars.

Structural checks run on both series. The extreme-return check runs on the
adjusted close only: a raw series legitimately gaps by the split ratio, and
that gap is not a bad print. The threshold is a flag for review, not a
verdict that the print is wrong.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from datetime import date
from typing import Literal

from systrade.data.calendar import nyse_sessions
from systrade.data.model import DailyBar, SymbolHistory, UniverseData

# A 50% adjusted close-to-close move is rare for this universe and worth a look.
# Earnings gaps in single stocks can exceed it; the report lists them, it does
# not drop them.
DEFAULT_MAX_ABS_DAILY_RETURN = 0.50

PriceSeries = Literal["raw", "adjusted"]
SessionCalendar = Callable[[date, date], Sequence[date]]


class ValidationIssue:
    """One problem found in a symbol's bars."""

    def __init__(self, code: str, symbol: str, session: date | None, message: str) -> None:
        self.code = code
        self.symbol = symbol
        self.session = session
        self.message = message

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationIssue):
            return NotImplemented
        return (
            self.code,
            self.symbol,
            self.session,
            self.message,
        ) == (other.code, other.symbol, other.session, other.message)

    def __repr__(self) -> str:
        return (
            f"ValidationIssue({self.code!r}, {self.symbol!r}, {self.session!r}, {self.message!r})"
        )


class ValidationReport:
    """Every issue found for one symbol. ``ok`` means the tuple is empty."""

    def __init__(self, symbol: str, issues: tuple[ValidationIssue, ...]) -> None:
        self.symbol = symbol
        self.issues = issues

    @property
    def ok(self) -> bool:
        return not self.issues

    def codes(self) -> frozenset[str]:
        return frozenset(issue.code for issue in self.issues)


def validate_history(
    history: SymbolHistory,
    *,
    max_abs_daily_return: float = DEFAULT_MAX_ABS_DAILY_RETURN,
    sessions_between: SessionCalendar = nyse_sessions,
) -> ValidationReport:
    """Check one symbol. ``sessions_between`` defaults to the NYSE calendar."""
    if not math.isfinite(max_abs_daily_return) or max_abs_daily_return <= 0:
        raise ValueError("max_abs_daily_return must be a positive finite number")

    issues: list[ValidationIssue] = []
    symbol = history.symbol
    raw = history.bars
    adjusted = history.adjusted

    if not raw and not adjusted:
        issues.append(ValidationIssue("empty", symbol, None, "no bars"))
        return ValidationReport(symbol, tuple(issues))

    raw_sessions = [bar.session for bar in raw]
    adjusted_sessions = [bar.session for bar in adjusted]
    if raw_sessions != adjusted_sessions:
        issues.append(
            ValidationIssue(
                "date_mismatch",
                symbol,
                None,
                "raw and adjusted series do not cover the same sessions",
            )
        )

    _duplicate_dates(issues, symbol, raw_sessions)
    _calendar_gaps(issues, symbol, raw_sessions, sessions_between)
    for bar in raw:
        _ohlc(issues, symbol, bar, "raw")
        _volume(issues, symbol, bar)
    for bar in adjusted:
        _ohlc(issues, symbol, bar, "adjusted")
    _extreme_returns(issues, symbol, adjusted, max_abs_daily_return)
    return ValidationReport(symbol, tuple(issues))


def validate_universe(
    data: UniverseData,
    *,
    max_abs_daily_return: float = DEFAULT_MAX_ABS_DAILY_RETURN,
) -> tuple[ValidationReport, ...]:
    """Validate every history in a loaded universe, in universe order."""
    return tuple(
        validate_history(history, max_abs_daily_return=max_abs_daily_return)
        for history in data.histories
    )


def _duplicate_dates(issues: list[ValidationIssue], symbol: str, sessions: Sequence[date]) -> None:
    seen: set[date] = set()
    for session in sessions:
        if session in seen:
            issues.append(
                ValidationIssue("duplicate_date", symbol, session, "duplicate session date")
            )
        seen.add(session)


def _calendar_gaps(
    issues: list[ValidationIssue],
    symbol: str,
    sessions: Sequence[date],
    sessions_between: SessionCalendar,
) -> None:
    if not sessions:
        return
    start, end = min(sessions), max(sessions)
    expected = set(sessions_between(start, end))
    actual = set(sessions)
    for session in sorted(expected - actual):
        issues.append(
            ValidationIssue(
                "missing_session",
                symbol,
                session,
                "NYSE session has no bar",
            )
        )
    for session in sorted(actual - expected):
        issues.append(
            ValidationIssue(
                "unexpected_session",
                symbol,
                session,
                "bar falls on a weekend or a NYSE holiday",
            )
        )


def _ohlc(
    issues: list[ValidationIssue],
    symbol: str,
    bar: DailyBar,
    series: PriceSeries,
) -> None:
    for field_name, value in (
        ("open", bar.open),
        ("high", bar.high),
        ("low", bar.low),
        ("close", bar.close),
    ):
        if not math.isfinite(value) or value <= 0:
            issues.append(
                ValidationIssue(
                    "non_positive_price",
                    symbol,
                    bar.session,
                    f"{series} {field_name} is not a positive finite price",
                )
            )
    if not _finite_range(bar):
        return
    if bar.high < bar.low:
        issues.append(
            ValidationIssue(
                "high_below_low",
                symbol,
                bar.session,
                f"{series} high is below low",
            )
        )
    if bar.close < bar.low or bar.close > bar.high:
        issues.append(
            ValidationIssue(
                "close_outside_range",
                symbol,
                bar.session,
                f"{series} close is outside [low, high]",
            )
        )
    if bar.open < bar.low or bar.open > bar.high:
        issues.append(
            ValidationIssue(
                "open_outside_range",
                symbol,
                bar.session,
                f"{series} open is outside [low, high]",
            )
        )


def _volume(issues: list[ValidationIssue], symbol: str, bar: DailyBar) -> None:
    if not math.isfinite(bar.volume) or bar.volume < 0:
        issues.append(
            ValidationIssue(
                "invalid_volume",
                symbol,
                bar.session,
                "raw volume is negative or not finite",
            )
        )
        return
    if bar.volume == 0:
        issues.append(ValidationIssue("zero_volume", symbol, bar.session, "raw volume is zero"))


def _extreme_returns(
    issues: list[ValidationIssue],
    symbol: str,
    adjusted: Sequence[DailyBar],
    max_abs_daily_return: float,
) -> None:
    ordered = sorted(adjusted, key=lambda bar: bar.session)
    for previous, bar in zip(ordered, ordered[1:], strict=False):
        if previous.session == bar.session:
            continue
        if previous.close <= 0 or bar.close <= 0:
            continue
        if not math.isfinite(previous.close) or not math.isfinite(bar.close):
            continue
        change = bar.close / previous.close - 1.0
        if abs(change) > max_abs_daily_return:
            issues.append(
                ValidationIssue(
                    "extreme_return",
                    symbol,
                    bar.session,
                    f"adjusted close return {change:.1%} exceeds {max_abs_daily_return:.0%}",
                )
            )


def _finite_range(bar: DailyBar) -> bool:
    return (
        math.isfinite(bar.open)
        and math.isfinite(bar.high)
        and math.isfinite(bar.low)
        and math.isfinite(bar.close)
    )
