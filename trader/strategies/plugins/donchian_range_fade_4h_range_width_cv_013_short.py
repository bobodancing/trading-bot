"""Promoted Slot B upper-bound SHORT overlay for 4h Donchian range fades."""

from __future__ import annotations

import pandas as pd

from trader.strategies.base import (
    Action,
    PositionDecision,
    SignalIntent,
    StopHint,
    StrategyContext,
)
from trader.strategies.plugins.donchian_range_fade_4h import DonchianRangeFade4hStrategy


class DonchianRangeFade4hRangeWidthCv013ShortStrategy(DonchianRangeFade4hStrategy):
    id = "donchian_range_fade_4h_range_width_cv_013_short"
    version = "0.1.0"
    tags = (
        DonchianRangeFade4hStrategy.tags
        - {"long_only"}
        | {
            "research_candidate",
            "slot_b",
            "short_only",
            "mirror_short",
            "range_width_cv_013",
            "upper_bound_fade",
        }
    )

    def __init__(self, params=None):
        merged = {"range_width_cv_max": 0.13, "rsi_entry": 60.0}
        if params:
            merged.update(dict(params))
        super().__init__(merged)

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        timeframe = self._timeframe()
        donchian_len = int(self.params.get("donchian_len", 20))
        range_window = int(self.params.get("range_window", 15))
        range_width_cv_max = float(self.params.get("range_width_cv_max", 0.13))
        touch_atr_band = float(self.params.get("touch_atr_band", 0.25))
        min_lower_touches = int(self.params.get("min_lower_touches", 1))
        min_upper_touches = int(self.params.get("min_upper_touches", 1))
        rsi_entry = float(self.params.get("rsi_entry", 60.0))
        stop_atr_mult = float(self.params.get("stop_atr_mult", 1.5))
        cooldown_bars = int(self.params.get("cooldown_bars", 3))
        emit_once = bool(self.params.get("emit_once", True))
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            frame = context.snapshot.get(symbol, timeframe)
            enriched = self._with_donchian(frame, donchian_len, range_window)
            if not self._has_entry_columns(enriched, range_window):
                continue

            latest = enriched.iloc[-1]
            range_state = self._range_state(
                enriched,
                range_window=range_window,
                range_width_cv_max=range_width_cv_max,
                touch_atr_band=touch_atr_band,
                min_lower_touches=min_lower_touches,
                min_upper_touches=min_upper_touches,
            )
            if not range_state["range_detected"]:
                continue

            upper_entry_band = float(latest["donchian_high"]) - touch_atr_band * float(latest["atr"])
            if float(latest["close"]) < upper_entry_band:
                continue
            if float(latest["rsi_14"]) <= rsi_entry:
                continue
            if self._is_cooling_down(enriched, symbol, timeframe, cooldown_bars):
                continue

            candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
            entry_price = context.snapshot.latest_close(symbol, timeframe)
            atr = float(latest["atr"])
            if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
                continue

            stop_price = entry_price + stop_atr_mult * atr
            if stop_price <= entry_price:
                continue

            key = f"{symbol}|{timeframe}|{candle_ts.isoformat()}"
            if emit_once and key in self._emitted_keys:
                continue
            self._emitted_keys.add(key)

            intents.append(
                SignalIntent(
                    strategy_id=self.id,
                    symbol=symbol,
                    side="SHORT",
                    timeframe=timeframe,
                    candle_ts=candle_ts,
                    entry_type="donchian_range_upper_fade",
                    stop_hint=StopHint(
                        price=stop_price,
                        reason="donchian_range_fade_atr_stop",
                        metadata={
                            "atr": atr,
                            "atr_mult": stop_atr_mult,
                            "donchian_low": float(latest["donchian_low"]),
                            "donchian_high": float(latest["donchian_high"]),
                            "width_cv": float(latest["width_cv"]),
                        },
                    ),
                    confidence=None,
                    metadata={
                        "donchian_high": float(latest["donchian_high"]),
                        "donchian_low": float(latest["donchian_low"]),
                        "donchian_mid": float(latest["donchian_mid"]),
                        "donchian_width": float(latest["donchian_width"]),
                        "width_cv": float(latest["width_cv"]),
                        "lower_touches": int(range_state["lower_touches"]),
                        "upper_touches": int(range_state["upper_touches"]),
                        "rsi_14": float(latest["rsi_14"]),
                        "atr": atr,
                        "close": float(latest["close"]),
                        "bars_in_range": int(range_state["bars_in_range"]),
                        "range_detected": bool(range_state["range_detected"]),
                        "entry_upper_band": upper_entry_band,
                        "range_width_cv_max": range_width_cv_max,
                        "exit_target": self._exit_target_mode(),
                    },
                    entry_price=entry_price,
                )
            )
            self._last_signal_ts[f"{symbol}|{timeframe}"] = pd.Timestamp(candle_ts)

        return intents

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = str(getattr(position, "symbol", self.params.get("symbol", "")) or "")
        timeframe = self._timeframe()
        donchian_len = int(self.params.get("donchian_len", 20))
        range_window = int(self.params.get("range_window", 15))
        touch_atr_band = float(self.params.get("touch_atr_band", 0.25))
        break_atr_mult = float(self.params.get("break_atr_mult", 0.5))

        frame = context.snapshot.get(symbol, timeframe)
        enriched = self._with_donchian(frame, donchian_len, range_window)
        if not self._has_exit_columns(enriched):
            return PositionDecision()

        latest = enriched.iloc[-1]
        previous = enriched.iloc[-2]
        atr = float(latest["atr"])
        exit_target = self._exit_target_mode()
        target_price = (
            float(latest["donchian_mid"])
            if exit_target == "mid"
            else float(latest["donchian_low"]) + touch_atr_band * atr
        )
        range_break_up = float(latest["donchian_high"]) > float(previous["donchian_high"]) + (
            break_atr_mult * atr
        )
        range_break_down = float(latest["donchian_low"]) < float(previous["donchian_low"]) - (
            break_atr_mult * atr
        )
        metadata = {
            "close": float(latest["close"]),
            "atr": atr,
            "rsi_14": float(latest["rsi_14"]),
            "donchian_high": float(latest["donchian_high"]),
            "donchian_low": float(latest["donchian_low"]),
            "donchian_mid": float(latest["donchian_mid"]),
            "target_price": target_price,
            "exit_target": exit_target,
            "range_break_up": range_break_up,
            "range_break_down": range_break_down,
        }

        if float(latest["close"]) <= target_price:
            return PositionDecision(
                action=Action.CLOSE,
                reason=(
                    "DONCHIAN_MID_TARGET"
                    if exit_target == "mid"
                    else "DONCHIAN_OPPOSITE_TARGET"
                ),
                metadata=metadata,
            )
        if range_break_up:
            return PositionDecision(
                action=Action.CLOSE,
                reason="DONCHIAN_RANGE_BREAK_UP",
                metadata=metadata,
            )
        if range_break_down:
            return PositionDecision(
                action=Action.CLOSE,
                reason="DONCHIAN_RANGE_BREAK_DOWN",
                metadata=metadata,
            )
        return PositionDecision()
