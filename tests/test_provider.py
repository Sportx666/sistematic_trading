from datetime import date

import pandas as pd
import pytest

from systrade.data.model import CorporateAction, ProviderError
from systrade.data.provider import YFinanceProvider, parse_yfinance_frame


def _frame(rows: dict[str, list[float]], index: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    if index is None:
        index = pd.to_datetime(["2020-08-28", "2020-08-31"])
    columns = {
        "Open": rows.get("Open", rows["Close"]),
        "High": rows.get("High", rows["Close"]),
        "Low": rows.get("Low", rows["Close"]),
        "Close": rows["Close"],
        "Volume": rows["Volume"],
        "Dividends": rows.get("Dividends", [0.0, 0.0]),
        "Stock Splits": rows.get("Stock Splits", [0.0, 0.0]),
    }
    if "Capital Gains" in rows:
        columns["Capital Gains"] = rows["Capital Gains"]
    return pd.DataFrame(columns, index=index)


def test_split_adjusted_yahoo_rows_become_raw_bars() -> None:
    frame = _frame(
        {
            "Close": [124.0, 127.0],
            "Volume": [400.0, 150.0],
            "Stock Splits": [0.0, 4.0],
        }
    )
    bars, actions = parse_yfinance_frame(frame)
    assert bars[0].session == date(2020, 8, 28)
    assert bars[0].close == pytest.approx(496)
    assert bars[0].volume == pytest.approx(100)
    assert bars[1].close == pytest.approx(127)
    assert bars[1].volume == pytest.approx(150)
    assert actions == (CorporateAction(date(2020, 8, 31), "split", 4.0),)


def test_timezone_aware_index_uses_the_new_york_date() -> None:
    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2020-08-31 04:00:00", tz="UTC"),
            pd.Timestamp("2020-09-01 04:00:00", tz="UTC"),
        ]
    )
    frame = _frame({"Close": [10.0, 11.0], "Volume": [5.0, 6.0]}, index=index)
    bars, _actions = parse_yfinance_frame(frame)
    assert [bar.session for bar in bars] == [date(2020, 8, 31), date(2020, 9, 1)]


def test_capital_gains_are_added_to_the_dividend() -> None:
    index = pd.to_datetime(["2024-06-03", "2024-06-04"])
    frame = _frame(
        {
            "Close": [100.0, 98.0],
            "Volume": [10.0, 10.0],
            "Dividends": [0.0, 1.0],
            "Capital Gains": [0.0, 0.5],
        },
        index=index,
    )
    _bars, actions = parse_yfinance_frame(frame)
    assert actions == (CorporateAction(date(2024, 6, 4), "dividend", 1.5),)


def test_missing_ohlc_row_is_dropped_but_its_dividend_is_kept() -> None:
    index = pd.to_datetime(["2024-06-03", "2024-06-04"])
    frame = _frame(
        {
            "Close": [10.0, float("nan")],
            "Volume": [100.0, float("nan")],
            "Dividends": [0.0, 0.25],
        },
        index=index,
    )
    bars, actions = parse_yfinance_frame(frame)
    assert len(bars) == 1
    assert bars[0].session == date(2024, 6, 3)
    assert actions == (CorporateAction(date(2024, 6, 4), "dividend", 0.25),)


def test_parser_rejects_bad_frames() -> None:
    with pytest.raises(ProviderError):
        parse_yfinance_frame(pd.DataFrame({"Open": [1.0]}))
    duplicate = _frame({"Close": [1.0, 1.0], "Volume": [1.0, 1.0]})
    duplicate.index = pd.to_datetime(["2024-06-03", "2024-06-03"])
    with pytest.raises(ProviderError):
        parse_yfinance_frame(duplicate)
    negative = _frame({"Close": [1.0, 1.0], "Volume": [1.0, 1.0], "Stock Splits": [0.0, -1.0]})
    with pytest.raises(ProviderError):
        parse_yfinance_frame(negative)
    empty = _frame({"Close": [1.0, 1.0], "Volume": [1.0, 1.0]}).iloc[0:0]
    assert parse_yfinance_frame(empty) == ((), ())
    multi = pd.DataFrame([[1.0]], columns=pd.MultiIndex.from_tuples([("Open", "SPY")]))
    with pytest.raises(ProviderError):
        parse_yfinance_frame(multi)


def test_fetch_daily_rejects_empty_or_unusable_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = YFinanceProvider()

    def empty(_symbol: str, _start: date, _end: date) -> pd.DataFrame:
        return pd.DataFrame()

    monkeypatch.setattr(provider, "_download", empty)
    with pytest.raises(ProviderError, match="no rows"):
        provider.fetch_daily("SPY", date(2024, 6, 3), date(2024, 6, 5))

    def unusable(_symbol: str, _start: date, _end: date) -> pd.DataFrame:
        index = pd.to_datetime(["2024-06-03"])
        return _frame(
            {
                "Close": [float("nan")],
                "Volume": [float("nan")],
                "Dividends": [0.0],
                "Stock Splits": [0.0],
            },
            index=index,
        )

    monkeypatch.setattr(provider, "_download", unusable)
    with pytest.raises(ProviderError, match="no usable OHLC"):
        provider.fetch_daily("SPY", date(2024, 6, 3), date(2024, 6, 5))


def test_yfinance_provider_rejects_bad_requests_without_downloading() -> None:
    provider = YFinanceProvider()
    assert provider.name == "yfinance"
    with pytest.raises(ValueError):
        provider.fetch_daily("SPY", date(2024, 6, 3), date(2024, 6, 3))
    with pytest.raises(ValueError):
        provider.fetch_daily("spy", date(2024, 6, 3), date(2024, 6, 4))
    with pytest.raises(ValueError):
        YFinanceProvider(timeout=0)


def test_missing_yfinance_is_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def blocked(name: str, *args: object, **kwargs: object) -> object:
        if name == "yfinance":
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ProviderError):
        YFinanceProvider().fetch_daily("SPY", date(2024, 6, 3), date(2024, 6, 5))
