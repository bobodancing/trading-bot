from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, PositionDecision, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.bb_fade_squeeze_1h import BbFadeSqueeze1hStrategy


def _entry_frame(
    *,
    size=120,
    latest_close=95.0,
    latest_rsi=25.0,
    latest_bb_lower=95.0,
    latest_bb_mid=100.0,
    latest_bb_upper=105.0,
    latest_bbw=1.0,
    bbw=None,
    atr=None,
    freq="1h",
):
    idx = pd.date_range("2026-01-01", periods=size, freq=freq, tz="UTC")
    closes = [100.0] * max(size - 1, 0) + [latest_close]
    rsi = [45.0] * max(size - 1, 0) + [latest_rsi]
    bb_lower = [98.0] * max(size - 1, 0) + [latest_bb_lower]
    bb_mid = [100.0] * max(size - 1, 0) + [latest_bb_mid]
    bb_upper = [102.0] * max(size - 1, 0) + [latest_bb_upper]
    if bbw is None:
        bbw = [5.0 + 0.01 * float(i) for i in range(max(size - 1, 0))] + [latest_bbw]
    if atr is None:
        atr = [4.0] * size

    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close + 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "rsi_14": pd.Series(rsi, index=idx, dtype=float),
            "bb_lower": pd.Series(bb_lower, index=idx, dtype=float),
            "bb_mid": pd.Series(bb_mid, index=idx, dtype=float),
            "bb_upper": pd.Series(bb_upper, index=idx, dtype=float),
            "bbw": pd.Series(bbw, index=idx, dtype=float),
            "atr": pd.Series(atr, index=idx, dtype=float),
        },
        index=idx,
    )


