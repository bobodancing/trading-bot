import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_remainder_ratchet import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67RemainderRatchetStrategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _position,
    _trend_frame,
)


def test_registry_loads_macd_signal_trending_up_4h_partial67_remainder_ratchet_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            [
                "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet"
            ]
        ),
        [
            "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet"
        ],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet"
    )
    assert isinstance(
        plugin,
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67RemainderRatchetStrategy,
    )
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)
    assert plugin.params["remainder_ratchet_arm_r"] == pytest.approx(1.0)
    assert plugin.params["remainder_ratchet_giveback_r"] == pytest.approx(1.0)


def test_partial67_remainder_ratchet_generates_same_long_intent_shape():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67RemainderRatchetStrategy()

    intents = plugin.generate_candidates(_context(_entry_frame(), _trend_frame()))

    assert len(intents) == 1
    assert (
        intents[0].strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet"
    )
    assert intents[0].entry_type == "macd_signal_cross_up"


def test_partial67_remainder_ratchet_closes_remainder_after_post_partial_giveback():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67RemainderRatchetStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=1700.0)
    position = _position(
        highest_price=109500.0,
        plugin_state={plugin.id: {"derisk_done": True}},
    )

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "REMAINDER_RATCHET_EXIT"
    assert position.exit_reason == "REMAINDER_RATCHET_EXIT"
    assert decision.metadata["max_favorable_r"] == pytest.approx(2.0)
    assert decision.metadata["current_r"] == pytest.approx(0.8)
    assert decision.metadata["giveback_r"] == pytest.approx(1.2)


def test_partial67_remainder_ratchet_waits_when_giveback_is_too_small():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67RemainderRatchetStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=2500.0)
    position = _position(
        highest_price=109500.0,
        plugin_state={plugin.id: {"derisk_done": True}},
    )

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.HOLD


def test_partial67_remainder_ratchet_preserves_partial67_partial_close():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67RemainderRatchetStrategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
    assert position.plugin_state[plugin.id]["derisk_done"] is True
