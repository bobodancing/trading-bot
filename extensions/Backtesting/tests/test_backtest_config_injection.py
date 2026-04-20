import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest_bot import create_backtest_bot
from backtest_engine import _backtest_context
from bot_compat import get_config_class
from config_presets import (
    ALLOWED_BACKTEST_OVERRIDES,
    apply_strategy_params_override,
    diagnostic_arbiter_off,
    plugin_runtime_defaults,
)
from trader.strategies.plugins._catalog import get_strategy_catalog
from mock_components import MockOrderEngine
from signal_audit import SignalAuditCollector
from time_series_engine import TimeSeriesEngine


def _ohlcv(rows=90):
    idx = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + rows), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def _fixture_runtime_overrides():
    return {
        "SYMBOLS": ["BTC/USDT"],
        "USE_SCANNER_SYMBOLS": False,
        "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
        "REGIME_ARBITER_ENABLED": False,
        "REGIME_ROUTER_ENABLED": False,
        "STRATEGY_RUNTIME_ENABLED": True,
        "ENABLED_STRATEGIES": ["fixture_long"],
    }


def _fixture_bot(*, allowed_plugin_ids):
    data = {
        "BTC/USDT": {
            "1h": _ohlcv(),
            "4h": _ohlcv(40),
            "1d": _ohlcv(20),
        }
    }
    tse = TimeSeriesEngine(data)
    tse.set_time(data["BTC/USDT"]["1h"].index[-1])
    bot = create_backtest_bot(
        tse,
        MockOrderEngine(tse, initial_balance=10000.0),
        _fixture_runtime_overrides(),
        allowed_plugin_ids=allowed_plugin_ids,
    )
    bot._signal_audit = SignalAuditCollector()
    return bot


def test_backtest_override_rejects_unknown_key():
    with pytest.raises(ValueError, match="Unknown backtest Config override"):
        with _backtest_context({"NOT_A_REAL_CONFIG_KEY": True}):
            pass


def test_backtest_override_rejects_forbidden_key():
    with pytest.raises(ValueError, match="Forbidden backtest Config override"):
        with _backtest_context({"STRATEGY_ROUTER_POLICY": "fail_open"}):
            pass


def test_backtest_override_whitelist_matches_current_config_attrs():
    Config = get_config_class()
    missing = sorted(key for key in ALLOWED_BACKTEST_OVERRIDES if not hasattr(Config, key))
    assert missing == []


def test_backtest_override_restores_config_after_exit():
    Config = get_config_class()
    original = Config.REGIME_ARBITER_ENABLED

    with _backtest_context({"REGIME_ARBITER_ENABLED": not original}) as ScopedConfig:
        assert ScopedConfig.REGIME_ARBITER_ENABLED is (not original)

    assert Config.REGIME_ARBITER_ENABLED is original


def test_plugin_runtime_defaults_preset_matches_config_defaults():
    Config = get_config_class()
    preset = plugin_runtime_defaults()

    assert preset
    for key, value in preset.items():
        assert value == getattr(Config, key)

    assert preset["REGIME_ARBITER_ENABLED"] is True
    assert preset["MACRO_OVERLAY_ENABLED"] is False
    assert "STRATEGY_CATALOG" not in preset
    if "BTC_TREND_FILTER_ENABLED" in preset:
        assert preset["BTC_TREND_FILTER_ENABLED"] is True


def test_diagnostic_arbiter_off_only_disables_arbiter_from_baseline():
    parity = plugin_runtime_defaults()
    diagnostic = diagnostic_arbiter_off()

    assert diagnostic["REGIME_ARBITER_ENABLED"] is False
    for key, value in parity.items():
        if key != "REGIME_ARBITER_ENABLED":
            assert diagnostic[key] == value


def test_backtest_allowed_plugin_ids_blocks_unlisted_plugin():
    bot = _fixture_bot(allowed_plugin_ids=["fixture_exit"])

    bot.scan_for_signals()

    assert "BTC/USDT" not in bot.active_trades
    summary = bot._signal_audit.summary()
    assert summary["lane_suppressed_by"] == {"allowlist": 1}
    assert summary["rejects_by_reason"] == {"backtest_plugin_id_allowlist": 1}


def test_backtest_allowed_plugin_ids_allows_listed_plugin():
    bot = _fixture_bot(allowed_plugin_ids=["fixture_long"])

    bot.scan_for_signals()

    assert "BTC/USDT" in bot.active_trades
    summary = bot._signal_audit.summary()
    assert summary["lane_candidates_by_signal_type"] == {"fixture_long": 1}
    assert summary["lane_selected_by_signal_type"] == {"fixture_long": 1}


def test_strategy_params_override_applies_to_catalog_copy_only():
    catalog = get_strategy_catalog(["fixture_long"])

    scoped = apply_strategy_params_override(
        catalog,
        {"fixture_long": {"stop_pct": 0.02}},
    )

    assert scoped["fixture_long"]["params"]["stop_pct"] == 0.02
    assert "stop_pct" not in catalog["fixture_long"]["params"]
    assert "stop_pct" not in get_strategy_catalog(["fixture_long"])["fixture_long"]["params"]


def test_strategy_params_override_rejects_unknown_param():
    catalog = get_strategy_catalog(["fixture_long"])

    with pytest.raises(ValueError, match="unknown param"):
        apply_strategy_params_override(catalog, {"fixture_long": {"not_real": 1}})
