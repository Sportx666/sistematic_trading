from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from systrade.data.adjust import build_history
from systrade.data.cache import DataCache, load_universe, refresh_history
from systrade.data.model import (
    CacheMissError,
    CorporateAction,
    DailyBar,
    DataError,
    DownloadRecord,
    parameter_pairs,
)
from systrade.data.universe import starting_symbols
from tests.market_fixtures import bar, known_split_dividend


class _MemoryProvider:
    name = "fixture"

    def __init__(self, bars: tuple[DailyBar, ...], actions: tuple[CorporateAction, ...]) -> None:
        self._bars = bars
        self._actions = actions
        self.calls = 0

    def fetch_daily(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> tuple[tuple[DailyBar, ...], tuple[CorporateAction, ...]]:
        self.calls += 1
        assert symbol == "SPY"
        assert start == date(2020, 8, 27)
        assert end == date(2020, 9, 4)
        return self._bars, self._actions


def _record(symbol: str, source: str = "fixture") -> DownloadRecord:
    return DownloadRecord(
        symbol=symbol,
        source=source,
        downloaded_at=datetime(2026, 11, 12, 19, 28, tzinfo=UTC),
        parameters=parameter_pairs({"start": "2024-06-03", "end": "2024-06-05", "interval": "1d"}),
        row_count=2,
        action_count=0,
    )


def _tiny(symbol: str) -> tuple[DailyBar, ...]:
    return (bar("2024-06-03", 100), bar("2024-06-04", 101))


def test_roundtrip_keeps_raw_and_adjusted_agreement(tmp_path: Path) -> None:
    bars, actions = known_split_dividend()
    history = build_history("AAPL", bars, actions)
    cache = DataCache(tmp_path)
    cache.write(
        history,
        DownloadRecord(
            symbol="AAPL",
            source="fixture",
            downloaded_at=datetime(2026, 11, 12, 19, 28, tzinfo=UTC),
            parameters=parameter_pairs({"start": "2020-08-27", "end": "2020-09-04"}),
            row_count=len(history.bars),
            action_count=len(history.actions),
        ),
    )
    loaded = cache.read("AAPL")
    assert [item.session for item in loaded.bars] == [item.session for item in loaded.adjusted]
    assert loaded.adjusted[1].close == pytest.approx(history.adjusted[1].close)
    assert loaded.bars[1].close == pytest.approx(history.bars[1].close)
    assert loaded.actions == history.actions


def test_load_universe_reads_the_whole_list_in_one_call(tmp_path: Path) -> None:
    cache = DataCache(tmp_path)
    for symbol in starting_symbols():
        cache.write(build_history(symbol, _tiny(symbol), ()), _record(symbol))
    panel = load_universe(cache)
    assert panel.symbols == starting_symbols()
    assert panel["SPY"].bars[0].close == pytest.approx(100)
    assert panel["XOM"].symbol == "XOM"
    assert len(panel.snapshot_id) == 64

    again = DataCache(tmp_path)
    assert load_universe(again).snapshot_id == panel.snapshot_id

    changed = build_history("SPY", (bar("2024-06-03", 100), bar("2024-06-04", 250)), ())
    cache.write(changed, _record("SPY"))
    assert load_universe(cache).snapshot_id != panel.snapshot_id


def test_load_universe_names_every_missing_symbol(tmp_path: Path) -> None:
    cache = DataCache(tmp_path)
    cache.write(build_history("SPY", _tiny("SPY"), ()), _record("SPY"))
    with pytest.raises(CacheMissError, match="QQQ"):
        load_universe(cache, symbols=("SPY", "QQQ"))


def test_refresh_records_source_timestamp_and_parameters(tmp_path: Path) -> None:
    bars, actions = known_split_dividend()
    provider = _MemoryProvider(bars, actions)
    cache = DataCache(tmp_path)
    when = datetime(2026, 11, 12, 19, 28, tzinfo=UTC)
    refresh_history(
        "SPY",
        date(2020, 8, 27),
        date(2020, 9, 4),
        provider,
        cache,
        downloaded_at=when,
    )
    assert provider.calls == 1
    stored = load_universe(cache, symbols=("SPY",))
    assert stored["SPY"].adjusted[1].close == pytest.approx(
        build_history("SPY", bars, actions).adjusted[1].close
    )
    manifest = cache.read_manifest()
    assert len(manifest) == 1
    record = manifest[0]
    assert record.source == "fixture"
    assert record.downloaded_at == when
    assert dict(record.parameters)["start"] == "2020-08-27"
    assert dict(record.parameters)["end"] == "2020-09-04"
    assert dict(record.parameters)["price_basis"] == "raw_as_traded"
    assert record.row_count == len(bars)

    refresh_history(
        "SPY",
        date(2020, 8, 27),
        date(2020, 9, 4),
        provider,
        cache,
        downloaded_at=when,
    )
    assert len(cache.read_manifest()) == 2


def test_cache_rejects_bad_symbols_and_empty_histories(tmp_path: Path) -> None:
    cache = DataCache(tmp_path)
    with pytest.raises(ValueError):
        cache.contains("../SPY")
    with pytest.raises(DataError):
        cache.write(build_history("SPY", (), ()), _record("SPY"))
