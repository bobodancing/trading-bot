"""Arbiter-layer regime confidence gate.

This module guards plugin entries before central execution. It does not modify
RegimeEngine thresholds or strategy plugin logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from trader.config import Config


FREEZE_LABELS = {"NEUTRAL", "SQUEEZE", "UNKNOWN"}
TREND_LABELS = {"TRENDING_UP", "TRENDING_DOWN"}


@dataclass(frozen=True)
class RegimeSnapshot:
    label: str
    confidence: float
    direction: Optional[str]
    source_regime: Optional[str]
    detected: Optional[str]
    macro_state: Optional[str]
    entry_allowed: bool
    reason: str
    components: dict[str, float | str | None] = field(default_factory=dict)

    def audit_fields(self) -> dict[str, object]:
        """Flatten stable fields for signal audit logs."""
        return {
            "arbiter_label": self.label,
            "arbiter_confidence": round(self.confidence, 4),
            "arbiter_entry_allowed": self.entry_allowed,
            "arbiter_reason": self.reason,
            "arbiter_macro_state": self.macro_state,
        }


class RegimeArbiter:
    """Stateful scalar-confidence arbiter for entry gating."""

    def __init__(self):
        self.current_label = "UNKNOWN"
        self._pending_label: Optional[str] = None
        self._pending_count = 0

    def evaluate(
        self,
        *,
        context: dict,
        df_4h: Optional[pd.DataFrame] = None,
        daily_df: Optional[pd.DataFrame] = None,
    ) -> RegimeSnapshot:
        macro_state = self._macro_state(daily_df)
        candidate_label, candidate_direction = self._candidate_label(context)
        components = self._feature_components(df_4h)

        if components.get("squeeze_like") == 1.0:
            candidate_label = "SQUEEZE"
            candidate_direction = None

        self._record_candidate(candidate_label)
        components["persistence_bars"] = float(self._pending_count)

        confidence, reason = self._score_candidate(candidate_label, context, components)
        label = candidate_label
        entry_allowed = label not in FREEZE_LABELS

        threshold = float(getattr(Config, "ARBITER_NEUTRAL_THRESHOLD", 0.0) or 0.0)
        exit_threshold = float(
            getattr(Config, "ARBITER_NEUTRAL_EXIT_THRESHOLD", threshold) or threshold
        )
        min_bars = int(getattr(Config, "ARBITER_NEUTRAL_MIN_BARS", 1) or 1)

        if label == "SQUEEZE":
            entry_allowed = False
            reason = "squeeze_freeze_new_entries"
        elif label == "UNKNOWN":
            entry_allowed = False
            reason = context.get("reason") or "regime_unknown"
        elif threshold > 0.0 and confidence < threshold:
            label = "NEUTRAL"
            entry_allowed = False
            reason = f"low_regime_confidence:{reason}"
        elif self.current_label == "NEUTRAL":
            if confidence < exit_threshold or self._pending_count < min_bars:
                label = "NEUTRAL"
                entry_allowed = False
                reason = "neutral_hysteresis"

        snapshot = RegimeSnapshot(
            label=label,
            confidence=max(0.0, min(1.0, confidence)),
            direction=candidate_direction,
            source_regime=context.get("regime"),
            detected=context.get("detected"),
            macro_state=macro_state,
            entry_allowed=entry_allowed,
            reason=reason,
            components=components,
        )
        self.current_label = snapshot.label
        return snapshot

    def can_enter(self, snapshot: RegimeSnapshot, signal_side: str) -> tuple[bool, str]:
        if not snapshot.entry_allowed:
            return False, snapshot.reason

        if not getattr(Config, "MACRO_OVERLAY_ENABLED", False):
            return True, snapshot.reason

        if snapshot.label not in TREND_LABELS:
            return True, snapshot.reason

        macro_state = snapshot.macro_state or "UNKNOWN"
        if macro_state in {"UNKNOWN", "MACRO_STALLED"}:
            return False, f"macro_overlay_blocked:{macro_state.lower()}"
        if macro_state == "MACRO_BULL" and signal_side == "SHORT":
            return False, "macro_overlay_blocked:bull_blocks_short"
        if macro_state == "MACRO_BEAR" and signal_side == "LONG":
            return False, "macro_overlay_blocked:bear_blocks_long"
        return True, snapshot.reason

    def _record_candidate(self, label: str) -> None:
        if label == self._pending_label:
            self._pending_count += 1
        else:
            self._pending_label = label
            self._pending_count = 1

    @staticmethod
    def _candidate_label(context: dict) -> tuple[str, Optional[str]]:
        regime = context.get("regime")
        direction = context.get("direction")
        if direction not in {"LONG", "SHORT"}:
            direction = None

        if regime == "TRENDING":
            if direction == "LONG":
                return "TRENDING_UP", direction
            if direction == "SHORT":
                return "TRENDING_DOWN", direction
            return "UNKNOWN", None
        if regime == "RANGING":
            return "RANGING", None
        if regime == "SQUEEZE":
            return "SQUEEZE", None
        return "UNKNOWN", None

    @staticmethod
    def _score_candidate(
        label: str,
        context: dict,
        components: dict[str, float | str | None],
    ) -> tuple[float, str]:
        if label in {"UNKNOWN", "SQUEEZE"}:
            return 0.0 if label == "UNKNOWN" else 0.85, context.get("reason") or label.lower()

        if label in TREND_LABELS:
            if components.get("chop_trend") == 1.0:
                return 0.35, "chop_trend_adx_falling"
            adx = components.get("adx")
            adx_slope_5 = components.get("adx_slope_5")
            if isinstance(adx, float) and adx >= Config.REGIME_ADX_TRENDING:
                if isinstance(adx_slope_5, float) and adx_slope_5 >= 0:
                    return 0.85, "clean_trend"
                return 0.65, "trend_adx_flat_or_falling"
            return 0.55, "trend_low_adx"

        if label == "RANGING":
            bbw_pct = components.get("bbw_pct50")
            if isinstance(bbw_pct, float) and bbw_pct < Config.REGIME_BBW_RANGING_PCT:
                return 0.80, "range_compression"
            return 0.65, "regime_ranging"

        return 0.0, "unhandled_label"

    @staticmethod
    def _feature_components(df_4h: Optional[pd.DataFrame]) -> dict[str, float | str | None]:
        empty = {
            "adx": None,
            "adx_slope_5": None,
            "bbw_pct50": None,
            "bbw_ratio": None,
            "atr_pct": None,
            "atr_ratio20": None,
            "squeeze_like": 0.0,
            "chop_trend": 0.0,
        }
        if df_4h is None or df_4h.empty:
            return empty

        adx = _last_float(df_4h.get("adx"))
        bbw = _last_float(df_4h.get("bbw"))
        atr = _last_float(df_4h.get("atr"))
        close = _last_float(df_4h.get("close"))

        adx_slope_5 = None
        adx_series = _numeric_series(df_4h.get("adx"))
        if adx_series is not None and len(adx_series.dropna()) >= 6:
            clean = adx_series.dropna()
            adx_slope_5 = float(clean.iloc[-1] - clean.iloc[-6])

        bbw_pct50 = None
        bbw_ratio = None
        bbw_series = _numeric_series(df_4h.get("bbw"))
        if bbw_series is not None:
            clean = bbw_series.dropna()
            if len(clean) >= 20 and bbw is not None:
                history = clean.iloc[-50:] if len(clean) >= 50 else clean
                mean_bbw = float(history.mean())
                bbw_pct50 = float((history < bbw).sum() / len(history) * 100.0)
                bbw_ratio = float(bbw / mean_bbw) if mean_bbw > 0 else None

        atr_ratio20 = None
        atr_series = _numeric_series(df_4h.get("atr"))
        if atr_series is not None:
            clean = atr_series.dropna()
            if len(clean) >= 20 and atr is not None:
                atr_mean20 = float(clean.iloc[-20:].mean())
                atr_ratio20 = float(atr / atr_mean20) if atr_mean20 > 0 else None

        atr_pct = float(atr / close) if atr is not None and close not in (None, 0.0) else None

        squeeze_like = (
            bbw_pct50 is not None
            and bbw_ratio is not None
            and atr_ratio20 is not None
            and bbw_pct50 < 5.0
            and bbw_ratio < 0.35
            and atr_ratio20 <= 1.1
        )
        chop_trend = (
            adx_slope_5 is not None
            and adx_slope_5 < 0
            and (
                (bbw_ratio is not None and bbw_ratio < 0.75)
                or (bbw_pct50 is not None and bbw_pct50 < 25.0)
            )
        )

        return {
            "adx": adx,
            "adx_slope_5": adx_slope_5,
            "bbw_pct50": bbw_pct50,
            "bbw_ratio": bbw_ratio,
            "atr_pct": atr_pct,
            "atr_ratio20": atr_ratio20,
            "squeeze_like": 1.0 if squeeze_like else 0.0,
            "chop_trend": 1.0 if chop_trend else 0.0,
        }

    @staticmethod
    def _macro_state(daily_df: Optional[pd.DataFrame]) -> str:
        if not getattr(Config, "MACRO_OVERLAY_ENABLED", False):
            return "DISABLED"
        if daily_df is None or daily_df.empty or "close" not in daily_df.columns:
            return "UNKNOWN"

        if not isinstance(daily_df.index, pd.DatetimeIndex):
            if "timestamp" not in daily_df.columns:
                return "UNKNOWN"
            daily_df = daily_df.set_index(pd.to_datetime(daily_df["timestamp"], errors="coerce"))

        close = pd.to_numeric(daily_df["close"], errors="coerce").dropna()
        if close.empty:
            return "UNKNOWN"

        weekly_close = close.resample("W-SUN").last().dropna()
        last_daily_ts = pd.Timestamp(close.index[-1])
        closed_weekly = weekly_close[weekly_close.index < last_daily_ts]
        if len(closed_weekly) < 20:
            return "UNKNOWN"

        ema20 = closed_weekly.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = closed_weekly.ewm(span=50, adjust=False).mean().iloc[-1]
        if ema50 == 0 or pd.isna(ema20) or pd.isna(ema50):
            return "UNKNOWN"

        spread = float((ema20 - ema50) / ema50)
        threshold = float(getattr(Config, "MACRO_WEEKLY_EMA_SPREAD_THRESHOLD", 0.015))
        if abs(spread) <= threshold:
            return "MACRO_STALLED"
        return "MACRO_BULL" if spread > 0 else "MACRO_BEAR"


def _numeric_series(series) -> Optional[pd.Series]:
    if series is None:
        return None
    return pd.to_numeric(series, errors="coerce")


def _last_float(series) -> Optional[float]:
    numeric = _numeric_series(series)
    if numeric is None or numeric.empty:
        return None
    value = numeric.iloc[-1]
    if pd.isna(value):
        return None
    return float(value)
