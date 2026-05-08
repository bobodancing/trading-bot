from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, PositionDecision, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.rsi2_pullback_1h import Rsi2Pullback1hStrategy


def _entry_frame(
    *,
    size=210,
    latest_drop=5.0,
    latest_close=None,
    atr=None,
    freq="1h",
):
    idx = pd.date_range("2026-01-01", periods=size, freq=freq, tz="UTC")
    closes = [200.0 + 0.5 * float(i) for i in range(size)]
    closes[-1] = float(latest_close) if latest_close is not None else closes[-2] - latest_drop
    close = pd.Series(closes, index=idx, dtype=float)
    atr_values = [4.0] * size if atr is None else list(atr)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close + 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "atr": pd.Series(atr_values, index=idx, dtype=float),
        },
        index=idx,
    )


def _htf_frame(*, size=210, latest_close=None, freq="4h"):
    idx = pd.date_range("2026-01-01", periods=size, freq=freq, tz="UTC")
    closes = [200.0 + 0.5 * float(i) for i in range(size)]
    if latest_close is not None:
        closes[-1] = float(latest_close)
    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def _context(entry_frame=None, htf_frame=None, symbols=None):
    entry_frame = entry_frame if entry_frame is not None else _entry_frame()
    htf_frame = htf_frame if htf_frame is not None else _htf_frame()
    symbols = symbols or ["BTC/USDT"]
    frames = {
        "BTC/USDT": {
            "1h": entry_frame,
            "4h": htf_frame,
        }
    }

    def _get(symbol, timeframe):
        return frames.get(symbol, {}).get(timeframe, pd.DataFrame())

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


def _position(symbol="BTC/USDT", entry_time=None, metadata=None):
    entry_time = entry_time or datetime(2026, 1, 9, 15, tzinfo=timezone.utc)
    return SimpleNamespace(symbol=symbol, entry_time=entry_time, metadata=metadata or {})


def test_registry_loads_rsi2_pullback_1h_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["rsi2_pullback_1h"]),
        ["rsi2_pullback_1h"],
    )

    plugin = registry.require("rsi2_pullback_1h")
    assert isinstance(plugin, Rsi2Pullback1hStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT", "ETH/USDT"}
    assert plugin.required_timeframes == {"1h": 400, "4h": 250}
    assert plugin.required_indicators == {"rsi", "sma", "atr"}
    assert plugin.risk_profile.sizing_mode == "fixed_risk_pct"
    assert plugin.risk_profile.risk_pct is None
    assert plugin.target_regime == "ANY"
    assert "rsi2" in plugin.tags
    assert plugin.params["rsi_period"] == 2
    assert plugin.params["rsi_entry"] == pytest.approx(10.0)
    assert plugin.params["max_hold_bars"] == 10


def test_rsi2_pullback_1h_generates_long_on_happy_path():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 2.0})
    frame = _entry_frame()

    intents = plugin.generate_candidates(_context(frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "rsi2_pullback_1h"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "1h"
    assert intent.entry_type == "rsi2_pullback_deep_oversold"
    assert intent.entry_price == pytest.approx(299.0)
    assert intent.stop_hint.price == pytest.approx(291.0)
    assert intent.stop_hint.reason == "rsi2_pullback_atr_stop"
    assert intent.metadata["rsi_2"] < 10.0
    assert intent.metadata["sma_200_1h"] == pytest.approx(254.7225)
    assert intent.metadata["sma_5_1h"] == pytest.approx(302.4)
    assert intent.metadata["sma_200_4h"] == pytest.approx(254.75)
    assert intent.metadata["close"] == pytest.approx(299.0)
    assert intent.metadata["close_4h"] == pytest.approx(304.5)
    assert intent.metadata["htf_timeframe"] == "4h"


def test_rsi2_pullback_1h_stop_hint_calculation():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 2.5})
    frame = _entry_frame(atr=[3.0] * 210)

    intent = plugin.generate_candidates(_context(frame))[0]

    assert intent.stop_hint.price == pytest.approx(291.5)
    assert intent.stop_hint.metadata == {
        "atr_1h": pytest.approx(3.0),
        "atr_mult": pytest.approx(2.5),
        "rsi_2": pytest.approx(intent.metadata["rsi_2"]),
        "sma_200_1h": pytest.approx(254.7225),
        "sma_200_4h": pytest.approx(254.75),
    }


