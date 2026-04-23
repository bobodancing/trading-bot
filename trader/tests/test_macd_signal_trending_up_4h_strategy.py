from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h import (
    MacdSignalTrendingUp4hStrategy,
)


def _entry_frame(
    length=30,
    macd_values=(-0.05, 0.08),
    signal_values=(-0.04, 0.02),
    atr=1200.0,
    freq="4h",
):
    idx = pd.date_range("2026-01-01", periods=length, freq=freq, tz="UTC")
    close = pd.Series([100000.0 + i * 250.0 for i in range(length)], index=idx)
    macd_series = [0.01] * max(length - 2, 0) + list(macd_values)
    signal_series = [0.0] * max(length - 2, 0) + list(signal_values)
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


def _context(entry_frame, trend_frame, symbols=None, entry_timeframe="4h", trend_timeframe="1d"):
    symbols = symbols or ["BTC/USDT"]
    snapshot = SimpleNamespace(
        get=lambda symbol, timeframe: (
            entry_frame
            if symbol == "BTC/USDT" and timeframe == entry_timeframe
            else trend_frame
            if symbol == "BTC/USDT" and timeframe == trend_timeframe
            else pd.DataFrame()
        ),
        latest_timestamp=lambda symbol, timeframe: (
            entry_frame.index[-1].to_pydatetime()
            if timeframe == entry_timeframe
            else trend_frame.index[-1].to_pydatetime()
        ),
        latest_close=lambda symbol, timeframe: (
            float(entry_frame["close"].iloc[-1])
            if timeframe == entry_timeframe
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


def test_registry_loads_macd_signal_trending_up_4h_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["macd_signal_btc_4h_trending_up"]),
        ["macd_signal_btc_4h_trending_up"],
    )

    plugin = registry.require("macd_signal_btc_4h_trending_up")
    assert isinstance(plugin, MacdSignalTrendingUp4hStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT"}
    assert plugin.params["entry_timeframe"] == "4h"
    assert plugin.params["trend_timeframe"] == "1d"
    assert plugin.params["trend_spread_min"] == pytest.approx(0.005)
    assert plugin.required_timeframes == {"4h": 200, "1d": 260}


def test_macd_signal_trending_up_4h_updates_required_timeframes_from_params():
    plugin = MacdSignalTrendingUp4hStrategy(
        params={"entry_timeframe": "1h", "trend_timeframe": "1d"}
    )
    entry_frame = _entry_frame(
        freq="1h",
        macd_values=(-0.02, 0.10),
        signal_values=(-0.01, 0.04),
        atr=800.0,
    )
    trend_frame = _trend_frame(ema_20_values=(100000.0,), ema_50_values=(99000.0,))

    intents = plugin.generate_candidates(
        _context(entry_frame, trend_frame, entry_timeframe="1h", trend_timeframe="1d")
    )

    assert plugin.required_timeframes == {"1h": 200, "1d": 260}
    assert len(intents) == 1
    assert intents[0].timeframe == "1h"


def test_macd_signal_trending_up_4h_generates_long_intent():
    plugin = MacdSignalTrendingUp4hStrategy(params={"stop_atr_mult": 1.5})
    entry_frame = _entry_frame(macd_values=(-0.02, 0.10), signal_values=(-0.01, 0.04), atr=800.0)
    trend_frame = _trend_frame(ema_20_values=(100000.0,), ema_50_values=(99000.0,))

    intents = plugin.generate_candidates(_context(entry_frame, trend_frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "macd_signal_btc_4h_trending_up"
    assert intent.timeframe == "4h"
    assert intent.entry_type == "macd_signal_cross_up"
    assert intent.stop_hint.price == pytest.approx(float(entry_frame["close"].iloc[-1]) - 1200.0)
    assert intent.metadata["trend_timeframe"] == "1d"
    assert intent.metadata["trend_spread"] > intent.metadata["trend_spread_min"]


def test_macd_signal_trending_up_4h_requires_btc_scope():
    plugin = MacdSignalTrendingUp4hStrategy()

    intents = plugin.generate_candidates(
        _context(_entry_frame(), _trend_frame(), symbols=["ETH/USDT"])
    )

    assert intents == []


def test_macd_signal_trending_up_4h_blocks_when_daily_trend_is_not_up():
    plugin = MacdSignalTrendingUp4hStrategy()
    trend_frame = _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))

    assert plugin.generate_candidates(_context(_entry_frame(), trend_frame)) == []


def test_macd_signal_trending_up_4h_blocks_when_trend_spread_is_too_small():
    plugin = MacdSignalTrendingUp4hStrategy(params={"trend_spread_min": 0.01})
    trend_frame = _trend_frame(ema_20_values=(100500.0,), ema_50_values=(100000.0,))

    assert plugin.generate_candidates(_context(_entry_frame(), trend_frame)) == []


def test_macd_signal_trending_up_4h_blocks_below_zero_cross_when_confirmation_is_enabled():
    plugin = MacdSignalTrendingUp4hStrategy(params={"require_signal_confirmation": True})
    entry_frame = _entry_frame(macd_values=(-0.50, -0.10), signal_values=(-0.40, -0.20))

    assert plugin.generate_candidates(_context(entry_frame, _trend_frame())) == []


def test_macd_signal_trending_up_4h_does_not_emit_duplicate_same_candle():
    plugin = MacdSignalTrendingUp4hStrategy()
    context = _context(_entry_frame(), _trend_frame())

    assert len(plugin.generate_candidates(context)) == 1
    assert plugin.generate_candidates(context) == []


def test_macd_signal_trending_up_4h_exit_on_signal_cross_down():
    plugin = MacdSignalTrendingUp4hStrategy()
    entry_frame = _entry_frame(macd_values=(0.20, 0.05), signal_values=(0.10, 0.08))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_SIGNAL_CROSS_DOWN"


def test_macd_signal_trending_up_4h_exit_on_trend_gate_loss():
    plugin = MacdSignalTrendingUp4hStrategy()
    trend_frame = _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(_entry_frame(), trend_frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "TREND_GATE_LOST"


def test_macd_signal_trending_up_4h_requires_indicator_warmup():
    plugin = MacdSignalTrendingUp4hStrategy()
    entry_frame = _entry_frame(length=25)
    trend_frame = _trend_frame(length=49)

    assert plugin.generate_candidates(_context(entry_frame, trend_frame)) == []
