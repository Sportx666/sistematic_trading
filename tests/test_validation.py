from systrade.data.adjust import build_history
from systrade.data.model import SymbolHistory
from systrade.data.validate import validate_history
from tests.market_fixtures import bar, known_split_dividend

_INJECTED = frozenset(
    {
        "zero_volume",
        "duplicate_date",
        "missing_session",
        "non_positive_price",
        "high_below_low",
        "close_outside_range",
        "open_outside_range",
        "unexpected_session",
        "extreme_return",
    }
)


def test_clean_week_passes() -> None:
    sessions = ("2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06", "2024-06-07")
    bars = tuple(bar(session, 100 + offset) for offset, session in enumerate(sessions))
    assert validate_history(build_history("TEST", bars, ())).ok


def test_july_fourth_is_not_a_missing_session() -> None:
    bars = tuple(bar(session, 100) for session in ("2024-07-03", "2024-07-05", "2024-07-08"))
    report = validate_history(build_history("TEST", bars, ()))
    assert report.ok


def test_missing_weekday_between_a_holiday_is_flagged() -> None:
    bars = tuple(bar(session, 100) for session in ("2024-07-03", "2024-07-08"))
    report = validate_history(build_history("TEST", bars, ()))
    missing = [issue.session for issue in report.issues if issue.code == "missing_session"]
    assert missing == [bar("2024-07-05", 1).session]


def test_validation_flags_injected_errors() -> None:
    raw = (
        bar("2024-06-03", 100, volume=0),
        bar("2024-06-04", 100),
        bar("2024-06-04", 100),
        bar("2024-06-06", 0, low=-1, high=1, open_=0),
        bar("2024-06-07", 15, low=20, high=10, open_=15),
        bar("2024-06-08", 100),
        bar("2024-06-10", 15, low=10, high=12, open_=11),
        bar("2024-06-11", 11, low=10, high=12, open_=9),
        bar("2024-06-12", 100),
        bar("2024-06-13", 250),
    )
    history = SymbolHistory("TEST", raw, raw, ())
    report = validate_history(history)
    assert not report.ok
    assert report.codes() >= _INJECTED


def test_known_split_is_not_an_extreme_return() -> None:
    bars, actions = known_split_dividend()
    report = validate_history(build_history("AAPL", bars, actions))
    assert report.ok


def test_date_mismatch_is_flagged() -> None:
    history = SymbolHistory("TEST", (bar("2024-06-03", 10),), (bar("2024-06-04", 10),), ())
    assert "date_mismatch" in validate_history(history).codes()


def test_threshold_must_be_positive() -> None:
    history = build_history("TEST", (bar("2024-06-03", 10),), ())
    import pytest

    with pytest.raises(ValueError):
        validate_history(history, max_abs_daily_return=0)
