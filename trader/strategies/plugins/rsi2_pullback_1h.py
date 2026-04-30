"""RSI(2) pullback long-only research cartridge on 1h."""

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


class Rsi2Pullback1hStrategy(StrategyPlugin):
    id = "rsi2_pullback_1h"
    version = "0.1.0"
    tags = {
        "external_candidate",
        "rsi2",
        "connors_style",
        "sma_trend",
        "1h",
        "long_only",
        "pullback",
        "high_freq",
    }
    target_regime = "ANY"
    required_timeframes = {"1h": 400, "4h": 250}
    required_indicators = {"rsi", "sma", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "htf_timeframe": "str",
        "rsi_period": "int",
        "rsi_entry": "float",
        "rsi_exit": "float",
        "sma_trend_len": "int",
        "sma_exit_len": "int",
        "htf_sma_trend_len": "int",
        "stop_atr_mult": "float",
        "max_hold_bars": "int",
        "cooldown_bars": "int",
        "emit_once": "bool",
        "min_sma5_gap_atr": "float",
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
        rsi_period = int(self.params.get("rsi_period", 2))
        rsi_entry = float(self.params.get("rsi_entry", 10.0))
        sma_trend_len = int(self.params.get("sma_trend_len", 200))
        sma_exit_len = int(self.params.get("sma_exit_len", 5))
        htf_sma_trend_len = int(self.params.get("htf_sma_trend_len", 200))
        stop_atr_mult = float(self.params.get("stop_atr_mult", 2.0))
        cooldown_bars = int(self.params.get("cooldown_bars", 4))
        emit_once = bool(self.params.get("emit_once", True))
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            frame = self._with_entry_indicators(
                context.snapshot.get(symbol, timeframe),
                rsi_period=rsi_period,
                sma_trend_len=sma_trend_len,
                sma_exit_len=sma_exit_len,
            )
            htf_frame = self._with_htf_indicators(
                context.snapshot.get(symbol, htf_timeframe),
                htf_sma_trend_len=htf_sma_trend_len,
            )
            if not self._has_entry_columns(frame, sma_trend_len):
                continue
            if not self._has_htf_columns(htf_frame, htf_sma_trend_len):
                continue

            latest = frame.iloc[-1]
            htf_latest = htf_frame.iloc[-1]
            trend_col = self._sma_col(sma_trend_len)
            htf_trend_col = self._sma_col(htf_sma_trend_len)
            if float(latest["rsi_2"]) >= rsi_entry:
                continue
            if float(latest["close"]) <= float(latest[trend_col]):
                continue
            if float(htf_latest["close"]) <= float(htf_latest[htf_trend_col]):
                continue

            atr = float(latest["atr"])
            if atr <= 0:
                continue
            sma5_gap_atr = (float(latest[self._sma_col(sma_exit_len)]) - float(latest["close"])) / atr
            min_sma5_gap_atr = self.params.get("min_sma5_gap_atr")
            if min_sma5_gap_atr is not None and sma5_gap_atr < float(min_sma5_gap_atr):
                continue
            if self._is_cooling_down(frame, symbol, timeframe, cooldown_bars):
                continue

            candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
            entry_price = context.snapshot.latest_close(symbol, timeframe)
            if candle_ts is None or entry_price is None or entry_price <= 0:
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
                    entry_type="rsi2_pullback_deep_oversold",
                    stop_hint=StopHint(
                        price=stop_price,
                        reason="rsi2_pullback_atr_stop",
                        metadata={
                            "atr_1h": atr,
                            "atr_mult": stop_atr_mult,
                            "rsi_2": float(latest["rsi_2"]),
                            "sma_200_1h": float(latest[trend_col]),
                            "sma_200_4h": float(htf_latest[htf_trend_col]),
                        },
                    ),
                    confidence=None,
                    metadata={
                        "rsi_2": float(latest["rsi_2"]),
                        "sma_200_1h": float(latest[trend_col]),
                        "sma_200_4h": float(htf_latest[htf_trend_col]),
                        "sma_5_1h": float(latest[self._sma_col(sma_exit_len)]),
                        "atr_1h": atr,
                        "close": float(latest["close"]),
                        "close_4h": float(htf_latest["close"]),
                        "sma5_gap_atr": float(sma5_gap_atr),
                        "min_sma5_gap_atr": (
                            None
                            if min_sma5_gap_atr is None
                            else float(min_sma5_gap_atr)
                        ),
                        "htf_timeframe": htf_timeframe,
                        "rsi_period": rsi_period,
                        "max_hold_bars": int(self.params.get("max_hold_bars", 10)),
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
        rsi_period = int(self.params.get("rsi_period", 2))
        rsi_exit = float(self.params.get("rsi_exit", 70.0))
        sma_trend_len = int(self.params.get("sma_trend_len", 200))
        sma_exit_len = int(self.params.get("sma_exit_len", 5))
        htf_sma_trend_len = int(self.params.get("htf_sma_trend_len", 200))
        max_hold_bars = int(self.params.get("max_hold_bars", 10))

        frame = self._with_entry_indicators(
            context.snapshot.get(symbol, timeframe),
            rsi_period=rsi_period,
            sma_trend_len=sma_trend_len,
            sma_exit_len=sma_exit_len,
        )
        if not self._has_exit_columns(frame, sma_exit_len):
            return PositionDecision()

        htf_frame = self._with_htf_indicators(
            context.snapshot.get(symbol, htf_timeframe),
            htf_sma_trend_len=htf_sma_trend_len,
        )
        latest = frame.iloc[-1]
        htf_ok = self._has_htf_columns(htf_frame, htf_sma_trend_len)
        htf_latest = htf_frame.iloc[-1] if htf_ok else None
        bars_in_position = self._bars_in_position(
            context.snapshot.latest_timestamp(symbol, timeframe),
            position,
            timeframe,
        )

        metadata = {
            "rsi_2": float(latest["rsi_2"]),
            "sma_5_1h": float(latest[self._sma_col(sma_exit_len)]),
            "close": float(latest["close"]),
            "htf_timeframe": htf_timeframe,
            "bars_in_position": bars_in_position,
            "max_hold_bars": max_hold_bars,
        }
        if htf_latest is not None:
            metadata.update(
                {
                    "close_4h": float(htf_latest["close"]),
                    "sma_200_4h": float(htf_latest[self._sma_col(htf_sma_trend_len)]),
                }
            )

        if float(latest["rsi_2"]) > rsi_exit:
            return PositionDecision(
                action=Action.CLOSE,
                reason="RSI2_EXIT_TARGET",
                metadata=metadata,
            )
        if float(latest["close"]) > float(latest[self._sma_col(sma_exit_len)]):
            return PositionDecision(
                action=Action.CLOSE,
                reason="SMA5_BOUNCE_EXIT",
                metadata=metadata,
            )
        if bars_in_position is not None and bars_in_position >= max_hold_bars:
            return PositionDecision(
                action=Action.CLOSE,
                reason="TIME_STOP",
                metadata=metadata,
            )
        if htf_latest is not None and float(htf_latest["close"]) < float(
            htf_latest[self._sma_col(htf_sma_trend_len)]
        ):
            return PositionDecision(
                action=Action.CLOSE,
                reason="HTF_TREND_FLIP",
                metadata=metadata,
            )
        return PositionDecision()

    def _required_timeframes_from_params(self) -> dict[str, int]:
        timeframe = self._timeframe()
        htf_timeframe = self._htf_timeframe()
        entry_warmup = max(
            400,
            int(self.params.get("sma_trend_len", 200)) + int(self.params.get("sma_exit_len", 5)),
        )
        htf_warmup = max(250, int(self.params.get("htf_sma_trend_len", 200)) + 50)
        requirements = {timeframe: entry_warmup}
        requirements[htf_timeframe] = max(requirements.get(htf_timeframe, 0), htf_warmup)
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

    @classmethod
    def _with_entry_indicators(
        cls,
        frame: pd.DataFrame,
        *,
        rsi_period: int,
        sma_trend_len: int,
        sma_exit_len: int,
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        enriched = frame.copy()
        enriched["rsi_2"] = cls._rsi(enriched["close"], rsi_period)
        for length in {sma_trend_len, sma_exit_len}:
            enriched[cls._sma_col(length)] = enriched["close"].rolling(length).mean()
        return enriched

    @classmethod
    def _with_htf_indicators(
        cls,
        frame: pd.DataFrame,
        *,
        htf_sma_trend_len: int,
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        enriched = frame.copy()
        col = cls._sma_col(htf_sma_trend_len)
        if col not in enriched.columns:
            enriched[col] = enriched["close"].rolling(htf_sma_trend_len).mean()
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

    @classmethod
    def _has_entry_columns(cls, frame: pd.DataFrame, sma_trend_len: int) -> bool:
        required = {"close", "atr", "rsi_2", cls._sma_col(sma_trend_len)}
        return (
            frame is not None
            and len(frame) >= sma_trend_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1].notna().all()
        )

    @classmethod
    def _has_exit_columns(cls, frame: pd.DataFrame, sma_exit_len: int) -> bool:
        required = {"close", "rsi_2", cls._sma_col(sma_exit_len)}
        return (
            frame is not None
            and len(frame) >= sma_exit_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1].notna().all()
        )

    @classmethod
    def _has_htf_columns(cls, frame: pd.DataFrame, htf_sma_trend_len: int) -> bool:
        required = {"close", cls._sma_col(htf_sma_trend_len)}
        return (
            frame is not None
            and len(frame) >= htf_sma_trend_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1].notna().all()
        )

    @staticmethod
    def _bars_in_position(latest_candle_ts, position, timeframe: str) -> int | None:
        entry_time = getattr(position, "entry_time", None)
        if entry_time is None:
            metadata = dict(getattr(position, "metadata", {}) or {})
            entry_time = metadata.get("candle_ts")
        if latest_candle_ts is None or entry_time is None:
            return None

        latest_ts = pd.Timestamp(latest_candle_ts)
        entry_ts = pd.Timestamp(entry_time)
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.tz_localize("UTC")
        else:
            latest_ts = latest_ts.tz_convert("UTC")
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.tz_localize("UTC")
        else:
            entry_ts = entry_ts.tz_convert("UTC")
        timeframe_seconds = Rsi2Pullback1hStrategy._timeframe_seconds(timeframe)
        elapsed_seconds = max((latest_ts - entry_ts).total_seconds(), 0.0)
        return int(elapsed_seconds // timeframe_seconds) if timeframe_seconds > 0 else 0

    @staticmethod
    def _timeframe_seconds(timeframe: str) -> int:
        timeframe = str(timeframe).strip().lower()
        if timeframe.endswith("m"):
            return int(timeframe[:-1]) * 60
        if timeframe.endswith("h"):
            return int(timeframe[:-1]) * 3600
        if timeframe.endswith("d"):
            return int(timeframe[:-1]) * 86400
        raise ValueError(f"unsupported timeframe for rsi2 pullback: {timeframe}")

    @staticmethod
    def _sma_col(length: int) -> str:
        return f"sma_{int(length)}"

    @staticmethod
    def _rsi(close: pd.Series, length: int) -> pd.Series:
        delta = close.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.ewm(alpha=1 / length, adjust=False).mean()
        avg_loss = losses.ewm(alpha=1 / length, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0.0, pd.NA)
        out = 100 - (100 / (1 + rs))
        out = out.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
        out = out.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
        out = out.mask((avg_gain == 0) & (avg_loss == 0), 50.0)
        return out
