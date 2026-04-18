"""MACD zero-line long-only candidate strategy."""

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


class MacdZeroLineLongStrategy(StrategyPlugin):
    id = "macd_zero_line_btc_1d"
    version = "0.1.0"
    tags = {"external_candidate", "macd", "daily", "long_only", "trend"}
    required_timeframes = {"1d": 260}
    required_indicators = {"macd", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "stop_atr_mult": "float",
        "require_signal_confirmation": "bool",
        "emit_once": "bool",
        "risk_pct": "float",
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
        timeframe = str(self.params.get("timeframe") or "1d")
        if symbol not in context.symbols:
            return []

        frame = context.snapshot.get(symbol, timeframe)
        if not self._has_entry_columns(frame):
            return []

        latest = frame.iloc[-1]
        previous = frame.iloc[-2]
        current_macd = float(latest["macd"])
        previous_macd = float(previous["macd"])
        if not (previous_macd <= 0.0 < current_macd):
            return []

        if bool(self.params.get("require_signal_confirmation", True)):
            if current_macd < float(latest["macd_signal"]):
                return []

        candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
        entry_price = context.snapshot.latest_close(symbol, timeframe)
        atr = float(latest["atr"])
        if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
            return []

        key = f"{symbol}|{timeframe}|{candle_ts.isoformat()}"
        if bool(self.params.get("emit_once", True)) and key in self._emitted_keys:
            return []
        self._emitted_keys.add(key)

        stop_atr_mult = float(self.params.get("stop_atr_mult", 2.0))
        stop_price = entry_price - stop_atr_mult * atr
        if stop_price <= 0:
            return []

        return [
            SignalIntent(
                strategy_id=self.id,
                symbol=symbol,
                side="LONG",
                timeframe=timeframe,
                candle_ts=candle_ts,
                entry_type="macd_zero_line_cross_up",
                stop_hint=StopHint(
                    price=stop_price,
                    reason="macd_zero_line_atr_stop",
                    metadata={"atr": atr, "atr_mult": stop_atr_mult},
                ),
                confidence=None,
                metadata={
                    "macd": current_macd,
                    "macd_signal": float(latest["macd_signal"]),
                    "previous_macd": previous_macd,
                },
                entry_price=entry_price,
            )
        ]

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = getattr(position, "symbol", self.params.get("symbol", "BTC/USDT"))
        timeframe = str(self.params.get("timeframe") or "1d")
        frame = context.snapshot.get(symbol, timeframe)
        if not self._has_exit_columns(frame):
            return PositionDecision()

        latest = frame.iloc[-1]
        previous = frame.iloc[-2]
        current_macd = float(latest["macd"])
        previous_macd = float(previous["macd"])
        if previous_macd >= 0.0 > current_macd:
            return PositionDecision(
                action=Action.CLOSE,
                reason="MACD_ZERO_LINE_CROSS_DOWN",
                metadata={"macd": current_macd, "previous_macd": previous_macd},
            )
        return PositionDecision()

    @staticmethod
    def _has_entry_columns(frame: pd.DataFrame) -> bool:
        required = {"macd", "macd_signal", "atr", "close"}
        return (
            frame is not None
            and len(frame) >= 2
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_exit_columns(frame: pd.DataFrame) -> bool:
        required = {"macd"}
        return (
            frame is not None
            and len(frame) >= 2
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )
