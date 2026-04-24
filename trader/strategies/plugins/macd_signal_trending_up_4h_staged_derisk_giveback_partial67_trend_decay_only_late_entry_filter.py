"""Partial67 weak-tape attribution probe using only trend-decay activation."""

from __future__ import annotations

from dataclasses import replace

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy,
)
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_decay_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TrendDecayOnlyLateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "trend_decay_only_late_entry_filter"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "weak_tape_defense",
        "trend_decay_only",
        "late_entry_filter",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
        "trend_spread_slope_bars": "int",
        "weak_tape_trend_spread_delta_max": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        if not MacdSignalTrendingUp4hStagedDeriskGivebackPartial67LateEntryFilterStrategy._has_late_entry_columns(  # noqa: SLF001
            entry_frame
        ):
            return []

        trend_spread_slope_bars = int(self.params.get("trend_spread_slope_bars", 3))
        trend_metrics = (
            MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy._trend_decay_metrics(  # noqa: SLF001
                trend_frame,
                bars=trend_spread_slope_bars,
            )
        )
        if trend_metrics is None:
            return []

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        atr = float(latest_entry["atr"])
        if atr <= 0.0:
            return []

        extension_atr = max((current_close - current_ema_20) / atr, 0.0)
        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        trend_spread_delta_max = float(self.params.get("weak_tape_trend_spread_delta_max", 0.0))
        trend_decay_active = trend_metrics["trend_spread_delta"] <= trend_spread_delta_max
        if trend_decay_active and extension_atr > extension_cap:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_trend_decay_only_late_entry_filtered",
                metadata={
                    **intent.metadata,
                    "entry_ema_20": current_ema_20,
                    "entry_extension_atr": extension_atr,
                    "entry_ema_extension_atr_max": extension_cap,
                    "weak_tape_gate_mode": "trend_decay_only",
                    "weak_tape_context_active": trend_decay_active,
                    "weak_tape_context_reason": "trend_decay" if trend_decay_active else "none",
                    "weak_tape_trend_decay_active": trend_decay_active,
                    "weak_tape_trend_spread_delta": float(trend_metrics["trend_spread_delta"]),
                    "weak_tape_trend_spread_delta_max": trend_spread_delta_max,
                    "weak_tape_trend_spread_slope_bars": trend_metrics[
                        "trend_spread_slope_bars"
                    ],
                    "weak_tape_trend_current_spread": float(
                        trend_metrics["trend_current_spread"]
                    ),
                    "weak_tape_trend_prior_spread": float(trend_metrics["trend_prior_spread"]),
                    "weak_tape_chop_trend_active": False,
                },
            )
            for intent in intents
        ]
