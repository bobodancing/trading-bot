from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins.macd_zero_line import MacdZeroLineLongStrategy


def _frame(macd_values=(-0.05, 0.08), signal_values=(-0.04, 0.02), atr=5.0):
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


def test_registry_loads_macd_zero_line_plugin():
    registry = StrategyRegistry.from_config(
        {
            "macd_zero_line_btc_1d": {
                "enabled": True,
                "module": "trader.strategies.plugins.macd_zero_line",
                "class": "MacdZeroLineLongStrategy",
                "params": {"risk_pct": 0.01},
            }
        },
        ["macd_zero_line_btc_1d"],
    )

    plugin = registry.require("macd_zero_line_btc_1d")
    assert isinstance(plugin, MacdZeroLineLongStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT"}
    assert plugin.max_concurrent_positions == 1
    assert plugin.risk_profile.risk_pct == pytest.approx(0.01)


def test_macd_zero_line_cross_up_generates_long_intent():
    plugin = MacdZeroLineLongStrategy(params={"stop_atr_mult": 2.0})
    frame = _frame(macd_values=(-0.02, 0.10), signal_values=(-0.01, 0.03), atr=4.0)

    intents = plugin.generate_candidates(_context(frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "macd_zero_line_btc_1d"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "1d"
    assert intent.entry_type == "macd_zero_line_cross_up"
    assert intent.stop_hint.price == pytest.approx(93.0)
    assert intent.stop_hint.reason == "macd_zero_line_atr_stop"


def test_macd_zero_line_requires_btc_scope():
    plugin = MacdZeroLineLongStrategy()

    intents = plugin.generate_candidates(_context(_frame(), symbols=["ETH/USDT"]))

    assert intents == []


def test_macd_zero_line_does_not_emit_duplicate_same_candle():
    plugin = MacdZeroLineLongStrategy()
    context = _context(_frame())

    assert len(plugin.generate_candidates(context)) == 1
    assert plugin.generate_candidates(context) == []


def test_macd_zero_line_blocks_when_signal_confirmation_fails():
    plugin = MacdZeroLineLongStrategy(params={"require_signal_confirmation": True})
    frame = _frame(macd_values=(-0.02, 0.03), signal_values=(-0.01, 0.05))

    assert plugin.generate_candidates(_context(frame)) == []


def test_macd_zero_line_can_disable_signal_confirmation():
    plugin = MacdZeroLineLongStrategy(params={"require_signal_confirmation": False})
    frame = _frame(macd_values=(-0.02, 0.03), signal_values=(-0.01, 0.05))

    assert len(plugin.generate_candidates(_context(frame))) == 1


def test_macd_zero_line_exit_on_cross_down():
    plugin = MacdZeroLineLongStrategy()
    frame = _frame(macd_values=(0.04, -0.01), signal_values=(0.02, 0.00))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_ZERO_LINE_CROSS_DOWN"
