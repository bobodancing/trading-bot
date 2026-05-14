from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.strategies import Action, StrategyContext, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.btc_recovery_band_trend_breadth_4h import (
    BtcRecoveryBandTrendBreadth4hStrategy,
)


PLUGIN_ID = "btc_recovery_band_trend_breadth_4h"


def _entry_frame(
    *,
    supertrend_flip=True,
    atr=1000.0,
    close_last=100000.0,
    aroon_break=False,
    distance_atr=1.0,
):
    idx = pd.date_range("2026-01-01", periods=30, freq="4h", tz="UTC")
    close = pd.Series([98000.0 + i * 50.0 for i in range(len(idx))], index=idx)
    close.iloc[-1] = close_last
    high = close + 200.0
    low = close - 200.0
    if aroon_break:
        high.iloc[-21:-1] = close_last - distance_atr * atr
        low.iloc[-21:-1] = close_last - 1200.0
        high.iloc[-1] = close_last + 200.0
        low.iloc[-1] = close_last - 200.0
    else:
        high.iloc[-21:-1] = close_last + 500.0
    supertrend = pd.Series([close_last - distance_atr * atr] * len(idx), index=idx)
    direction = pd.Series([1.0] * len(idx), index=idx)
    if supertrend_flip:
        direction.iloc[-2] = -1.0
        direction.iloc[-1] = 1.0
    else:
        direction.iloc[-2:] = 1.0
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 100.0,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000.0,
            "atr": atr,
            "supertrend": supertrend,
            "supertrend_direction": direction,
        },
        index=idx,
    )


def _trend_frame(
    *,
    spreads=(-0.03, -0.03),
    latest_day="2025-12-31",
):
    idx = pd.date_range(latest_day, periods=2, freq="D", tz="UTC")
    ema_50 = [100000.0, 100000.0]
    ema_20 = [ema_50[i] * (1.0 + spreads[i]) for i in range(2)]
    return pd.DataFrame(
        {
            "timestamp": idx,
            "close": ema_20,
            "ema_20": ema_20,
            "ema_50": ema_50,
        },
        index=idx,
    )


def _context(entry_frame, trend_frame, *, symbols=None, now=None):
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
        now=now or datetime(2026, 5, 13, tzinfo=timezone.utc),
    )


def test_registry_loads_recovery_band_trend_breadth_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog([PLUGIN_ID]),
        [PLUGIN_ID],
    )

    plugin = registry.require(PLUGIN_ID)
    assert isinstance(plugin, BtcRecoveryBandTrendBreadth4hStrategy)
    assert plugin.allowed_symbols == {"BTC/USDT"}
    assert plugin.required_timeframes == {"4h": 200, "1d": 260}
    assert plugin.params["ema_spread_min"] == pytest.approx(-0.08)
    assert plugin.params["ema_spread_max"] == pytest.approx(-0.01)


def test_supertrend_recovery_band_emits_long_intent():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    intents = plugin.generate_candidates(_context(_entry_frame(), _trend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == PLUGIN_ID
    assert intent.entry_type == "btc_recovery_band_supertrend_flip"
    assert intent.stop_hint.price == pytest.approx(98500.0)
    assert intent.metadata["primary_mechanism"] == "supertrend_flip"
    assert intent.metadata["ema_spread_1d"] == pytest.approx(-0.03)


def test_aroon_recovery_band_emits_long_intent():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    intents = plugin.generate_candidates(
        _context(
            _entry_frame(supertrend_flip=False, aroon_break=True, distance_atr=0.5),
            _trend_frame(),
        )
    )

    assert len(intents) == 1
    assert intents[0].entry_type == "btc_recovery_band_aroon_break_hh"
    assert intents[0].metadata["primary_mechanism"] == "aroon_break_hh"
    assert intents[0].metadata["trigger_mechanisms"] == ["aroon_break_hh"]


def test_dual_trigger_emits_once_and_keeps_both_trigger_payloads():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    intents = plugin.generate_candidates(
        _context(
            _entry_frame(supertrend_flip=True, aroon_break=True, distance_atr=0.5),
            _trend_frame(),
        )
    )

    assert len(intents) == 1
    assert intents[0].entry_type == "btc_recovery_band_dual_trigger"
    assert intents[0].metadata["trigger_mechanisms"] == ["aroon_break_hh", "supertrend_flip"]


def test_blocks_outside_recovery_band():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    trend = _trend_frame(spreads=(-0.09, -0.09))

    assert plugin.generate_candidates(_context(_entry_frame(), trend)) == []


def test_blocks_when_distance_cap_is_exceeded():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy(params={"distance_atr_max": 3.0})
    entry = _entry_frame(distance_atr=3.5)

    assert plugin.generate_candidates(_context(entry, _trend_frame())) == []


def test_requires_btc_scope_and_dedupes_same_candle():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    context = _context(_entry_frame(), _trend_frame())

    assert plugin.generate_candidates(_context(_entry_frame(), _trend_frame(), symbols=["ETH/USDT"])) == []
    assert len(plugin.generate_candidates(context)) == 1
    assert plugin.generate_candidates(context) == []


def test_exit_when_recovery_band_is_lost():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    trend = _trend_frame(spreads=(-0.03, -0.005))
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(_entry_frame(), trend), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "RECOVERY_BAND_EXIT"


def test_exit_when_supertrend_flips_down():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    entry = _entry_frame(supertrend_flip=False)
    entry.loc[entry.index[-2], "supertrend_direction"] = 1.0
    entry.loc[entry.index[-1], "supertrend_direction"] = -1.0
    position = SimpleNamespace(symbol="BTC/USDT")

    decision = plugin.update_position(_context(entry, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "SUPERTREND_RECOVERY_FLIP_DOWN"


def test_completed_daily_recovery_band_uses_previous_row_when_latest_day_is_open():
    plugin = BtcRecoveryBandTrendBreadth4hStrategy()
    trend = _trend_frame(spreads=(-0.03, 0.02), latest_day="2026-01-04")
    now = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)

    intents = plugin.generate_candidates(_context(_entry_frame(), trend, now=now))

    assert len(intents) == 1
    assert intents[0].metadata["ema_spread_1d"] == pytest.approx(-0.03)
