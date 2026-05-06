import pytest

from trader.strategies import Action, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short import (
    DonchianRangeFade4hRangeWidthCv013ShortStrategy,
)
from trader.tests.test_donchian_range_fade_4h_strategy import (
    _context,
    _frame,
    _position,
)


STRATEGY_ID = "donchian_range_fade_4h_range_width_cv_013_short"


def _stable_upper_range_frame(*, size=40, latest_close=109.2, latest_rsi=65.0):
    closes = [100.0] * (size - 1) + [latest_close]
    rsi = [55.0] * (size - 1) + [latest_rsi]
    return _frame(size=size, closes=closes, rsi=rsi)


def test_registry_loads_donchian_range_fade_4h_range_width_cv_013_short_plugin():
    registry = StrategyRegistry.from_config(
        get_strategy_catalog([STRATEGY_ID]),
        [STRATEGY_ID],
    )

    plugin = registry.require(STRATEGY_ID)
    assert isinstance(plugin, DonchianRangeFade4hRangeWidthCv013ShortStrategy)
    assert plugin.params["range_width_cv_max"] == pytest.approx(0.13)
    assert plugin.params["rsi_entry"] == pytest.approx(60.0)
    assert plugin.allowed_symbols == {"BTC/USDT", "ETH/USDT"}
    assert "short_only" in plugin.tags


def test_donchian_range_fade_4h_range_width_cv_013_short_emits_on_upper_fade():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortStrategy(
        params={"symbol": "BTC/USDT", "stop_atr_mult": 1.5}
    )
    frame = _stable_upper_range_frame()

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == STRATEGY_ID
    assert intent.symbol == "BTC/USDT"
    assert intent.side == "SHORT"
    assert intent.entry_type == "donchian_range_upper_fade"
    assert intent.entry_price == pytest.approx(109.2)
    assert intent.stop_hint.price == pytest.approx(115.2)
    assert intent.stop_hint.metadata["donchian_high"] == pytest.approx(110.0)
    assert intent.metadata["entry_upper_band"] == pytest.approx(109.0)
    assert intent.metadata["range_width_cv_max"] == pytest.approx(0.13)


def test_donchian_range_fade_4h_range_width_cv_013_short_requires_upper_band():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_upper_range_frame(latest_close=108.0)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_range_width_cv_013_short_requires_overbought_rsi():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_upper_range_frame(latest_rsi=55.0)

    intents = plugin.generate_candidates(_context({"BTC/USDT": frame}))

    assert intents == []


def test_donchian_range_fade_4h_range_width_cv_013_short_keeps_fixed_scope():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortStrategy()
    frame = _stable_upper_range_frame()

    intents = plugin.generate_candidates(
        _context({"BTC/USDT": frame, "ETH/USDT": frame.copy(), "SOL/USDT": frame.copy()})
    )

    assert [intent.symbol for intent in intents] == ["BTC/USDT", "ETH/USDT"]


def test_donchian_range_fade_4h_range_width_cv_013_short_cooldown_expires():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortStrategy(
        params={"symbol": "BTC/USDT", "cooldown_bars": 3, "emit_once": False}
    )
    base = _stable_upper_range_frame(size=40)
    within = _stable_upper_range_frame(size=42)
    expired = _stable_upper_range_frame(size=43)

    first = plugin.generate_candidates(_context({"BTC/USDT": base}))
    blocked = plugin.generate_candidates(_context({"BTC/USDT": within}))
    second = plugin.generate_candidates(_context({"BTC/USDT": expired}))

    assert len(first) == 1
    assert blocked == []
    assert len(second) == 1


def test_donchian_range_fade_4h_range_width_cv_013_short_exits_at_mid_target():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortStrategy(params={"symbol": "BTC/USDT"})
    frame = _stable_upper_range_frame(latest_close=99.5, latest_rsi=45.0)

    decision = plugin.update_position(_context({"BTC/USDT": frame}), _position())

    assert decision.action == Action.CLOSE
    assert decision.reason == "DONCHIAN_MID_TARGET"
    assert decision.metadata["target_price"] == pytest.approx(100.0)
