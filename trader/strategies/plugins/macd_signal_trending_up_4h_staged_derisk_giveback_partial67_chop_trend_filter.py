"""Partial67 cartridge with a local chop-trend no-trade filter."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "chop_filter",
        "no_trade_discipline",
        "chop_trend_filter",
    }
    required_indicators = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.required_indicators
        | {"adx", "bbw"}
    )
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_bbw_ratio_min": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        metrics = self._entry_chop_metrics(entry_frame)
        if metrics is None:
            return []

        bbw_ratio_min = float(self.params.get("entry_bbw_ratio_min", 0.75))
        is_chop_trend = (
            metrics["adx_slope_5"] < 0.0 and metrics["bbw_ratio"] < bbw_ratio_min
        )
        if is_chop_trend:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_chop_trend_filtered",
                metadata={
                    **intent.metadata,
                    "entry_adx": metrics["adx"],
                    "entry_adx_slope_5": metrics["adx_slope_5"],
                    "entry_bbw": metrics["bbw"],
                    "entry_bbw_ratio": metrics["bbw_ratio"],
                    "entry_bbw_ratio_min": bbw_ratio_min,
                },
            )
            for intent in intents
        ]

    @classmethod
    def _entry_chop_metrics(cls, frame: pd.DataFrame) -> dict[str, float] | None:
        required = {"adx", "bbw"}
        if (
            frame is None
            or len(frame) < max(cls.entry_min_bars, 20)
            or not required.issubset(frame.columns)
        ):
            return None

        adx_series = pd.to_numeric(frame["adx"], errors="coerce").dropna()
        bbw_series = pd.to_numeric(frame["bbw"], errors="coerce").dropna()
        if len(adx_series) < 6 or len(bbw_series) < 20:
            return None

        adx = float(adx_series.iloc[-1])
        bbw = float(bbw_series.iloc[-1])
        history = bbw_series.iloc[-50:] if len(bbw_series) >= 50 else bbw_series
        mean_bbw = float(history.mean())
        if pd.isna(adx) or pd.isna(bbw) or mean_bbw <= 0.0:
            return None

        return {
            "adx": adx,
            "adx_slope_5": float(adx_series.iloc[-1] - adx_series.iloc[-6]),
            "bbw": bbw,
            "bbw_ratio": float(bbw / mean_bbw),
        }
