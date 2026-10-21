import pytest

from systrade import safety


def test_live_trading_hard_disabled() -> None:
    assert safety.LIVE_TRADING_ALLOWED is False


def test_default_environment_is_paper_only() -> None:
    assert safety.live_trading_requested({}) is False
    safety.assert_paper_only({})


@pytest.mark.parametrize("value", ["false", "0", "no", "", "off"])
def test_falsy_values_allowed(value: str) -> None:
    safety.assert_paper_only({safety.LIVE_TRADING_ENV_VAR: value})


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", " on "])
def test_enabling_live_trading_raises(value: str) -> None:
    with pytest.raises(safety.LiveTradingDisabledError):
        safety.assert_paper_only({safety.LIVE_TRADING_ENV_VAR: value})


def test_env_example_keeps_live_trading_off() -> None:
    from systrade.config import PROJECT_ROOT

    text = (PROJECT_ROOT / ".env.example").read_text()
    assert f"{safety.LIVE_TRADING_ENV_VAR}=false" in text
