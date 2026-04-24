"""Partial67 weak-tape defense candidate with a context-gated stretch cap."""

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
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_decay_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ContextGatedLateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "context_gated_late_entry_filter"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "weak_tape_defense",
        "context_gated",
        "late_entry_filter",
    }
    required_indicators = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.required_indicators
        | {"adx", "bbw"}
    )
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
        "trend_spread_slope_bars": "int",
        "weak_tape_trend_spread_delta_max": "float",
        "entry_bbw_ratio_min": "float",
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

        metrics = self._weak_tape_context_metrics(entry_frame, trend_frame)
        if metrics is None:
            return []

        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        if metrics["weak_tape_context_active"] and metrics["entry_extension_atr"] > extension_cap:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_context_gated_late_entry_filtered",
                metadata={
                    **intent.metadata,
                    "entry_ema_20": metrics["entry_ema_20"],
                    "entry_extension_atr": metrics["entry_extension_atr"],
                    "entry_ema_extension_atr_max": extension_cap,
                    "weak_tape_context_active": metrics["weak_tape_context_active"],
                    "weak_tape_context_reason": metrics["weak_tape_context_reason"],
                    "weak_tape_trend_decay_active": metrics["weak_tape_trend_decay_active"],
                    "weak_tape_trend_spread_delta": metrics["weak_tape_trend_spread_delta"],
                    "weak_tape_trend_spread_delta_max": metrics[
                        "weak_tape_trend_spread_delta_max"
                    ],
                    "weak_tape_chop_trend_active": metrics["weak_tape_chop_trend_active"],
                    "weak_tape_entry_adx": metrics["weak_tape_entry_adx"],
                    "weak_tape_entry_adx_slope_5": metrics["weak_tape_entry_adx_slope_5"],
                    "weak_tape_entry_bbw": metrics["weak_tape_entry_bbw"],
                    "weak_tape_entry_bbw_ratio": metrics["weak_tape_entry_bbw_ratio"],
                    "weak_tape_entry_bbw_ratio_min": metrics["weak_tape_entry_bbw_ratio_min"],
                },
            )
            for intent in intents
        ]

    def _weak_tape_context_metrics(self, entry_frame, trend_frame) -> dict[str, float | bool | str] | None:
        trend_spread_slope_bars = int(self.params.get("trend_spread_slope_bars", 3))
        trend_spread_delta_max = float(self.params.get("weak_tape_trend_spread_delta_max", 0.0))
        entry_bbw_ratio_min = float(self.params.get("entry_bbw_ratio_min", 0.75))

        trend_metrics = (
            MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionDecayFilterStrategy._trend_decay_metrics(  # noqa: SLF001
                trend_frame,
                bars=trend_spread_slope_bars,
            )
        )
        chop_metrics = (
            MacdSignalTrendingUp4hStagedDeriskGivebackPartial67ChopTrendFilterStrategy._entry_chop_metrics(  # noqa: SLF001
                entry_frame
            )
        )
        if trend_metrics is None or chop_metrics is None:
            return None

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        atr = float(latest_entry["atr"])
        if atr <= 0.0:
            return None

        entry_extension_atr = max((current_close - current_ema_20) / atr, 0.0)
        trend_decay_active = trend_metrics["trend_spread_delta"] <= trend_spread_delta_max
        chop_trend_active = (
            chop_metrics["adx_slope_5"] < 0.0
            and chop_metrics["bbw_ratio"] < entry_bbw_ratio_min
        )
        weak_tape_context_active = trend_decay_active or chop_trend_active

        reasons: list[str] = []
        if trend_decay_active:
            reasons.append("trend_decay")
        if chop_trend_active:
            reasons.append("chop_trend")

        return {
            "entry_ema_20": current_ema_20,
            "entry_extension_atr": entry_extension_atr,
            "weak_tape_context_active": weak_tape_context_active,
            "weak_tape_context_reason": "+".join(reasons) if reasons else "none",
            "weak_tape_trend_decay_active": trend_decay_active,
            "weak_tape_trend_spread_delta": float(trend_metrics["trend_spread_delta"]),
            "weak_tape_trend_spread_delta_max": trend_spread_delta_max,
            "weak_tape_chop_trend_active": chop_trend_active,
            "weak_tape_entry_adx": float(chop_metrics["adx"]),
            "weak_tape_entry_adx_slope_5": float(chop_metrics["adx_slope_5"]),
            "weak_tape_entry_bbw": float(chop_metrics["bbw"]),
            "weak_tape_entry_bbw_ratio": float(chop_metrics["bbw_ratio"]),
            "weak_tape_entry_bbw_ratio_min": entry_bbw_ratio_min,
        }
