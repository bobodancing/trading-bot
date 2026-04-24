import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _position,
    _trend_frame,
)


def _trend_frame_with_tail_spreads(spreads, *, ema_50=100000.0):
    frame = _trend_frame()
    for idx, spread in zip(frame.index[-len(spreads) :], spreads):
        frame.loc[idx, "ema_50"] = ema_50
        frame.loc[idx, "ema_20"] = ema_50 * (1.0 + spread)
        frame.loc[idx, "close"] = frame.loc[idx, "ema_20"]
    return frame


def _entry_frame_with_context(*, close_offset, adx_values, bbw_values, ema_20=106000.0):
    frame = _entry_frame(ema_20=ema_20, close_offset=close_offset)
    adx_series = list(adx_values)
    bbw_series = list(bbw_values)
    if len(adx_series) < len(frame):
        adx_series = [float(adx_series[0])] * (len(frame) - len(adx_series)) + adx_series
    if len(bbw_series) < len(frame):
        bbw_series = [float(bbw_series[0])] * (len(frame) - len(bbw_series)) + bbw_series
    frame["adx"] = adx_series[-len(frame) :]
    frame["bbw"] = bbw_series[-len(frame) :]
    return frame


def test_registry_loads_macd_signal_trending_up_4h_partial67_chop_trend_only_late_entry_filter_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["entry_ema_extension_atr_max"] == pytest.approx(1.25)
    assert plugin.params["entry_bbw_ratio_min"] == pytest.approx(0.75)
    assert {"adx", "bbw"}.issubset(plugin.required_indicators)


def test_chop_trend_only_late_entry_filter_allows_overextended_entry_when_chop_trend_is_inactive():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy()
    )
    trend_frame = _trend_frame_with_tail_spreads([0.015, 0.014, 0.013, 0.012])
    entry_frame = _entry_frame_with_context(
        close_offset=2000.0,
        adx_values=[24.0] * 20 + [25.0, 26.0, 27.0, 28.0, 29.0, 30.0],
        bbw_values=[0.03] * 10 + [0.032] * 10 + [0.034] * 6,
    )

    intents = plugin.generate_candidates(_context(entry_frame, trend_frame))

    assert len(intents) == 1
    intent = intents[0]
    assert (
        intent.strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter"
    )
    assert intent.entry_type == "macd_signal_cross_up_chop_trend_only_late_entry_filtered"
    assert intent.metadata["weak_tape_gate_mode"] == "chop_trend_only"
    assert intent.metadata["weak_tape_context_active"] is False
    assert intent.metadata["weak_tape_context_reason"] == "none"
    assert intent.metadata["weak_tape_trend_decay_active"] is False
    assert intent.metadata["entry_extension_atr"] > intent.metadata["entry_ema_extension_atr_max"]


def test_chop_trend_only_late_entry_filter_blocks_overextended_entry_when_chop_trend_is_active():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy()
    )
    trend_frame = _trend_frame_with_tail_spreads([0.012, 0.013, 0.014, 0.015])
    entry_frame = _entry_frame_with_context(
        close_offset=2000.0,
        adx_values=[35.0] * 20 + [35.0, 34.0, 33.0, 31.0, 29.0, 26.0],
        bbw_values=[0.05] * 20 + [0.02] * 6,
    )

    intents = plugin.generate_candidates(_context(entry_frame, trend_frame))

    assert intents == []


def test_chop_trend_only_late_entry_filter_ignores_trend_decay_activation():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy()
    )
    trend_frame = _trend_frame_with_tail_spreads([0.015, 0.014, 0.013, 0.012])
    entry_frame = _entry_frame_with_context(
        close_offset=2000.0,
        adx_values=[24.0] * 20 + [25.0, 26.0, 27.0, 28.0, 29.0, 30.0],
        bbw_values=[0.03] * 10 + [0.032] * 10 + [0.034] * 6,
    )

    intents = plugin.generate_candidates(_context(entry_frame, trend_frame))

    assert len(intents) == 1
    assert intents[0].metadata["weak_tape_context_active"] is False
    assert intents[0].metadata["weak_tape_context_reason"] == "none"


def test_chop_trend_only_late_entry_filter_keeps_entry_when_chop_trend_is_active_but_stretch_is_small():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy()
    )
    trend_frame = _trend_frame_with_tail_spreads([0.012, 0.013, 0.014, 0.015])
    entry_frame = _entry_frame_with_context(
        close_offset=500.0,
        adx_values=[35.0] * 20 + [35.0, 34.0, 33.0, 31.0, 29.0, 26.0],
        bbw_values=[0.05] * 20 + [0.02] * 6,
    )

    intents = plugin.generate_candidates(_context(entry_frame, trend_frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.metadata["weak_tape_context_active"] is True
    assert intent.metadata["weak_tape_context_reason"] == "chop_trend"
    assert intent.metadata["weak_tape_chop_trend_active"] is True
    assert intent.metadata["entry_extension_atr"] == pytest.approx(500.0 / 1200.0)


def test_chop_trend_only_late_entry_filter_preserves_partial67_management():
    plugin = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy()
    )
    trend_frame = _trend_frame_with_tail_spreads([0.012, 0.013, 0.014, 0.015])
    entry_frame = _entry_frame_with_context(
        close_offset=-200.0,
        adx_values=[24.0] * 20 + [25.0, 26.0, 27.0, 28.0, 29.0, 30.0],
        bbw_values=[0.03] * 10 + [0.032] * 10 + [0.034] * 6,
    )
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, trend_frame), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
