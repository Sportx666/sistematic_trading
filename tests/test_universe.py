from systrade.config import PROJECT_ROOT
from systrade.data.model import check_symbol
from systrade.data.universe import STARTING_UNIVERSE, starting_symbols

_REQUIRED_ETFS = (
    "SPY",
    "QQQ",
    "IWM",
    "TLT",
    "GLD",
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLI",
    "XLY",
    "XLP",
    "XLU",
    "XLB",
    "XLRE",
    "XLC",
)
_STOCKS = ("AAPL", "MSFT", "AMZN", "JPM", "JNJ", "XOM")


def test_universe_shape() -> None:
    etfs = [item for item in STARTING_UNIVERSE if item.kind == "etf"]
    stocks = [item for item in STARTING_UNIVERSE if item.kind == "stock"]
    assert 10 <= len(etfs) <= 20
    assert {item.symbol for item in etfs} >= set(_REQUIRED_ETFS)
    assert tuple(item.symbol for item in stocks) == _STOCKS
    assert len({item.symbol for item in STARTING_UNIVERSE}) == len(STARTING_UNIVERSE)
    for item in STARTING_UNIVERSE:
        check_symbol(item.symbol)
    assert starting_symbols("etf")[0] == "SPY"
    assert set(starting_symbols("stock")) == set(_STOCKS)


def test_data_doc_covers_the_contract() -> None:
    text = (PROJECT_ROOT / "docs" / "data.md").read_text(encoding="utf-8").lower()
    assert "survivorship" in text
    assert "signal" in text
    assert "fill" in text
    assert "yfinance" in text
    assert "snapshot" in text
