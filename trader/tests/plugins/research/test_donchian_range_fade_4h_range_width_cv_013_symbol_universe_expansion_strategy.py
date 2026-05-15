import pytest

from trader.strategies import StrategyRegistry
from trader.strategies.plugins._catalog import (
    CATALOG_CLASS_ACTIVE_RESEARCH,
    STRATEGY_CATALOG,
    get_strategy_catalog,
    get_strategy_classification,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short import (
    DonchianRangeFade4hRangeWidthCv013ShortStrategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion import (
    DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion_repair import (
    REPAIR_SHORT_SYMBOLS,
    DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionRepairStrategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion import (
    EXPANSION_SYMBOLS,
    DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion_repair import (
    REPAIR_LONG_SYMBOLS,
    DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionRepairStrategy,
)
from trader.tests.plugins.promoted.test_donchian_range_fade_4h_range_width_cv_013_strategy import (
    _moderately_expanding_range_frame,
)
from trader.tests.plugins.promoted.test_donchian_range_fade_4h_range_width_cv_013_short_strategy import (
    _stable_upper_range_frame,
)
from trader.tests.plugins.research.test_donchian_range_fade_4h_strategy import _context


LONG_ID = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion"
SHORT_ID = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion"
REPAIR_LONG_ID = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion_repair"
REPAIR_SHORT_ID = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion_repair"


def test_symbol_universe_expansion_plugins_are_research_only_catalog_entries():
    assert STRATEGY_CATALOG[LONG_ID]["enabled"] is False
    assert STRATEGY_CATALOG[SHORT_ID]["enabled"] is False
    assert get_strategy_classification(LONG_ID) == CATALOG_CLASS_ACTIVE_RESEARCH
    assert get_strategy_classification(SHORT_ID) == CATALOG_CLASS_ACTIVE_RESEARCH

    registry = StrategyRegistry.from_config(
        get_strategy_catalog([LONG_ID, SHORT_ID]),
        [LONG_ID, SHORT_ID],
    )

    long_plugin = registry.require(LONG_ID)
    short_plugin = registry.require(SHORT_ID)
    assert isinstance(long_plugin, DonchianRangeFade4hRangeWidthCv013Strategy)
    assert isinstance(short_plugin, DonchianRangeFade4hRangeWidthCv013ShortStrategy)
    assert long_plugin.params["range_width_cv_max"] == pytest.approx(0.13)
    assert short_plugin.params["rsi_entry"] == pytest.approx(60.0)


def test_symbol_universe_expansion_scope_excludes_promoted_btc_eth():
    long_plugin = DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy()
    short_plugin = DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy()

    assert long_plugin.allowed_symbols == EXPANSION_SYMBOLS
    assert short_plugin.allowed_symbols == EXPANSION_SYMBOLS
    assert "BTC/USDT" not in EXPANSION_SYMBOLS
    assert "ETH/USDT" not in EXPANSION_SYMBOLS


def test_symbol_universe_expansion_long_only_emits_for_candidate_symbols():
    plugin = DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy()
    frame = _moderately_expanding_range_frame()

    intents = plugin.generate_candidates(
        _context({"BTC/USDT": frame.copy(), "SOL/USDT": frame.copy()})
    )

    assert [intent.symbol for intent in intents] == ["SOL/USDT"]
    assert intents[0].strategy_id == LONG_ID


def test_symbol_universe_expansion_short_only_emits_for_candidate_symbols():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy()
    frame = _stable_upper_range_frame()

    intents = plugin.generate_candidates(
        _context({"ETH/USDT": frame.copy(), "LINK/USDT": frame.copy()})
    )

    assert [intent.symbol for intent in intents] == ["LINK/USDT"]
    assert intents[0].strategy_id == SHORT_ID


def test_symbol_universe_expansion_repair_plugins_are_research_only_catalog_entries():
    assert STRATEGY_CATALOG[REPAIR_LONG_ID]["enabled"] is False
    assert STRATEGY_CATALOG[REPAIR_SHORT_ID]["enabled"] is False
    assert get_strategy_classification(REPAIR_LONG_ID) == CATALOG_CLASS_ACTIVE_RESEARCH
    assert get_strategy_classification(REPAIR_SHORT_ID) == CATALOG_CLASS_ACTIVE_RESEARCH

    registry = StrategyRegistry.from_config(
        get_strategy_catalog([REPAIR_LONG_ID, REPAIR_SHORT_ID]),
        [REPAIR_LONG_ID, REPAIR_SHORT_ID],
    )

    long_plugin = registry.require(REPAIR_LONG_ID)
    short_plugin = registry.require(REPAIR_SHORT_ID)
    assert isinstance(long_plugin, DonchianRangeFade4hRangeWidthCv013Strategy)
    assert isinstance(short_plugin, DonchianRangeFade4hRangeWidthCv013ShortStrategy)
    assert long_plugin.params["range_width_cv_max"] == pytest.approx(0.13)
    assert short_plugin.params["rsi_entry"] == pytest.approx(60.0)


def test_symbol_universe_expansion_repair_scope_is_side_specific():
    long_plugin = DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionRepairStrategy()
    short_plugin = DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionRepairStrategy()

    assert long_plugin.allowed_symbols == REPAIR_LONG_SYMBOLS
    assert short_plugin.allowed_symbols == REPAIR_SHORT_SYMBOLS
    assert "ADA/USDT" not in REPAIR_LONG_SYMBOLS
    assert "LINK/USDT" in REPAIR_LONG_SYMBOLS
    assert "LINK/USDT" not in REPAIR_SHORT_SYMBOLS
    assert "ADA/USDT" in REPAIR_SHORT_SYMBOLS
    assert "BTC/USDT" not in REPAIR_LONG_SYMBOLS | REPAIR_SHORT_SYMBOLS
    assert "ETH/USDT" not in REPAIR_LONG_SYMBOLS | REPAIR_SHORT_SYMBOLS


def test_symbol_universe_expansion_repair_long_drops_ada_only():
    plugin = DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionRepairStrategy()
    frame = _moderately_expanding_range_frame()

    intents = plugin.generate_candidates(
        _context({"ADA/USDT": frame.copy(), "LINK/USDT": frame.copy()})
    )

    assert [intent.symbol for intent in intents] == ["LINK/USDT"]
    assert intents[0].strategy_id == REPAIR_LONG_ID


def test_symbol_universe_expansion_repair_short_drops_link_only():
    plugin = DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionRepairStrategy()
    frame = _stable_upper_range_frame()

    intents = plugin.generate_candidates(
        _context({"LINK/USDT": frame.copy(), "ADA/USDT": frame.copy()})
    )

    assert [intent.symbol for intent in intents] == ["ADA/USDT"]
    assert intents[0].strategy_id == REPAIR_SHORT_ID