def test_rsi2_pullback_1h_skips_unsupported_symbol():
    plugin = Rsi2Pullback1hStrategy()

    intents = plugin.generate_candidates(_context(symbols=["SOL/USDT"]))

    assert intents == []


def test_rsi2_pullback_1h_handles_insufficient_data():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(size=50)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_rsi2_pullback_1h_handles_nan_indicators():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame()
    frame.loc[frame.index[-1], "atr"] = float("nan")

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_rsi2_pullback_1h_cooldown_blocks_rapid_signals_then_expires():
    plugin = Rsi2Pullback1hStrategy(
        params={"symbol": "BTC/USDT", "cooldown_bars": 4, "emit_once": False}
    )
    base = _entry_frame(size=210)
    within = _entry_frame(size=213)
    expired = _entry_frame(size=214)

    first = plugin.generate_candidates(_context(base))
    blocked = plugin.generate_candidates(_context(within))
    second = plugin.generate_candidates(_context(expired))

    assert len(first) == 1
    assert blocked == []
    assert len(second) == 1


def test_rsi2_pullback_1h_requires_rsi2_below_entry():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_drop=1.0)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_rsi2_pullback_1h_requires_close_above_1h_sma200():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_drop=80.0)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_rsi2_pullback_1h_requires_close_above_4h_sma200():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    htf = _htf_frame(latest_close=240.0)

    intents = plugin.generate_candidates(_context(htf_frame=htf))

    assert intents == []


def test_rsi2_pullback_1h_computes_rsi2_when_registry_absent():
    plugin = Rsi2Pullback1hStrategy()
    frame = _entry_frame()

    enriched = plugin._with_entry_indicators(
        frame,
        rsi_period=2,
        sma_trend_len=200,
        sma_exit_len=5,
    )

    assert "rsi_2" in enriched.columns
    assert enriched["rsi_2"].iloc[-1] == pytest.approx(9.0909090909)


def test_rsi2_pullback_1h_computes_sma5_when_registry_absent():
    plugin = Rsi2Pullback1hStrategy()
    frame = _entry_frame()

    enriched = plugin._with_entry_indicators(
        frame,
        rsi_period=2,
        sma_trend_len=200,
        sma_exit_len=5,
    )

    assert "sma_5" in enriched.columns
    assert enriched["sma_5"].iloc[-1] == pytest.approx(302.4)


def test_rsi2_pullback_1h_exit_on_rsi2_recovery():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_drop=-5.0)

    decision = plugin.update_position(_context(frame), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "RSI2_EXIT_TARGET"
    assert decision.metadata["rsi_2"] > 70.0


def test_rsi2_pullback_1h_exit_on_close_above_sma5():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT", "rsi_exit": 101.0})
    frame = _entry_frame(latest_drop=-1.0)

    decision = plugin.update_position(_context(frame), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "SMA5_BOUNCE_EXIT"
    assert decision.metadata["close"] > decision.metadata["sma_5_1h"]


def test_rsi2_pullback_1h_exit_on_max_hold_bars():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT", "max_hold_bars": 10})
    frame = _entry_frame()
    latest_ts = frame.index[-1].to_pydatetime()
    position = _position(entry_time=latest_ts - timedelta(hours=10))

    decision = plugin.update_position(_context(frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "TIME_STOP"
    assert decision.metadata["bars_in_position"] == 10


def test_rsi2_pullback_1h_exit_on_htf_flip():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame()
    htf = _htf_frame(latest_close=240.0)

    decision = plugin.update_position(_context(frame, htf_frame=htf), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "HTF_TREND_FLIP"
    assert decision.metadata["close_4h"] < decision.metadata["sma_200_4h"]


def test_rsi2_pullback_1h_hold_when_conditions_intact():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame()
    latest_ts = frame.index[-1].to_pydatetime()
    position = _position(entry_time=latest_ts - timedelta(hours=3))

    decision = plugin.update_position(_context(frame), position)

    assert decision == PositionDecision()
    assert decision.action == Action.HOLD
    assert decision.reason == "NONE"
