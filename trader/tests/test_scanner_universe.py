import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from scanner.universe_scanner import ScannerUniverseScanner, ScannerUniverseSettings
from trader.config import Config
from trader.strategies import StrategyPlugin
from trader.strategy_runtime import StrategyRuntime

PROMOTED_STRATEGIES = [
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter",
    "donchian_range_fade_4h_range_width_cv_013",
]


def _ohlcv(rows=320, freq="4h"):
    now = pd.Timestamp.now(tz="UTC")
    index = pd.date_range(end=now, periods=rows, freq=freq)
    base = pd.Series(range(rows), dtype="float64").to_numpy()
    close = 100.0 + base * 0.1
    return pd.DataFrame(
        {
            "timestamp": index,
            "open": close - 0.1,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0 + base,
        },
        index=index,
    )


class DummyProvider:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        self.calls.append((symbol, timeframe, limit))
        freq = "1d" if timeframe == "1d" else "4h"
        return _ohlcv(rows=max(limit, 320), freq=freq)


def _exchange():
    exchange = MagicMock()
    exchange.markets = {
        "BTC/USDT:USDT": {"symbol": "BTC/USDT:USDT"},
        "BTC/USDT:USDT-LOW": {"symbol": "BTC/USDT:USDT-LOW"},
        "ETH/USDT:USDT": {"symbol": "ETH/USDT:USDT"},
        "USDC/USDT:USDT": {"symbol": "USDC/USDT:USDT"},
        "LOW/USDT:USDT": {"symbol": "LOW/USDT:USDT"},
        "BTCUP/USDT:USDT": {"symbol": "BTCUP/USDT:USDT"},
    }
    exchange.fetch_tickers.return_value = {
        "BTC/USDT:USDT": {"symbol": "BTC/USDT:USDT", "quoteVolume": 90_000_000_000.0},
        "BTC/USDT:USDT-LOW": {"symbol": "BTC/USDT:USDT-LOW", "quoteVolume": 1_000.0},
        "ETH/USDT:USDT": {"symbol": "ETH/USDT:USDT", "quoteVolume": 40_000_000_000.0},
        "USDC/USDT:USDT": {"symbol": "USDC/USDT:USDT", "quoteVolume": 5_000_000_000.0},
        "LOW/USDT:USDT": {"symbol": "LOW/USDT:USDT", "quoteVolume": 10_000.0},
        "BTCUP/USDT:USDT": {"symbol": "BTCUP/USDT:USDT", "quoteVolume": 3_000_000_000.0},
    }
    return exchange


def _settings(tmp_path: Path):
    return ScannerUniverseSettings(
        output_json_path=tmp_path / "scanner_universe.json",
        top_n=2,
        candidate_scan_limit=5,
        min_quote_volume_usd=20_000_000.0,
        freshness_multiplier=100000.0,
        required_timeframes={"4h": 20, "1d": 20},
    )


def test_scanner_universe_filters_liquid_usdt_symbols_and_reason_codes(tmp_path):
    scanner = ScannerUniverseScanner(
        settings=_settings(tmp_path),
        exchange=_exchange(),
        data_provider=DummyProvider(),
    )

    report = scanner.scan(write=False)

    assert report["scanner_contract_version"] == "scanner-universe/v1"
    assert [item["symbol"] for item in report["eligible_symbols"]] == ["BTC/USDT", "ETH/USDT"]
    excluded = {
        item["symbol"]: set(item["reason_codes"])
        for item in report["excluded_symbols"]
    }
    assert "BTC/USDT" not in excluded
    assert "excluded_symbol" in excluded["USDC/USDT"]
    assert "low_volume" in excluded["LOW/USDT"]
    assert "excluded_pattern" in excluded["BTCUP/USDT"]


