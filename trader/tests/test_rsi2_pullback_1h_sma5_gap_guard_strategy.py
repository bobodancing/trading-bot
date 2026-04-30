import pytest

from trader.strategies import StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.rsi2_pullback_1h import Rsi2Pullback1hStrategy
from trader.strategies.plugins.rsi2_pullback_1h_sma5_gap_guard import (
    Rsi2Pullback1hSma5GapGuardStrategy,
)
from trader.tests.test_rsi2_pullback_1h_strategy import _context, _entry_frame


def test_registry_loads_rsi2_pullback_1h_sma5_gap_guard_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["rsi2_pullback_1h_sma5_gap_guard"]),
        ["rsi2_pullback_1h_sma5_gap_guard"],
    )

    plugin = registry.require("rsi2_pullback_1h_sma5_gap_guard")
    assert isinstance(plugin, Rsi2Pullback1hSma5GapGuardStrategy)
    assert plugin.params["min_sma5_gap_atr"] == pytest.approx(0.75)
    assert plugin.target_regime == "ANY"
    assert "sma5_gap_guard" in plugin.tags


def test_rsi2_pullback_1h_sma5_gap_guard_blocks_shallow_expected_bounce():
    plugin = Rsi2Pullback1hSma5GapGuardStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_drop=5.0, atr=[10.0] * 210)

    intents = plugin.generate_candidates(_context(frame))

    assert intents == []


def test_rsi2_pullback_1h_sma5_gap_guard_emits_when_gap_passes():
    plugin = Rsi2Pullback1hSma5GapGuardStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_drop=5.0, atr=[4.0] * 210)

    intents = plugin.generate_candidates(_context(frame))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "rsi2_pullback_1h_sma5_gap_guard"
    assert intent.metadata["sma5_gap_atr"] == pytest.approx(0.85)
    assert intent.metadata["min_sma5_gap_atr"] == pytest.approx(0.75)


def test_rsi2_pullback_1h_parent_default_does_not_apply_gap_guard():
    plugin = Rsi2Pullback1hStrategy(params={"symbol": "BTC/USDT"})
    frame = _entry_frame(latest_drop=5.0, atr=[10.0] * 210)

    intents = plugin.generate_candidates(_context(frame))

    assert len(intents) == 1
    assert intents[0].metadata["min_sma5_gap_atr"] is None
