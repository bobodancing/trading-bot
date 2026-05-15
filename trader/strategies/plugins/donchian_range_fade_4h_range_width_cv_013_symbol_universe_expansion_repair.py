"""Research-only Slot B Donchian LONG symbol-universe repair candidate."""

from __future__ import annotations

from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion import (
    DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy,
)


REPAIR_LONG_SYMBOLS = {
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "LINK/USDT",
}


class DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionRepairStrategy(
    DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy
):
    id = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion_repair"
    version = "0.1.0"
    tags = DonchianRangeFade4hRangeWidthCv013SymbolUniverseExpansionStrategy.tags | {
        "symbol_universe_expansion_repair",
        "drop_ada_long",
    }
    allowed_symbols = REPAIR_LONG_SYMBOLS
