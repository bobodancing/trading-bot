"""Research-only Slot B Donchian SHORT symbol-universe repair candidate."""

from __future__ import annotations

from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion import (
    DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy,
)


REPAIR_SHORT_SYMBOLS = {
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
}


class DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionRepairStrategy(
    DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy
):
    id = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion_repair"
    version = "0.1.0"
    tags = DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy.tags | {
        "symbol_universe_expansion_repair",
        "drop_link_short",
    }
    allowed_symbols = REPAIR_SHORT_SYMBOLS
