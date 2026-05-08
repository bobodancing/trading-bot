from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.donchian_range_fade_4h import DonchianRangeFade4hStrategy


def _frame(
    *,
    size=40,
    highs=None,
    lows=None,
    closes=None,
    rsi=None,
    atr=None,
    freq="4h",
):
    idx = pd.date_range("2026-01-01", periods=size, freq=freq, tz="UTC")

    def _series(values, default):
        if values is None:
            values = [default] * size
        return list(values)

    highs = _series(highs, 110.0)
    lows = _series(lows, 90.0)
    closes = _series(closes, 100.0)
    rsi = _series(rsi, 45.0)
    atr = _series(atr, 4.0)

    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close,
            "high": pd.Series(highs, index=idx, dtype=float),
            "low": pd.Series(lows, index=idx, dtype=float),
            "close": close,
            "volume": 1000.0,
            "rsi_14": pd.Series(rsi, index=idx, dtype=float),
            "atr": pd.Series(atr, index=idx, dtype=float),
        },
        index=idx,
    )


def _stable_range_frame(*, size=40, latest_close=90.8, latest_rsi=35.0):
    closes = [100.0] * (size - 1) + [latest_close]
    rsi = [45.0] * (size - 1) + [latest_rsi]
    return _frame(size=size, closes=closes, rsi=rsi)


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


def _position(symbol="BTC/USDT"):
    return SimpleNamespace(symbol=symbol)


def test_registry_loads_donchian_range_fade_4h_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["donchian_range_fade_4h"]),
        ["donchian_range_fade_4h"],
    )

    plugin = registry.require("donchian_range_fade_4h")
    assert isinstance(plugin, DonchianRangeFade4hStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT", "ETH/USDT"}
    assert plugin.required_timeframes == {"4h": 200}
    assert plugin.required_indicators == {"rsi", "atr"}
    assert plugin.params["donchian_len"] == 20
    assert plugin.params["range_window"] == 15
    assert plugin.params["range_width_cv_max"] == pytest.approx(0.10)
    assert plugin.params["touch_atr_band"] == pytest.approx(0.25)
    assert plugin.params["exit_target"] == "mid"


def test_donchian_range_fade_4h_emits_long_on_happy_path():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 1.5})
    frame = _stable_range_frame()

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "donchian_range_fade_4h"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "4h"
    assert intent.entry_type == "donchian_range_lower_fade"
    assert intent.entry_price == pytest.approx(90.8)
    assert intent.stop_hint.price == pytest.approx(84.8)
    assert intent.stop_hint.reason == "donchian_range_fade_atr_stop"
    assert intent.stop_hint.metadata["atr"] == pytest.approx(4.0)
    assert intent.stop_hint.metadata["atr_mult"] == pytest.approx(1.5)
    assert intent.stop_hint.metadata["donchian_low"] == pytest.approx(90.0)
    assert intent.stop_hint.metadata["donchian_high"] == pytest.approx(110.0)
    assert intent.metadata["donchian_mid"] == pytest.approx(100.0)
    assert intent.metadata["donchian_width"] == pytest.approx(20.0)
    assert intent.metadata["width_cv"] == pytest.approx(0.0)
    assert intent.metadata["lower_touches"] >= 1
    assert intent.metadata["upper_touches"] >= 1
    assert intent.metadata["rsi_14"] == pytest.approx(35.0)
    assert intent.metadata["close"] == pytest.approx(90.8)
    assert intent.metadata["range_detected"] is True


def test_donchian_range_fade_4h_requires_range_stability_cv():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    highs = [110.0] * 20 + [110.0 + 4.0 * float(i) for i in range(20)]
    closes = [100.0] * 39 + [91.0]
    rsi = [45.0] * 39 + [35.0]
    frame = _frame(highs=highs, closes=closes, rsi=rsi)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_requires_lower_touches():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    lows = [90.0] * 25 + [92.0] * 15
    closes = [100.0] * 39 + [90.8]
    rsi = [45.0] * 39 + [35.0]
    frame = _frame(lows=lows, closes=closes, rsi=rsi)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_requires_upper_touches():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    highs = [110.0] * 25 + [108.0] * 15
    closes = [100.0] * 39 + [90.8]
    rsi = [45.0] * 39 + [35.0]
    frame = _frame(highs=highs, closes=closes, rsi=rsi)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_requires_close_near_lower_band():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_range_frame(latest_close=96.0)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_requires_rsi_below_entry():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_range_frame(latest_rsi=45.0)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_cooldown_blocks_rapid_signals_then_expires():
    plugin = DonchianRangeFade4hStrategy(
        params={"symbol": "BTC/USDT", "cooldown_bars": 3, "emit_once": False}
    )
    base = _stable_range_frame(size=40)
    within = _stable_range_frame(size=42)
    expired = _stable_range_frame(size=43)

    first = plugin.generate_candidates(_context({"BTC/USDT": base}))
    blocked = plugin.generate_candidates(_context({"BTC/USDT": within}))
    second = plugin.generate_candidates(_context({"BTC/USDT": expired}))

    assert len(first) == 1
    assert blocked == []
    assert len(second) == 1


def test_donchian_range_fade_4h_skips_unsupported_symbol():
    plugin = DonchianRangeFade4hStrategy()
    frame = _stable_range_frame()

    intents = plugin.generate_candidates(_context({"SOL/USDT": frame}, symbols=["SOL/USDT"]))

    assert intents == []


def test_donchian_range_fade_4h_handles_insufficient_data():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_range_frame(size=10)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_handles_nan_indicators():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_range_frame()
    frame.loc[frame.index[-1], "rsi_14"] = float("nan")

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_exit_on_close_reaching_mid_target():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_range_frame(latest_close=100.5, latest_rsi=55.0)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_MID_TARGET"
    assert decision.metadata["target_price"] == pytest.approx(100.0)
    assert decision.metadata["exit_target"] == "mid"


def test_donchian_range_fade_4h_exit_on_close_reaching_opposite_target():
    plugin = DonchianRangeFade4hStrategy(
        params={"symbol": "BTC/USDT", "exit_target": "opposite"}
    )
    frame = _stable_range_frame(latest_close=109.5, latest_rsi=55.0)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_OPPOSITE_TARGET"
    assert decision.metadata["target_price"] == pytest.approx(109.0)
    assert decision.metadata["exit_target"] == "opposite"


def test_donchian_range_fade_4h_exit_on_range_break_up():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    highs = [110.0] * 39 + [113.0]
    closes = [100.0] * 39 + [100.0]
    frame = _frame(highs=highs, closes=closes, rsi=[45.0] * 40)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_RANGE_BREAK_UP"
    assert decision.metadata["range_break_up"] is True
    assert decision.metadata["range_break_down"] is False


def test_donchian_range_fade_4h_exit_on_range_break_down():
    plugin = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    lows = [90.0] * 39 + [87.0]
    closes = [100.0] * 39 + [89.0]
    frame = _frame(lows=lows, closes=closes, rsi=[45.0] * 40)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_RANGE_BREAK_DOWN"
    assert decision.metadata["range_break_up"] is False
    assert decision.metadata["range_break_down"] is True
