import pytest

from trader.strategies import StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_buffer import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionBufferStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _trend_frame,
)


def test_registry_loads_macd_signal_trending_up_4h_partial67_transition_buffer_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionBufferStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["trend_persistence_bars"] == 3


def test_partial67_transition_buffer_generates_long_intent_after_persistent_trend():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionBufferStrategy()

    intents = plugin.generate_candidates(_context(_entry_frame(), _trend_frame()))

    assert len(intents) == 1
    assert (
        intents[0].strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer"
    )
    assert intents[0].entry_type == "macd_signal_cross_up_transition_buffered"
    assert intents[0].metadata["trend_persistence_bars"] == 3
    assert intents[0].metadata["trend_persistence_count"] == 3


def test_partial67_transition_buffer_blocks_fresh_trend_flip():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionBufferStrategy()
    trend_frame = _trend_frame()
    trend_frame.loc[trend_frame.index[-3], "ema_20"] = 99000.0
    trend_frame.loc[trend_frame.index[-3], "ema_50"] = 100000.0

    intents = plugin.generate_candidates(_context(_entry_frame(), trend_frame))

    assert intents == []


def test_partial67_transition_buffer_can_be_relaxed_to_latest_trend_only():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionBufferStrategy(
        {"trend_persistence_bars": 1}
    )
    trend_frame = _trend_frame()
    trend_frame.loc[trend_frame.index[-2], "ema_20"] = 99000.0
    trend_frame.loc[trend_frame.index[-2], "ema_50"] = 100000.0

    intents = plugin.generate_candidates(_context(_entry_frame(), trend_frame))

    assert len(intents) == 1
    assert intents[0].metadata["trend_persistence_bars"] == 1
