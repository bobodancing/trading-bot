"""Locked staged de-risk cartridge with a larger first partial."""

from __future__ import annotations

from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback import (
    MacdSignalTrendingUp4hStagedDeriskGivebackStrategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackStrategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackStrategy.tags | {
        "locked_candidate",
        "partial67",
    }

    def __init__(self, params=None):
        locked = {"derisk_close_pct": 0.67}
        merged = {**locked, **dict(params or {})}
        super().__init__(params=merged)
