"""Local Parquet cache. Reads do not touch the network.

Layout (under ``data/cache`` by default, gitignored):

- ``ohlcv/{SYMBOL}.parquet`` — raw and adjusted daily bars
- ``actions/{SYMBOL}.parquet`` — splits and cash distributions
- ``manifest.jsonl`` — one JSON object per download

``load_universe`` is the single call that returns the whole starting universe
from that cache.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from systrade.config import DATA_DIR
from systrade.data.adjust import build_history
from systrade.data.model import (
    ActionKind,
    CacheMissError,
    CorporateAction,
    DailyBar,
    DataError,
    DownloadRecord,
    ProviderError,
    SymbolHistory,
    UniverseData,
    check_symbol,
    parameter_pairs,
)
from systrade.data.provider import DataProvider
from systrade.data.universe import starting_symbols

OHLCV_COLUMNS = (
    "session",
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "volume_raw",
    "open_adj",
    "high_adj",
    "low_adj",
    "close_adj",
    "volume_adj",
)
ACTION_COLUMNS = ("session", "kind", "amount")


def default_cache_dir() -> Path:
    """Gitignored cache directory, ``data/cache``."""
    return DATA_DIR / "cache"


class DataCache:
    """Parquet files plus an append-only download manifest."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.jsonl"

    def contains(self, symbol: str) -> bool:
        check_symbol(symbol)
        return self._ohlcv_path(symbol).is_file() and self._actions_path(symbol).is_file()

    def write(self, history: SymbolHistory, record: DownloadRecord) -> None:
        """Replace one symbol's files and append a manifest line."""
        _check_history(history)
        if record.symbol != history.symbol:
            raise DataError("download record symbol does not match the history")
        _write_parquet(self._ohlcv_path(history.symbol), _ohlcv_frame(history))
        _write_parquet(self._actions_path(history.symbol), _actions_frame(history))
        self._append_manifest(record)

    def read(self, symbol: str) -> SymbolHistory:
        """Return the stored series. Does not recompute the adjustment."""
        check_symbol(symbol)
        if not self.contains(symbol):
            raise CacheMissError(f"{symbol} is not in the local cache")
        raw, adjusted = _read_ohlcv(self._ohlcv_path(symbol))
        actions = _read_actions(self._actions_path(symbol))
        return SymbolHistory(symbol=symbol, bars=raw, adjusted=adjusted, actions=actions)

    def read_many(self, symbols: Sequence[str]) -> UniverseData:
        """Load every requested symbol or raise with the full missing list."""
        chosen = tuple(check_symbol(symbol) for symbol in symbols)
        missing = [symbol for symbol in chosen if not self.contains(symbol)]
        if missing:
            raise CacheMissError("not in the local cache: " + ", ".join(missing))
        histories = tuple(self.read(symbol) for symbol in chosen)
        return UniverseData(
            symbols=chosen,
            histories=histories,
            snapshot_id=content_id(histories),
        )

    def read_manifest(self) -> tuple[DownloadRecord, ...]:
        path = self.manifest_path
        if not path.is_file():
            return ()
        records: list[DownloadRecord] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataError(f"manifest line {line_number} is not JSON") from exc
            records.append(_record_from_payload(payload))
        return tuple(records)

    def _ohlcv_path(self, symbol: str) -> Path:
        return self.root / "ohlcv" / f"{symbol}.parquet"

    def _actions_path(self, symbol: str) -> Path:
        return self.root / "actions" / f"{symbol}.parquet"

    def _append_manifest(self, record: DownloadRecord) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        line = json.dumps(_record_payload(record), sort_keys=True)
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def load_universe(
    cache: DataCache | None = None,
    symbols: Sequence[str] | None = None,
) -> UniverseData:
    """Load the starting universe from the local cache. Does not download.

    Pass ``symbols`` to load a subset. The default is every name in
    ``STARTING_UNIVERSE``, in that order. ``snapshot_id`` identifies the
    logical bars, adjusted bars and actions (not the Parquet bytes).
    """
    store = DataCache(default_cache_dir()) if cache is None else cache
    chosen = starting_symbols() if symbols is None else symbols
    return store.read_many(chosen)


