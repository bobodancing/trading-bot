from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback import (
    MacdSignalTrendingUp4hStagedDeriskGivebackStrategy,
)


def _entry_frame(
    length=30,
    macd_values=(-0.05, 0.08),
    signal_values=(-0.04, 0.02),
    atr=1200.0,
    ema_20=106000.0,
    close_offset=500.0,
):
    idx = pd.date_range("2026-01-01", periods=length, freq="4h", tz="UTC")
    close = pd.Series([100000.0 + i * 250.0 for i in range(length)], index=idx)
    macd_series = [0.01] * max(length - 2, 0) + list(macd_values)
    signal_series = [0.0] * max(length - 2, 0) + list(signal_values)
    ema_20_series = [float(ema_20)] * length
    close.iloc[-1] = ema_20 + close_offset
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 100.0,
            "high": close + 300.0,
            "low": close - 300.0,
            "close": close,
            "volume": 1000.0,
            "macd": macd_series,
            "macd_signal": signal_series,
            "macd_hist": [m - s for m, s in zip(macd_series, signal_series)],
            "ema_20": ema_20_series,
            "atr": atr,
        },
        index=idx,
    )


def _trend_frame(length=60, ema_20_values=(100000.0,), ema_50_values=(99000.0,)):
    idx = pd.date_range("2025-12-01", periods=length, freq="D", tz="UTC")
    ema_20_series = [float(ema_20_values[0])] * length
    ema_50_series = [float(ema_50_values[0])] * length
    return pd.DataFrame(
        {
            "timestamp": idx,
            "close": ema_20_series,
            "ema_20": ema_20_series,
            "ema_50": ema_50_series,
        },
        index=idx,
    )


def _context(entry_frame, trend_frame, symbols=None):
    symbols = symbols or ["BTC/USDT"]
    snapshot = SimpleNamespace(
        get=lambda symbol, timeframe: (
            entry_frame
            if symbol == "BTC/USDT" and timeframe == "4h"
            else trend_frame
            if symbol == "BTC/USDT" and timeframe == "1d"
            else pd.DataFrame()
        ),
        latest_timestamp=lambda symbol, timeframe: (
            entry_frame.index[-1].to_pydatetime()
            if timeframe == "4h"
            else trend_frame.index[-1].to_pydatetime()
        ),
        latest_close=lambda symbol, timeframe: (
            float(entry_frame["close"].iloc[-1])
            if timeframe == "4h"
            else float(trend_frame["close"].iloc[-1])
        ),
    )
    return StrategyContext(
        snapshot=snapshot,
        symbols=symbols,
        active_positions={},
        config=SimpleNamespace(),
        now=datetime.now(timezone.utc),
    )


def _position(
    *,
    entry_price=106500.0,
    current_sl=105000.0,
    initial_sl=105000.0,
    highest_price=108200.0,
    plugin_state=None,
):
    return SimpleNamespace(
        symbol="BTC/USDT",
        entry_time=datetime(2026, 1, 5, tzinfo=timezone.utc),
        entry_price=entry_price,
        avg_entry=entry_price,
        current_sl=current_sl,
        initial_sl=initial_sl,
        highest_price=highest_price,
        plugin_state=dict(plugin_state or {}),
        exit_reason=None,
    )


def test_registry_loads_macd_signal_trending_up_4h_staged_derisk_giveback_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            ["macd_signal_btc_4h_trending_up_staged_derisk_giveback"]
        ),
        ["macd_signal_btc_4h_trending_up_staged_derisk_giveback"],
    )

    plugin = registry.require("macd_signal_btc_4h_trending_up_staged_derisk_giveback")
    assert isinstance(plugin, MacdSignalTrendingUp4hStagedDeriskGivebackStrategy)
    assert plugin.params["derisk_arm_r"] == pytest.approx(1.0)
    assert plugin.params["giveback_exit_arm_r"] == pytest.approx(1.5)


def test_macd_signal_trending_up_4h_staged_derisk_giveback_generates_long_intent():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()

    intents = plugin.generate_candidates(_context(_entry_frame(), _trend_frame()))

    assert len(intents) == 1
    assert (
        intents[0].strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback"
    )
    assert intents[0].entry_type == "macd_signal_cross_up"


def test_staged_derisk_triggers_partial_close_on_giveback_below_ema20():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.5)
    assert decision.new_sl == pytest.approx(106500.0)
    assert position.plugin_state[plugin.id]["derisk_done"] is True


def test_staged_derisk_only_fires_once():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    position = _position(
        highest_price=108200.0,
        plugin_state={plugin.id: {"derisk_done": True}},
    )

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.HOLD


def test_giveback_exit_closes_remaining_position_after_deeper_fade():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    position = _position(
        highest_price=110200.0,
        plugin_state={plugin.id: {"derisk_done": True}},
    )

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "GIVEBACK_EXIT"
    assert position.exit_reason == "GIVEBACK_EXIT"


def test_giveback_partial_does_not_fire_while_open_profit_is_still_above_one_r():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=2500.0)
    position = _position(highest_price=110200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.HOLD


def test_preserves_signal_cross_down_exit_when_giveback_is_not_armed():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()
    entry_frame = _entry_frame(macd_values=(0.20, 0.05), signal_values=(0.10, 0.08))
    position = _position(highest_price=107000.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_SIGNAL_CROSS_DOWN"


def test_preserves_trend_gate_loss_exit_precedence():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy()
    trend_frame = _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))
    position = _position(highest_price=110200.0)

    decision = plugin.update_position(_context(_entry_frame(), trend_frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "TREND_GATE_LOST"
