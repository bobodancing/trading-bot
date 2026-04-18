import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest_bot import create_backtest_bot
from backtest_engine import _backtest_context
from bot_compat import get_config_class
from config_presets import ALLOWED_BACKTEST_OVERRIDES, diagnostic_arbiter_off, runtime_parity
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
        "STRATEGY_CATALOG": {
            "fixture_long": {
                "enabled": True,
                "module": "trader.strategies.plugins.fixture",
                "class": "FixtureLongStrategy",
                "params": {"symbol": "BTC/USDT", "stop_pct": 0.02},
            }
        },
    }


def _fixture_bot(*, allowed_signal_types):
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
        allowed_signal_types=allowed_signal_types,
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


def test_backtest_override_rejects_allowed_but_missing_config_attr():
    Config = get_config_class()
    missing_key = next(
        (key for key in sorted(ALLOWED_BACKTEST_OVERRIDES) if not hasattr(Config, key)),
        None,
    )
    if missing_key is None:
        pytest.skip("all allowed backtest overrides exist on this Config")

    with pytest.raises(ValueError, match="target does not exist"):
        with _backtest_context({missing_key: True}):
            pass


def test_backtest_override_restores_config_after_exit():
    Config = get_config_class()
    original = Config.REGIME_ARBITER_ENABLED

    with _backtest_context({"REGIME_ARBITER_ENABLED": not original}) as ScopedConfig:
        assert ScopedConfig.REGIME_ARBITER_ENABLED is (not original)

    assert Config.REGIME_ARBITER_ENABLED is original


def test_runtime_parity_preset_matches_config_defaults():
    Config = get_config_class()
    preset = runtime_parity()

    assert preset
    for key, value in preset.items():
        assert value == getattr(Config, key)

    assert preset["REGIME_ARBITER_ENABLED"] is True
    assert preset["MACRO_OVERLAY_ENABLED"] is False
    if "BTC_TREND_FILTER_ENABLED" in preset:
        assert preset["BTC_TREND_FILTER_ENABLED"] is True
    if "V7_MIN_SIGNAL_TIER" in preset:
        assert preset["V7_MIN_SIGNAL_TIER"] == "A"


def test_diagnostic_arbiter_off_only_disables_arbiter_from_parity():
    parity = runtime_parity()
    diagnostic = diagnostic_arbiter_off()

    assert diagnostic["REGIME_ARBITER_ENABLED"] is False
    for key, value in parity.items():
        if key != "REGIME_ARBITER_ENABLED":
            assert diagnostic[key] == value


def test_backtest_allowed_signal_types_blocks_unlisted_signal():
    bot = _fixture_bot(allowed_signal_types=["fixture_exit"])

    bot.scan_for_signals()

    assert "BTC/USDT" not in bot.active_trades
    summary = bot._signal_audit.summary()
    assert summary["lane_suppressed_by"] == {"allowlist": 1}
    assert summary["rejects_by_reason"] == {"backtest_signal_type_allowlist": 1}


def test_backtest_allowed_signal_types_allows_listed_signal():
    bot = _fixture_bot(allowed_signal_types=["fixture_long"])

    bot.scan_for_signals()

    assert "BTC/USDT" in bot.active_trades
    summary = bot._signal_audit.summary()
    assert summary["lane_candidates_by_signal_type"] == {"fixture_long": 1}
    assert summary["lane_selected_by_signal_type"] == {"fixture_long": 1}
