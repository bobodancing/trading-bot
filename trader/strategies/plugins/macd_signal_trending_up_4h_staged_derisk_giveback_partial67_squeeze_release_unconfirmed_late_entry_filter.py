"""Partial67 weak-tape defense for squeeze-release entries without confirmation."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from trader.strategies.base import SignalIntent, StrategyContext
from trader.strategies.plugins.macd_signal_trending_up_4h_staged_derisk_giveback_partial67 import (
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackPartial67SqueezeReleaseUnconfirmedLateEntryFilterStrategy(
    MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy
):
    id = (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "squeeze_release_unconfirmed_late_entry_filter"
    )
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.tags | {
        "weak_tape_defense",
        "squeeze_release_unconfirmed",
        "late_entry_filter",
    }
    required_indicators = (
        MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.required_indicators
        | {"bbw"}
    )
    params_schema = {
        **MacdSignalTrendingUp4hStagedDeriskGivebackPartial67Strategy.params_schema,
        "entry_ema_extension_atr_max": "float",
        "squeeze_pctrank_window": "int",
        "squeeze_trough_lookback": "int",
        "squeeze_release_current_pctrank_min": "float",
        "squeeze_trough_pctrank_max": "float",
        "weak_breakout_upper_fraction": "float",
    }

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        metrics = self._squeeze_release_unconfirmed_metrics(
            entry_frame,
            pctrank_window=int(self.params.get("squeeze_pctrank_window", 100)),
            trough_lookback=int(self.params.get("squeeze_trough_lookback", 20)),
            current_pctrank_min=float(
                self.params.get("squeeze_release_current_pctrank_min", 60.0)
            ),
            trough_pctrank_max=float(self.params.get("squeeze_trough_pctrank_max", 15.0)),
            weak_breakout_upper_fraction=float(
                self.params.get("weak_breakout_upper_fraction", 0.25)
            ),
        )
        if metrics is None:
            return []

        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        context_active = bool(metrics["weak_tape_squeeze_release_context_active"])
        veto_active = context_active and metrics["entry_extension_atr"] > extension_cap
        if veto_active:
            return []

        intents = super().generate_candidates(context)
        if not intents:
            return []

        return [
            replace(
                intent,
                entry_type=(
                    "macd_signal_cross_up_squeeze_release_unconfirmed_"
                    "late_entry_filtered"
                ),
                metadata={
                    **intent.metadata,
                    "entry_ema_20": metrics["entry_ema_20"],
                    "entry_extension_atr": metrics["entry_extension_atr"],
                    "entry_ema_extension_atr_max": extension_cap,
                    "weak_tape_gate_mode": "squeeze_release_unconfirmed",
                    "weak_tape_context_active": veto_active,
                    "weak_tape_context_reason": (
                        "squeeze_release_unconfirmed" if veto_active else "none"
                    ),
                    "weak_tape_squeeze_release_context_active": context_active,
                    "weak_tape_squeeze_release_veto_active": veto_active,
                    "weak_tape_squeeze_release_active": metrics[
                        "weak_tape_squeeze_release_active"
                    ],
                    "weak_tape_unconfirmed_breakout_active": metrics[
                        "weak_tape_unconfirmed_breakout_active"
                    ],
                    "weak_tape_squeeze_pctrank_window": metrics[
                        "weak_tape_squeeze_pctrank_window"
                    ],
                    "weak_tape_squeeze_trough_lookback": metrics[
                        "weak_tape_squeeze_trough_lookback"
                    ],
                    "weak_tape_squeeze_release_current_pctrank": metrics[
                        "weak_tape_squeeze_release_current_pctrank"
                    ],
                    "weak_tape_squeeze_release_current_pctrank_min": metrics[
                        "weak_tape_squeeze_release_current_pctrank_min"
                    ],
                    "weak_tape_squeeze_trough_pctrank_min": metrics[
                        "weak_tape_squeeze_trough_pctrank_min"
                    ],
                    "weak_tape_squeeze_trough_pctrank_max": metrics[
                        "weak_tape_squeeze_trough_pctrank_max"
                    ],
                    "weak_tape_squeeze_trough_bbw_min": metrics[
                        "weak_tape_squeeze_trough_bbw_min"
                    ],
                    "weak_tape_prev_close": metrics["weak_tape_prev_close"],
                    "weak_tape_prev_high": metrics["weak_tape_prev_high"],
                    "weak_tape_prev_low": metrics["weak_tape_prev_low"],
                    "weak_tape_weak_breakout_upper_fraction": metrics[
                        "weak_tape_weak_breakout_upper_fraction"
                    ],
                },
            )
            for intent in intents
        ]

    @classmethod
    def _squeeze_release_unconfirmed_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        pctrank_window: int,
        trough_lookback: int,
        current_pctrank_min: float,
        trough_pctrank_max: float,
        weak_breakout_upper_fraction: float,
    ) -> dict[str, float | bool | int] | None:
        pctrank_window = max(int(pctrank_window), 2)
        trough_lookback = max(int(trough_lookback), 1)
        weak_breakout_upper_fraction = max(float(weak_breakout_upper_fraction), 0.0)
        if not cls._has_squeeze_release_columns(frame, pctrank_window, trough_lookback):
            return None

        enriched = frame.copy()
        enriched["bbw_pctrank"] = (
            pd.to_numeric(enriched["bbw"], errors="coerce")
            .rolling(pctrank_window)
            .rank(pct=True)
            * 100.0
        )

        latest = enriched.iloc[-1]
        previous = enriched.iloc[-2]
        prior_tail = enriched.iloc[-(trough_lookback + 1) : -1]
        if (
            pd.isna(latest["bbw_pctrank"])
            or prior_tail["bbw_pctrank"].isna().any()
            or prior_tail["bbw"].isna().any()
        ):
            return None

        current_close = float(latest["close"])
        current_ema_20 = float(latest["ema_20"])
        atr = float(latest["atr"])
        if atr <= 0.0:
            return None

        prev_close = float(previous["close"])
        prev_high = float(previous["high"])
        prev_low = float(previous["low"])
        prev_range = prev_high - prev_low
        if prev_range <= 0.0:
            return None

        current_pctrank = float(latest["bbw_pctrank"])
        trough_pctrank_min = float(prior_tail["bbw_pctrank"].min())
        trough_bbw_min = float(prior_tail["bbw"].min())
        squeeze_release_active = (
            current_pctrank >= float(current_pctrank_min)
            and trough_pctrank_min <= float(trough_pctrank_max)
        )
        unconfirmed_breakout_active = (
            prev_close < prev_high - weak_breakout_upper_fraction * prev_range
        )
        context_active = squeeze_release_active and unconfirmed_breakout_active

        return {
            "entry_ema_20": current_ema_20,
            "entry_extension_atr": max((current_close - current_ema_20) / atr, 0.0),
            "weak_tape_squeeze_release_context_active": context_active,
            "weak_tape_squeeze_release_active": squeeze_release_active,
            "weak_tape_unconfirmed_breakout_active": unconfirmed_breakout_active,
            "weak_tape_squeeze_pctrank_window": pctrank_window,
            "weak_tape_squeeze_trough_lookback": trough_lookback,
            "weak_tape_squeeze_release_current_pctrank": current_pctrank,
            "weak_tape_squeeze_release_current_pctrank_min": float(
                current_pctrank_min
            ),
            "weak_tape_squeeze_trough_pctrank_min": trough_pctrank_min,
            "weak_tape_squeeze_trough_pctrank_max": float(trough_pctrank_max),
            "weak_tape_squeeze_trough_bbw_min": trough_bbw_min,
            "weak_tape_prev_close": prev_close,
            "weak_tape_prev_high": prev_high,
            "weak_tape_prev_low": prev_low,
            "weak_tape_weak_breakout_upper_fraction": weak_breakout_upper_fraction,
        }

    @classmethod
    def _has_squeeze_release_columns(
        cls,
        frame: pd.DataFrame,
        pctrank_window: int,
        trough_lookback: int,
    ) -> bool:
        required = {"close", "ema_20", "atr", "bbw", "high", "low"}
        min_len = max(cls.entry_min_bars, int(pctrank_window) + int(trough_lookback))
        return (
            frame is not None
            and len(frame) >= min_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-min_len:].notna().all().all()
        )
