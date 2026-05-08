from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_confirmed import (
    MacdSignalTrendingUp4hConfirmedStrategy,
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
            entry_frame.index[-1].to_pydatetime() if timeframe == "4h" else trend_frame.index[-1].to_pydatetime()
        ),
        latest_close=lambda symbol, timeframe: (
            float(entry_frame["close"].iloc[-1]) if timeframe == "4h" else float(trend_frame["close"].iloc[-1])
        ),
    )
    return StrategyContext(
        snapshot=snapshot,
        symbols=symbols,
        active_positions={},
        config=SimpleNamespace(),
        now=datetime.now(timezone.utc),
    )


def test_registry_loads_macd_signal_trending_up_4h_confirmed_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["macd_signal_btc_4h_trending_up_confirmed"]),
        ["macd_signal_btc_4h_trending_up_confirmed"],
    )

    plugin = registry.require("macd_signal_btc_4h_trending_up_confirmed")
    assert isinstance(plugin, MacdSignalTrendingUp4hConfirmedStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT"}
    assert plugin.params["entry_timeframe"] == "4h"
    assert plugin.params["trend_timeframe"] == "1d"
    assert plugin.params["trend_spread_min"] == pytest.approx(0.005)


def test_macd_signal_trending_up_4h_confirmed_generates_long_intent():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy(params={"stop_atr_mult": 1.5})
    entry_frame = _entry_frame(macd_values=(-0.02, 0.10), signal_values=(-0.01, 0.04), atr=800.0)
    trend_frame = _trend_frame(ema_20_values=(100000.0,), ema_50_values=(99000.0,))

    intents = plugin.generate_candidates(_context(entry_frame, trend_frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "macd_signal_btc_4h_trending_up_confirmed"
    assert intent.timeframe == "4h"
    assert intent.entry_type == "macd_signal_cross_up_confirmed"
    assert intent.stop_hint.price == pytest.approx(float(entry_frame["close"].iloc[-1]) - 1200.0)
    assert intent.metadata["entry_ema_20"] == pytest.approx(float(entry_frame["ema_20"].iloc[-1]))
    assert intent.metadata["macd_hist"] > intent.metadata["previous_macd_hist"]


def test_macd_signal_trending_up_4h_confirmed_requires_btc_scope():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()

    intents = plugin.generate_candidates(
        _context(_entry_frame(), _trend_frame(), symbols=["ETH/USDT"])
    )

    assert intents == []


def test_macd_signal_trending_up_4h_confirmed_blocks_when_daily_trend_is_not_up():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    trend_frame = _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))

    assert plugin.generate_candidates(_context(_entry_frame(), trend_frame)) == []


def test_macd_signal_trending_up_4h_confirmed_blocks_when_trend_spread_is_too_small():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy(params={"trend_spread_min": 0.01})
    trend_frame = _trend_frame(ema_20_values=(100500.0,), ema_50_values=(100000.0,))

    assert plugin.generate_candidates(_context(_entry_frame(), trend_frame)) == []


def test_macd_signal_trending_up_4h_confirmed_blocks_when_histogram_is_not_expanding():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    entry_frame = _entry_frame(macd_values=(-0.05, 0.08), signal_values=(-0.01, 0.07))

    assert plugin.generate_candidates(_context(entry_frame, _trend_frame())) == []


def test_macd_signal_trending_up_4h_confirmed_blocks_when_close_is_not_above_entry_ema():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    entry_frame = _entry_frame(close_offset=-10.0)

    assert plugin.generate_candidates(_context(entry_frame, _trend_frame())) == []


def test_macd_signal_trending_up_4h_confirmed_does_not_emit_duplicate_same_candle():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    context = _context(_entry_frame(), _trend_frame())

    assert len(plugin.generate_candidates(context)) == 1
    assert plugin.generate_candidates(context) == []


def test_macd_signal_trending_up_4h_confirmed_exit_on_signal_cross_down():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    entry_frame = _entry_frame(macd_values=(0.20, 0.05), signal_values=(0.10, 0.08))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_SIGNAL_CROSS_DOWN"


def test_macd_signal_trending_up_4h_confirmed_exit_on_trend_gate_loss():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    trend_frame = _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(_entry_frame(), trend_frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "TREND_GATE_LOST"


def test_macd_signal_trending_up_4h_confirmed_requires_indicator_warmup():
    plugin = MacdSignalTrendingUp4hConfirmedStrategy()
    entry_frame = _entry_frame(length=25)
    trend_frame = _trend_frame(length=49)

    assert plugin.generate_candidates(_context(entry_frame, trend_frame)) == []
