import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from scanner.shadow_universe_scanner import (
    CONTRACT_VERSION,
    SLOT_B_LONG_ID,
    SLOT_B_SHORT_ID,
    ScannerShadowUniverseScanner,
    ShadowUniverseSettings,
    _matches_excluded_pattern,
)
from trader.config import Config


PROMOTED_STRATEGIES = [
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter",
    SLOT_B_LONG_ID,
    SLOT_B_SHORT_ID,
]


def _ohlcv(rows=260, freq="4h"):
    now = pd.Timestamp.now(tz="UTC").floor(freq)
    index = pd.date_range(end=now, periods=rows, freq=freq)
    base = pd.Series(range(rows), dtype="float64").to_numpy()
    wave = ((base % 6) - 3.0) * 0.15
    close = 100.0 + wave
    return pd.DataFrame(
        {
            "timestamp": index,
            "open": close,
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
        return _ohlcv(rows=max(limit, 260), freq=freq)


def _exchange():
    def market(symbol, *, underlying="COIN", contract_type="PERPETUAL"):
        base = symbol.split("/")[0]
        return {
            "symbol": f"{symbol}:USDT",
            "id": symbol.replace("/", ""),
            "base": base,
            "quote": "USDT",
            "settle": "USDT",
            "type": "swap",
            "active": True,
            "contract": True,
            "swap": True,
            "linear": True,
            "info": {
                "contractType": contract_type,
                "underlyingType": underlying,
                "underlyingSubType": ["Layer-1"] if underlying == "COIN" else ["TradFi"],
            },
        }

    exchange = MagicMock()
    exchange.markets = {
        "BTC/USDT:USDT": market("BTC/USDT"),
        "ETH/USDT:USDT": market("ETH/USDT"),
        "SOL/USDT:USDT": market("SOL/USDT"),
        "ADA/USDT:USDT": market("ADA/USDT"),
        "LINK/USDT:USDT": market("LINK/USDT"),
        "CL/USDT:USDT": market(
            "CL/USDT",
            underlying="COMMODITY",
            contract_type="TRADIFI_PERPETUAL",
        ),
        "USDC/USDT:USDT": market("USDC/USDT"),
        "LOW/USDT:USDT": market("LOW/USDT"),
        "BTCUP/USDT:USDT": market("BTCUP/USDT"),
    }
    exchange.fetch_tickers.return_value = {
        "BTC/USDT:USDT": {"symbol": "BTC/USDT:USDT", "quoteVolume": 90_000_000_000.0},
        "ETH/USDT:USDT": {"symbol": "ETH/USDT:USDT", "quoteVolume": 40_000_000_000.0},
        "CL/USDT:USDT": {"symbol": "CL/USDT:USDT", "quoteVolume": 6_000_000_000.0},
        "SOL/USDT:USDT": {"symbol": "SOL/USDT:USDT", "quoteVolume": 5_000_000_000.0},
        "USDC/USDT:USDT": {"symbol": "USDC/USDT:USDT", "quoteVolume": 2_000_000_000.0},
        "ADA/USDT:USDT": {"symbol": "ADA/USDT:USDT", "quoteVolume": 19_000_000.0},
        "LOW/USDT:USDT": {"symbol": "LOW/USDT:USDT", "quoteVolume": 10_000.0},
        "BTCUP/USDT:USDT": {"symbol": "BTCUP/USDT:USDT", "quoteVolume": 3_000_000_000.0},
    }
    return exchange


def _settings(tmp_path: Path):
    return ShadowUniverseSettings(
        output_json_path=tmp_path / "scanner_shadow_universe.json",
        output_csv_path=tmp_path / "scanner_shadow_universe.csv",
        report_path=tmp_path / "scanner_v3_shadow_universe_packet.md",
        top_n=4,
        candidate_scan_limit=5,
        min_quote_volume_usd=20_000_000.0,
        freshness_multiplier=100000.0,
        required_timeframes={"4h": 20},
        watchlist_symbols=("SOL/USDT", "ADA/USDT", "LINK/USDT"),
    )


def _scanner(tmp_path: Path):
    return ScannerShadowUniverseScanner(
        settings=_settings(tmp_path),
        exchange=_exchange(),
        data_provider=DummyProvider(),
    )


def test_shadow_scanner_contract_keeps_runtime_feed_disabled(tmp_path):
    with patch.object(Config, "SYMBOLS", ["BTC/USDT", "ETH/USDT"]), patch.object(
        Config,
        "ENABLED_STRATEGIES",
        PROMOTED_STRATEGIES,
    ), patch.object(Config, "USE_SCANNER_SYMBOLS", False), patch.object(
        Config,
        "SCANNER_UNIVERSE_ENABLED",
        False,
    ):
        report = _scanner(tmp_path).scan(write=False, write_csv=False)

    assert report["scanner_contract_version"] == CONTRACT_VERSION
    assert report["runtime_selection_feeds_trading"] is False
    assert report["deployment_boundary"]["feeds_strategy_runtime"] is False
    assert report["deployment_boundary"]["writes_hot_symbols"] is False
    assert report["baseline_runtime_symbols"] == ["BTC/USDT", "ETH/USDT"]
    assert report["config_scope"]["use_scanner_symbols"] is False
    assert report["config_scope"]["scanner_universe_enabled"] is False
    assert "hot_symbols" not in report
    assert "bot_symbols" not in report


def test_shadow_scanner_filters_symbols_and_keeps_baseline_separate(tmp_path):
    report = _scanner(tmp_path).scan(write=False, write_csv=False)

    assert [item["symbol"] for item in report["eligible_symbols"]] == [
        "BTC/USDT",
        "ETH/USDT",
        "CL/USDT",
        "SOL/USDT",
    ]
    assert {item["asset_class"] for item in report["eligible_symbols"]} == {
        "COIN",
        "COMMODITY",
    }
    shadow_symbols = {item["symbol"] for item in report["shadow_candidates"]}
    assert shadow_symbols == {"CL/USDT", "SOL/USDT"}
    assert set(report["baseline_runtime_diagnostics"]) == {"BTC/USDT", "ETH/USDT"}
    assert all(item["runtime_eligible"] is False for item in report["shadow_candidates"])
    assert any(
        item["symbol"] == "CL/USDT" and item["asset_class"] == "COMMODITY"
        for item in report["shadow_candidates"]
    )

    excluded = {item["symbol"]: set(item["reason_codes"]) for item in report["excluded_symbols"]}
    assert "excluded_symbol" in excluded["USDC/USDT"]
    assert "low_volume" in excluded["LOW/USDT"]
    assert "excluded_pattern" in excluded["BTCUP/USDT"]

    watchlist = {item["symbol"]: item for item in report["watchlist_availability"]}
    assert watchlist["SOL/USDT"]["in_top_eligible"] is True
    assert watchlist["ADA/USDT"]["data_ready"] is True
    assert "low_volume" in watchlist["ADA/USDT"]["reason_codes"]
    assert watchlist["LINK/USDT"]["data_ready"] is True
    assert "volume_unavailable" in watchlist["LINK/USDT"]["reason_codes"]


def test_shadow_scanner_includes_plugin_side_diagnostics(tmp_path):
    report = _scanner(tmp_path).scan(write=False, write_csv=False)

    by_side = {
        (item["strategy_id"], item["side"]): item
        for item in report["shadow_candidates"]
    }
    assert set(by_side) == {
        (SLOT_B_LONG_ID, "LONG"),
        (SLOT_B_SHORT_ID, "SHORT"),
    }
    for item in by_side.values():
        diagnostics = item["diagnostics"]
        assert item["slot_hint"] == "slot_b"
        assert item["asset_class"] in {"COIN", "COMMODITY"}
        assert item["contract_type"] in {"PERPETUAL", "TRADIFI_PERPETUAL"}
        assert item["decision"] == "observe"
        assert item["candidate_class"] in {
            "entry_ready_shadow",
            "near_setup",
            "regime_compatible",
            "eligible_only",
        }
        assert diagnostics["columns_ready"] is True
        assert "range_detected" in diagnostics
        assert "width_cv" in diagnostics
        assert "range_width_cv_max" in diagnostics
        assert "lower_touches" in diagnostics
        assert "upper_touches" in diagnostics
        assert "distance_to_lower_band_atr" in diagnostics
        assert "distance_to_upper_band_atr" in diagnostics
        assert "rsi_14" in diagnostics


def test_shadow_scanner_writes_json_csv_and_report_without_legacy_outputs(tmp_path):
    scanner = _scanner(tmp_path)

    report = scanner.scan(write=True, write_csv=True, write_report=True)

    payload = json.loads((tmp_path / "scanner_shadow_universe.json").read_text(encoding="utf-8"))
    csv_text = (tmp_path / "scanner_shadow_universe.csv").read_text(encoding="utf-8")
    report_text = (tmp_path / "scanner_v3_shadow_universe_packet.md").read_text(encoding="utf-8")

    assert payload["scanner_contract_version"] == CONTRACT_VERSION
    assert payload["runtime_selection_feeds_trading"] is False
    assert payload["filter_config"]["asset_class_filter"] == "none_asset_class_tagged_only"
    assert "SOL/USDT" in csv_text
    assert "asset_class" in csv_text
    assert "Scanner V3 Shadow Universe Packet" in report_text
    assert "Watchlist Availability" in report_text
    assert report["shadow_candidates"]
    assert not (tmp_path / "hot_symbols.json").exists()


def test_shadow_scanner_excluded_pattern_does_not_reject_short_base_symbols():
    assert _matches_excluded_pattern("BTCUP/USDT", "UP/USDT") is True
    assert _matches_excluded_pattern("JUP/USDT", "UP/USDT") is False
    assert _matches_excluded_pattern("ETHDOWN/USDT", "DOWN/USDT") is True
