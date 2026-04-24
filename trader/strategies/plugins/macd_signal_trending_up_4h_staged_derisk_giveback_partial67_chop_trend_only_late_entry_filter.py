"""Partial67 weak-tape attribution probe using only chop-trend activation."""

from __future__ import annotations

from dataclasses import replace

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_chop_trend_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy,
)
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendOnlyLateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "chop_trend_only_late_entry_filter"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "weak_tape_defense",
        "chop_trend_only",
        "late_entry_filter",
    }
    required_indicators = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.required_indicators
        | {"adx", "bbw"}
    )
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
        "entry_bbw_ratio_min": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        if not MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy._has_late_entry_columns(  # noqa: SLF001
            entry_frame
        ):
            return []

        chop_metrics = (
            MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy._entry_chop_metrics(  # noqa: SLF001
                entry_frame
            )
        )
        if chop_metrics is None:
            return []

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        atr = float(latest_entry["atr"])
        if atr <= 0.0:
            return []

        extension_atr = max((current_close - current_ema_20) / atr, 0.0)
        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        entry_bbw_ratio_min = float(self.params.get("entry_bbw_ratio_min", 0.75))
        chop_trend_active = (
            chop_metrics["adx_slope_5"] < 0.0
            and chop_metrics["bbw_ratio"] < entry_bbw_ratio_min
        )
        if chop_trend_active and extension_atr > extension_cap:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_chop_trend_only_late_entry_filtered",
                metadata={
                    **intent.metadata,
                    "entry_ema_20": current_ema_20,
                    "entry_extension_atr": extension_atr,
                    "entry_ema_extension_atr_max": extension_cap,
                    "weak_tape_gate_mode": "chop_trend_only",
                    "weak_tape_context_active": chop_trend_active,
                    "weak_tape_context_reason": "chop_trend" if chop_trend_active else "none",
                    "weak_tape_trend_decay_active": False,
                    "weak_tape_chop_trend_active": chop_trend_active,
                    "weak_tape_entry_adx": float(chop_metrics["adx"]),
                    "weak_tape_entry_adx_slope_5": float(chop_metrics["adx_slope_5"]),
                    "weak_tape_entry_bbw": float(chop_metrics["bbw"]),
                    "weak_tape_entry_bbw_ratio": float(chop_metrics["bbw_ratio"]),
                    "weak_tape_entry_bbw_ratio_min": entry_bbw_ratio_min,
                },
            )
            for intent in intents
        ]
