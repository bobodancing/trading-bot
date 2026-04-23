"""Partial67 cartridge with a narrow late-entry stretch cap."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "late_entry_filter",
        "entry_stretch_cap",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        if not self._has_late_entry_columns(entry_frame):
            return []

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        atr = float(latest_entry["atr"])
        extension_atr = max((current_close - current_ema_20) / atr, 0.0)
        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        if extension_atr > extension_cap:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_late_entry_filtered",
                metadata={
                    **intent.metadata,
                    "entry_ema_20": current_ema_20,
                    "entry_extension_atr": extension_atr,
                    "entry_ema_extension_atr_max": extension_cap,
                },
            )
            for intent in intents
        ]

    @staticmethod
    def _has_late_entry_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "ema_20", "atr"}
        return (
            frame is not None
            and len(frame)
            >= MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )
