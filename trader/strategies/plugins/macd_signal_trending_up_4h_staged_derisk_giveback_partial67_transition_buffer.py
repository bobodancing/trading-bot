"""Partial67 cartridge with a 1d trend persistence buffer."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionBufferStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "transition_bleed",
        "trend_persistence_buffer",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "trend_persistence_bars": "int",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        if symbol not in context.symbols:
            return []

        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        metrics = self._trend_persistence_metrics(
            trend_frame,
            trend_spread_min=float(self.params.get("trend_spread_min", 0.005)),
            bars=int(self.params.get("trend_persistence_bars", 3)),
        )
        if metrics is None or not metrics["trend_persistent"]:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_transition_buffered",
                metadata={
                    **intent.metadata,
                    "trend_persistence_bars": metrics["trend_persistence_bars"],
                    "trend_persistence_count": metrics["trend_persistence_count"],
                    "trend_recent_min_spread": metrics["trend_recent_min_spread"],
                },
            )
            for intent in intents
        ]

    @classmethod
    def _trend_persistence_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        trend_spread_min: float,
        bars: int,
    ) -> dict[str, float | int | bool] | None:
        required = {"ema_20", "ema_50"}
        bars = max(int(bars), 1)
        if frame is None or len(frame) < max(cls.trend_min_bars, bars):
            return None
        if not required.issubset(frame.columns):
            return None

        window = frame.iloc[-bars:]
        ema_20 = pd.to_numeric(window["ema_20"], errors="coerce")
        ema_50 = pd.to_numeric(window["ema_50"], errors="coerce")
        if ema_20.isna().any() or ema_50.isna().any() or (ema_50 <= 0).any():
            return None

        spreads = (ema_20 - ema_50) / ema_50
        allowed = (ema_20 > ema_50) & (spreads >= trend_spread_min)
        persistence_count = 0
        for value in reversed(list(allowed)):
            if not bool(value):
                break
            persistence_count += 1

        return {
            "trend_persistent": persistence_count >= bars,
            "trend_persistence_bars": bars,
            "trend_persistence_count": persistence_count,
            "trend_recent_min_spread": float(spreads.min()),
        }
