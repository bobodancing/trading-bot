"""4h MACD continuation cartridge under a 1d trend gate."""

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


class MacdSignalTrendingUp4hStrategy(StrategyPlugin):
    entry_min_bars = 26
    trend_min_bars = 50
    entry_warmup_bars = 200
    trend_warmup_bars = 260
    id = "macd_signal_btc_4h_trending_up"
    version = "0.1.0"
    tags = {"external_candidate", "macd", "4h", "long_only", "trend", "regime_declared"}
    required_timeframes = {"4h": entry_warmup_bars, "1d": trend_warmup_bars}
    required_indicators = {"macd", "atr", "ema"}
    params_schema = {
        "symbol": "str",
        "entry_timeframe": "str",
        "trend_timeframe": "str",
        "stop_atr_mult": "float",
        "require_signal_confirmation": "bool",
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

    def _target_symbols(self, context_symbols: list[str]) -> list[str]:
        configured = self.params.get("symbol")
        if configured:
            symbols = [str(configured)]
        elif getattr(self, "supports_dynamic_universe", False):
            symbols = list(context_symbols)
        else:
            symbols = list(self.allowed_symbols or context_symbols)

        allowed = set(self.allowed_symbols or set())
        dynamic_unbounded = getattr(self, "supports_dynamic_universe", False) and not allowed
        return [
            symbol
            for symbol in dict.fromkeys(symbols)
            if symbol in context_symbols and (dynamic_unbounded or not allowed or symbol in allowed)
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

        latest_entry = entry_frame.iloc[-1]
        previous_entry = entry_frame.iloc[-2]
        current_macd = float(latest_entry["macd"])
        previous_macd = float(previous_entry["macd"])
        current_signal = float(latest_entry["macd_signal"])
        previous_signal = float(previous_entry["macd_signal"])
        if not (previous_macd <= previous_signal and current_macd > current_signal):
            return []

        if bool(self.params.get("require_signal_confirmation", True)) and current_macd <= 0.0:
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
                entry_type="macd_signal_cross_up",
                stop_hint=StopHint(
                    price=stop_price,
                    reason="macd_signal_atr_stop",
                    metadata={"atr": atr, "atr_mult": stop_atr_mult},
                ),
                confidence=None,
                metadata={
                    "macd": current_macd,
                    "macd_signal": current_signal,
                    "previous_macd": previous_macd,
                    "previous_macd_signal": previous_signal,
                    "entry_timeframe": entry_timeframe,
                    "trend_timeframe": trend_timeframe,
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

    @classmethod
    def _required_timeframes_from_params(
        cls,
        entry_timeframe: str | None,
        trend_timeframe: str | None,
    ) -> dict[str, int]:
        requirements = {}
        requirements[str(entry_timeframe or "4h")] = cls.entry_warmup_bars
        trend_key = str(trend_timeframe or "1d")
        requirements[trend_key] = max(
            requirements.get(trend_key, 0),
            cls.trend_warmup_bars,
        )
        return requirements

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
        required = {"macd", "macd_signal", "atr", "close"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingUp4hStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_trend_columns(frame: pd.DataFrame) -> bool:
        required = {"ema_20", "ema_50"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingUp4hStrategy.trend_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )
