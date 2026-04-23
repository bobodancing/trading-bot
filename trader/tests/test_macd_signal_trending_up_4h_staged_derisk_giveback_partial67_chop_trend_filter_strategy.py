import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_chop_trend_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _position,
    _trend_frame,
)


def _entry_frame_with_chop_metrics(*, adx_values, bbw_values):
    frame = _entry_frame()
    adx_series = list(adx_values)
    bbw_series = list(bbw_values)
    if len(adx_series) < len(frame):
        adx_series = [float(adx_series[0])] * (len(frame) - len(adx_series)) + adx_series
    if len(bbw_series) < len(frame):
        bbw_series = [float(bbw_series[0])] * (len(frame) - len(bbw_series)) + bbw_series
    frame["adx"] = adx_series[-len(frame) :]
    frame["bbw"] = bbw_series[-len(frame) :]
    return frame


def test_registry_loads_macd_signal_trending_up_4h_partial67_chop_trend_filter_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["entry_bbw_ratio_min"] == pytest.approx(0.75)
    assert {"adx", "bbw"}.issubset(plugin.required_indicators)


def test_partial67_chop_trend_filter_generates_long_intent_when_compression_is_not_present():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy()
    adx_values = [24.0] * 20 + [25.0, 26.0, 27.0, 28.0, 29.0, 30.0]
    bbw_values = [0.03] * 10 + [0.032] * 10 + [0.034] * 6

    intents = plugin.generate_candidates(
        _context(
            _entry_frame_with_chop_metrics(adx_values=adx_values, bbw_values=bbw_values),
            _trend_frame(),
        )
    )

    assert len(intents) == 1
    intent = intents[0]
    assert (
        intent.strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter"
    )
    assert intent.entry_type == "macd_signal_cross_up_chop_trend_filtered"
    assert intent.metadata["entry_adx_slope_5"] == pytest.approx(5.0)
    assert intent.metadata["entry_bbw_ratio"] > intent.metadata["entry_bbw_ratio_min"]


def test_partial67_chop_trend_filter_blocks_falling_adx_with_compressed_bbw():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy()
    adx_values = [35.0] * 20 + [35.0, 34.0, 33.0, 31.0, 29.0, 26.0]
    bbw_values = [0.05] * 20 + [0.02] * 6

    intents = plugin.generate_candidates(
        _context(
            _entry_frame_with_chop_metrics(adx_values=adx_values, bbw_values=bbw_values),
            _trend_frame(),
        )
    )

    assert intents == []


def test_partial67_chop_trend_filter_preserves_partial67_management():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    entry_frame["adx"] = [25.0] * len(entry_frame)
    entry_frame["bbw"] = [0.03] * len(entry_frame)
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
