"""Market data acquisition, caching, validation and corporate actions (M2).

Signals use the adjusted series. Fills and P&L use the raw series plus the
corporate-action table. The contract is in ``docs/data.md``.
"""

from systrade.data.adjust import adjust_bars, build_history
from systrade.data.cache import (
    DataCache,
    content_id,
    default_cache_dir,
    load_universe,
    refresh_history,
)
from systrade.data.calendar import nyse_holidays, nyse_sessions
from systrade.data.model import (
    AdjustmentError,
    CacheMissError,
    CorporateAction,
    DailyBar,
    DataError,
    DownloadRecord,
    ProviderError,
    SymbolHistory,
    UniverseData,
)
from systrade.data.provider import DataProvider, YFinanceProvider, parse_yfinance_frame
from systrade.data.universe import (
    STARTING_UNIVERSE,
    SUGGESTED_HISTORY_START,
    Instrument,
    starting_symbols,
)
from systrade.data.validate import (
    DEFAULT_MAX_ABS_DAILY_RETURN,
    ValidationIssue,
    ValidationReport,
    validate_history,
    validate_universe,
)

__all__ = [
    "DEFAULT_MAX_ABS_DAILY_RETURN",
    "STARTING_UNIVERSE",
    "SUGGESTED_HISTORY_START",
    "AdjustmentError",
    "CacheMissError",
    "CorporateAction",
    "DailyBar",
    "DataCache",
    "DataError",
    "DataProvider",
    "DownloadRecord",
    "Instrument",
    "ProviderError",
    "SymbolHistory",
    "UniverseData",
    "ValidationIssue",
    "ValidationReport",
    "YFinanceProvider",
    "adjust_bars",
    "build_history",
    "content_id",
    "default_cache_dir",
    "load_universe",
    "nyse_holidays",
    "nyse_sessions",
    "parse_yfinance_frame",
    "refresh_history",
    "starting_symbols",
    "validate_history",
    "validate_universe",
]
