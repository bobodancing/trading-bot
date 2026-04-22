from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, PositionDecision, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.rsi_mean_reversion_1h import RsiMeanReversion1hStrategy


def _frame(
    *,
    closes=None,
    rsi=None,
    bb_lower=None,
    bb_mid=None,
    adx=None,
    atr=None,
    freq="1h",
):
    closes = closes or [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
    size = len(closes)
    idx = pd.date_range("2026-01-01", periods=size, freq=freq, tz="UTC")

    def _series(values, default):
        if values is None:
            values = [default] * size
        return list(values)

    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close + 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "rsi_14": _series(rsi, 50.0),
            "bb_lower": _series(bb_lower, float(close.iloc[-1]) - 1.0),
            "bb_mid": _series(bb_mid, float(close.iloc[-1]) + 2.0),
            "adx": _series(adx, 18.0),
            "atr": _series(atr, 4.0),
        },
        index=idx,
    )


def _context(frames, symbols=None):
    symbols = symbols or list(frames)

    def _get(symbol, timeframe):
        if timeframe != "1h":
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


def test_registry_loads_rsi_mean_reversion_1h_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["rsi_mean_reversion_1h"]),
        ["rsi_mean_reversion_1h"],
    )

    plugin = registry.require("rsi_mean_reversion_1h")
    assert isinstance(plugin, RsiMeanReversion1hStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT", "ETH/USDT"}
    assert plugin.risk_profile.sizing_mode == "fixed_risk_pct"
    assert plugin.risk_profile.risk_pct is None


def test_rsi_mr_1h_emits_long_on_oversold_with_bb_and_low_adx():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 1.5})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0, 18.0, 17.0, 18.0, 19.0, 18.0],
        atr=[4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
    )

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "rsi_mean_reversion_1h"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "1h"
    assert intent.entry_type == "rsi_mean_reversion_oversold"
    assert intent.entry_price == pytest.approx(100.0)
    assert intent.stop_hint.price == pytest.approx(94.0)
    assert intent.stop_hint.reason == "rsi_mean_reversion_atr_stop"
    assert intent.stop_hint.metadata["atr"] == pytest.approx(4.0)
    assert intent.stop_hint.metadata["atr_mult"] == pytest.approx(1.5)
    assert intent.stop_hint.metadata["rsi_14"] == pytest.approx(20.0)
    assert intent.stop_hint.metadata["bb_lower"] == pytest.approx(100.0)
    assert intent.metadata["rsi_14"] == pytest.approx(20.0)
    assert intent.metadata["bb_mid"] == pytest.approx(102.0)
    assert intent.metadata["adx"] == pytest.approx(18.0)
    assert intent.metadata["atr"] == pytest.approx(4.0)
    assert intent.metadata["close"] == pytest.approx(100.0)


def test_rsi_mr_1h_requires_rsi_below_threshold():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 35.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_rsi_mr_1h_requires_bb_lower_touch():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 101.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_rsi_mr_1h_blocks_in_trending_market():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0, 18.0, 18.0, 18.0, 20.0, 28.0],
        atr=[4.0] * 6,
    )

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_rsi_mr_1h_emit_once_blocks_same_candle_duplicate():
    plugin = RsiMeanReversion1hStrategy(
        params={"symbol": "BTC/USDT", "emit_once": True, "cooldown_bars": 0}
    )
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )
    context = _context({"BTC/USDT": frame})

    first = plugin.generate_candidates(context)
    second = plugin.generate_candidates(context)

    assert len(first) == 1
    assert second == []


def test_rsi_mr_1h_cooldown_blocks_within_n_bars():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT", "cooldown_bars": 5, "emit_once": False})
    base = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )
    within = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0, 99.0, 98.0, 97.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0, 22.0, 21.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0, 100.0, 99.0, 97.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0, 101.0, 100.0, 99.0],
        adx=[18.0] * 9,
        atr=[4.0] * 9,
    )
    expired = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0, 22.0, 21.0, 20.0, 19.0, 18.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0, 100.0, 99.0, 97.0, 96.0, 95.0, 94.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0, 101.0, 100.0, 99.0, 98.0, 97.0, 96.0],
        adx=[18.0] * 12,
        atr=[4.0] * 12,
    )

    first = plugin.generate_candidates(_context({"BTC/USDT": base}))
    blocked = plugin.generate_candidates(_context({"BTC/USDT": within}))
    second = plugin.generate_candidates(_context({"BTC/USDT": expired}))

    assert len(first) == 1
    assert blocked == []
    assert len(second) == 1


def test_rsi_mr_1h_skips_unsupported_symbol():
    plugin = RsiMeanReversion1hStrategy()
    frame = _frame()

    intents = plugin.generate_candidates(_context({"SOL/USDT": frame}, symbols=["SOL/USDT"]))

    assert intents == []


def test_rsi_mr_1h_handles_nan_indicators():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame()
    frame.loc[frame.index[-1], "rsi_14"] = float("nan")

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_rsi_mr_1h_exit_on_rsi_recovery():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 101.0],
        rsi=[30.0, 32.0, 35.0, 40.0, 50.0, 65.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 105.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "RSI_EXIT_TARGET"
    assert decision.metadata["rsi_14"] == pytest.approx(65.0)


def test_rsi_mr_1h_exit_on_bb_mid_cross():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 103.0],
        rsi=[30.0, 32.0, 35.0, 40.0, 50.0, 50.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "BB_MID_RECOVERY"
    assert decision.metadata["close"] == pytest.approx(103.0)


def test_rsi_mr_1h_exit_on_adx_trend_onset():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 99.0],
        rsi=[30.0, 32.0, 35.0, 40.0, 50.0, 50.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 100.0],
        adx=[18.0, 18.0, 19.0, 20.0, 22.0, 32.0],
        atr=[4.0] * 6,
    )

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "ADX_TREND_ONSET"
    assert decision.metadata["adx"] == pytest.approx(32.0)


def test_rsi_mr_1h_hold_when_still_oversold():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 99.0],
        rsi=[30.0, 32.0, 35.0, 40.0, 44.0, 45.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 100.0],
        adx=[18.0, 18.0, 19.0, 20.0, 22.0, 22.0],
        atr=[4.0] * 6,
    )

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision == PositionDecision()
    assert decision.action == Action.HOLD
    assert decision.reason == "NONE"


def test_rsi_mr_1h_stop_hint_math():
    plugin = RsiMeanReversion1hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 1.5})
    frame = _frame(
        closes=[101.0, 100.0, 99.0, 98.0, 97.0, 100.0],
        rsi=[40.0, 38.0, 32.0, 28.0, 24.0, 20.0],
        bb_lower=[102.0, 101.0, 100.0, 99.0, 98.0, 100.0],
        bb_mid=[104.0, 103.0, 102.0, 101.0, 100.0, 102.0],
        adx=[18.0] * 6,
        atr=[4.0] * 6,
    )

    intent = plugin.generate_candidates(_context({"BTC/USDT": frame}))[0]

    assert intent.stop_hint.price == pytest.approx(94.0)
    assert intent.stop_hint.metadata == {
        "atr": pytest.approx(4.0),
        "atr_mult": pytest.approx(1.5),
        "rsi_14": pytest.approx(20.0),
        "bb_lower": pytest.approx(100.0),
    }
