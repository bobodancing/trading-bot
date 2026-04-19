from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.ema_cross_7_19 import EmaCross719LongOnlyStrategy


def _frame(closes, *, atr=2.0, freq="4h"):
    idx = pd.date_range("2026-01-01", periods=len(closes), freq=freq, tz="UTC")
    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "atr": atr,
        },
        index=idx,
    )


def _cross_up_frame(*, atr=2.0):
    closes = [100.0] * 93 + [99.0, 98.0, 97.0, 96.0, 95.0, 98.0, 102.0, 106.0]
    return _frame(closes, atr=atr)


def _cross_down_frame():
    closes = [100.0] * 93 + [101.0, 102.0, 103.0, 104.0, 105.0, 102.0, 98.0, 94.0]
    return _frame(closes)


def _context(frames, symbols=None):
    symbols = symbols or list(frames)

    def _get(symbol, timeframe):
        if timeframe != "4h":
            return pd.DataFrame()
        return frames.get(symbol, pd.DataFrame())

    return StrategyContext(
        snapshot=SimpleNamespace(
            get=_get,
            latest_timestamp=lambda symbol, timeframe: _get(symbol, timeframe).index[-1].to_pydatetime(),
            latest_close=lambda symbol, timeframe: float(_get(symbol, timeframe)["close"].iloc[-1]),
        ),
        symbols=list(symbols),
        active_positions={},
        config=SimpleNamespace(),
        now=datetime.now(timezone.utc),
    )


def test_registry_loads_ema_cross_7_19_plugin_from_catalog():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["ema_cross_7_19_long_only"]),
        ["ema_cross_7_19_long_only"],
    )

    plugin = registry.require("ema_cross_7_19_long_only")
    assert isinstance(plugin, EmaCross719LongOnlyStrategy)
    assert plugin.params == {"timeframe": "4h", "atr_mult": 1.5}
    assert plugin.allowed_symbols == {"BTC/USDT", "ETH/USDT"}
    assert plugin.required_timeframes == {"4h": 100}
    assert plugin.required_indicators == {"ema", "atr"}
    assert plugin.max_concurrent_positions is None


def test_ema_cross_7_19_generates_long_intent_with_atr_stop():
    plugin = EmaCross719LongOnlyStrategy(params={"symbol": "BTC/USDT", "atr_mult": 1.5})
    frame = _cross_up_frame(atr=2.0)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "ema_cross_7_19_long_only"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "4h"
    assert intent.entry_type == "ema_7_19_cross_up"
    assert intent.entry_price == pytest.approx(106.0)
    assert intent.stop_hint.price == pytest.approx(103.0)
    assert intent.stop_hint.reason == "ema_7_19_atr_stop"
    assert intent.stop_hint.metadata == {"atr": 2.0, "atr_mult": 1.5}
    assert intent.metadata["previous_ema_7"] <= intent.metadata["previous_ema_19"]
    assert intent.metadata["ema_7"] > intent.metadata["ema_19"]


def test_ema_cross_7_19_emits_btc_and_eth_when_both_cross():
    plugin = EmaCross719LongOnlyStrategy()
    btc = _cross_up_frame(atr=2.0)
    eth = _cross_up_frame(atr=1.0)

    intents = plugin.generate_candidates(
        _context({"BTC/USDT": btc, "ETH/USDT": eth}, symbols=["BTC/USDT", "ETH/USDT"])
    )

    assert [intent.symbol for intent in intents] == ["BTC/USDT", "ETH/USDT"]
    assert all(intent.side == "LONG" for intent in intents)


def test_ema_cross_7_19_ignores_symbols_outside_scope():
    plugin = EmaCross719LongOnlyStrategy(params={"symbol": "SOL/USDT"})

    intents = plugin.generate_candidates(
        _context({"SOL/USDT": _cross_up_frame()}, symbols=["SOL/USDT"])
    )

    assert intents == []


def test_ema_cross_7_19_returns_no_intent_without_cross_up():
    plugin = EmaCross719LongOnlyStrategy(params={"symbol": "BTC/USDT"})
    flat = _frame([100.0] * 101)

    intents = plugin.generate_candidates(_context({"BTC/USDT": flat}))

    assert intents == []


def test_ema_cross_7_19_exit_on_cross_down():
    plugin = EmaCross719LongOnlyStrategy()
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context({"BTC/USDT": _cross_down_frame()}), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "EMA_7_19_CROSS_DOWN"
    assert decision.metadata["previous_ema_7"] >= decision.metadata["previous_ema_19"]
    assert decision.metadata["ema_7"] < decision.metadata["ema_19"]
