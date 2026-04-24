import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard import (
    DonchianRangeFade4hRangeWidthCv013TouchImbalanceGuardStrategy,
)
from trader.tests.test_donchian_range_fade_4h_strategy import (
    _context,
    _frame,
    _position,
    _stable_range_frame,
)


def _touch_imbalanced_range_frame():
    highs = [110.0] * 25 + [110.0, 108.0, 108.0, 108.0, 108.0, 108.0, 110.0, 108.0, 108.0, 108.0, 108.0, 108.0, 108.0, 108.0, 110.0]
    lows = [90.0] * 25 + [92.0] * 14 + [90.0]
    closes = [100.0] * 39 + [90.8]
    rsi = [45.0] * 39 + [35.0]
    return _frame(highs=highs, lows=lows, closes=closes, rsi=rsi)


def _softly_balanced_relaxed_range_frame():
    highs = [110.0] * 25 + [110.0, 108.0, 108.0, 110.0, 108.0, 108.0, 110.0, 108.0, 108.0, 110.0, 108.0, 108.0, 108.0, 108.0, 110.0]
    lows = [90.0] * 25 + [92.0] * 13 + [90.0, 90.0]
    closes = [100.0] * 39 + [90.8]
    rsi = [45.0] * 39 + [35.0]
    return _frame(highs=highs, lows=lows, closes=closes, rsi=rsi)


def test_registry_loads_donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard"]),
        ["donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard"],
    )

    plugin = registry.require("donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard")
    assert isinstance(plugin, DonchianRangeFade4hRangeWidthCv013TouchImbalanceGuardStrategy)
    assert plugin.params["range_width_cv_max"] == pytest.approx(0.13)
    assert plugin.params["touch_imbalance_ratio_max"] == pytest.approx(2.5)
    assert "touch_imbalance_guard" in plugin.tags


def test_touch_imbalance_guard_blocks_three_to_one_boundary_structures():
    parent = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    child = DonchianRangeFade4hRangeWidthCv013TouchImbalanceGuardStrategy(
        params={"symbol": "BTC/USDT"}
    )
    frame = _touch_imbalanced_range_frame()
    context = _context({"BTC/USDT": frame})

    parent_intents = parent.generate_candidates(context)
    child_intents = child.generate_candidates(context)
    child_state = child._range_state(
        child._with_donchian(frame, 20, 15),
        range_window=15,
        range_width_cv_max=0.13,
        touch_atr_band=0.25,
        min_lower_touches=1,
        min_upper_touches=1,
    )

    assert len(parent_intents) == 1
    assert child_intents == []
    assert child_state["touch_imbalance_ratio"] == pytest.approx(3.0)
    assert child_state["touch_imbalance_ratio"] > child.params["touch_imbalance_ratio_max"]


def test_touch_imbalance_guard_keeps_softly_balanced_relaxed_ranges_live():
    parent = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    child = DonchianRangeFade4hRangeWidthCv013TouchImbalanceGuardStrategy(
        params={"symbol": "BTC/USDT"}
    )
    frame = _softly_balanced_relaxed_range_frame()
    context = _context({"BTC/USDT": frame})

    parent_intents = parent.generate_candidates(context)
    child_intents = child.generate_candidates(context)
    child_state = child._range_state(
        child._with_donchian(frame, 20, 15),
        range_window=15,
        range_width_cv_max=0.13,
        touch_atr_band=0.25,
        min_lower_touches=1,
        min_upper_touches=1,
    )

    assert len(parent_intents) == 1
    assert len(child_intents) == 1
    assert child_state["touch_imbalance_ratio"] == pytest.approx(2.5)
    assert child_intents[0].strategy_id == "donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard"


def test_touch_imbalance_guard_preserves_exit_logic():
    plugin = DonchianRangeFade4hRangeWidthCv013TouchImbalanceGuardStrategy(
        params={"symbol": "BTC/USDT"}
    )
    frame = _stable_range_frame(latest_close=100.5, latest_rsi=55.0)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_MID_TARGET"
