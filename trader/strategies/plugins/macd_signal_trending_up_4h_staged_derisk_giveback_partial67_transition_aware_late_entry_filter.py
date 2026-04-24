"""Partial67 side-branch probe with a transition-aware late-entry veto."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67TransitionAwareLateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "transition_aware_late_entry_filter"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "weak_tape_defense",
        "transition_aware",
        "late_entry_filter",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
        "transition_lookback_bars": "int",
        "transition_hist_ratio_max": "float",
        "transition_prior_positive_hist_min": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        metrics = self._transition_aware_metrics(
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
        if metrics["weak_tape_context_active"] and metrics["entry_extension_atr"] > extension_cap:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type="macd_signal_cross_up_transition_aware_late_entry_filtered",
                metadata={
                    **intent.metadata,
                    "entry_ema_20": metrics["entry_ema_20"],
                    "entry_extension_atr": metrics["entry_extension_atr"],
                    "entry_ema_extension_atr_max": extension_cap,
                    "weak_tape_gate_mode": "transition_aware",
                    "weak_tape_context_active": metrics["weak_tape_context_active"],
                    "weak_tape_context_reason": metrics["weak_tape_context_reason"],
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
                },
            )
            for intent in intents
        ]

    @classmethod
    def _transition_aware_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        lookback_bars: int,
        hist_ratio_max: float,
        prior_positive_hist_min: float,
    ) -> dict[str, float | bool | str | None] | None:
        if not cls._has_transition_columns(frame, lookback_bars):
            return None

        lookback_bars = max(int(lookback_bars), 2)
        window = frame.iloc[-(lookback_bars + 1) :]
        prior = window.iloc[:-1]
        latest = window.iloc[-1]

        current_close = float(latest["close"])
        current_high = float(latest["high"])
        current_ema_20 = float(latest["ema_20"])
        current_hist = float(latest["macd_hist"])
        atr = float(latest["atr"])
        if atr <= 0.0:
            return None

        prior_hist = pd.to_numeric(prior["macd_hist"], errors="coerce")
        prior_high = pd.to_numeric(prior["high"], errors="coerce")
        if prior_hist.isna().any() or prior_high.isna().any():
            return None

        prior_positive_hist_max = float(prior_hist.clip(lower=0.0).max())
        prior_high_max = float(prior_high.max())
        hist_ratio = (
            current_hist / prior_positive_hist_max if prior_positive_hist_max > 0.0 else None
        )

        entry_extension_atr = max((current_close - current_ema_20) / atr, 0.0)
        price_breakout_active = prior_high_max > 0.0 and current_high >= prior_high_max
        hist_exhaustion_active = (
            current_hist > 0.0
            and prior_positive_hist_max >= float(prior_positive_hist_min)
            and hist_ratio is not None
            and hist_ratio <= float(hist_ratio_max)
        )
        weak_tape_context_active = price_breakout_active and hist_exhaustion_active

        return {
            "entry_ema_20": current_ema_20,
            "entry_extension_atr": entry_extension_atr,
            "weak_tape_context_active": weak_tape_context_active,
            "weak_tape_context_reason": (
                "transition_hist_exhaustion" if weak_tape_context_active else "none"
            ),
            "weak_tape_transition_breakout_active": price_breakout_active,
            "weak_tape_transition_hist_exhaustion_active": hist_exhaustion_active,
            "weak_tape_transition_lookback_bars": lookback_bars,
            "weak_tape_transition_current_hist": current_hist,
            "weak_tape_transition_prior_positive_hist_max": prior_positive_hist_max,
            "weak_tape_transition_hist_ratio": hist_ratio,
            "weak_tape_transition_hist_ratio_max": float(hist_ratio_max),
            "weak_tape_transition_prior_positive_hist_min": float(
                prior_positive_hist_min
            ),
            "weak_tape_transition_prior_high_max": prior_high_max,
            "weak_tape_transition_entry_high": current_high,
        }

    @classmethod
    def _has_transition_columns(
        cls,
        frame: pd.DataFrame,
        lookback_bars: int,
    ) -> bool:
        required = {"close", "high", "ema_20", "atr", "macd_hist"}
        min_len = max(cls.entry_min_bars, max(int(lookback_bars), 2) + 1)
        return (
            frame is not None
            and len(frame) >= min_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-min_len:].notna().all().all()
        )