def refresh_history(
    symbol: str,
    start: date,
    end: date,
    provider: DataProvider,
    cache: DataCache,
    *,
    downloaded_at: datetime | None = None,
) -> SymbolHistory:
    """Download one symbol, adjust it, and record the request in the manifest.

    This is the only function that calls the provider. Tests pass a fake
    provider; ``YFinanceProvider`` is what uses the network.
    """
    check_symbol(symbol)
    when = datetime.now(UTC) if downloaded_at is None else downloaded_at
    if when.tzinfo is None:
        raise ValueError("downloaded_at must be timezone-aware")
    bars, actions = provider.fetch_daily(symbol, start, end)
    if not bars:
        raise ProviderError(f"{symbol}: provider returned no bars")
    history = build_history(symbol, bars, actions)
    record = DownloadRecord(
        symbol=symbol,
        source=provider.name,
        downloaded_at=when,
        parameters=parameter_pairs(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "interval": "1d",
                "price_basis": "raw_as_traded",
                "adjustment": "backward_split_and_dividend",
            }
        ),
        row_count=len(history.bars),
        action_count=len(history.actions),
    )
    cache.write(history, record)
    return history


def content_id(histories: Sequence[SymbolHistory]) -> str:
    """sha256 of the logical content, stable across Parquet rewrites."""
    payload = [
        _history_payload(history) for history in sorted(histories, key=lambda item: item.symbol)
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _check_history(history: SymbolHistory) -> None:
    check_symbol(history.symbol)
    if not history.bars:
        raise DataError(f"{history.symbol}: refusing to cache an empty history")
    raw_sessions = [bar.session for bar in history.bars]
    adjusted_sessions = [bar.session for bar in history.adjusted]
    if raw_sessions != adjusted_sessions:
        raise DataError(f"{history.symbol}: raw and adjusted sessions differ")
    if raw_sessions != sorted(raw_sessions) or len(set(raw_sessions)) != len(raw_sessions):
        raise DataError(f"{history.symbol}: sessions must be sorted and unique")


def _stamp(session: date) -> datetime:
    return datetime(session.year, session.month, session.day)


def _ohlcv_frame(history: SymbolHistory) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for raw, adjusted in zip(history.bars, history.adjusted, strict=True):
        rows.append(
            {
                "session": _stamp(raw.session),
                "open_raw": raw.open,
                "high_raw": raw.high,
                "low_raw": raw.low,
                "close_raw": raw.close,
                "volume_raw": raw.volume,
                "open_adj": adjusted.open,
                "high_adj": adjusted.high,
                "low_adj": adjusted.low,
                "close_adj": adjusted.close,
                "volume_adj": adjusted.volume,
            }
        )
    return pd.DataFrame(rows, columns=list(OHLCV_COLUMNS))


def _actions_frame(history: SymbolHistory) -> pd.DataFrame:
    rows: list[dict[str, object]] = [
        {"session": _stamp(action.session), "kind": action.kind, "amount": action.amount}
        for action in history.actions
    ]
    if rows:
        return pd.DataFrame(rows, columns=list(ACTION_COLUMNS))
    return pd.DataFrame(
        {
            "session": pd.to_datetime(pd.Series([], dtype="datetime64[ns]")),
            "kind": pd.Series([], dtype="object"),
            "amount": pd.Series([], dtype="float64"),
        }
    )


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        frame.to_parquet(temporary, index=False, engine="pyarrow")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_ohlcv(path: Path) -> tuple[tuple[DailyBar, ...], tuple[DailyBar, ...]]:
    frame = pd.read_parquet(path, engine="pyarrow")
    _require_columns(frame, OHLCV_COLUMNS, path)
    raw: list[DailyBar] = []
    adjusted: list[DailyBar] = []
    for record in _records(frame):
        session = _as_date(record["session"])
        raw.append(
            DailyBar(
                session=session,
                open=_number(record["open_raw"]),
                high=_number(record["high_raw"]),
                low=_number(record["low_raw"]),
                close=_number(record["close_raw"]),
                volume=_number(record["volume_raw"]),
            )
        )
        adjusted.append(
            DailyBar(
                session=session,
                open=_number(record["open_adj"]),
                high=_number(record["high_adj"]),
                low=_number(record["low_adj"]),
                close=_number(record["close_adj"]),
                volume=_number(record["volume_adj"]),
            )
        )
    return tuple(raw), tuple(adjusted)


def _read_actions(path: Path) -> tuple[CorporateAction, ...]:
    frame = pd.read_parquet(path, engine="pyarrow")
    _require_columns(frame, ACTION_COLUMNS, path)
    actions: list[CorporateAction] = []
    for record in _records(frame):
        actions.append(
            CorporateAction(
                session=_as_date(record["session"]),
                kind=_kind(record["kind"]),
                amount=_number(record["amount"]),
            )
        )
    return tuple(actions)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    raw_records = frame.to_dict(orient="records")
    records: list[dict[str, object]] = []
    for record in raw_records:
        converted: dict[str, object] = {}
        for key, value in record.items():
            if not isinstance(key, str):
                raise DataError("cache column name is not a string")
            converted[key] = value
        records.append(converted)
    return records


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], path: Path) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataError(f"{path.name} is missing columns: {', '.join(missing)}")


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise DataError(f"cannot read a session date from {value!r}")


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DataError(f"expected a number, got {value!r}")
    return float(value)


def _kind(value: object) -> ActionKind:
    if value == "split":
        return "split"
    if value == "dividend":
        return "dividend"
    raise DataError(f"unknown corporate action kind: {value!r}")


def _history_payload(history: SymbolHistory) -> dict[str, object]:
    return {
        "symbol": history.symbol,
        "bars": [_bar_payload(bar) for bar in history.bars],
        "adjusted": [_bar_payload(bar) for bar in history.adjusted],
        "actions": [
            {"session": action.session.isoformat(), "kind": action.kind, "amount": action.amount}
            for action in history.actions
        ],
    }


def _bar_payload(bar: DailyBar) -> dict[str, object]:
    return {
        "session": bar.session.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
    }


def _record_payload(record: DownloadRecord) -> dict[str, object]:
    return {
        "symbol": record.symbol,
        "source": record.source,
        "downloaded_at": record.downloaded_at.astimezone(UTC).isoformat(timespec="seconds"),
        "parameters": dict(record.parameters),
        "row_count": record.row_count,
        "action_count": record.action_count,
    }


def _record_from_payload(payload: object) -> DownloadRecord:
    data = _object_dict(payload)
    parameters = _object_dict(data["parameters"])
    string_parameters: dict[str, str] = {}
    for key, value in parameters.items():
        if not isinstance(value, str):
            raise DataError(f"manifest parameter {key} is not a string")
        string_parameters[key] = value
    return DownloadRecord(
        symbol=check_symbol(_require_str(data, "symbol")),
        source=_require_str(data, "source"),
        downloaded_at=datetime.fromisoformat(_require_str(data, "downloaded_at")),
        parameters=parameter_pairs(string_parameters),
        row_count=_require_int(data, "row_count"),
        action_count=_require_int(data, "action_count"),
    )


def _object_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DataError("manifest entry is not an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise DataError("manifest key is not a string")
        result[key] = item
    return result


def _require_str(payload: Mapping[str, object], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise DataError(f"manifest field {key} is not a string")
    return value


def _require_int(payload: Mapping[str, object], key: str) -> int:
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(f"manifest field {key} is not an integer")
    return value
