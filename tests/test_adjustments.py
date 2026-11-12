from datetime import date

import pytest

from systrade.data.adjust import adjust_bars, build_history
from systrade.data.model import AdjustmentError, CorporateAction, DailyBar
from tests.market_fixtures import bar, known_split_dividend


def _closes(bars: tuple[DailyBar, ...]) -> list[float]:
    return [item.close for item in bars]


def test_raw_and_adjusted_cover_the_same_dates_and_match_the_fixture() -> None:
    bars, actions = known_split_dividend()
    history = build_history("TEST", bars, actions)

    assert [item.session for item in history.bars] == [item.session for item in history.adjusted]

    last_action = max(action.session for action in history.actions)
    for raw, adjusted in zip(history.bars, history.adjusted, strict=True):
        if raw.session >= last_action:
            assert adjusted.open == pytest.approx(raw.open)
            assert adjusted.high == pytest.approx(raw.high)
            assert adjusted.low == pytest.approx(raw.low)
            assert adjusted.close == pytest.approx(raw.close)
            assert adjusted.volume == pytest.approx(raw.volume)

    # 496 / 4 * 125/126. The raw print is the pre-split price.
    assert history.bars[1].close == pytest.approx(496)
    assert history.adjusted[1].close == pytest.approx(124 * 125 / 126)
    assert history.adjusted[1].volume == pytest.approx(1_100 * 4)
    # Session before the $1 dividend: 126 * 125/126 = 125.
    assert history.adjusted[3].close == pytest.approx(125)


def test_split_removes_the_raw_gap() -> None:
    bars = (bar("2024-06-03", 100, volume=10), bar("2024-06-04", 55, volume=20))
    split = CorporateAction(date(2024, 6, 4), "split", 2.0)
    history = build_history("TEST", bars, (split,))
    assert history.adjusted[0].close == pytest.approx(50)
    assert history.adjusted[1].close == pytest.approx(55)
    assert history.adjusted[0].volume == pytest.approx(20)
    assert history.adjusted[1].volume == pytest.approx(20)


def test_same_day_split_and_dividend() -> None:
    bars = (bar("2024-06-03", 100), bar("2024-06-04", 50))
    actions = (
        CorporateAction(date(2024, 6, 4), "split", 2.0),
        CorporateAction(date(2024, 6, 4), "dividend", 1.0),
    )
    history = build_history("TEST", bars, actions)
    assert history.adjusted[0].close == pytest.approx(49.5)
    assert history.adjusted[1].close == pytest.approx(50)


def test_two_dividends_use_the_split_adjusted_close_not_a_compounded_base() -> None:
    sessions = ("2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06", "2024-06-07")
    bars = tuple(bar(session, 100) for session in sessions)
    actions = (
        CorporateAction(date(2024, 6, 5), "dividend", 1.0),
        CorporateAction(date(2024, 6, 7), "dividend", 1.0),
    )
    history = build_history("TEST", bars, actions)
    assert _closes(history.adjusted) == pytest.approx([98.01, 98.01, 99, 99, 100])


def test_same_day_cash_is_summed() -> None:
    bars = (bar("2024-06-03", 100), bar("2024-06-04", 98.5))
    actions = (
        CorporateAction(date(2024, 6, 4), "dividend", 1.0),
        CorporateAction(date(2024, 6, 4), "dividend", 0.5),
    )
    history = build_history("TEST", bars, actions)
    assert history.adjusted[0].close == pytest.approx(98.5)


def test_future_split_does_not_change_past_returns() -> None:
    bars = (bar("2024-06-03", 100), bar("2024-06-04", 99), bar("2024-06-05", 100))
    dividend = CorporateAction(date(2024, 6, 4), "dividend", 1.0)
    future_split = CorporateAction(date(2024, 6, 6), "split", 4.0)
    base = build_history("TEST", bars, (dividend,))
    later = build_history("TEST", bars, (dividend, future_split))

    def returns(closes: list[float]) -> list[float]:
        return [closes[index] / closes[index - 1] - 1 for index in range(1, len(closes))]

    assert returns(_closes(later.adjusted)) == pytest.approx(returns(_closes(base.adjusted)))
    assert later.adjusted[-1].close == pytest.approx(base.adjusted[-1].close / 4)


def test_no_actions_leaves_prices_unchanged() -> None:
    bars = (bar("2024-06-04", 10, volume=3), bar("2024-06-03", 9, volume=4))
    history = build_history("TEST", bars, ())
    assert [item.session for item in history.bars] == [date(2024, 6, 3), date(2024, 6, 4)]
    assert history.adjusted == history.bars


def test_dividend_after_the_sample_scales_every_bar() -> None:
    bars = (bar("2024-06-03", 100), bar("2024-06-04", 100))
    action = CorporateAction(date(2024, 6, 5), "dividend", 1.0)
    history = build_history("TEST", bars, (action,))
    assert history.adjusted[0].close == pytest.approx(99)
    assert history.adjusted[1].close == pytest.approx(99)


def test_dividend_before_the_sample_is_ignored() -> None:
    bars = (bar("2024-06-03", 10),)
    action = CorporateAction(date(2024, 1, 2), "dividend", 1.0)
    history = build_history("TEST", bars, (action,))
    assert history.adjusted[0].close == pytest.approx(10)


def test_adjustment_rejects_bad_inputs() -> None:
    good = (bar("2024-06-03", 10), bar("2024-06-04", 10))
    with pytest.raises(AdjustmentError):
        adjust_bars((bar("2024-06-04", 10), bar("2024-06-03", 10)), ())
    with pytest.raises(AdjustmentError):
        adjust_bars((bar("2024-06-03", 10), bar("2024-06-03", 11)), ())
    with pytest.raises(AdjustmentError):
        build_history("TEST", good, (CorporateAction(date(2024, 6, 4), "split", 0),))
    with pytest.raises(AdjustmentError):
        build_history("TEST", good, (CorporateAction(date(2024, 6, 4), "dividend", 10),))
    assert adjust_bars((), ()) == ()
