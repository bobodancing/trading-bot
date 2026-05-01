"""Donchian structural range-fade long-only research cartridge on 4h."""

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


class DonchianRangeFade4hStrategy(StrategyPlugin):
    id = "donchian_range_fade_4h"
    version = "0.1.0"
    tags = {
        "external_candidate",
        "donchian",
        "structural_range",
        "rsi",
        "4h",
        "long_only",
        "mean_reversion",
        "ranging",
    }
    required_timeframes = {"4h": 200}
    required_indicators = {"rsi", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "donchian_len": "int",
        "range_window": "int",
        "range_width_cv_max": "float",
        "touch_atr_band": "float",
        "min_lower_touches": "int",
        "min_upper_touches": "int",
        "rsi_entry": "float",
        "exit_target": "str",
        "break_atr_mult": "float",
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
        timeframe = self._timeframe()
        donchian_len = int(self.params.get("donchian_len", 20))
        range_window = int(self.params.get("range_window", 15))
        range_width_cv_max = float(self.params.get("range_width_cv_max", 0.10))
        touch_atr_band = float(self.params.get("touch_atr_band", 0.25))
        min_lower_touches = int(self.params.get("min_lower_touches", 1))
        min_upper_touches = int(self.params.get("min_upper_touches", 1))
        rsi_entry = float(self.params.get("rsi_entry", 40.0))
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

            lower_entry_band = float(latest["donchian_low"]) + touch_atr_band * float(latest["atr"])
            if float(latest["close"]) > lower_entry_band:
                continue
            if float(latest["rsi_14"]) >= rsi_entry:
                continue
            if self._is_cooling_down(enriched, symbol, timeframe, cooldown_bars):
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
                    entry_type="donchian_range_lower_fade",
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
                        "entry_lower_band": lower_entry_band,
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
            else float(latest["donchian_high"]) - touch_atr_band * atr
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

        if float(latest["close"]) >= target_price:
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

    def _target_symbols(self, context_symbols: list[str]) -> list[str]:
        configured = self.params.get("symbol")
        symbols = [str(configured)] if configured else list(context_symbols)
        allowed = set(self.allowed_symbols or set())
        dynamic_unbounded = getattr(self, "supports_dynamic_universe", False) and not allowed
        return [
            symbol
            for symbol in dict.fromkeys(symbols)
            if symbol in context_symbols and (dynamic_unbounded or symbol in allowed)
        ]

    def _timeframe(self) -> str:
        return str(self.params.get("timeframe") or "4h")

    def _exit_target_mode(self) -> str:
        return "opposite" if str(self.params.get("exit_target") or "mid") == "opposite" else "mid"

    @staticmethod
    def _with_donchian(
        frame: pd.DataFrame,
        donchian_len: int,
        range_window: int,
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()

        enriched = frame.copy()
        enriched["donchian_high"] = enriched["high"].rolling(donchian_len).max()
        enriched["donchian_low"] = enriched["low"].rolling(donchian_len).min()
        enriched["donchian_mid"] = (enriched["donchian_high"] + enriched["donchian_low"]) / 2.0
        enriched["donchian_width"] = enriched["donchian_high"] - enriched["donchian_low"]
        width_mean = enriched["donchian_width"].rolling(range_window).mean()
        width_std = enriched["donchian_width"].rolling(range_window).std(ddof=0)
        enriched["width_cv"] = width_std / width_mean
        return enriched

    @staticmethod
    def _range_state(
        frame: pd.DataFrame,
        *,
        range_window: int,
        range_width_cv_max: float,
        touch_atr_band: float,
        min_lower_touches: int,
        min_upper_touches: int,
    ) -> dict[str, int | float | bool]:
        tail = frame.tail(range_window)
        latest = tail.iloc[-1]
        lower_touches = int(
            (
                tail["low"]
                <= (tail["donchian_low"] + touch_atr_band * tail["atr"])
            ).sum()
        )
        upper_touches = int(
            (
                tail["high"]
                >= (tail["donchian_high"] - touch_atr_band * tail["atr"])
            ).sum()
        )
        width_cv = float(latest["width_cv"])
        range_detected = (
            width_cv < range_width_cv_max
            and lower_touches >= min_lower_touches
            and upper_touches >= min_upper_touches
        )
        return {
            "range_detected": range_detected,
            "lower_touches": lower_touches,
            "upper_touches": upper_touches,
            "bars_in_range": len(tail),
        }

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
    def _has_entry_columns(frame: pd.DataFrame, range_window: int) -> bool:
        window_required = {"high", "low", "atr", "donchian_high", "donchian_low"}
        latest_required = {"close", "rsi_14", "donchian_mid", "donchian_width", "width_cv"}
        return (
            frame is not None
            and len(frame) >= range_window
            and window_required.union(latest_required).issubset(frame.columns)
            and frame[list(window_required)].tail(range_window).notna().all().all()
            and frame[list(latest_required)].iloc[-1].notna().all()
        )

    @staticmethod
    def _has_exit_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "rsi_14", "atr", "donchian_high", "donchian_low", "donchian_mid"}
        return (
            frame is not None
            and len(frame) >= 2
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )
