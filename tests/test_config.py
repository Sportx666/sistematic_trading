import pytest

from systrade.config import AccountConfig, default_settings


def test_default_scope_is_long_only_daily() -> None:
    scope = default_settings().scope
    assert scope.long_only
    assert not scope.allow_leverage
    assert not scope.allow_shorting
    assert scope.timeframe == "1d"


def test_default_account() -> None:
    account = default_settings().account
    assert account.risk_capital == 2_000.0
    assert account.base_currency == "EUR"
    assert account.max_risk_per_trade == pytest.approx(20.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"risk_capital": 0},
        {"max_risk_per_trade_pct": 0},
        {"max_risk_per_trade_pct": 5},
        {"max_gross_exposure_pct": 150},
    ],
)
def test_invalid_account_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        AccountConfig(**kwargs)
