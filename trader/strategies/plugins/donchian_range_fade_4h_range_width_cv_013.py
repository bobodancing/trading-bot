"""Donchian range-fade child candidate with a relaxed width-CV gate."""

from __future__ import annotations

from trader.strategies.plugins.donchian_range_fade_4h import DonchianRangeFade4hStrategy


class DonchianRangeFade4hRangeWidthCv013Strategy(DonchianRangeFade4hStrategy):
    id = "donchian_range_fade_4h_range_width_cv_013"
    version = "0.1.0"
    tags = DonchianRangeFade4hStrategy.tags | {
        "range_width_cv_013",
        "child_candidate",
        "second_pass",
    }
    allowed_symbols = set()
    supports_dynamic_universe = True
    dynamic_universe_quote = "USDT"
    dynamic_universe_max_symbols = 20

    def __init__(self, params=None):
        merged = {"range_width_cv_max": 0.13}
        if params:
            merged.update(dict(params))
        super().__init__(merged)
