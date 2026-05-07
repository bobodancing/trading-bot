"""Research-only Slot A SHORT probe that preserves bearish follow-through."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_snapback_guard import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy,
)


class MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy(
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy
):
    id = (
        "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
        "snapback_followthrough_guard"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy.tags | {
        "followthrough_guard",
        "exhausted_breakdown_guard",
    }
    params_schema = {
        **MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy.params_schema,
        "followthrough_close_through_atr_min": "float",
        "followthrough_close_through_atr_max": "float",
        "followthrough_close_location_max": "float",
        "followthrough_downside_move_atr_max": "float",
        "followthrough_entry_extension_atr_max": "float",
        "followthrough_hist_expansion_min": "float",
        "followthrough_votes_min": "int",
    }

    def __init__(self, params=None):
        defaults = {
            "followthrough_close_through_atr_min": 0.25,
            "followthrough_close_through_atr_max": 1.0,
            "followthrough_close_location_max": 0.35,
            "followthrough_downside_move_atr_max": 3.5,
            "followthrough_entry_extension_atr_max": 2.0,
            "followthrough_hist_expansion_min": 1.0,
            "followthrough_votes_min": 2,
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
            snapback_metrics = self._followthrough_guard_metrics(
                entry_frame,
                lookback_bars=int(self.params.get("snapback_guard_lookback_bars", 12)),
                downside_move_atr_min=float(
                    self.params.get("snapback_downside_move_atr_min", 3.0)
                ),
                entry_extension_atr_min=float(
                    self.params.get("snapback_entry_extension_atr_min", 1.25)
                ),
                close_through_atr_min=float(
                    self.params.get("followthrough_close_through_atr_min", 0.25)
                ),
                close_through_atr_max=float(
                    self.params.get("followthrough_close_through_atr_max", 1.0)
                ),
                close_location_max=float(
                    self.params.get("followthrough_close_location_max", 0.35)
                ),
                downside_move_atr_max=float(
                    self.params.get("followthrough_downside_move_atr_max", 3.5)
                ),
                entry_extension_atr_max=float(
                    self.params.get("followthrough_entry_extension_atr_max", 2.0)
                ),
                hist_expansion_min=float(
                    self.params.get("followthrough_hist_expansion_min", 1.0)
                ),
                votes_min=int(self.params.get("followthrough_votes_min", 2)),
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
                            "macd_signal_cross_down_snapback_followthrough_"
                            "late_entry_filtered"
                        ),
                        metadata={
                            **intent.metadata,
                            "entry_ema_20": transition_metrics["entry_ema_20"],
                            "entry_extension_atr": transition_metrics[
                                "entry_extension_atr"
                            ],
                            "entry_ema_extension_atr_max": extension_cap,
                            "weak_tape_gate_mode": "snapback_followthrough_guard",
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
    def _followthrough_guard_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        lookback_bars: int,
        downside_move_atr_min: float,
        entry_extension_atr_min: float,
        close_through_atr_min: float,
        close_through_atr_max: float,
        close_location_max: float,
        downside_move_atr_max: float,
        entry_extension_atr_max: float,
        hist_expansion_min: float,
        votes_min: int,
    ) -> dict[str, float | bool | str | int] | None:
        if not cls._has_followthrough_columns(frame, lookback_bars):
            return None

        base_metrics = cls._snapback_guard_metrics(
            frame,
            lookback_bars=lookback_bars,
            downside_move_atr_min=downside_move_atr_min,
            entry_extension_atr_min=entry_extension_atr_min,
        )
        if base_metrics is None:
            return None

        lookback_bars = max(int(lookback_bars), 2)
        window = frame.iloc[-(lookback_bars + 1) :]
        prior = window.iloc[:-1]
        latest = window.iloc[-1]
        previous = window.iloc[-2]

        current_close = float(latest["close"])
        current_high = float(latest["high"])
        current_low = float(latest["low"])
        current_hist = float(latest["macd_hist"])
        previous_hist = float(previous["macd_hist"])
        atr = float(latest["atr"])
        prior_low_min = float(pd.to_numeric(prior["low"], errors="coerce").min())
        if atr <= 0.0 or current_high <= current_low:
            return None

        close_through_atr = max((prior_low_min - current_close) / atr, 0.0)
        close_location = (current_close - current_low) / (current_high - current_low)
        close_through_active = close_through_atr >= float(close_through_atr_min)
        close_near_low_active = close_location <= float(close_location_max)
        hist_expansion_active = (
            current_hist < 0.0
            and abs(current_hist) >= abs(previous_hist) * float(hist_expansion_min)
        )
        votes = sum(
            1
            for item in (
                close_through_active,
                close_near_low_active,
                hist_expansion_active,
            )
            if item
        )
        exhaustion_reasons = []
        if close_through_atr > float(close_through_atr_max):
            exhaustion_reasons.append("close_through_overextended")
        if (
            float(base_metrics["snapback_guard_downside_move_atr"])
            > float(downside_move_atr_max)
        ):
            exhaustion_reasons.append("downside_move_overextended")
        if (
            float(base_metrics["snapback_guard_entry_extension_atr"])
            > float(entry_extension_atr_max)
        ):
            exhaustion_reasons.append("entry_extension_overextended")

        exhaustion_active = bool(exhaustion_reasons)
        raw_followthrough_confirmed = votes >= int(votes_min)
        followthrough_confirmed = raw_followthrough_confirmed and not exhaustion_active
        late_breakdown_active = bool(base_metrics["snapback_guard_active"])
        guard_active = late_breakdown_active and not followthrough_confirmed

        return {
            **base_metrics,
            "snapback_guard_active": guard_active,
            "snapback_guard_reason": (
                "exhausted_breakdown_without_followthrough"
                if guard_active
                else "none"
            ),
            "snapback_late_breakdown_active": late_breakdown_active,
            "followthrough_confirmed": followthrough_confirmed,
            "followthrough_raw_confirmed": raw_followthrough_confirmed,
            "followthrough_votes": votes,
            "followthrough_votes_min": int(votes_min),
            "followthrough_exhaustion_active": exhaustion_active,
            "followthrough_exhaustion_reason": (
                ",".join(exhaustion_reasons) if exhaustion_reasons else "none"
            ),
            "followthrough_close_through_active": close_through_active,
            "followthrough_close_through_atr": close_through_atr,
            "followthrough_close_through_atr_min": float(close_through_atr_min),
            "followthrough_close_through_atr_max": float(close_through_atr_max),
            "followthrough_close_near_low_active": close_near_low_active,
            "followthrough_close_location": close_location,
            "followthrough_close_location_max": float(close_location_max),
            "followthrough_downside_move_atr_max": float(downside_move_atr_max),
            "followthrough_entry_extension_atr_max": float(entry_extension_atr_max),
            "followthrough_hist_expansion_active": hist_expansion_active,
            "followthrough_current_hist": current_hist,
            "followthrough_previous_hist": previous_hist,
            "followthrough_hist_expansion_min": float(hist_expansion_min),
        }

    @classmethod
    def _has_followthrough_columns(
        cls,
        frame: pd.DataFrame,
        lookback_bars: int,
    ) -> bool:
        required = {"close", "high", "low", "ema_20", "atr", "macd_hist"}
        min_len = max(cls.entry_min_bars, max(int(lookback_bars), 2) + 1)
        return (
            frame is not None
            and len(frame) >= min_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-min_len:].notna().all().all()
        )
