from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_zero_line_trending_up import (
    MacdZeroLineTrendingUpStrategy,
)


def _frame(
    macd_values=(-0.05, 0.08),
    signal_values=(-0.04, 0.02),
    atr=5.0,
    ema_20_values=(100.0, 102.0),
    ema_50_values=(99.0, 100.0),
):
    idx = pd.date_range("2026-01-01", periods=len(macd_values), freq="D", tz="UTC")
    close = pd.Series([100.0 + i for i in range(len(macd_values))], index=idx)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 1.0,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": 1000.0,
            "macd": list(macd_values),
            "macd_signal": list(signal_values),
            "macd_hist": [m - s for m, s in zip(macd_values, signal_values)],
            "atr": atr,
            "ema_20": list(ema_20_values),
            "ema_50": list(ema_50_values),
        },
        index=idx,
    )


def _context(frame, symbols=None):
    symbols = symbols or ["BTC/USDT"]
    snapshot = SimpleNamespace(
        get=lambda symbol, timeframe: frame if symbol == "BTC/USDT" and timeframe == "1d" else pd.DataFrame(),
        latest_timestamp=lambda symbol, timeframe: frame.index[-1].to_pydatetime(),
        latest_close=lambda symbol, timeframe: float(frame["close"].iloc[-1]),
    )
    return StrategyContext(
        snapshot=snapshot,
        symbols=symbols,
        active_positions={},
        config=SimpleNamespace(),
        now=datetime.now(timezone.utc),
    )


def test_registry_loads_macd_zero_line_trending_up_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["macd_zero_line_btc_1d_trending_up"]),
        ["macd_zero_line_btc_1d_trending_up"],
    )

    plugin = registry.require("macd_zero_line_btc_1d_trending_up")
    assert isinstance(plugin, MacdZeroLineTrendingUpStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT"}
    assert plugin.max_concurrent_positions == 1
    assert plugin.params["stop_atr_mult"] == pytest.approx(1.5)
    assert plugin.params["trend_spread_min"] == pytest.approx(0.005)


def test_macd_zero_line_trending_up_generates_long_intent():
    plugin = MacdZeroLineTrendingUpStrategy(params={"stop_atr_mult": 2.0})
    frame = _frame(
        macd_values=(-0.02, 0.10),
        signal_values=(-0.01, 0.03),
        atr=4.0,
        ema_20_values=(100.0, 103.0),
        ema_50_values=(99.0, 100.0),
    )

    intents = plugin.generate_candidates(_context(frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "macd_zero_line_btc_1d_trending_up"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "1d"
    assert intent.entry_type == "macd_zero_line_cross_up"
    assert intent.stop_hint.price == pytest.approx(93.0)
    assert intent.stop_hint.reason == "macd_zero_line_atr_stop"
    assert intent.metadata["trend_spread"] > intent.metadata["trend_spread_min"]


def test_macd_zero_line_trending_up_requires_btc_scope():
    plugin = MacdZeroLineTrendingUpStrategy()

    intents = plugin.generate_candidates(_context(_frame(), symbols=["ETH/USDT"]))

    assert intents == []


def test_macd_zero_line_trending_up_blocks_when_trend_is_not_up():
    plugin = MacdZeroLineTrendingUpStrategy()
    frame = _frame(ema_20_values=(100.0, 99.0), ema_50_values=(101.0, 100.0))

    assert plugin.generate_candidates(_context(frame)) == []


def test_macd_zero_line_trending_up_blocks_when_trend_spread_is_too_small():
    plugin = MacdZeroLineTrendingUpStrategy(params={"trend_spread_min": 0.005})
    frame = _frame(ema_20_values=(100.0, 100.3), ema_50_values=(100.0, 100.0))

    assert plugin.generate_candidates(_context(frame)) == []


def test_macd_zero_line_trending_up_does_not_emit_duplicate_same_candle():
    plugin = MacdZeroLineTrendingUpStrategy()
    context = _context(_frame())

    assert len(plugin.generate_candidates(context)) == 1
    assert plugin.generate_candidates(context) == []


def test_macd_zero_line_trending_up_blocks_when_signal_confirmation_fails():
    plugin = MacdZeroLineTrendingUpStrategy(params={"require_signal_confirmation": True})
    frame = _frame(macd_values=(-0.02, 0.03), signal_values=(-0.01, 0.05))

    assert plugin.generate_candidates(_context(frame)) == []


def test_macd_zero_line_trending_up_exit_on_cross_down():
    plugin = MacdZeroLineTrendingUpStrategy()
    frame = _frame(macd_values=(0.04, -0.01), signal_values=(0.02, 0.00))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_ZERO_LINE_CROSS_DOWN"
