"""Research-only Slot B Donchian SHORT symbol-universe expansion candidate."""

from __future__ import annotations

from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion import (
    EXPANSION_SYMBOLS,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short import (
    DonchianRangeFade4hRangeWidthCv013ShortStrategy,
)


class DonchianRangeFade4hRangeWidthCv013ShortSymbolUniverseExpansionStrategy(
    DonchianRangeFade4hRangeWidthCv013ShortStrategy
):
    id = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion"
    version = "0.1.0"
    tags = DonchianRangeFade4hRangeWidthCv013ShortStrategy.tags | {
        "active_research",
        "slot_b",
        "symbol_universe_expansion",
        "research_only",
    }
    allowed_symbols = EXPANSION_SYMBOLS
