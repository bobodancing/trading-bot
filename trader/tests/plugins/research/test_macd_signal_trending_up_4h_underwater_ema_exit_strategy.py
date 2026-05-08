from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_underwater_ema_exit import (
    MacdSignalTrendingUp4hUnderwaterEmaExitStrategy,
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


def _position(entry_time, entry_price=106500.0):
    return SimpleNamespace(
        symbol="BTC/USDT",
        entry_time=entry_time,
        entry_price=entry_price,
    )


def test_registry_loads_macd_signal_trending_up_4h_underwater_ema_exit_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["macd_signal_btc_4h_trending_up_underwater_ema_exit"]),
        ["macd_signal_btc_4h_trending_up_underwater_ema_exit"],
    )

    plugin = registry.require("macd_signal_btc_4h_trending_up_underwater_ema_exit")
    assert isinstance(plugin, MacdSignalTrendingUp4hUnderwaterEmaExitStrategy)
    assert plugin.params["underwater_ema_exit_bars"] == 1
    assert plugin.params["entry_timeframe"] == "4h"


def test_macd_signal_trending_up_4h_underwater_ema_exit_generates_long_intent():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy()

    intents = plugin.generate_candidates(_context(_entry_frame(), _trend_frame()))

    assert len(intents) == 1
    assert intents[0].strategy_id == "macd_signal_btc_4h_trending_up_underwater_ema_exit"
    assert intents[0].entry_type == "macd_signal_cross_up"


def test_macd_signal_trending_up_4h_underwater_ema_exit_closes_underwater_below_ema20():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy(
        params={"underwater_ema_exit_bars": 1}
    )
    entry_frame = _entry_frame(close_offset=-50.0)
    latest_ts = entry_frame.index[-1].to_pydatetime()
    position = _position(latest_ts - timedelta(hours=4), entry_price=106500.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "UNDERWATER_EMA20_EXIT"
    assert decision.metadata["bars_since_entry"] == 1


def test_macd_signal_trending_up_4h_underwater_ema_exit_waits_for_grace_bar_count():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy(
        params={"underwater_ema_exit_bars": 2}
    )
    entry_frame = _entry_frame(close_offset=-50.0)
    latest_ts = entry_frame.index[-1].to_pydatetime()
    position = _position(latest_ts - timedelta(hours=4), entry_price=106500.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.HOLD


def test_macd_signal_trending_up_4h_underwater_ema_exit_holds_if_not_underwater():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy(
        params={"underwater_ema_exit_bars": 1}
    )
    entry_frame = _entry_frame(close_offset=-50.0)
    latest_ts = entry_frame.index[-1].to_pydatetime()
    position = _position(latest_ts - timedelta(hours=4), entry_price=105900.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.HOLD


def test_macd_signal_trending_up_4h_underwater_ema_exit_holds_if_still_above_ema20():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy(
        params={"underwater_ema_exit_bars": 1}
    )
    entry_frame = _entry_frame(close_offset=150.0)
    latest_ts = entry_frame.index[-1].to_pydatetime()
    position = _position(latest_ts - timedelta(hours=4), entry_price=106300.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.HOLD


def test_macd_signal_trending_up_4h_underwater_ema_exit_preserves_signal_cross_down_exit():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy()
    entry_frame = _entry_frame(macd_values=(0.20, 0.05), signal_values=(0.10, 0.08))
    latest_ts = entry_frame.index[-1].to_pydatetime()
    position = _position(latest_ts - timedelta(hours=12))

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_SIGNAL_CROSS_DOWN"


def test_macd_signal_trending_up_4h_underwater_ema_exit_preserves_trend_gate_loss_exit():
    plugin = MacdSignalTrendingUp4hUnderwaterEmaExitStrategy()
    trend_frame = _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))
    latest_ts = _entry_frame().index[-1].to_pydatetime()
    position = _position(latest_ts - timedelta(hours=12))

    decision = plugin.update_position(_context(_entry_frame(), trend_frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "TREND_GATE_LOST"


def test_macd_signal_trending_up_4h_underwater_ema_exit_counts_elapsed_4h_bars():
    latest_ts = datetime(2026, 1, 2, 8, tzinfo=timezone.utc)

    assert (
        MacdSignalTrendingUp4hUnderwaterEmaExitStrategy._bars_since_entry(
            latest_ts, latest_ts - timedelta(hours=9), "4h"
        )
        == 2
    )
