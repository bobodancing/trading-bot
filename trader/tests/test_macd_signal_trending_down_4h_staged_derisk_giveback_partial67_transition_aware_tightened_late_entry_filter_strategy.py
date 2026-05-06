from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _trend_frame,
)


STRATEGY_ID = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)


def _downtrend_frame():
    return _trend_frame(ema_20_values=(99000.0,), ema_50_values=(100000.0,))


def _short_entry_frame(**kwargs):
    params = {
        "macd_values": (0.05, -0.08),
        "signal_values": (0.04, -0.02),
        "ema_20": 106000.0,
        "close_offset": -500.0,
    }
    params.update(kwargs)
    return _entry_frame(**params)


def _short_position(
    *,
    entry_price=106500.0,
    current_sl=108000.0,
    initial_sl=108000.0,
    lowest_price=104500.0,
    plugin_state=None,
):
    return SimpleNamespace(
        symbol="BTC/USDT",
        entry_time=datetime(2026, 1, 5, tzinfo=timezone.utc),
        entry_price=entry_price,
        avg_entry=entry_price,
        current_sl=current_sl,
        initial_sl=initial_sl,
        lowest_price=lowest_price,
        plugin_state=dict(plugin_state or {}),
        exit_reason=None,
    )


def test_registry_loads_macd_signal_trending_down_research_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog([STRATEGY_ID]),
        [STRATEGY_ID],
    )

    plugin = registry.require(STRATEGY_ID)
    assert isinstance(
        plugin,
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["transition_prior_negative_hist_min"] == pytest.approx(10.0)
    assert plugin.allowed_symbols == {"BTC/USDT"}
    assert plugin.max_concurrent_positions == 1
    assert "short_only" in plugin.tags


def test_macd_signal_trending_down_research_plugin_generates_short_intent():
    plugin = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )

    intents = plugin.generate_candidates(_context(_short_entry_frame(), _downtrend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == STRATEGY_ID
    assert intent.side == "SHORT"
    assert intent.entry_type == (
        "macd_signal_cross_down_transition_aware_tightened_late_entry_filtered"
    )
    assert intent.stop_hint.price > intent.entry_price
    assert intent.metadata["trend_spread"] == pytest.approx(0.01)


def test_macd_signal_trending_down_research_plugin_requires_downtrend_gate():
    plugin = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )

    intents = plugin.generate_candidates(_context(_short_entry_frame(), _trend_frame()))

    assert intents == []


def test_macd_signal_trending_down_research_plugin_triggers_short_partial_derisk():
    plugin = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )
    entry_frame = _short_entry_frame(
        macd_values=(-0.08, -0.10),
        signal_values=(-0.02, -0.05),
        close_offset=-200.0,
    )
    position = _short_position(lowest_price=104500.0)

    decision = plugin.update_position(_context(entry_frame, _downtrend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
    assert decision.new_sl == pytest.approx(106500.0)
    assert position.plugin_state[plugin.id]["derisk_done"] is True


def test_macd_signal_trending_down_research_plugin_preserves_cross_up_exit():
    plugin = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy()
    )
    entry_frame = _short_entry_frame(
        macd_values=(-0.08, 0.04),
        signal_values=(-0.02, 0.01),
        close_offset=100.0,
    )
    position = _short_position(lowest_price=106000.0)

    decision = plugin.update_position(_context(entry_frame, _downtrend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "MACD_SIGNAL_CROSS_UP"
