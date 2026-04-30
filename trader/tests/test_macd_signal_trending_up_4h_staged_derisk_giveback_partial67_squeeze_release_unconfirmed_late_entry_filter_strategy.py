import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _position,
    _trend_frame,
)


PLUGIN_ID = (
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
    "squeeze_release_unconfirmed_late_entry_filter"
)


def _entry_frame_with_squeeze_release(
    *,
    close_offset=500.0,
    release_active=True,
    unconfirmed_breakout=True,
):
    frame = _entry_frame(length=130, close_offset=close_offset)
    frame["bbw"] = 1.0
    if release_active:
        frame.loc[frame.index[-21:-1], "bbw"] = 0.2
        frame.loc[frame.index[-1], "bbw"] = 2.0
    if not unconfirmed_breakout:
        prev_idx = frame.index[-2]
        frame.loc[prev_idx, "close"] = frame.loc[prev_idx, "high"]
    return frame


def test_registry_loads_macd_signal_trending_up_4h_partial67_squeeze_release_unconfirmed_late_entry_filter_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog([PLUGIN_ID]),
        [PLUGIN_ID],
    )

    plugin = registry.require(PLUGIN_ID)

    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["entry_ema_extension_atr_max"] == pytest.approx(1.25)
    assert plugin.params["squeeze_pctrank_window"] == 100
    assert plugin.params["squeeze_trough_lookback"] == 20
    assert plugin.params["squeeze_release_current_pctrank_min"] == pytest.approx(60.0)
    assert plugin.params["squeeze_trough_pctrank_max"] == pytest.approx(15.0)
    assert plugin.params["weak_breakout_upper_fraction"] == pytest.approx(0.25)
    assert "bbw" in plugin.required_indicators


def test_squeeze_release_unconfirmed_late_entry_filter_allows_overextended_entry_when_context_is_inactive():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_squeeze_release(
        close_offset=2000.0,
        release_active=False,
    )

    intents = plugin.generate_candidates(_context(entry_frame, _trend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == PLUGIN_ID
    assert (
        intent.entry_type
        == "macd_signal_cross_up_squeeze_release_unconfirmed_late_entry_filtered"
    )
    assert intent.metadata["weak_tape_gate_mode"] == "squeeze_release_unconfirmed"
    assert intent.metadata["weak_tape_squeeze_release_context_active"] is False
    assert intent.metadata["weak_tape_context_active"] is False
    assert intent.metadata["weak_tape_context_reason"] == "none"
    assert intent.metadata["entry_extension_atr"] > intent.metadata[
        "entry_ema_extension_atr_max"
    ]


def test_squeeze_release_unconfirmed_late_entry_filter_blocks_overextended_entry_when_context_is_active():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_squeeze_release(close_offset=2000.0)

    intents = plugin.generate_candidates(_context(entry_frame, _trend_frame()))

    assert intents == []


def test_squeeze_release_unconfirmed_late_entry_filter_keeps_inside_cap_entry_when_context_is_active():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_squeeze_release(close_offset=500.0)

    intents = plugin.generate_candidates(_context(entry_frame, _trend_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.metadata["weak_tape_squeeze_release_context_active"] is True
    assert intent.metadata["weak_tape_squeeze_release_veto_active"] is False
    assert intent.metadata["weak_tape_context_active"] is False
    assert intent.metadata["weak_tape_unconfirmed_breakout_active"] is True
    assert intent.metadata["weak_tape_squeeze_release_current_pctrank"] >= 60.0
    assert intent.metadata["weak_tape_squeeze_trough_pctrank_min"] <= 15.0
    assert intent.metadata["entry_extension_atr"] == pytest.approx(500.0 / 1200.0)


def test_squeeze_release_unconfirmed_late_entry_filter_skips_out_of_scope_symbol():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_squeeze_release()

    intents = plugin.generate_candidates(
        _context(entry_frame, _trend_frame(), symbols=["ETH/USDT"])
    )

    assert intents == []


def test_squeeze_release_unconfirmed_late_entry_filter_preserves_partial67_management():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy()
    )
    entry_frame = _entry_frame_with_squeeze_release(close_offset=-200.0)
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
