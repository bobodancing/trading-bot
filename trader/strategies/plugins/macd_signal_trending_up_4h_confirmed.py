"""Confirmed 4h MACD continuation cartridge under a 1d trend gate."""

from __future__ import annotations

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


class MacdSignalTrendingUp4hConfirmedStrategy(StrategyPlugin):
    entry_min_bars = 26
    trend_min_bars = 50
    id = "macd_signal_btc_4h_trending_up_confirmed"
    version = "0.1.0"
    tags = {
        "external_candidate",
        "macd",
        "4h",
        "long_only",
        "trend",
        "regime_declared",
        "confirmed_entry",
    }
    required_timeframes = {"4h": 200, "1d": 260}
    required_indicators = {"macd", "atr", "ema"}
    params_schema = {
        "symbol": "str",
        "entry_timeframe": "str",
        "trend_timeframe": "str",
        "stop_atr_mult": "float",
        "emit_once": "bool",
        "risk_pct": "float",
        "trend_spread_min": "float",
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

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or "BTC/USDT")
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        if symbol not in context.symbols:
            return []

        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        if not self._has_entry_columns(entry_frame) or not self._has_trend_columns(trend_frame):
            return []

        latest_entry = entry_frame.iloc[-1]
        previous_entry = entry_frame.iloc[-2]
        current_macd = float(latest_entry["macd"])
        previous_macd = float(previous_entry["macd"])
        current_signal = float(latest_entry["macd_signal"])
        previous_signal = float(previous_entry["macd_signal"])
        if not (previous_macd <= previous_signal and current_macd > current_signal):
            return []

        current_hist = float(latest_entry["macd_hist"])
        previous_hist = float(previous_entry["macd_hist"])
        if current_macd <= 0.0 or current_hist <= 0.0 or current_hist <= abs(previous_hist):
            return []

        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        if current_close <= current_ema_20:
            return []

        trend_spread_min = float(self.params.get("trend_spread_min", 0.005))
        trend_allowed, trend_spread = self._trend_gate(trend_frame, trend_spread_min)
        if not trend_allowed:
            return []

        candle_ts = context.snapshot.latest_timestamp(symbol, entry_timeframe)
        entry_price = context.snapshot.latest_close(symbol, entry_timeframe)
        atr = float(latest_entry["atr"])
        if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
            return []

        key = f"{symbol}|{entry_timeframe}|{candle_ts.isoformat()}"
        if bool(self.params.get("emit_once", True)) and key in self._emitted_keys:
            return []
        self._emitted_keys.add(key)

        stop_atr_mult = float(self.params.get("stop_atr_mult", 1.5))
        stop_price = entry_price - stop_atr_mult * atr
        if stop_price <= 0:
            return []

        latest_trend = trend_frame.iloc[-1]
        return [
            SignalIntent(
                strategy_id=self.id,
                symbol=symbol,
                side="LONG",
                timeframe=entry_timeframe,
                candle_ts=candle_ts,
                entry_type="macd_signal_cross_up_confirmed",
                stop_hint=StopHint(
                    price=stop_price,
                    reason="macd_signal_atr_stop",
                    metadata={"atr": atr, "atr_mult": stop_atr_mult},
                ),
                confidence=None,
                metadata={
                    "macd": current_macd,
                    "macd_signal": current_signal,
                    "macd_hist": current_hist,
                    "previous_macd": previous_macd,
                    "previous_macd_signal": previous_signal,
                    "previous_macd_hist": previous_hist,
                    "entry_timeframe": entry_timeframe,
                    "trend_timeframe": trend_timeframe,
                    "entry_ema_20": current_ema_20,
                    "trend_spread": trend_spread,
                    "trend_spread_min": trend_spread_min,
                    "trend_ema_20": float(latest_trend["ema_20"]),
                    "trend_ema_50": float(latest_trend["ema_50"]),
                },
                entry_price=entry_price,
            )
        ]

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = getattr(position, "symbol", self.params.get("symbol", "BTC/USDT"))
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(self.params.get("trend_timeframe") or "1d")
        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        trend_frame = context.snapshot.get(symbol, trend_timeframe)
        if not self._has_entry_columns(entry_frame) or not self._has_trend_columns(trend_frame):
            return PositionDecision()

        latest_entry = entry_frame.iloc[-1]
        previous_entry = entry_frame.iloc[-2]
        current_macd = float(latest_entry["macd"])
        previous_macd = float(previous_entry["macd"])
        current_signal = float(latest_entry["macd_signal"])
        previous_signal = float(previous_entry["macd_signal"])
        if previous_macd >= previous_signal and current_macd < current_signal:
            return PositionDecision(
                action=Action.CLOSE,
                reason="MACD_SIGNAL_CROSS_DOWN",
                metadata={"macd": current_macd, "macd_signal": current_signal},
            )

        trend_spread_min = float(self.params.get("trend_spread_min", 0.005))
        trend_allowed, trend_spread = self._trend_gate(trend_frame, trend_spread_min)
        if not trend_allowed:
            latest_trend = trend_frame.iloc[-1]
            return PositionDecision(
                action=Action.CLOSE,
                reason="TREND_GATE_LOST",
                metadata={
                    "trend_spread": trend_spread,
                    "trend_spread_min": trend_spread_min,
                    "trend_ema_20": float(latest_trend["ema_20"]),
                    "trend_ema_50": float(latest_trend["ema_50"]),
                },
            )
        return PositionDecision()

    @staticmethod
    def _trend_gate(frame: pd.DataFrame, trend_spread_min: float) -> tuple[bool, float]:
        latest = frame.iloc[-1]
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])
        if ema_50 <= 0:
            return False, 0.0
        trend_spread = (ema_20 - ema_50) / ema_50
        return ema_20 > ema_50 and trend_spread >= trend_spread_min, float(trend_spread)

    @staticmethod
    def _has_entry_columns(frame: pd.DataFrame) -> bool:
        required = {"macd", "macd_signal", "macd_hist", "ema_20", "atr", "close"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingUp4hConfirmedStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_trend_columns(frame: pd.DataFrame) -> bool:
        required = {"ema_20", "ema_50"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingUp4hConfirmedStrategy.trend_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )
