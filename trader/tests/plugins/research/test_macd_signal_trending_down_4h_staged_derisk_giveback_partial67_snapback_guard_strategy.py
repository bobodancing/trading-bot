import pytest

from trader.strategies import StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_snapback_followthrough_guard import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy,
)
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_snapback_guard import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy,
)
from trader.tests.plugins.research.test_macd_signal_trending_down_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter_strategy import (
    _downtrend_frame,
    _short_entry_frame,
)
from trader.tests.plugins.research.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
)


STRATEGY_ID = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "snapback_guard"
)
FOLLOWTHROUGH_STRATEGY_ID = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "snapback_followthrough_guard"
)


def _late_breakdown_frame():
    frame = _short_entry_frame(ema_20=106000.0, close_offset=-4000.0)
    frame.loc[frame.index[:-1], "high"] = 107500.0
    frame.loc[frame.index[:-1], "low"] = 104000.0
    frame.loc[frame.index[-1], "low"] = 101700.0
    return frame


def _moderate_followthrough_breakdown_frame():
    frame = _short_entry_frame(ema_20=106000.0, close_offset=-1800.0)
    frame.loc[frame.index[:-1], "high"] = 108000.0
    frame.loc[frame.index[:-1], "low"] = 104800.0
    frame.loc[frame.index[-1], "high"] = 106000.0
    frame.loc[frame.index[-1], "low"] = 103900.0
    return frame


def _exhausted_late_breakdown_frame():
    frame = _short_entry_frame(
        ema_20=106000.0,
        close_offset=-4000.0,
        macd_values=(0.05, -0.08),
        signal_values=(0.04, -0.02),
    )
    frame.loc[frame.index[:-1], "high"] = 107500.0
    frame.loc[frame.index[:-1], "low"] = 104000.0
    frame.loc[frame.index[-1], "high"] = 106000.0
    frame.loc[frame.index[-1], "low"] = 101700.0
    return frame


def test_registry_loads_snapback_guard_research_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog([STRATEGY_ID]),
        [STRATEGY_ID],
    )

    plugin = registry.require(STRATEGY_ID)

    assert isinstance(
        plugin,
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy,
    )
    assert plugin.params["snapback_guard_lookback_bars"] == 12
    assert plugin.params["snapback_downside_move_atr_min"] == pytest.approx(3.0)
    assert plugin.params["snapback_entry_extension_atr_min"] == pytest.approx(1.25)
    assert "snapback_guard" in plugin.tags
    assert "failure_attribution_repair_probe" in plugin.tags


def test_snapback_guard_blocks_late_breakdown_short_entry():
    plugin = MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy()

    intents = plugin.generate_candidates(
        _context(_late_breakdown_frame(), _downtrend_frame())
    )

    assert intents == []


def test_snapback_guard_allows_moderate_breakdown_short_entry():
    plugin = MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy()
    frame = _short_entry_frame(ema_20=106000.0, close_offset=-1000.0)
    frame.loc[frame.index[:-1], "high"] = 107000.0
    frame.loc[frame.index[:-1], "low"] = 104500.0
    frame.loc[frame.index[-1], "low"] = 104300.0

    intents = plugin.generate_candidates(_context(frame, _downtrend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == STRATEGY_ID
    assert intent.side == "SHORT"
    assert intent.entry_type == "macd_signal_cross_down_snapback_guard_late_entry_filtered"
    assert intent.metadata["weak_tape_gate_mode"] == "snapback_guard"
    assert intent.metadata["snapback_guard_active"] is False
    assert intent.metadata["snapback_guard_breakdown_active"] is True
    assert intent.metadata["snapback_guard_downside_move_atr"] < 3.0


def test_registry_loads_snapback_followthrough_guard_research_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog([FOLLOWTHROUGH_STRATEGY_ID]),
        [FOLLOWTHROUGH_STRATEGY_ID],
    )

    plugin = registry.require(FOLLOWTHROUGH_STRATEGY_ID)

    assert isinstance(
        plugin,
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy,
    )
    assert plugin.params["followthrough_close_through_atr_min"] == pytest.approx(0.25)
    assert plugin.params["followthrough_close_through_atr_max"] == pytest.approx(1.0)
    assert plugin.params["followthrough_close_location_max"] == pytest.approx(0.35)
    assert plugin.params["followthrough_downside_move_atr_max"] == pytest.approx(3.5)
    assert plugin.params["followthrough_entry_extension_atr_max"] == pytest.approx(2.0)
    assert plugin.params["followthrough_hist_expansion_min"] == pytest.approx(1.0)
    assert plugin.params["followthrough_votes_min"] == 2
    assert "followthrough_guard" in plugin.tags


def test_snapback_followthrough_guard_keeps_confirmed_bearish_continuation():
    plugin = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy()
    )

    intents = plugin.generate_candidates(
        _context(_moderate_followthrough_breakdown_frame(), _downtrend_frame())
    )

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == FOLLOWTHROUGH_STRATEGY_ID
    assert intent.entry_type == (
        "macd_signal_cross_down_snapback_followthrough_late_entry_filtered"
    )
    assert intent.metadata["weak_tape_gate_mode"] == "snapback_followthrough_guard"
    assert intent.metadata["snapback_late_breakdown_active"] is True
    assert intent.metadata["followthrough_confirmed"] is True
    assert intent.metadata["followthrough_exhaustion_active"] is False
    assert intent.metadata["followthrough_votes"] >= 2


def test_snapback_followthrough_guard_blocks_exhausted_breakdown():
    plugin = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy()
    )
    frame = _exhausted_late_breakdown_frame()

    metrics = plugin._followthrough_guard_metrics(
        frame,
        lookback_bars=plugin.params["snapback_guard_lookback_bars"],
        downside_move_atr_min=plugin.params["snapback_downside_move_atr_min"],
        entry_extension_atr_min=plugin.params["snapback_entry_extension_atr_min"],
        close_through_atr_min=plugin.params["followthrough_close_through_atr_min"],
        close_through_atr_max=plugin.params["followthrough_close_through_atr_max"],
        close_location_max=plugin.params["followthrough_close_location_max"],
        downside_move_atr_max=plugin.params["followthrough_downside_move_atr_max"],
        entry_extension_atr_max=plugin.params["followthrough_entry_extension_atr_max"],
        hist_expansion_min=plugin.params["followthrough_hist_expansion_min"],
        votes_min=plugin.params["followthrough_votes_min"],
    )

    assert metrics is not None
    assert metrics["followthrough_raw_confirmed"] is True
    assert metrics["followthrough_exhaustion_active"] is True
    assert metrics["followthrough_confirmed"] is False
    intents = plugin.generate_candidates(_context(frame, _downtrend_frame()))

    assert intents == []
