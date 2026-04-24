import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_mid_drift_guard import (
    DonchianRangeFade4hRangeWidthCv013MidDriftGuardStrategy,
)
from trader.tests.test_donchian_range_fade_4h_strategy import (
    _context,
    _frame,
    _position,
    _stable_range_frame,
)


def _drifting_range_frame():
    highs = [110.0] * 20 + [110.0 + 0.8 * float(i) for i in range(20)]
    closes = [100.0] * 39 + [91.0]
    rsi = [45.0] * 39 + [35.0]
    return _frame(highs=highs, closes=closes, rsi=rsi)


def _stable_mid_relaxed_range_frame():
    highs = [110.0] * 20 + [110.0 + 0.5 * float(i) for i in range(20)]
    lows = [90.0] * 20 + [90.0 - 0.3 * float(i) for i in range(20)]
    closes = [100.0] * 39 + [85.0]
    rsi = [45.0] * 39 + [35.0]
    return _frame(highs=highs, lows=lows, closes=closes, rsi=rsi)


def test_registry_loads_donchian_range_fade_4h_range_width_cv_013_mid_drift_guard_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["donchian_range_fade_4h_range_width_cv_013_mid_drift_guard"]),
        ["donchian_range_fade_4h_range_width_cv_013_mid_drift_guard"],
    )

    plugin = registry.require("donchian_range_fade_4h_range_width_cv_013_mid_drift_guard")
    assert isinstance(plugin, DonchianRangeFade4hRangeWidthCv013MidDriftGuardStrategy)
    assert plugin.params["range_width_cv_max"] == pytest.approx(0.13)
    assert plugin.params["mid_drift_ratio_max"] == pytest.approx(0.10)
    assert "mid_drift_guard" in plugin.tags


def test_mid_drift_guard_blocks_drifting_channels_that_cv_013_allows():
    parent = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    child = DonchianRangeFade4hRangeWidthCv013MidDriftGuardStrategy(
        params={"symbol": "BTC/USDT"}
    )
    frame = _drifting_range_frame()
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
    assert child_state["mid_drift_ratio"] > child.params["mid_drift_ratio_max"]


def test_mid_drift_guard_keeps_low_drift_relaxed_ranges_live():
    parent = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    child = DonchianRangeFade4hRangeWidthCv013MidDriftGuardStrategy(
        params={"symbol": "BTC/USDT"}
    )
    frame = _stable_mid_relaxed_range_frame()
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
    assert child_state["mid_drift_ratio"] < child.params["mid_drift_ratio_max"]
    assert child_intents[0].strategy_id == "donchian_range_fade_4h_range_width_cv_013_mid_drift_guard"


def test_mid_drift_guard_preserves_exit_logic():
    plugin = DonchianRangeFade4hRangeWidthCv013MidDriftGuardStrategy(
        params={"symbol": "BTC/USDT"}
    )
    frame = _stable_range_frame(latest_close=100.5, latest_rsi=55.0)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_MID_TARGET"
