"""RSI mean reversion long-only research cartridge on 15m."""

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


class RsiMeanReversionStrategy(StrategyPlugin):
    id = "rsi_mean_reversion_15m"
    version = "0.1.0"
    tags = {"external_candidate", "rsi", "bollinger", "15m", "long_only", "mean_reversion"}
    required_timeframes = {"15m": 200}
    required_indicators = {"rsi", "bollinger", "adx", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "rsi_entry": "float",
        "rsi_exit": "float",
        "adx_max": "float",
        "adx_exit": "float",
        "stop_atr_mult": "float",
        "cooldown_bars": "int",
        "emit_once": "bool",
        "risk_pct": "float",
    }
    allowed_symbols = {"BTC/USDT", "ETH/USDT"}
    max_concurrent_positions = None
    risk_profile = StrategyRiskProfile.fixed_risk_pct()

    def __init__(self, params=None):
        super().__init__(params)
        self._emitted_keys: set[str] = set()
        self._last_signal_ts: dict[str, pd.Timestamp] = {}
        risk_pct = self.params.get("risk_pct")
        if risk_pct is not None:
            self.risk_profile = StrategyRiskProfile.fixed_risk_pct(float(risk_pct))

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        timeframe = str(self.params.get("timeframe") or "15m")
        rsi_entry = float(self.params.get("rsi_entry", 25.0))
        adx_max = float(self.params.get("adx_max", 25.0))
        stop_atr_mult = float(self.params.get("stop_atr_mult", 1.5))
        cooldown_bars = int(self.params.get("cooldown_bars", 5))
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            frame = context.snapshot.get(symbol, timeframe)
            if not self._has_entry_columns(frame):
                continue

            latest = frame.iloc[-1]
            if float(latest["rsi_14"]) >= rsi_entry:
                continue
            if float(latest["close"]) > float(latest["bb_lower"]):
                continue
            if float(latest["adx"]) >= adx_max:
                continue
            if self._is_cooling_down(frame, symbol, timeframe, cooldown_bars):
                continue

            candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
            entry_price = context.snapshot.latest_close(symbol, timeframe)
            atr = float(latest["atr"])
            if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
                continue

            key = f"{symbol}|{timeframe}|{candle_ts.isoformat()}"
            if bool(self.params.get("emit_once", True)) and key in self._emitted_keys:
                continue
            self._emitted_keys.add(key)

            stop_price = entry_price - stop_atr_mult * atr
            if stop_price <= 0:
                continue

            intents.append(
                SignalIntent(
                    strategy_id=self.id,
                    symbol=symbol,
                    side="LONG",
                    timeframe=timeframe,
                    candle_ts=candle_ts,
                    entry_type="rsi_mean_reversion_oversold",
                    stop_hint=StopHint(
                        price=stop_price,
                        reason="rsi_mean_reversion_atr_stop",
                        metadata={
                            "atr": atr,
                            "atr_mult": stop_atr_mult,
                            "rsi_14": float(latest["rsi_14"]),
                            "bb_lower": float(latest["bb_lower"]),
                        },
                    ),
                    confidence=None,
                    metadata={
                        "rsi_14": float(latest["rsi_14"]),
                        "bb_lower": float(latest["bb_lower"]),
                        "bb_mid": float(latest["bb_mid"]),
                        "adx": float(latest["adx"]),
                        "atr": atr,
                        "close": float(latest["close"]),
                    },
                    entry_price=entry_price,
                )
            )
            self._last_signal_ts[f"{symbol}|{timeframe}"] = pd.Timestamp(candle_ts)

        return intents

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = str(getattr(position, "symbol", self.params.get("symbol", "")) or "")
        timeframe = str(self.params.get("timeframe") or "15m")
        frame = context.snapshot.get(symbol, timeframe)
        if not self._has_exit_columns(frame):
            return PositionDecision()

        latest = frame.iloc[-1]
        metadata = {
            "rsi_14": float(latest["rsi_14"]),
            "bb_mid": float(latest["bb_mid"]),
            "adx": float(latest["adx"]),
            "close": float(latest["close"]),
        }

        if float(latest["rsi_14"]) > float(self.params.get("rsi_exit", 60.0)):
            return PositionDecision(
                action=Action.CLOSE,
                reason="RSI_EXIT_TARGET",
                metadata=metadata,
            )
        if float(latest["close"]) > float(latest["bb_mid"]):
            return PositionDecision(
                action=Action.CLOSE,
                reason="BB_MID_RECOVERY",
                metadata=metadata,
            )
        if float(latest["adx"]) >= float(self.params.get("adx_exit", 30.0)):
            return PositionDecision(
                action=Action.CLOSE,
                reason="ADX_TREND_ONSET",
                metadata=metadata,
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

    def _is_cooling_down(
        self,
        frame: pd.DataFrame,
        symbol: str,
        timeframe: str,
        cooldown_bars: int,
    ) -> bool:
        key = f"{symbol}|{timeframe}"
        last_ts = self._last_signal_ts.get(key)
        if last_ts is not None and cooldown_bars > 0:
            try:
                last_idx = frame.index.get_loc(last_ts)
                current_idx = len(frame) - 1
                if isinstance(last_idx, int) and (current_idx - last_idx) < cooldown_bars:
                    return True
            except KeyError:
                pass
        return False

    @staticmethod
    def _has_entry_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "rsi_14", "bb_lower", "adx", "atr"}
        return (
            frame is not None
            and len(frame) >= 2
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_exit_columns(frame: pd.DataFrame) -> bool:
        required = {"rsi_14", "bb_mid", "adx", "close"}
        return (
            frame is not None
            and len(frame) >= 2
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )
