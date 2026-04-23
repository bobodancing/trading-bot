import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _position,
    _trend_frame,
)


def test_registry_loads_macd_signal_trending_up_4h_partial67_late_entry_filter_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["entry_ema_extension_atr_max"] == pytest.approx(1.25)


def test_partial67_late_entry_filter_generates_long_intent_within_stretch_cap():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy()

    intents = plugin.generate_candidates(
        _context(_entry_frame(ema_20=106000.0, close_offset=500.0), _trend_frame())
    )

    assert len(intents) == 1
    intent = intents[0]
    assert (
        intent.strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter"
    )
    assert intent.entry_type == "macd_signal_cross_up_late_entry_filtered"
    assert intent.metadata["entry_extension_atr"] == pytest.approx(500.0 / 1200.0)
    assert intent.metadata["entry_ema_extension_atr_max"] == pytest.approx(1.25)


def test_partial67_late_entry_filter_blocks_overextended_entry():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy()

    intents = plugin.generate_candidates(
        _context(_entry_frame(ema_20=106000.0, close_offset=2000.0), _trend_frame())
    )

    assert intents == []


def test_partial67_late_entry_filter_preserves_partial67_management():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)

