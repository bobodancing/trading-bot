"""Partial67 cartridge with a 1d trend-spread decay filter."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "transition_bleed",
        "trend_decay_filter",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "trend_spread_slope_bars": "int",
        "trend_spread_slope_min": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        if symbol not in context.symbols:
            return []

        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        metrics = self._trend_decay_metrics(
            trend_frame,
            bars=int(self.params.get("trend_spread_slope_bars", 3)),
        )
        if metrics is None:
            return []

        slope_min = float(self.params.get("trend_spread_slope_min", 0.0))
        if metrics["trend_spread_delta"] < slope_min:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_transition_decay_filtered",
                metadata={
                    **intent.metadata,
                    "trend_spread_slope_bars": metrics["trend_spread_slope_bars"],
                    "trend_spread_delta": metrics["trend_spread_delta"],
                    "trend_spread_slope_min": slope_min,
                    "trend_current_spread": metrics["trend_current_spread"],
                    "trend_prior_spread": metrics["trend_prior_spread"],
                },
            )
            for intent in intents
        ]

    @classmethod
    def _trend_decay_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        bars: int,
    ) -> dict[str, float | int] | None:
        required = {"ema_20", "ema_50"}
        bars = max(int(bars), 1)
        min_len = max(cls.trend_min_bars, bars + 1)
        if frame is None or len(frame) < min_len:
            return None
        if not required.issubset(frame.columns):
            return None

        window = frame.iloc[-(bars + 1) :]
        ema_20 = pd.to_numeric(window["ema_20"], errors="coerce")
        ema_50 = pd.to_numeric(window["ema_50"], errors="coerce")
        if ema_20.isna().any() or ema_50.isna().any() or (ema_50 <= 0).any():
            return None

        spreads = (ema_20 - ema_50) / ema_50
        current_spread = float(spreads.iloc[-1])
        prior_spread = float(spreads.iloc[0])
        return {
            "trend_spread_slope_bars": bars,
            "trend_current_spread": current_spread,
            "trend_prior_spread": prior_spread,
            "trend_spread_delta": current_spread - prior_spread,
        }
