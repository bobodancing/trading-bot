"""BTC-only 4h recovery-band breadth cartridge for Phase 4 frequency research."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trader.strategies.base import (
    Action,
    PositionDecision,
    SignalIntent,
    StopHint,
    StrategyContext,
    StrategyPlugin,
    StrategyRiskProfile,
)


class BtcRecoveryBandTrendBreadth4hStrategy(StrategyPlugin):
    entry_min_bars = 21
    trend_min_bars = 2
    entry_warmup_bars = 200
    trend_warmup_bars = 260
    id = "btc_recovery_band_trend_breadth_4h"
    version = "0.1.0"
    tags = {
        "active_research",
        "btc",
        "4h",
        "long_only",
        "trend",
        "frequency_complement",
        "regime_declared",
    }
    required_timeframes = {"4h": entry_warmup_bars, "1d": trend_warmup_bars}
    required_indicators = {"atr", "ema", "supertrend"}
    params_schema = {
        "symbol": "str",
        "entry_timeframe": "str",
        "trend_timeframe": "str",
        "stop_atr_mult": "float",
        "emit_once": "bool",
        "risk_pct": "float",
        "ema_spread_min": "float",
        "ema_spread_max": "float",
        "distance_atr_max": "float",
        "aroon_period": "int",
        "swing_lookback": "int",
    }
    allowed_symbols = {"BTC/USDT"}
    max_concurrent_positions = 1
    risk_profile = StrategyRiskProfile.fixed_risk_pct()

    def __init__(self, params=None):
        super().__init__(params)
        self._emitted_keys: set[str] = set()
        risk_pct = self.params.get("risk_pct")
        if risk_pct is not None:
            self.risk_profile = StrategyRiskProfile.fixed_risk_pct(float(risk_pct))
        self.required_timeframes = self._required_timeframes_from_params(
            self.params.get("entry_timeframe"),
            self.params.get("trend_timeframe"),
        )

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        intents: list[SignalIntent] = []
        for symbol in self._target_symbols(context.symbols):
            intents.extend(
                self._generate_candidate_for_symbol(
                    context,
                    symbol,
                    entry_timeframe,
                    trend_timeframe,
                )
            )
        return intents

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = getattr(position, "symbol", self.params.get("symbol", "BTC/USDT"))
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        if not self._has_entry_columns(entry_frame) or not self._has_trend_columns(trend_frame):
            return PositionDecision()

        band_allowed, spread, trend_row = self._recovery_band_gate(
            context,
            trend_frame,
            trend_timeframe=trend_timeframe,
        )
        if not band_allowed:
            return PositionDecision(
                action=Action.CLOSE,
                reason="RECOVERY_BAND_EXIT",
                metadata={
                    "ema_spread_1d": spread,
                    "ema_spread_min": float(self.params.get("ema_spread_min", -0.08)),
                    "ema_spread_max": float(self.params.get("ema_spread_max", -0.01)),
                    "trend_ema_20": float(trend_row["ema_20"]) if trend_row is not None else None,
                    "trend_ema_50": float(trend_row["ema_50"]) if trend_row is not None else None,
                },
            )

        latest = entry_frame.iloc[-1]
        previous = entry_frame.iloc[-2]
        previous_direction = float(previous["supertrend_direction"])
        current_direction = float(latest["supertrend_direction"])
        if previous_direction >= 1.0 and current_direction <= -1.0:
            return PositionDecision(
                action=Action.CLOSE,
                reason="SUPERTREND_RECOVERY_FLIP_DOWN",
                metadata={
                    "previous_supertrend_direction": previous_direction,
                    "supertrend_direction": current_direction,
                },
            )
        return PositionDecision()

    def _target_symbols(self, context_symbols: list[str]) -> list[str]:
        configured = self.params.get("symbol")
        symbols = [str(configured)] if configured else list(self.allowed_symbols)
        allowed = set(self.allowed_symbols or set())
        return [
            symbol
            for symbol in dict.fromkeys(symbols)
            if symbol in context_symbols and (not allowed or symbol in allowed)
        ]

    def _generate_candidate_for_symbol(
        self,
        context: StrategyContext,
        symbol: str,
        entry_timeframe: str,
        trend_timeframe: str,
    ) -> list[SignalIntent]:
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        if not self._has_entry_columns(entry_frame) or not self._has_trend_columns(trend_frame):
            return []

        band_allowed, spread, trend_row = self._recovery_band_gate(
            context,
            trend_frame,
            trend_timeframe=trend_timeframe,
        )
        if not band_allowed or trend_row is None:
            return []

        latest = entry_frame.iloc[-1]
        previous = entry_frame.iloc[-2]
        atr = float(latest["atr"])
        entry_price = context.snapshot.latest_close(symbol, entry_timeframe)
        candle_ts = context.snapshot.latest_timestamp(symbol, entry_timeframe)
        if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
            return []

        triggers = self._qualifying_triggers(entry_frame, latest, previous, atr, entry_price)
        if not triggers:
            return []

        key = f"{symbol}|{entry_timeframe}|{candle_ts.isoformat()}"
        if bool(self.params.get("emit_once", True)) and key in self._emitted_keys:
            return []

        stop_atr_mult = float(self.params.get("stop_atr_mult", 1.5))
        stop_price = entry_price - stop_atr_mult * atr
        if stop_price <= 0:
            return []
        self._emitted_keys.add(key)

        primary_mechanism = min(
            triggers,
            key=lambda mechanism: (float(triggers[mechanism]["distance_atr"]), mechanism),
        )
        entry_type = (
            "btc_recovery_band_dual_trigger"
            if len(triggers) > 1
            else f"btc_recovery_band_{primary_mechanism}"
        )
        return [
            SignalIntent(
                strategy_id=self.id,
                symbol=symbol,
                side="LONG",
                timeframe=entry_timeframe,
                candle_ts=candle_ts,
                entry_type=entry_type,
                stop_hint=StopHint(
                    price=stop_price,
                    reason="btc_recovery_band_atr_stop",
                    metadata={"atr": atr, "atr_mult": stop_atr_mult},
                ),
                confidence=None,
                metadata={
                    "candidate_family": "trend_dominant_silent_week_companion",
                    "entry_timeframe": entry_timeframe,
                    "trend_timeframe": trend_timeframe,
                    "ema_spread_1d": spread,
                    "ema_spread_min": float(self.params.get("ema_spread_min", -0.08)),
                    "ema_spread_max": float(self.params.get("ema_spread_max", -0.01)),
                    "trend_ema_20": float(trend_row["ema_20"]),
                    "trend_ema_50": float(trend_row["ema_50"]),
                    "distance_atr_max": float(self.params.get("distance_atr_max", 3.0)),
                    "primary_mechanism": primary_mechanism,
                    "trigger_mechanisms": sorted(triggers),
                    "trigger_details": triggers,
                },
                entry_price=entry_price,
            )
        ]

    def _qualifying_triggers(
        self,
        entry_frame: pd.DataFrame,
        latest: pd.Series,
        previous: pd.Series,
        atr: float,
        entry_price: float,
    ) -> dict[str, dict[str, float]]:
        distance_atr_max = float(self.params.get("distance_atr_max", 3.0))
        triggers: dict[str, dict[str, float]] = {}

        previous_direction = float(previous["supertrend_direction"])
        current_direction = float(latest["supertrend_direction"])
        if previous_direction <= -1.0 and current_direction >= 1.0:
            supertrend = float(latest["supertrend"])
            distance_atr = (entry_price - supertrend) / atr
            if distance_atr <= distance_atr_max:
                triggers["supertrend_flip"] = {
                    "distance_atr": float(distance_atr),
                    "supertrend": supertrend,
                    "previous_supertrend_direction": previous_direction,
                    "supertrend_direction": current_direction,
                }

        aroon_period = int(self.params.get("aroon_period", 14))
        swing_lookback = int(self.params.get("swing_lookback", 20))
        aroon_up, aroon_down = self._aroon(entry_frame, period=aroon_period)
        current_aroon_up = float(aroon_up.iloc[-1])
        current_aroon_down = float(aroon_down.iloc[-1])
        prior_swing_high = float(entry_frame["high"].shift(1).rolling(swing_lookback).max().iloc[-1])
        aroon_trigger = (
            pd.notna(current_aroon_up)
            and pd.notna(current_aroon_down)
            and pd.notna(prior_swing_high)
            and current_aroon_up > 70.0
            and current_aroon_down < 30.0
            and entry_price > prior_swing_high
        )
        if aroon_trigger:
            distance_atr = (entry_price - prior_swing_high) / atr
            if distance_atr <= distance_atr_max:
                triggers["aroon_break_hh"] = {
                    "distance_atr": float(distance_atr),
                    "aroon_up": current_aroon_up,
                    "aroon_down": current_aroon_down,
                    "prior_swing_high": prior_swing_high,
                }
        return triggers

    def _recovery_band_gate(
        self,
        context: StrategyContext,
        trend_frame: pd.DataFrame,
        *,
        trend_timeframe: str,
    ) -> tuple[bool, float | None, pd.Series | None]:
        trend_row = self._completed_trend_row(context, trend_frame, trend_timeframe=trend_timeframe)
        if trend_row is None:
            return False, None, None
        ema_20 = float(trend_row["ema_20"])
        ema_50 = float(trend_row["ema_50"])
        if ema_50 <= 0:
            return False, None, trend_row
        spread = float((ema_20 - ema_50) / ema_50)
        lower = float(self.params.get("ema_spread_min", -0.08))
        upper = float(self.params.get("ema_spread_max", -0.01))
        return lower <= spread <= upper, spread, trend_row

    @staticmethod
    def _completed_trend_row(
        context: StrategyContext,
        frame: pd.DataFrame,
        *,
        trend_timeframe: str,
    ) -> pd.Series | None:
        if frame is None or frame.empty:
            return None
        if trend_timeframe != "1d":
            return frame.iloc[-1]

        latest_ts = pd.Timestamp(frame.index[-1])
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.tz_localize("UTC")
        else:
            latest_ts = latest_ts.tz_convert("UTC")
        now_ts = pd.Timestamp(context.now)
        if now_ts.tzinfo is None:
            now_ts = now_ts.tz_localize("UTC")
        else:
            now_ts = now_ts.tz_convert("UTC")

        if latest_ts + pd.Timedelta(days=1) <= now_ts:
            return frame.iloc[-1]
        if len(frame) >= 2:
            return frame.iloc[-2]
        return None

    @classmethod
    def _required_timeframes_from_params(
        cls,
        entry_timeframe: str | None,
        trend_timeframe: str | None,
    ) -> dict[str, int]:
        requirements = {str(entry_timeframe or "4h"): cls.entry_warmup_bars}
        trend_key = str(trend_timeframe or "1d")
        requirements[trend_key] = max(requirements.get(trend_key, 0), cls.trend_warmup_bars)
        return requirements

    @staticmethod
    def _aroon(frame: pd.DataFrame, *, period: int) -> tuple[pd.Series, pd.Series]:
        highs = frame["high"].tolist()
        lows = frame["low"].tolist()
        index = frame.index
        aroon_up = pd.Series(index=index, dtype="float64")
        aroon_down = pd.Series(index=index, dtype="float64")
        for i in range(period - 1, len(frame)):
            high_window = highs[i - period + 1 : i + 1]
            low_window = lows[i - period + 1 : i + 1]
            high_pos = max(range(period), key=lambda pos: high_window[pos])
            low_pos = min(range(period), key=lambda pos: low_window[pos])
            bars_since_high = period - 1 - high_pos
            bars_since_low = period - 1 - low_pos
            aroon_up.iloc[i] = ((period - bars_since_high) / period) * 100.0
            aroon_down.iloc[i] = ((period - bars_since_low) / period) * 100.0
        return aroon_up, aroon_down

    @staticmethod
    def _has_entry_columns(frame: pd.DataFrame) -> bool:
        required = {"high", "low", "close", "atr", "supertrend", "supertrend_direction"}
        return (
            frame is not None
            and len(frame) >= BtcRecoveryBandTrendBreadth4hStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_trend_columns(frame: pd.DataFrame) -> bool:
        required = {"ema_20", "ema_50"}
        return (
            frame is not None
            and len(frame) >= BtcRecoveryBandTrendBreadth4hStrategy.trend_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )
