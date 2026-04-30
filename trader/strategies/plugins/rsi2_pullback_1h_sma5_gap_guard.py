"""RSI(2) pullback child candidate with a minimum SMA5 bounce gap."""

from __future__ import annotations

from trader.strategies.plugins.rsi2_pullback_1h import Rsi2Pullback1hStrategy


class Rsi2Pullback1hSma5GapGuardStrategy(Rsi2Pullback1hStrategy):
    id = "rsi2_pullback_1h_sma5_gap_guard"
    version = "0.1.0"
    tags = Rsi2Pullback1hStrategy.tags | {
        "sma5_gap_guard",
        "child_candidate",
        "second_pass",
        "churn_reduction",
    }

    def __init__(self, params=None):
        merged = {"min_sma5_gap_atr": 0.75}
        if params:
            merged.update(dict(params))
        super().__init__(merged)