def test_scanner_universe_writes_json(tmp_path):
    scanner = ScannerUniverseScanner(
        settings=_settings(tmp_path),
        exchange=_exchange(),
        data_provider=DummyProvider(),
    )

    scanner.scan(write=True)

    payload = json.loads((tmp_path / "scanner_universe.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["filter_config"]["mode"] == "eligibility_only"
    assert payload["eligible_symbols"][0]["symbol"] == "BTC/USDT"


class _AuditCollector:
    def record_reject(self, **_kwargs):
        return None

    def record_entry(self, **_kwargs):
        return None


class _FakeBot:
    def __init__(self):
        self.active_trades = {}
        self._signal_audit = _AuditCollector()
        self.signal_scanner = SimpleNamespace(check_cooldowns=lambda symbol: True)
        self.precision_handler = SimpleNamespace()
        self.risk_manager = SimpleNamespace(get_balance=lambda: 10000.0)
        self.exchange = SimpleNamespace(markets={})
        self._scanner_symbol_meta = {}

    def load_scanner_results(self):
        return ["LEGACY/USDT"]


class _ScopedStrategy(StrategyPlugin):
    id = "scoped"
    required_timeframes = {}
    required_indicators = set()
    allowed_symbols = {"BTC/USDT", "ETH/USDT"}

    def generate_candidates(self, context):
        return []


class _DynamicStrategy(StrategyPlugin):
    id = "dynamic"
    required_timeframes = {}
    required_indicators = set()
    allowed_symbols = set()
    supports_dynamic_universe = True
    dynamic_universe_quote = "USDT"
    dynamic_universe_max_symbols = 2

    def generate_candidates(self, context):
        return []


def _write_universe(path: Path, eligible, *, expires_delta=timedelta(minutes=30)):
    now = datetime.now(timezone.utc)
    payload = {
        "scanner_contract_version": "scanner-universe/v1",
        "scan_time": now.isoformat(),
        "expires_at": (now + expires_delta).isoformat(),
        "status": "ok",
        "eligible_symbols": eligible,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_strategy_runtime_uses_scanner_universe_before_slot_scope(tmp_path):
    universe_path = tmp_path / "scanner_universe.json"
    _write_universe(
        universe_path,
        [
            {"symbol": "ETH/USDT", "rank": 1, "quote_volume_24h": 40_000_000_000.0},
            {"symbol": "SOL/USDT", "rank": 2, "quote_volume_24h": 10_000_000_000.0},
        ],
    )
    runtime = StrategyRuntime(_FakeBot())
    plugin = _ScopedStrategy()

    with patch.object(Config, "SCANNER_UNIVERSE_ENABLED", True), patch.object(
        Config,
        "SCANNER_UNIVERSE_JSON_PATH",
        str(universe_path),
    ), patch.object(Config, "USE_SCANNER_SYMBOLS", False), patch.object(
        Config,
        "SYMBOLS",
        ["BTC/USDT", "ETH/USDT"],
    ):
        base_symbols = runtime._base_symbols_for_entry_scan([plugin])
        scoped_symbols = runtime._symbols_for_snapshot(base_symbols, [plugin])

    assert base_symbols == ["ETH/USDT", "SOL/USDT"]
    assert scoped_symbols == ["ETH/USDT"]


def test_promoted_slots_consume_scanner_universe_symbols(tmp_path):
    universe_path = tmp_path / "scanner_universe.json"
    scanner_symbols = [
        {"symbol": "BTC/USDT", "rank": 1, "quote_volume_24h": 90_000_000_000.0},
        {"symbol": "ETH/USDT", "rank": 2, "quote_volume_24h": 40_000_000_000.0},
        {"symbol": "SOL/USDT", "rank": 3, "quote_volume_24h": 1_000_000_000.0},
    ]
    _write_universe(universe_path, scanner_symbols)

    with patch.object(Config, "STRATEGY_RUNTIME_ENABLED", True), patch.object(
        Config,
        "ENABLED_STRATEGIES",
        PROMOTED_STRATEGIES,
    ), patch.object(Config, "SCANNER_UNIVERSE_ENABLED", True), patch.object(
        Config,
        "SCANNER_UNIVERSE_JSON_PATH",
        str(universe_path),
    ), patch.object(Config, "USE_SCANNER_SYMBOLS", False), patch.object(
        Config,
        "SYMBOLS",
        ["BTC/USDT", "ETH/USDT"],
    ):
        runtime = StrategyRuntime(_FakeBot())
        plugins = runtime.enabled_plugins()
        base_symbols = runtime._base_symbols_for_entry_scan(plugins)
        snapshot_symbols = runtime._symbols_for_snapshot(base_symbols, plugins)
        plugin_symbols = {
            plugin.id: runtime._plugin_symbols(plugin, base_symbols)
            for plugin in plugins
        }

    expected = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    assert base_symbols == expected
    assert snapshot_symbols == expected
    for strategy_id in PROMOTED_STRATEGIES:
        assert plugin_symbols[strategy_id] == expected


def test_strategy_runtime_falls_back_to_fixed_symbols_when_universe_stale(tmp_path):
    universe_path = tmp_path / "scanner_universe.json"
    _write_universe(
        universe_path,
        [{"symbol": "SOL/USDT", "rank": 1, "quote_volume_24h": 10_000_000_000.0}],
        expires_delta=timedelta(minutes=-1),
    )
    runtime = StrategyRuntime(_FakeBot())

    with patch.object(Config, "SCANNER_UNIVERSE_ENABLED", True), patch.object(
        Config,
        "SCANNER_UNIVERSE_JSON_PATH",
        str(universe_path),
    ), patch.object(Config, "USE_SCANNER_SYMBOLS", False), patch.object(
        Config,
        "SYMBOLS",
        ["BTC/USDT", "ETH/USDT"],
    ):
        symbols = runtime._base_symbols_for_entry_scan([_ScopedStrategy()])

    assert symbols == ["BTC/USDT", "ETH/USDT"]


def test_strategy_runtime_accepts_utf8_sig_scanner_universe(tmp_path):
    universe_path = tmp_path / "scanner_universe.json"
    now = datetime.now(timezone.utc)
    payload = {
        "scanner_contract_version": "scanner-universe/v1",
        "scan_time": now.isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
        "status": "ok",
        "eligible_symbols": [
            {"symbol": "SOL/USDT", "rank": 1, "quote_volume_24h": 10_000_000_000.0}
        ],
    }
    universe_path.write_text(json.dumps(payload), encoding="utf-8-sig")
    runtime = StrategyRuntime(_FakeBot())

    with patch.object(Config, "SCANNER_UNIVERSE_ENABLED", True), patch.object(
        Config,
        "SCANNER_UNIVERSE_JSON_PATH",
        str(universe_path),
    ), patch.object(Config, "USE_SCANNER_SYMBOLS", False), patch.object(
        Config,
        "SYMBOLS",
        ["BTC/USDT", "ETH/USDT"],
    ):
        symbols = runtime._base_symbols_for_entry_scan([_DynamicStrategy()])

    assert symbols == ["SOL/USDT"]


def test_dynamic_universe_plugin_opt_in_can_receive_scanner_symbols():
    runtime = StrategyRuntime(_FakeBot())

    symbols = runtime._plugin_symbols(
        _DynamicStrategy(),
        ["BTC/USDT", "ETH/USDT", "BTC/USDC", "SOL/USDT"],
    )

    assert symbols == ["BTC/USDT", "ETH/USDT"]
