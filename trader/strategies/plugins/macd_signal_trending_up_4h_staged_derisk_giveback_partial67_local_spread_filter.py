"""Partial67 cartridge with a narrow local EMA spread chop filter."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LocalSpreadFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "chop_filter",
        "local_spread_filter",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_local_spread_min": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        if not self._has_local_spread_columns(entry_frame):
            return []

        latest_entry = entry_frame.iloc[-1]
        ema_20 = float(latest_entry["ema_20"])
        ema_50 = float(latest_entry["ema_50"])
        if ema_50 <= 0 or ema_20 <= ema_50:
            return []

        local_spread = (ema_20 - ema_50) / ema_50
        local_spread_min = float(self.params.get("entry_local_spread_min", 0.002))
        if local_spread < local_spread_min:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_local_spread_filtered",
                metadata={
                    **intent.metadata,
                    "entry_ema_20": ema_20,
                    "entry_ema_50": ema_50,
                    "entry_local_spread": local_spread,
                    "entry_local_spread_min": local_spread_min,
                },
            )
            for intent in intents
        ]

    @staticmethod
    def _has_local_spread_columns(frame: pd.DataFrame) -> bool:
        required = {"ema_20", "ema_50"}
        return (
            frame is not None
            and len(frame)
            >= MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LocalSpreadFilterStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )
