"""Range-break retest continuation cartridge for Phase 4D research."""

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


class RangeBreakRetest4hConservative30Strategy(StrategyPlugin):
    id = "range_break_retest_4h_conservative_30"
    version = "0.1.0"
    tags = {
        "active_research",
        "frequency_complement",
        "range_break",
        "retest",
        "continuation",
        "4h",
        "long_short",
        "regime_declared",
    }
    required_timeframes = {"4h": 220}
    required_indicators = {"atr", "adx", "bbw", "ema"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "donchian_len": "int",
        "range_window": "int",
        "bbw_pctrank_window": "int",
        "width_cv_max": "float",
        "range_width_pct_max": "float",
        "bbw_pctrank_max": "float",
        "break_atr_min": "float",
        "max_retest_bars": "int",
        "retest_band_atr": "float",
        "min_retest_distance_atr": "float",
        "max_retest_distance_atr": "float",
        "min_adx": "float",
        "min_adx_slope_5": "float",
        "breakout_close_quality_min": "float",
        "trend_aligned": "bool",
        "stop_atr_mult": "float",
        "profit_target_r": "float",
        "max_hold_bars": "int",
        "failure_atr_mult": "float",
        "emit_once": "bool",
        "risk_pct": "float",
    }
    allowed_symbols = {"BTC/USDT", "ETH/USDT"}
    max_concurrent_positions = 1
    risk_profile = StrategyRiskProfile.fixed_risk_pct()

    def __init__(self, params=None):
        super().__init__(params)
        self._emitted_keys: set[str] = set()
        risk_pct = self.params.get("risk_pct")
        if risk_pct is not None:
            self.risk_profile = StrategyRiskProfile.fixed_risk_pct(float(risk_pct))

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        timeframe = self._timeframe()
        intents: list[SignalIntent] = []
        for symbol in self._target_symbols(context.symbols):
            frame = context.snapshot.get(symbol, timeframe)
            enriched = self._with_range_features(frame)
            signal = self._latest_signal(enriched)
            if signal is None:
                continue

            candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
            entry_price = context.snapshot.latest_close(symbol, timeframe)
            if candle_ts is None or entry_price is None or entry_price <= 0:
                continue
            side = str(signal["side"])
            key = f"{symbol}|{timeframe}|{candle_ts.isoformat()}|{side}"
            if bool(self.params.get("emit_once", True)) and key in self._emitted_keys:
                continue

            atr = float(signal["retest_atr"])
            stop_atr_mult = float(self.params.get("stop_atr_mult", 1.5))
            if side == "LONG":
                stop_price = float(entry_price) - stop_atr_mult * atr
                if stop_price <= 0.0 or stop_price >= float(entry_price):
                    continue
            else:
                stop_price = float(entry_price) + stop_atr_mult * atr
                if stop_price <= float(entry_price):
                    continue

            self._emitted_keys.add(key)
            intents.append(
                SignalIntent(
                    strategy_id=self.id,
                    symbol=symbol,
                    side=side,
                    timeframe=timeframe,
                    candle_ts=candle_ts,
                    entry_type="range_break_retest_continuation",
                    stop_hint=StopHint(
                        price=stop_price,
                        reason="range_break_retest_atr_stop",
                        metadata={
                            "atr": atr,
                            "atr_mult": stop_atr_mult,
                            "range_boundary": float(signal["range_boundary"]),
                        },
                    ),
                    confidence=None,
                    metadata={
                        "candidate_family": "range_break_retest_frequency_complement",
                        "mechanism": "donchian30_break_retest_hold_4h_continuation",
                        "variant_id": self.id,
                        "entry_timeframe": timeframe,
                        "breakout_timestamp": signal["breakout_timestamp"],
                        "range_boundary": float(signal["range_boundary"]),
                        "retest_lag_bars": int(signal["retest_lag_bars"]),
                        "retest_distance_atr": float(signal["retest_distance_atr"]),
                        "break_strength_atr": float(signal["break_strength_atr"]),
                        "breakout_close_quality": float(signal["breakout_close_quality"]),
                        "width_cv": float(signal["width_cv"]),
                        "range_width_pct": float(signal["range_width_pct"]),
                        "bbw_pctrank": float(signal["bbw_pctrank"]),
                        "adx": float(signal["adx"]),
                        "adx_slope_5": float(signal["adx_slope_5"]),
                        "ema_spread_20_50": float(signal["ema_spread_20_50"]),
                        "profit_target_r": float(self.params.get("profit_target_r", 1.5)),
                        "max_hold_bars": int(self.params.get("max_hold_bars", 18)),
                        "failure_atr_mult": float(self.params.get("failure_atr_mult", 0.25)),
                    },
                    entry_price=float(entry_price),
                )
            )
        return intents

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        symbol = str(getattr(position, "symbol", self.params.get("symbol", "")) or "")
        timeframe = self._timeframe()
        frame = context.snapshot.get(symbol, timeframe)
        if frame is None or len(frame) < 2:
            return PositionDecision()

        latest = frame.iloc[-1]
        if "atr" not in frame.columns or pd.isna(latest.get("atr")):
            return PositionDecision()

        metadata = dict(getattr(position, "metadata", {}) or {})
        side = str(getattr(position, "side", "") or "").upper()
        boundary = self._metadata_float(metadata, "range_boundary")
        if side not in {"LONG", "SHORT"} or boundary is None:
            return PositionDecision()

        close = float(latest["close"])
        atr = float(latest["atr"])
        failure_atr_mult = float(metadata.get("failure_atr_mult", self.params.get("failure_atr_mult", 0.25)))
        if side == "LONG" and close < boundary - failure_atr_mult * atr:
            return self._close_decision(
                position,
                "RANGE_BREAK_RETEST_BOUNDARY_FAIL",
                {"close": close, "range_boundary": boundary, "atr": atr},
            )
        if side == "SHORT" and close > boundary + failure_atr_mult * atr:
            return self._close_decision(
                position,
                "RANGE_BREAK_RETEST_BOUNDARY_FAIL",
                {"close": close, "range_boundary": boundary, "atr": atr},
            )

        risk_dist = abs(
            float(getattr(position, "avg_entry", 0.0) or 0.0)
            - float(getattr(position, "initial_sl", 0.0) or 0.0)
        )
        target_r = float(metadata.get("profit_target_r", self.params.get("profit_target_r", 1.5)))
        entry = float(getattr(position, "avg_entry", 0.0) or 0.0)
        if risk_dist > 0.0 and entry > 0.0:
            target_price = entry + target_r * risk_dist if side == "LONG" else entry - target_r * risk_dist
            if (side == "LONG" and close >= target_price) or (
                side == "SHORT" and close <= target_price
            ):
                return self._close_decision(
                    position,
                    "RANGE_BREAK_RETEST_TARGET_R",
                    {
                        "close": close,
                        "target_price": target_price,
                        "target_r": target_r,
                    },
                )

        max_hold_bars = int(metadata.get("max_hold_bars", self.params.get("max_hold_bars", 18)))
        bars_held = self._bars_since_entry(frame, metadata.get("candle_ts"))
        if max_hold_bars > 0 and bars_held is not None and bars_held >= max_hold_bars:
            return self._close_decision(
                position,
                "RANGE_BREAK_RETEST_TIME_STOP",
                {"bars_held": bars_held, "max_hold_bars": max_hold_bars},
            )

        return PositionDecision()

    def _latest_signal(self, frame: pd.DataFrame) -> dict[str, Any] | None:
        max_retest_bars = int(self.params.get("max_retest_bars", 3))
        if not self._has_entry_columns(frame, max_retest_bars):
            return None

        latest_idx = len(frame) - 1
        latest = frame.iloc[latest_idx]
        signals: list[dict[str, Any]] = []
        for lag in range(1, max_retest_bars + 1):
            breakout_idx = latest_idx - lag
            if breakout_idx < 0:
                continue
            breakout = frame.iloc[breakout_idx]
            for side in ("LONG", "SHORT"):
                if not self._passes_breakout(breakout, side=side):
                    continue
                boundary = float(
                    breakout["range_high"] if side == "LONG" else breakout["range_low"]
                )
                if self._had_prior_retest(
                    frame,
                    breakout_idx=breakout_idx,
                    latest_idx=latest_idx,
                    side=side,
                    boundary=boundary,
                ):
                    continue
                passed, distance_atr = self._passes_retest(
                    latest,
                    side=side,
                    boundary=boundary,
                )
                if not passed or distance_atr is None:
                    continue
                break_strength = (
                    float((breakout["close"] - boundary) / breakout["atr"])
                    if side == "LONG"
                    else float((boundary - breakout["close"]) / breakout["atr"])
                )
                signals.append(
                    {
                        "side": side,
                        "breakout_timestamp": pd.Timestamp(frame.index[breakout_idx]).isoformat(),
                        "range_boundary": boundary,
                        "retest_lag_bars": lag,
                        "retest_distance_atr": float(distance_atr),
                        "break_strength_atr": float(break_strength),
                        "breakout_close_quality": float(
                            self._breakout_close_quality(breakout, side) or 0.0
                        ),
                        "retest_atr": float(latest["atr"]),
                        "width_cv": float(breakout["width_cv"]),
                        "range_width_pct": float(breakout["range_width_pct"]),
                        "bbw_pctrank": float(breakout["bbw_pctrank"]),
                        "adx": float(breakout["adx"]),
                        "adx_slope_5": float(breakout["adx_slope_5"]),
                        "ema_spread_20_50": float(breakout["ema_spread_20_50"]),
                    }
                )
        if not signals:
            return None
        return max(signals, key=lambda item: (float(item["break_strength_atr"]), -int(item["retest_lag_bars"])))

    def _with_range_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        enriched = frame.copy()
        donchian_len = int(self.params.get("donchian_len", 30))
        range_window = int(self.params.get("range_window", 15))
        bbw_window = int(self.params.get("bbw_pctrank_window", 50))
        enriched["range_high"] = enriched["high"].shift(1).rolling(donchian_len).max()
        enriched["range_low"] = enriched["low"].shift(1).rolling(donchian_len).min()
        enriched["range_width"] = enriched["range_high"] - enriched["range_low"]
        enriched["range_mid"] = (enriched["range_high"] + enriched["range_low"]) / 2.0
        width_mean = enriched["range_width"].rolling(range_window).mean()
        width_std = enriched["range_width"].rolling(range_window).std(ddof=0)
        enriched["width_cv"] = width_std / width_mean
        enriched["range_width_pct"] = enriched["range_width"] / enriched["close"]
        enriched["bbw_pctrank"] = enriched["bbw"].rolling(bbw_window).rank(pct=True) * 100.0
        enriched["adx_slope_5"] = enriched["adx"] - enriched["adx"].shift(5)
        enriched["ema_spread_20_50"] = (
            enriched["ema_20"] - enriched["ema_50"]
        ) / enriched["ema_50"]
        return enriched

    def _passes_breakout(self, row: pd.Series, *, side: str) -> bool:
        required = [
            "atr",
            "range_high",
            "range_low",
            "width_cv",
            "bbw_pctrank",
            "adx",
            "adx_slope_5",
            "ema_spread_20_50",
        ]
        if row[required].isna().any() or float(row["atr"]) <= 0.0:
            return False
        if float(row["width_cv"]) > float(self.params.get("width_cv_max", 0.18)):
            return False
        range_width_pct_max = self.params.get("range_width_pct_max")
        if range_width_pct_max is not None and float(row["range_width_pct"]) > float(range_width_pct_max):
            return False
        if float(row["bbw_pctrank"]) > float(self.params.get("bbw_pctrank_max", 45.0)):
            return False
        if float(row["adx"]) < float(self.params.get("min_adx", 12.0)):
            return False
        if float(row["adx_slope_5"]) < float(self.params.get("min_adx_slope_5", -2.0)):
            return False
        quality = self._breakout_close_quality(row, side)
        if quality is None or quality < float(self.params.get("breakout_close_quality_min", 0.55)):
            return False
        break_atr = float(self.params.get("break_atr_min", 0.05)) * float(row["atr"])
        if side == "LONG":
            if bool(self.params.get("trend_aligned", False)) and float(row["ema_spread_20_50"]) < 0.0:
                return False
            return float(row["close"]) > float(row["range_high"]) + break_atr
        if bool(self.params.get("trend_aligned", False)) and float(row["ema_spread_20_50"]) > 0.0:
            return False
        return float(row["close"]) < float(row["range_low"]) - break_atr

    def _passes_retest(
        self,
        row: pd.Series,
        *,
        side: str,
        boundary: float,
    ) -> tuple[bool, float | None]:
        if pd.isna(row.get("atr")) or float(row["atr"]) <= 0.0:
            return False, None
        atr = float(row["atr"])
        band = float(self.params.get("retest_band_atr", 0.35)) * atr
        if side == "LONG":
            distance_atr = float((row["low"] - boundary) / atr)
            touched = float(row["low"]) <= boundary + band
            held = float(row["close"]) >= boundary
        else:
            distance_atr = float((boundary - row["high"]) / atr)
            touched = float(row["high"]) >= boundary - band
            held = float(row["close"]) <= boundary
        min_distance = self.params.get("min_retest_distance_atr")
        if min_distance is not None and distance_atr < float(min_distance):
            return False, distance_atr
        max_distance = self.params.get("max_retest_distance_atr")
        if max_distance is not None and distance_atr > float(max_distance):
            return False, distance_atr
        return bool(touched and held), distance_atr

    def _had_prior_retest(
        self,
        frame: pd.DataFrame,
        *,
        breakout_idx: int,
        latest_idx: int,
        side: str,
        boundary: float,
    ) -> bool:
        for idx in range(breakout_idx + 1, latest_idx):
            passed, _distance_atr = self._passes_retest(
                frame.iloc[idx],
                side=side,
                boundary=boundary,
            )
            if passed:
                return True
        return False

    def _target_symbols(self, context_symbols: list[str]) -> list[str]:
        configured = self.params.get("symbol")
        symbols = [str(configured)] if configured else list(context_symbols)
        allowed = set(self.allowed_symbols or set())
        return [
            symbol
            for symbol in dict.fromkeys(symbols)
            if symbol in context_symbols and (not allowed or symbol in allowed)
        ]

    def _timeframe(self) -> str:
        return str(self.params.get("timeframe") or "4h")

    @staticmethod
    def _breakout_close_quality(row: pd.Series, side: str) -> float | None:
        candle_range = float(row["high"] - row["low"])
        if candle_range <= 0.0:
            return None
        if side == "LONG":
            return float((row["close"] - row["low"]) / candle_range)
        return float((row["high"] - row["close"]) / candle_range)

    @staticmethod
    def _metadata_float(metadata: dict[str, Any], key: str) -> float | None:
        try:
            value = metadata.get(key)
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _close_decision(position, reason: str, metadata: dict[str, Any]) -> PositionDecision:
        position.exit_reason = reason
        return PositionDecision(action=Action.CLOSE, reason=reason, metadata=metadata)

    @staticmethod
    def _bars_since_entry(frame: pd.DataFrame, raw_ts: Any) -> int | None:
        if raw_ts is None:
            return None
        ts = pd.Timestamp(raw_ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        index = frame.index
        if not isinstance(index, pd.DatetimeIndex):
            return None
        if index.tz is None:
            index = index.tz_localize("UTC")
        else:
            index = index.tz_convert("UTC")
        return int((index > ts).sum())

    @staticmethod
    def _has_entry_columns(frame: pd.DataFrame, max_retest_bars: int) -> bool:
        required = {
            "open",
            "high",
            "low",
            "close",
            "atr",
            "adx",
            "bbw",
            "ema_20",
            "ema_50",
            "range_high",
            "range_low",
            "width_cv",
            "range_width_pct",
            "bbw_pctrank",
            "adx_slope_5",
            "ema_spread_20_50",
        }
        return (
            frame is not None
            and len(frame) >= max(2, max_retest_bars + 1)
            and required.issubset(frame.columns)
            and frame[list(required)].tail(max_retest_bars + 1).notna().all().all()
        )
