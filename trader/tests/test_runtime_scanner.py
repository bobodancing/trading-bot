import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from scanner.runtime_scanner import RuntimeScanner, RuntimeScannerSettings
from trader.config import Config


PROMOTED_STRATEGIES = [
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter",
    "donchian_range_fade_4h_range_width_cv_013",
]


class DummyProvider:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        self.calls.append((symbol, timeframe, limit))
        freq = "1d" if timeframe == "1d" else "4h"
        return _ohlcv(rows=max(limit, 320), freq=freq)


def _ohlcv(rows=320, freq="4h"):
    index = pd.date_range("2026-01-01", periods=rows, freq=freq, tz="UTC")
    base = pd.Series(range(rows), dtype="float64").to_numpy()
    close = 100.0 + base * 0.2
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


def _scanner(tmp_path: Path, provider: DummyProvider):
    exchange = MagicMock()
    exchange.fetch_ticker.return_value = {
        "last": 100.0,
        "bid": 99.9,
        "ask": 100.1,
        "quoteVolume": 1_000_000_000.0,
    }
    settings = RuntimeScannerSettings(output_json_path=tmp_path / "runtime_scanner.json")
    return RuntimeScanner(settings=settings, exchange=exchange, data_provider=provider)


def test_promoted_runtime_default_does_not_use_scanner_symbols():
    assert Config.SYMBOLS == ["BTC/USDT", "ETH/USDT"]
    assert Config.USE_SCANNER_SYMBOLS is False
    assert Config.RUNTIME_SCANNER_JSON_PATH == "runtime_scanner.json"


def test_runtime_scanner_uses_plugin_scope_not_legacy_bot_universe(tmp_path):
    provider = DummyProvider()

    with patch.object(Config, "ENABLED_STRATEGIES", PROMOTED_STRATEGIES), patch.object(
        Config,
        "SYMBOLS",
        ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT"],
    ):
        report = _scanner(tmp_path, provider).scan(write=False)

    assert report["scanner_contract_version"] == "runtime-context/v1"
    assert report["runtime_selection_feeds_trading"] is False
    assert report["runtime_symbols"] == ["BTC/USDT", "ETH/USDT"]
    assert "SOL/USDT" not in report["symbols"]
    assert "DOGE/USDT" not in report["symbols"]
    assert "bot_symbols" not in report
    assert "hot_symbols" not in report
    assert ("ETH/USDT", "1d") not in {
        (symbol, timeframe) for symbol, timeframe, _limit in provider.calls
    }
    assert report["plugin_scopes"][PROMOTED_STRATEGIES[0]]["slot_hint"] == "slot_a"
    assert report["plugin_scopes"][PROMOTED_STRATEGIES[1]]["slot_hint"] == "slot_b"


def test_runtime_scanner_writes_advisory_json(tmp_path):
    provider = DummyProvider()

    with patch.object(Config, "ENABLED_STRATEGIES", PROMOTED_STRATEGIES), patch.object(
        Config,
        "SYMBOLS",
        ["BTC/USDT", "ETH/USDT"],
    ):
        scanner = _scanner(tmp_path, provider)
        report = scanner.scan(write=True)

    payload = json.loads((tmp_path / "runtime_scanner.json").read_text(encoding="utf-8"))
    assert payload["scanner_contract_version"] == "runtime-context/v1"
    assert payload["deployment_boundary"]["feeds_strategy_runtime"] is False
    assert payload["runtime_symbols"] == report["runtime_symbols"]
    assert payload["symbols"]["BTC/USDT"]["strategy_readiness"][PROMOTED_STRATEGIES[0]][
        "diagnostic_only"
    ] is True
