"""Project-wide defaults for the research programme.

Values here describe the programme's scope and default risk settings. Strategy-specific
parameters belong in that strategy's spec under ``strategies/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class ProgrammeScope:
    """What the research programme covers."""

    asset_classes: tuple[str, ...] = ("us_equity", "us_etf")
    timeframe: str = "1d"
    style: str = "swing"
    long_only: bool = True
    allow_leverage: bool = False
    allow_shorting: bool = False


@dataclass(frozen=True)
class AccountConfig:
    """The planned future account. Used to size backtests realistically."""

    risk_capital: float = 2_000.0
    base_currency: str = "EUR"
    trading_currency: str = "USD"
    max_risk_per_trade_pct: float = 1.0
    max_gross_exposure_pct: float = 100.0

    def __post_init__(self) -> None:
        if self.risk_capital <= 0:
            raise ValueError("risk_capital must be positive")
        if not 0 < self.max_risk_per_trade_pct <= 2.0:
            raise ValueError("max_risk_per_trade_pct must be in (0, 2]")
        if not 0 < self.max_gross_exposure_pct <= 100.0:
            raise ValueError("max_gross_exposure_pct must be in (0, 100]; no leverage")

    @property
    def max_risk_per_trade(self) -> float:
        """Maximum loss per trade, in base currency."""
        return self.risk_capital * self.max_risk_per_trade_pct / 100.0


@dataclass(frozen=True)
class Settings:
    scope: ProgrammeScope = field(default_factory=ProgrammeScope)
    account: AccountConfig = field(default_factory=AccountConfig)
    data_dir: Path = DATA_DIR


def default_settings() -> Settings:
    return Settings()
