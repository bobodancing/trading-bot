"""Research-only Slot B Donchian LONG symbol-universe expansion candidate."""

from __future__ import annotations

from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)


EXPANSION_SYMBOLS = {
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "LINK/USDT",
}


class DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy(
    DonchianRangeFade4hRangeWidthCv013Strategy
):
    id = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion"
    version = "0.1.0"
    tags = DonchianRangeFade4hRangeWidthCv013Strategy.tags | {
        "active_research",
        "slot_b",
        "symbol_universe_expansion",
        "research_only",
    }
    allowed_symbols = EXPANSION_SYMBOLS
