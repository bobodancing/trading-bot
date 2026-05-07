"""Research-only Slot A SHORT probe with a late-breakdown snapback guard."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy,
)


class MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy(
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy
):
    id = (
        "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
        "snapback_guard"
    )
    version = "0.1.0"
    tags = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy.tags
        | {
            "snapback_guard",
            "late_breakdown_guard",
            "failure_attribution_repair_probe",
        }
    )
    params_schema = {
        **MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy.params_schema,
        "snapback_guard_lookback_bars": "int",
        "snapback_downside_move_atr_min": "float",
        "snapback_entry_extension_atr_min": "float",
    }

    def __init__(self, params=None):
        defaults = {
            "snapback_guard_lookback_bars": 12,
            "snapback_downside_move_atr_min": 3.0,
            "snapback_entry_extension_atr_min": 1.25,
        }
        merged = {**defaults, **dict(params or {})}
        super().__init__(merged)

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        extension_trigger = float(
            self.params.get("transition_extension_atr_trigger", 3.0)
        )
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            entry_frame = context.snapshot.get(symbol, entry_timeframe)
            snapback_metrics = self._snapback_guard_metrics(
                entry_frame,
                lookback_bars=int(self.params.get("snapback_guard_lookback_bars", 12)),
                downside_move_atr_min=float(
                    self.params.get("snapback_downside_move_atr_min", 3.0)
                ),
                entry_extension_atr_min=float(
                    self.params.get("snapback_entry_extension_atr_min", 1.25)
                ),
            )
            if snapback_metrics is None:
                continue
            if snapback_metrics["snapback_guard_active"]:
                continue

            transition_metrics = self._transition_aware_metrics(
                entry_frame,
                lookback_bars=int(self.params.get("transition_lookback_bars", 12)),
                hist_ratio_max=float(self.params.get("transition_hist_ratio_max", 0.25)),
                prior_negative_hist_min=float(
                    self.params.get("transition_prior_negative_hist_min", 10.0)
                ),
            )
            if transition_metrics is None:
                continue

            transition_context_active = bool(transition_metrics["weak_tape_context_active"])
            tightened_veto_active = (
                transition_context_active
                and transition_metrics["entry_extension_atr"] > extension_cap
                and transition_metrics["entry_extension_atr"] >= extension_trigger
            )
            if tightened_veto_active:
                continue

            for intent in self._generate_candidate_for_symbol(
                context,
                symbol,
                entry_timeframe,
                trend_timeframe,
            ):
                intents.append(
                    replace(
                        intent,
                        entry_type=(
                            "macd_signal_cross_down_snapback_guard_"
                            "late_entry_filtered"
                        ),
                        metadata={
                            **intent.metadata,
                            "entry_ema_20": transition_metrics["entry_ema_20"],
                            "entry_extension_atr": transition_metrics[
                                "entry_extension_atr"
                            ],
                            "entry_ema_extension_atr_max": extension_cap,
                            "weak_tape_gate_mode": "snapback_guard",
                            "weak_tape_context_active": tightened_veto_active,
                            "weak_tape_context_reason": (
                                "transition_aware_tightened"
                                if tightened_veto_active
                                else "none"
                            ),
                            "weak_tape_transition_context_active": (
                                transition_context_active
                            ),
                            "weak_tape_transition_veto_active": tightened_veto_active,
                            "weak_tape_transition_breakdown_active": transition_metrics[
                                "weak_tape_transition_breakdown_active"
                            ],
                            "weak_tape_transition_hist_exhaustion_active": (
                                transition_metrics[
                                    "weak_tape_transition_hist_exhaustion_active"
                                ]
                            ),
                            "weak_tape_transition_hist_ratio": transition_metrics[
                                "weak_tape_transition_hist_ratio"
                            ],
                            "weak_tape_transition_extension_atr_trigger": (
                                extension_trigger
                            ),
                            **snapback_metrics,
                        },
                    )
                )
        return intents

    @classmethod
    def _snapback_guard_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        lookback_bars: int,
        downside_move_atr_min: float,
        entry_extension_atr_min: float,
    ) -> dict[str, float | bool | str] | None:
        if not cls._has_snapback_columns(frame, lookback_bars):
            return None

        lookback_bars = max(int(lookback_bars), 2)
        window = frame.iloc[-(lookback_bars + 1) :]
        prior = window.iloc[:-1]
        latest = window.iloc[-1]

        current_close = float(latest["close"])
        current_low = float(latest["low"])
        current_ema_20 = float(latest["ema_20"])
        atr = float(latest["atr"])
        if atr <= 0.0:
            return None

        prior_high = pd.to_numeric(prior["high"], errors="coerce")
        prior_low = pd.to_numeric(prior["low"], errors="coerce")
        if prior_high.isna().any() or prior_low.isna().any():
            return None

        prior_high_max = float(prior_high.max())
        prior_low_min = float(prior_low.min())
        downside_move_atr = max((prior_high_max - current_close) / atr, 0.0)
        entry_extension_atr = max((current_ema_20 - current_close) / atr, 0.0)
        breakdown_active = prior_low_min > 0.0 and current_low <= prior_low_min
        snapback_guard_active = (
            breakdown_active
            and downside_move_atr >= float(downside_move_atr_min)
            and entry_extension_atr >= float(entry_extension_atr_min)
        )

        return {
            "snapback_guard_active": snapback_guard_active,
            "snapback_guard_reason": (
                "late_breakdown_snapback" if snapback_guard_active else "none"
            ),
            "snapback_guard_breakdown_active": breakdown_active,
            "snapback_guard_lookback_bars": lookback_bars,
            "snapback_guard_prior_high_max": prior_high_max,
            "snapback_guard_prior_low_min": prior_low_min,
            "snapback_guard_current_low": current_low,
            "snapback_guard_downside_move_atr": downside_move_atr,
            "snapback_guard_downside_move_atr_min": float(downside_move_atr_min),
            "snapback_guard_entry_extension_atr": entry_extension_atr,
            "snapback_guard_entry_extension_atr_min": float(entry_extension_atr_min),
        }

    @classmethod
    def _has_snapback_columns(
        cls,
        frame: pd.DataFrame,
        lookback_bars: int,
    ) -> bool:
        required = {"close", "high", "low", "ema_20", "atr"}
        min_len = max(cls.entry_min_bars, max(int(lookback_bars), 2) + 1)
        return (
            frame is not None
            and len(frame) >= min_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-min_len:].notna().all().all()
        )
