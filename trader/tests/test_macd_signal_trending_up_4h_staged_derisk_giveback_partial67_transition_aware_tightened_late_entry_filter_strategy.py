import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_aware_late_entry_filter_strategy import (
    _entry_frame_with_transition_hist,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _position,
    _trend_frame,
)


def test_registry_loads_macd_signal_trending_up_4h_partial67_transition_aware_tightened_late_entry_filter_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["entry_ema_extension_atr_max"] == pytest.approx(1.25)
    assert plugin.params["transition_lookback_bars"] == 12
    assert plugin.params["transition_hist_ratio_max"] == pytest.approx(0.25)
    assert plugin.params["transition_prior_positive_hist_min"] == pytest.approx(10.0)
    assert plugin.params["transition_extension_atr_trigger"] == pytest.approx(3.0)


def test_transition_aware_tightened_late_entry_filter_allows_overextended_entry_when_transition_context_is_inactive():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_transition_hist(
        close_offset=2000.0,
        hist_tail=[-2.0, -1.5, -1.0, -0.8, -0.6, -0.4, -0.3, -0.2, -0.1, -0.05, -0.02, 0.08],
    )

    intents = plugin.generate_candidates(_context(entry_frame, _trend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert (
        intent.strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter"
    )
    assert (
        intent.entry_type
        == "macd_signal_cross_up_transition_aware_tightened_late_entry_filtered"
    )
    assert intent.metadata["weak_tape_gate_mode"] == "transition_aware_tightened"
    assert intent.metadata["weak_tape_transition_context_active"] is False
    assert intent.metadata["weak_tape_context_active"] is False
    assert intent.metadata["weak_tape_context_reason"] == "none"
    assert intent.metadata["entry_extension_atr"] > intent.metadata["entry_ema_extension_atr_max"]


def test_transition_aware_tightened_late_entry_filter_keeps_moderate_overextension_when_transition_context_is_active():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_transition_hist(
        close_offset=2000.0,
        hist_tail=[12.0, 18.0, 24.0, 30.0, 22.0, 16.0, 10.0, 4.0, 1.0, 0.5, -1.0, 6.0],
    )

    intents = plugin.generate_candidates(_context(entry_frame, _trend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.metadata["weak_tape_transition_context_active"] is True
    assert intent.metadata["weak_tape_context_active"] is False
    assert intent.metadata["weak_tape_transition_veto_active"] is False
    assert intent.metadata["weak_tape_transition_hist_ratio"] == pytest.approx(6.0 / 30.0)
    assert intent.metadata["entry_extension_atr"] == pytest.approx(2000.0 / 1200.0)
    assert (
        intent.metadata["entry_extension_atr"]
        < intent.metadata["weak_tape_transition_extension_atr_trigger"]
    )


def test_transition_aware_tightened_late_entry_filter_blocks_extreme_overextended_entry_when_transition_context_is_active():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_transition_hist(
        close_offset=4000.0,
        hist_tail=[12.0, 18.0, 24.0, 30.0, 22.0, 16.0, 10.0, 4.0, 1.0, 0.5, -1.0, 6.0],
    )

    intents = plugin.generate_candidates(_context(entry_frame, _trend_frame()))

    assert intents == []


def test_transition_aware_tightened_late_entry_filter_preserves_partial67_management():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_transition_hist(
        close_offset=-200.0,
        hist_tail=[-2.0, -1.5, -1.0, -0.8, -0.6, -0.4, -0.3, -0.2, -0.1, -0.05, -0.02, 0.08],
    )
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
