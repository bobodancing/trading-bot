"""Partial67 cartridge with a narrow local ADX chop filter."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "chop_filter",
        "no_trade_discipline",
    }
    required_indicators = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.required_indicators
        | {"adx"}
    )
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_adx_min": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        if not self._has_chop_columns(entry_frame):
            return []

        latest_entry = entry_frame.iloc[-1]
        current_adx = float(latest_entry["adx"])
        adx_min = float(self.params.get("entry_adx_min", 22.0))
        if current_adx < adx_min:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_chop_filtered",
                metadata={
                    **intent.metadata,
                    "entry_adx": current_adx,
                    "entry_adx_min": adx_min,
                },
            )
            for intent in intents
        ]

    @staticmethod
    def _has_chop_columns(frame: pd.DataFrame) -> bool:
        required = {"adx"}
        return (
            frame is not None
            and len(frame)
            >= MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopFilterStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )
