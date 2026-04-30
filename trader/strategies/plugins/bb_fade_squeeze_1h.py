"""Bollinger squeeze fade long-only research cartridge on 1h."""

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


class BbFadeSqueeze1hStrategy(StrategyPlugin):
    id = "bb_fade_squeeze_1h"
    version = "0.1.0"
    tags = {
        "external_candidate",
        "bollinger",
        "rsi",
        "bbw_squeeze",
        "1h",
        "long_only",
        "mean_reversion",
        "ranging",
    }
    target_regime = "RANGING"
    required_timeframes = {"1h": 200, "4h": 120}
    required_indicators = {"bollinger", "rsi", "bbw", "adx", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "htf_timeframe": "str",
        "rsi_entry": "float",
        "rsi_exit": "float",
        "bbw_pctrank_max": "float",
        "bbw_pctrank_window": "int",
        "htf_adx_max": "float",
        "htf_adx_exit": "float",
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
        self.required_timeframes = self._required_timeframes_from_params()
        self._emitted_keys: set[str] = set()
        self._last_signal_ts: dict[str, pd.Timestamp] = {}
        risk_pct = self.params.get("risk_pct")
        if risk_pct is not None:
            self.risk_profile = StrategyRiskProfile.fixed_risk_pct(float(risk_pct))

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        timeframe = self._timeframe()
        htf_timeframe = self._htf_timeframe()
        rsi_entry = float(self.params.get("rsi_entry", 30.0))
        bbw_pctrank_max = float(self.params.get("bbw_pctrank_max", 20.0))
        bbw_pctrank_window = int(self.params.get("bbw_pctrank_window", 100))
        htf_adx_max = float(self.params.get("htf_adx_max", 20.0))
        stop_atr_mult = float(self.params.get("stop_atr_mult", 1.5))
        cooldown_bars = int(self.params.get("cooldown_bars", 5))
        emit_once = bool(self.params.get("emit_once", True))
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            frame = self._with_bbw_pctrank(
                context.snapshot.get(symbol, timeframe),
                bbw_pctrank_window,
            )
            htf_frame = context.snapshot.get(symbol, htf_timeframe)
            if not self._has_entry_columns(frame, bbw_pctrank_window):
                continue
            if not self._has_htf_columns(htf_frame):
                continue

            latest = frame.iloc[-1]
            htf_latest = htf_frame.iloc[-1]
            htf_adx = float(htf_latest["adx"])
            if float(latest["rsi_14"]) >= rsi_entry:
                continue
            if float(latest["close"]) > float(latest["bb_lower"]):
                continue
            if float(latest["bbw_pctrank"]) >= bbw_pctrank_max:
                continue
            if htf_adx >= htf_adx_max:
                continue
            if self._is_cooling_down(frame, symbol, timeframe, cooldown_bars):
                continue

            candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
            entry_price = context.snapshot.latest_close(symbol, timeframe)
            atr = float(latest["atr"])
            if candle_ts is None or entry_price is None or entry_price <= 0 or atr <= 0:
                continue

            stop_price = entry_price - stop_atr_mult * atr
            if stop_price <= 0:
                continue

            key = f"{symbol}|{timeframe}|{candle_ts.isoformat()}"
            if emit_once and key in self._emitted_keys:
                continue
            self._emitted_keys.add(key)

            intents.append(
                SignalIntent(
                    strategy_id=self.id,
                    symbol=symbol,
                    side="LONG",
                    timeframe=timeframe,
                    candle_ts=candle_ts,
                    entry_type="bb_fade_squeeze_lower_fade",
                    stop_hint=StopHint(
                        price=stop_price,
                        reason="bb_fade_squeeze_atr_stop",
                        metadata={
                            "atr_1h": atr,
                            "atr_mult": stop_atr_mult,
                            "bb_lower": float(latest["bb_lower"]),
                            "bbw_pctrank": float(latest["bbw_pctrank"]),
                            "htf_adx": htf_adx,
                        },
                    ),
                    confidence=None,
                    metadata={
                        "rsi_14": float(latest["rsi_14"]),
                        "bb_lower": float(latest["bb_lower"]),
                        "bb_mid": float(latest["bb_mid"]),
                        "bb_upper": float(latest["bb_upper"]),
                        "bbw": float(latest["bbw"]),
                        "bbw_pctrank": float(latest["bbw_pctrank"]),
                        "htf_adx": htf_adx,
                        "atr_1h": atr,
                        "close": float(latest["close"]),
                        "htf_timeframe": htf_timeframe,
                        "bbw_pctrank_window": bbw_pctrank_window,
                        "bbw_pctrank_max": bbw_pctrank_max,
                        "htf_adx_max": htf_adx_max,
                    },
                    entry_price=entry_price,
                )
            )
            self._last_signal_ts[f"{symbol}|{timeframe}"] = pd.Timestamp(candle_ts)

        return intents

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = str(getattr(position, "symbol", self.params.get("symbol", "")) or "")
        timeframe = self._timeframe()
        htf_timeframe = self._htf_timeframe()
        frame = context.snapshot.get(symbol, timeframe)
        htf_frame = context.snapshot.get(symbol, htf_timeframe)
        if not self._has_exit_columns(frame):
            return PositionDecision()
        if not self._has_htf_columns(htf_frame):
            return PositionDecision()

        latest = frame.iloc[-1]
        htf_latest = htf_frame.iloc[-1]
        htf_adx = float(htf_latest["adx"])
        metadata = {
            "rsi_14": float(latest["rsi_14"]),
            "bb_mid": float(latest["bb_mid"]),
            "htf_adx": htf_adx,
            "close": float(latest["close"]),
            "htf_timeframe": htf_timeframe,
        }

        if float(latest["close"]) > float(latest["bb_mid"]):
            return PositionDecision(
                action=Action.CLOSE,
                reason="BB_MID_RECOVERY",
                metadata=metadata,
            )
        if float(latest["rsi_14"]) > float(self.params.get("rsi_exit", 55.0)):
            return PositionDecision(
                action=Action.CLOSE,
                reason="RSI_EXIT_TARGET",
                metadata=metadata,
            )
        if htf_adx > float(self.params.get("htf_adx_exit", 25.0)):
            return PositionDecision(
                action=Action.CLOSE,
                reason="HTF_ADX_TREND_ONSET",
                metadata=metadata,
            )
        return PositionDecision()

    def _required_timeframes_from_params(self) -> dict[str, int]:
        timeframe = self._timeframe()
        htf_timeframe = self._htf_timeframe()
        entry_warmup = max(200, int(self.params.get("bbw_pctrank_window", 100)))
        requirements = {timeframe: entry_warmup}
        requirements[htf_timeframe] = max(requirements.get(htf_timeframe, 0), 120)
        return requirements

    def _target_symbols(self, context_symbols: list[str]) -> list[str]:
        configured = self.params.get("symbol")
        symbols = [str(configured)] if configured else list(context_symbols)
        return [
            symbol
            for symbol in dict.fromkeys(symbols)
            if symbol in self.allowed_symbols and symbol in context_symbols
        ]

    def _timeframe(self) -> str:
        return str(self.params.get("timeframe") or "1h")

    def _htf_timeframe(self) -> str:
        return str(self.params.get("htf_timeframe") or "4h")

    @staticmethod
    def _with_bbw_pctrank(frame: pd.DataFrame, window: int) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        enriched = frame.copy()
        if "bbw" not in enriched.columns:
            return enriched
        enriched["bbw_pctrank"] = enriched["bbw"].rolling(window).rank(pct=True) * 100.0
        return enriched

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
    def _has_entry_columns(frame: pd.DataFrame, bbw_pctrank_window: int) -> bool:
        required = {
            "close",
            "rsi_14",
            "bb_lower",
            "bb_mid",
            "bb_upper",
            "bbw",
            "bbw_pctrank",
            "atr",
        }
        return (
            frame is not None
            and len(frame) >= bbw_pctrank_window
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1].notna().all()
        )

    @staticmethod
    def _has_exit_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "rsi_14", "bb_mid"}
        return (
            frame is not None
            and len(frame) >= 1
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1].notna().all()
        )

    @staticmethod
    def _has_htf_columns(frame: pd.DataFrame) -> bool:
        return (
            frame is not None
            and len(frame) >= 1
            and "adx" in frame.columns
            and pd.notna(frame["adx"].iloc[-1])
        )
