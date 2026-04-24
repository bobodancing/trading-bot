"""Partial67 transition-aware localization pass with a tighter late-entry veto."""

from __future__ import annotations

from dataclasses import replace

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_aware_late_entry_filter import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareLateEntryFilterStrategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "transition_aware_tightened_late_entry_filter"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "weak_tape_defense",
        "transition_aware_tightened",
        "late_entry_filter",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
        "transition_lookback_bars": "int",
        "transition_hist_ratio_max": "float",
        "transition_prior_positive_hist_min": "float",
        "transition_extension_atr_trigger": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        metrics = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareLateEntryFilterStrategy._transition_aware_metrics(  # noqa: SLF001
            entry_frame,
            lookback_bars=int(self.params.get("transition_lookback_bars", 12)),
            hist_ratio_max=float(self.params.get("transition_hist_ratio_max", 0.25)),
            prior_positive_hist_min=float(
                self.params.get("transition_prior_positive_hist_min", 10.0)
            ),
        )
        if metrics is None:
            return []

        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        extension_trigger = float(
            self.params.get("transition_extension_atr_trigger", 3.0)
        )
        transition_context_active = bool(metrics["weak_tape_context_active"])
        tightened_veto_active = (
            transition_context_active
            and metrics["entry_extension_atr"] > extension_cap
            and metrics["entry_extension_atr"] >= extension_trigger
        )
        if tightened_veto_active:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type=(
                    "macd_signal_cross_up_transition_aware_tightened_"
                    "late_entry_filtered"
                ),
                metadata={
                    **intent.metadata,
                    "entry_ema_20": metrics["entry_ema_20"],
                    "entry_extension_atr": metrics["entry_extension_atr"],
                    "entry_ema_extension_atr_max": extension_cap,
                    "weak_tape_gate_mode": "transition_aware_tightened",
                    "weak_tape_context_active": tightened_veto_active,
                    "weak_tape_context_reason": (
                        "transition_aware_tightened" if tightened_veto_active else "none"
                    ),
                    "weak_tape_transition_context_active": transition_context_active,
                    "weak_tape_transition_veto_active": tightened_veto_active,
                    "weak_tape_transition_breakout_active": metrics[
                        "weak_tape_transition_breakout_active"
                    ],
                    "weak_tape_transition_hist_exhaustion_active": metrics[
                        "weak_tape_transition_hist_exhaustion_active"
                    ],
                    "weak_tape_transition_lookback_bars": metrics[
                        "weak_tape_transition_lookback_bars"
                    ],
                    "weak_tape_transition_current_hist": metrics[
                        "weak_tape_transition_current_hist"
                    ],
                    "weak_tape_transition_prior_positive_hist_max": metrics[
                        "weak_tape_transition_prior_positive_hist_max"
                    ],
                    "weak_tape_transition_hist_ratio": metrics[
                        "weak_tape_transition_hist_ratio"
                    ],
                    "weak_tape_transition_hist_ratio_max": metrics[
                        "weak_tape_transition_hist_ratio_max"
                    ],
                    "weak_tape_transition_prior_positive_hist_min": metrics[
                        "weak_tape_transition_prior_positive_hist_min"
                    ],
                    "weak_tape_transition_prior_high_max": metrics[
                        "weak_tape_transition_prior_high_max"
                    ],
                    "weak_tape_transition_entry_high": metrics[
                        "weak_tape_transition_entry_high"
                    ],
                    "weak_tape_transition_extension_atr_trigger": extension_trigger,
                },
            )
            for intent in intents
        ]
