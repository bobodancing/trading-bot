import pytest

from trader.strategies import StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_decay_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _trend_frame,
)


def _trend_frame_with_tail_spreads(spreads, *, ema_50=100000.0):
    frame = _trend_frame()
    for idx, spread in zip(frame.index[-len(spreads) :], spreads):
        frame.loc[idx, "ema_50"] = ema_50
        frame.loc[idx, "ema_20"] = ema_50 * (1.0 + spread)
        frame.loc[idx, "close"] = frame.loc[idx, "ema_20"]
    return frame


def test_registry_loads_macd_signal_trending_up_4h_partial67_transition_decay_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["trend_spread_slope_bars"] == 3
    assert plugin.params["trend_spread_slope_min"] == pytest.approx(0.0)


def test_partial67_transition_decay_generates_long_intent_when_spread_expands():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy()
    trend_frame = _trend_frame_with_tail_spreads([0.012, 0.013, 0.014, 0.015])

    intents = plugin.generate_candidates(_context(_entry_frame(), trend_frame))

    assert len(intents) == 1
    assert (
        intents[0].strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter"
    )
    assert intents[0].entry_type == "macd_signal_cross_up_transition_decay_filtered"
    assert intents[0].metadata["trend_spread_delta"] == pytest.approx(0.003)


def test_partial67_transition_decay_blocks_when_spread_contracts():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy()
    trend_frame = _trend_frame_with_tail_spreads([0.015, 0.014, 0.013, 0.012])

    intents = plugin.generate_candidates(_context(_entry_frame(), trend_frame))

    assert intents == []


def test_partial67_transition_decay_can_be_relaxed_with_negative_slope_min():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy(
        {"trend_spread_slope_min": -0.01}
    )
    trend_frame = _trend_frame_with_tail_spreads([0.015, 0.014, 0.013, 0.012])

    intents = plugin.generate_candidates(_context(_entry_frame(), trend_frame))

    assert len(intents) == 1
    assert intents[0].metadata["trend_spread_slope_min"] == pytest.approx(-0.01)
