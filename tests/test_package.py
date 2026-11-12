import importlib

import pytest

import systrade

SUBPACKAGES = ["data", "strategies", "backtest", "risk", "validation", "paper"]


def test_version() -> None:
    assert systrade.__version__ == "0.1.0"


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackages_import(name: str) -> None:
    importlib.import_module(f"systrade.{name}")
