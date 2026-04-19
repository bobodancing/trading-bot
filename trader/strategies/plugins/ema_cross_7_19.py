"""EMA 7/19 cross long-only research candidate."""

from __future__ import annotations

import pandas as pd

from trader.indicators.technical import _ema
from trader.strategies.base import (
    Action,
    PositionDecision,
    SignalIntent,
    StopHint,
    StrategyContext,
    StrategyPlugin,
    StrategyRiskProfile,
)


class EmaCross719LongOnlyStrategy(StrategyPlugin):
    id = "ema_cross_7_19_long_only"
    version = "0.1.0"
    tags = {"external_candidate", "ema", "4h", "long_only", "trend"}
    required_timeframes = {"4h": 100}
    required_indicators = {"ema", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "atr_mult": "float",
    }
    allowed_symbols = {"BTC/USDT", "ETH/USDT"}
    # Kernel limits are plugin-wide; this candidate needs the existing
    # per-symbol active_trades slot so BTC and ETH can each hold one position.
    max_concurrent_positions = None
    risk_profile = StrategyRiskProfile.fixed_risk_pct()

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        timeframe = self._timeframe()
        atr_mult = self._atr_mult()
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            frame = context.snapshot.get(symbol, timeframe)
            if not self._has_required_columns(frame):
                continue

            enriched = self._with_emas(frame)
            if not self._is_cross_up(enriched):
                continue

            candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
            entry_price = context.snapshot.latest_close(symbol, timeframe)
            latest = enriched.iloc[-1]
            atr = float(latest["atr"])
            if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
                continue

            stop_price = entry_price - atr_mult * atr
            if stop_price <= 0:
                continue

            intents.append(
                SignalIntent(
                    strategy_id=self.id,
                    symbol=symbol,
                    side="LONG",
                    timeframe=timeframe,
                    candle_ts=candle_ts,
                    entry_type="ema_7_19_cross_up",
                    stop_hint=StopHint(
                        price=stop_price,
                        reason="ema_7_19_atr_stop",
                        metadata={"atr": atr, "atr_mult": atr_mult},
                    ),
                    confidence=None,
                    metadata=self._metadata(enriched),
                    entry_price=entry_price,
                )
            )

        return intents

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = str(getattr(position, "symbol", self.params.get("symbol", "")) or "")
        timeframe = self._timeframe()
        frame = context.snapshot.get(symbol, timeframe)
        if not self._has_close_series(frame):
            return PositionDecision()

        enriched = self._with_emas(frame)
        if self._is_cross_down(enriched):
            return PositionDecision(
                action=Action.CLOSE,
                reason="EMA_7_19_CROSS_DOWN",
                metadata=self._metadata(enriched),
            )
        return PositionDecision()

    def _target_symbols(self, context_symbols: list[str]) -> list[str]:
        configured = self.params.get("symbol")
        symbols = [str(configured)] if configured else list(context_symbols)
        return [
            symbol
            for symbol in dict.fromkeys(symbols)
            if symbol in self.allowed_symbols and symbol in context_symbols
        ]

    def _timeframe(self) -> str:
        return str(self.params.get("timeframe") or "4h")

    def _atr_mult(self) -> float:
        return float(self.params.get("atr_mult", 1.5))

    @staticmethod
    def _with_emas(frame: pd.DataFrame) -> pd.DataFrame:
        enriched = frame.copy()
        enriched["ema_7"] = _ema(enriched["close"], length=7)
        enriched["ema_19"] = _ema(enriched["close"], length=19)
        return enriched

    @staticmethod
    def _is_cross_up(frame: pd.DataFrame) -> bool:
        if len(frame) < 2 or not {"ema_7", "ema_19"}.issubset(frame.columns):
            return False
        previous = frame.iloc[-2]
        latest = frame.iloc[-1]
        if pd.isna(previous["ema_7"]) or pd.isna(previous["ema_19"]):
            return False
        if pd.isna(latest["ema_7"]) or pd.isna(latest["ema_19"]):
            return False
        return float(previous["ema_7"]) <= float(previous["ema_19"]) and float(
            latest["ema_7"]
        ) > float(latest["ema_19"])

    @staticmethod
    def _is_cross_down(frame: pd.DataFrame) -> bool:
        if len(frame) < 2 or not {"ema_7", "ema_19"}.issubset(frame.columns):
            return False
        previous = frame.iloc[-2]
        latest = frame.iloc[-1]
        if pd.isna(previous["ema_7"]) or pd.isna(previous["ema_19"]):
            return False
        if pd.isna(latest["ema_7"]) or pd.isna(latest["ema_19"]):
            return False
        return float(previous["ema_7"]) >= float(previous["ema_19"]) and float(
            latest["ema_7"]
        ) < float(latest["ema_19"])

    @staticmethod
    def _has_required_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "atr"}
        return (
            frame is not None
            and len(frame) >= 2
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_close_series(frame: pd.DataFrame) -> bool:
        return (
            frame is not None
            and len(frame) >= 2
            and "close" in frame.columns
            and frame[["close"]].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _metadata(frame: pd.DataFrame) -> dict[str, float]:
        latest = frame.iloc[-1]
        previous = frame.iloc[-2]
        return {
            "ema_7": float(latest["ema_7"]),
            "ema_19": float(latest["ema_19"]),
            "previous_ema_7": float(previous["ema_7"]),
            "previous_ema_19": float(previous["ema_19"]),
        }
