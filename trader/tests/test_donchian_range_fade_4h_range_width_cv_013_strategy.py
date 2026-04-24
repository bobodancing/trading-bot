import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.donchian_range_fade_4h import DonchianRangeFade4hStrategy
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)
from trader.tests.test_donchian_range_fade_4h_strategy import (
    _context,
    _frame,
    _position,
    _stable_range_frame,
)


def _moderately_expanding_range_frame():
    highs = [110.0] * 20 + [110.0 + 0.8 * float(i) for i in range(20)]
    closes = [100.0] * 39 + [91.0]
    rsi = [45.0] * 39 + [35.0]
    return _frame(highs=highs, closes=closes, rsi=rsi)


def test_registry_loads_donchian_range_fade_4h_range_width_cv_013_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog(["donchian_range_fade_4h_range_width_cv_013"]),
        ["donchian_range_fade_4h_range_width_cv_013"],
    )

    plugin = registry.require("donchian_range_fade_4h_range_width_cv_013")
    assert isinstance(plugin, DonchianRangeFade4hRangeWidthCv013Strategy)
    assert plugin.params["range_width_cv_max"] == pytest.approx(0.13)
    assert "range_width_cv_013" in plugin.tags


def test_donchian_range_fade_4h_range_width_cv_013_emits_where_baseline_is_starved():
    baseline = DonchianRangeFade4hStrategy(params={"symbol": "BTC/USDT"})
    child = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    frame = _moderately_expanding_range_frame()
    context = _context({"BTC/USDT": frame})

    baseline_intents = baseline.generate_candidates(context)
    child_intents = child.generate_candidates(context)

    assert baseline_intents == []
    assert len(child_intents) == 1
    intent = child_intents[0]
    assert intent.strategy_id == "donchian_range_fade_4h_range_width_cv_013"
    assert intent.metadata["range_width_cv_max"] == pytest.approx(0.13)
    assert 0.10 < intent.metadata["width_cv"] < 0.13


def test_donchian_range_fade_4h_range_width_cv_013_still_rejects_overexpanded_ranges():
    plugin = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    highs = [110.0] * 20 + [110.0 + 1.0 * float(i) for i in range(20)]
    frame = _frame(highs=highs, closes=[100.0] * 39 + [91.0], rsi=[45.0] * 39 + [35.0])

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_range_width_cv_013_preserves_exit_logic():
    plugin = DonchianRangeFade4hRangeWidthCv013Strategy(params={"symbol": "BTC/USDT"})
    frame = _stable_range_frame(latest_close=100.5, latest_rsi=55.0)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_MID_TARGET"