def _htf_frame(*, size=40, latest_adx=18.0, freq="4h"):
    idx = pd.date_range("2026-01-01", periods=size, freq=freq, tz="UTC")
    adx = [18.0] * max(size - 1, 0) + [latest_adx]
    close = pd.Series([100.0] * size, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "adx": pd.Series(adx, index=idx, dtype=float),
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


def _position(symbol="BTC/USDT"):
    return SimpleNamespace(symbol=symbol)


def test_registry_loads_bb_fade_squeeze_1h_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["bb_fade_squeeze_1h"]),
        ["bb_fade_squeeze_1h"],
    )

    plugin = registry.require("bb_fade_squeeze_1h")
    assert isinstance(plugin, BbFadeSqueeze1hStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT", "ETH/USDT"}
    assert plugin.required_timeframes == {"1h": 200, "4h": 120}
    assert plugin.required_indicators == {"bollinger", "rsi", "bbw", "adx", "atr"}
    assert plugin.risk_profile.sizing_mode == "fixed_risk_pct"
    assert plugin.risk_profile.risk_pct is None
    assert plugin.target_regime == "RANGING"
    assert "ranging" in plugin.tags
    assert "bbw_squeeze" in plugin.tags
    assert plugin.params["rsi_entry"] == pytest.approx(30.0)
    assert plugin.params["bbw_pctrank_window"] == 100
    assert plugin.params["htf_adx_max"] == pytest.approx(20.0)


def test_bb_fade_squeeze_1h_generates_long_on_happy_path():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 1.5})
    frame = _entry_frame()

    intents = plugin.generate_candidates(_context(frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "bb_fade_squeeze_1h"
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "LONG"
    assert intent.timeframe == "1h"
    assert intent.entry_type == "bb_fade_squeeze_lower_fade"
    assert intent.entry_price == pytest.approx(95.0)
    assert intent.stop_hint.price == pytest.approx(89.0)
    assert intent.stop_hint.reason == "bb_fade_squeeze_atr_stop"
    assert intent.metadata["rsi_14"] == pytest.approx(25.0)
    assert intent.metadata["bb_lower"] == pytest.approx(95.0)
    assert intent.metadata["bb_mid"] == pytest.approx(100.0)
    assert intent.metadata["bb_upper"] == pytest.approx(105.0)
    assert intent.metadata["bbw"] == pytest.approx(1.0)
    assert intent.metadata["bbw_pctrank"] < 20.0
    assert intent.metadata["htf_adx"] == pytest.approx(18.0)
    assert intent.metadata["atr_1h"] == pytest.approx(4.0)
    assert intent.metadata["close"] == pytest.approx(95.0)
    assert intent.metadata["htf_timeframe"] == "4h"


def test_bb_fade_squeeze_1h_stop_hint_calculation():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT", "stop_atr_mult": 2.0})
    frame = _entry_frame(latest_close=96.0, latest_bb_lower=96.0, atr=[3.0] * 120)

    intent = plugin.generate_candidates(_context(frame))[0]

    assert intent.stop_hint.price == pytest.approx(90.0)
    assert intent.stop_hint.metadata == {
        "atr_1h": pytest.approx(3.0),
        "atr_mult": pytest.approx(2.0),
        "bb_lower": pytest.approx(96.0),
        "bbw_pctrank": pytest.approx(1.0),
        "htf_adx": pytest.approx(18.0),
    }


def test_bb_fade_squeeze_1h_skips_unsupported_symbol():
    plugin = BbFadeSqueeze1hStrategy()

    intents = plugin.generate_candidates(_context(symbols=["SOL/USDT"]))

    assert intents == []


def test_bb_fade_squeeze_1h_handles_insufficient_data():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(size=50)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_bb_fade_squeeze_1h_handles_nan_indicators():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame()
    frame.loc[frame.index[-1], "rsi_14"] = float("nan")

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_bb_fade_squeeze_1h_cooldown_blocks_rapid_signals_then_expires():
    plugin = BbFadeSqueeze1hStrategy(
        params={"symbol": "BTC/USDT", "cooldown_bars": 5, "emit_once": False}
    )
    base = _entry_frame(size=120)
    within = _entry_frame(size=124)
    expired = _entry_frame(size=125)

    first = plugin.generate_candidates(_context(base))
    blocked = plugin.generate_candidates(_context(within))
    second = plugin.generate_candidates(_context(expired))

    assert len(first) == 1
    assert blocked == []
    assert len(second) == 1


def test_bb_fade_squeeze_1h_requires_rsi_below_entry():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_rsi=35.0)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_bb_fade_squeeze_1h_requires_close_at_or_below_bb_lower():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_close=96.0, latest_bb_lower=95.0)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_bb_fade_squeeze_1h_requires_bbw_pctrank_below_threshold():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    bbw = [1.0 + 0.01 * float(i) for i in range(119)] + [10.0]
    frame = _entry_frame(bbw=bbw, latest_bbw=10.0)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_bb_fade_squeeze_1h_requires_htf_adx_below_gate():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})

    intents = plugin.generate_candidates(_context(htf_frame=_htf_frame(latest_adx=25.0)))

    assert intents == []


def test_bb_fade_squeeze_1h_exit_on_close_above_bb_mid():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_close=101.0, latest_rsi=45.0, latest_bb_mid=100.0)

    decision = plugin.update_position(_context(frame), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "BB_MID_RECOVERY"
    assert decision.metadata["close"] == pytest.approx(101.0)


def test_bb_fade_squeeze_1h_exit_on_rsi_recovery():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_close=98.0, latest_rsi=60.0, latest_bb_mid=100.0)

    decision = plugin.update_position(_context(frame), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "RSI_EXIT_TARGET"
    assert decision.metadata["rsi_14"] == pytest.approx(60.0)


def test_bb_fade_squeeze_1h_exit_on_htf_adx_flip():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_close=98.0, latest_rsi=45.0, latest_bb_mid=100.0)

    decision = plugin.update_position(
        _context(frame, htf_frame=_htf_frame(latest_adx=26.0)),
        _position(),
    )

    assert decision.action == Action.CLOSE
    assert decision.reason == "HTF_ADX_TREND_ONSET"
    assert decision.metadata["htf_adx"] == pytest.approx(26.0)


def test_bb_fade_squeeze_1h_hold_when_still_oversold():
    plugin = BbFadeSqueeze1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_close=98.0, latest_rsi=45.0, latest_bb_mid=100.0)

    decision = plugin.update_position(_context(frame), _position())

    assert decision == PositionDecision()
    assert decision.action == Action.HOLD
    assert decision.reason == "NONE"
