import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)
from trader.tests.test_macd_signal_trending_up_4h_staged_derisk_giveback_strategy import (
    _context,
    _entry_frame,
    _position,
    _trend_frame,
)


def test_registry_loads_macd_signal_trending_up_4h_staged_derisk_giveback_partial67_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(
            ["macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67"]
        ),
        ["macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67"],
    )

    plugin = registry.require(
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67"
    )
    assert isinstance(plugin, MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy)
    assert plugin.params["derisk_close_pct"] == pytest.approx(0.67)


def test_macd_signal_trending_up_4h_staged_derisk_giveback_partial67_generates_long_intent():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy()

    intents = plugin.generate_candidates(_context(_entry_frame(), _trend_frame()))

    assert len(intents) == 1
    assert (
        intents[0].strategy_id
        == "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67"
    )


def test_staged_derisk_partial67_uses_larger_partial_close_size():
    plugin = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy()
    entry_frame = _entry_frame(ema_20=106000.0, close_offset=-200.0)
    position = _position(highest_price=108200.0)

    decision = plugin.update_position(_context(entry_frame, _trend_frame()), position)

    assert decision.action == Action.PARTIAL_CLOSE
    assert decision.reason == "DERISK_PARTIAL_GIVEBACK"
    assert decision.close_pct == pytest.approx(0.67)
    assert position.plugin_state[plugin.id]["derisk_done"] is True
