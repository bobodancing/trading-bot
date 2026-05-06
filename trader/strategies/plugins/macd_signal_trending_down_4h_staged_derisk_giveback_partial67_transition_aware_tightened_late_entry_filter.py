"""Research-only mirrored SHORT probe for the promoted Slot A cartridge."""

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


class MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy(
    StrategyPlugin
):
    entry_min_bars = 26
    trend_min_bars = 50
    entry_warmup_bars = 200
    trend_warmup_bars = 260
    id = (
        "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
        "transition_aware_tightened_late_entry_filter"
    )
    version = "0.1.0"
    tags = {
        "research_candidate",
        "slot_a",
        "macd",
        "4h",
        "short_only",
        "trend",
        "trending_down",
        "regime_declared",
        "mirror_short",
        "staged_derisk",
        "giveback_exit",
        "partial67",
        "weak_tape_defense",
        "transition_aware_tightened",
        "late_entry_filter",
    }
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
        "derisk_arm_r": "float",
        "derisk_giveback_r": "float",
        "derisk_close_pct": "float",
        "giveback_exit_arm_r": "float",
        "giveback_exit_floor_r": "float",
        "entry_ema_extension_atr_max": "float",
        "transition_lookback_bars": "int",
        "transition_hist_ratio_max": "float",
        "transition_prior_negative_hist_min": "float",
        "transition_extension_atr_trigger": "float",
    }
    allowed_symbols = {"BTC/USDT"}
    max_concurrent_positions = 1
    risk_profile = StrategyRiskProfile.fixed_risk_pct()

    def __init__(self, params=None):
        defaults = {
            "symbol": "BTC/USDT",
            "entry_timeframe": "4h",
            "trend_timeframe": "1d",
            "stop_atr_mult": 1.5,
            "require_signal_confirmation": True,
            "emit_once": True,
            "trend_spread_min": 0.005,
            "derisk_arm_r": 1.0,
            "derisk_giveback_r": 0.75,
            "derisk_close_pct": 0.67,
            "giveback_exit_arm_r": 1.5,
            "giveback_exit_floor_r": 0.25,
            "entry_ema_extension_atr_max": 1.25,
            "transition_lookback_bars": 12,
            "transition_hist_ratio_max": 0.25,
            "transition_prior_negative_hist_min": 10.0,
            "transition_extension_atr_trigger": 3.0,
        }
        merged = {**defaults, **dict(params or {})}
        super().__init__(merged)
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
        extension_cap = float(self.params.get("entry_ema_extension_atr_max", 1.25))
        extension_trigger = float(
            self.params.get("transition_extension_atr_trigger", 3.0)
        )
        intents: list[SignalIntent] = []

        for symbol in self._target_symbols(context.symbols):
            entry_frame = context.snapshot.get(symbol, entry_timeframe)
            metrics = self._transition_aware_metrics(
                entry_frame,
                lookback_bars=int(self.params.get("transition_lookback_bars", 12)),
                hist_ratio_max=float(self.params.get("transition_hist_ratio_max", 0.25)),
                prior_negative_hist_min=float(
                    self.params.get("transition_prior_negative_hist_min", 10.0)
                ),
            )
            if metrics is None:
                continue

            transition_context_active = bool(metrics["weak_tape_context_active"])
            tightened_veto_active = (
                transition_context_active
                and metrics["entry_extension_atr"] > extension_cap
                and metrics["entry_extension_atr"] >= extension_trigger
            )
            if tightened_veto_active:
                continue

            for intent in self._generate_candidate_for_symbol(
                context,
                symbol,
                entry_timeframe,
                trend_timeframe,
            ):
                intents.append(
                    SignalIntent(
                        strategy_id=intent.strategy_id,
                        symbol=intent.symbol,
                        side=intent.side,
                        timeframe=intent.timeframe,
                        candle_ts=intent.candle_ts,
                        entry_type=(
                            "macd_signal_cross_down_transition_aware_tightened_"
                            "late_entry_filtered"
                        ),
                        stop_hint=intent.stop_hint,
                        confidence=intent.confidence,
                        metadata={
                            **intent.metadata,
                            "entry_ema_20": metrics["entry_ema_20"],
                            "entry_extension_atr": metrics["entry_extension_atr"],
                            "entry_ema_extension_atr_max": extension_cap,
                            "weak_tape_gate_mode": "transition_aware_tightened",
                            "weak_tape_context_active": tightened_veto_active,
                            "weak_tape_context_reason": (
                                "transition_aware_tightened"
                                if tightened_veto_active
                                else "none"
                            ),
                            "weak_tape_transition_context_active": transition_context_active,
                            "weak_tape_transition_veto_active": tightened_veto_active,
                            "weak_tape_transition_breakdown_active": metrics[
                                "weak_tape_transition_breakdown_active"
                            ],
                            "weak_tape_transition_hist_exhaustion_active": metrics[
                                "weak_tape_transition_hist_exhaustion_active"
                            ],
                            "weak_tape_transition_lookback_bars": metrics[
                                "weak_tape_transition_lookback_bars"
                            ],
                            "weak_tape_transition_current_hist": metrics[
                                "weak_tape_transition_current_hist"
                            ],
                            "weak_tape_transition_prior_negative_hist_abs_max": metrics[
                                "weak_tape_transition_prior_negative_hist_abs_max"
                            ],
                            "weak_tape_transition_hist_ratio": metrics[
                                "weak_tape_transition_hist_ratio"
                            ],
                            "weak_tape_transition_hist_ratio_max": metrics[
                                "weak_tape_transition_hist_ratio_max"
                            ],
                            "weak_tape_transition_prior_negative_hist_min": metrics[
                                "weak_tape_transition_prior_negative_hist_min"
                            ],
                            "weak_tape_transition_prior_low_min": metrics[
                                "weak_tape_transition_prior_low_min"
                            ],
                            "weak_tape_transition_entry_low": metrics[
                                "weak_tape_transition_entry_low"
                            ],
                            "weak_tape_transition_extension_atr_trigger": extension_trigger,
                        },
                        entry_price=intent.entry_price,
                    )
                )
        return intents

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
        if not (previous_macd >= previous_signal and current_macd < current_signal):
            return []

        if bool(self.params.get("require_signal_confirmation", True)) and current_macd >= 0.0:
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
        stop_price = entry_price + stop_atr_mult * atr
        if stop_price <= entry_price:
            return []

        latest_trend = trend_frame.iloc[-1]
        return [
            SignalIntent(
                strategy_id=self.id,
                symbol=symbol,
                side="SHORT",
                timeframe=entry_timeframe,
                candle_ts=candle_ts,
                entry_type="macd_signal_cross_down",
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
        base_decision = self._signal_or_trend_exit(context, position)
        if base_decision.action == Action.CLOSE and base_decision.reason == "TREND_GATE_LOST":
            return base_decision

        symbol = getattr(position, "symbol", self.params.get("symbol", "BTC/USDT"))
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        if not self._has_giveback_columns(entry_frame):
            return PositionDecision()

        entry_price = float(
            getattr(position, "entry_price", getattr(position, "avg_entry", 0.0)) or 0.0
        )
        initial_sl = float(getattr(position, "initial_sl", 0.0) or 0.0)
        if entry_price <= 0 or initial_sl <= 0:
            return PositionDecision()

        risk_dist = initial_sl - entry_price
        if risk_dist <= 0:
            return PositionDecision()

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        lowest_price = float(getattr(position, "lowest_price", entry_price) or entry_price)
        max_favorable_r = max((entry_price - lowest_price) / risk_dist, 0.0)
        current_r = (entry_price - current_close) / risk_dist
        giveback_r = max(max_favorable_r - current_r, 0.0)

        state = self._position_state(position)
        if (
            state.get("derisk_done")
            and max_favorable_r >= float(self.params.get("giveback_exit_arm_r", 1.5))
            and current_r <= float(self.params.get("giveback_exit_floor_r", 0.25))
        ):
            state["giveback_exit_done"] = True
            self._store_position_state(position, state)
            position.exit_reason = "GIVEBACK_EXIT"
            return PositionDecision(
                action=Action.CLOSE,
                reason="GIVEBACK_EXIT",
                metadata={
                    "max_favorable_r": max_favorable_r,
                    "current_r": current_r,
                    "giveback_r": giveback_r,
                    "giveback_exit_arm_r": float(
                        self.params.get("giveback_exit_arm_r", 1.5)
                    ),
                    "giveback_exit_floor_r": float(
                        self.params.get("giveback_exit_floor_r", 0.25)
                    ),
                    "current_close": current_close,
                    "entry_price": entry_price,
                    "entry_ema_20": current_ema_20,
                },
            )

        if (
            not state.get("derisk_done")
            and max_favorable_r >= float(self.params.get("derisk_arm_r", 1.0))
            and giveback_r >= float(self.params.get("derisk_giveback_r", 0.75))
            and current_r <= float(self.params.get("derisk_arm_r", 1.0))
        ):
            state["derisk_done"] = True
            self._store_position_state(position, state)
            current_sl = float(getattr(position, "current_sl", 0.0) or 0.0)
            new_sl = min(current_sl, entry_price) if current_sl > 0 else entry_price
            return PositionDecision(
                action=Action.PARTIAL_CLOSE,
                reason="DERISK_PARTIAL_GIVEBACK",
                new_sl=new_sl,
                close_pct=float(self.params.get("derisk_close_pct", 0.67)),
                metadata={
                    "max_favorable_r": max_favorable_r,
                    "current_r": current_r,
                    "giveback_r": giveback_r,
                    "derisk_arm_r": float(self.params.get("derisk_arm_r", 1.0)),
                    "derisk_giveback_r": float(
                        self.params.get("derisk_giveback_r", 0.75)
                    ),
                    "current_close": current_close,
                    "entry_price": entry_price,
                    "entry_ema_20": current_ema_20,
                },
            )

        if base_decision.action != Action.HOLD:
            return base_decision
        return PositionDecision()

    def _signal_or_trend_exit(self, context: StrategyContext, position) -> PositionDecision:
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
        if previous_macd <= previous_signal and current_macd > current_signal:
            return PositionDecision(
                action=Action.CLOSE,
                reason="MACD_SIGNAL_CROSS_UP",
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

    def _position_state(self, position) -> dict:
        state = dict(getattr(position, "plugin_state", {}) or {})
        return dict(state.get(self.id, {}) or {})

    def _store_position_state(self, position, own_state: dict) -> None:
        state = dict(getattr(position, "plugin_state", {}) or {})
        state[self.id] = dict(own_state)
        position.plugin_state = state

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
        trend_spread = (ema_50 - ema_20) / ema_50
        return ema_50 > ema_20 and trend_spread >= trend_spread_min, float(trend_spread)

    @classmethod
    def _transition_aware_metrics(
        cls,
        frame: pd.DataFrame,
        *,
        lookback_bars: int,
        hist_ratio_max: float,
        prior_negative_hist_min: float,
    ) -> dict[str, float | bool | str | None] | None:
        if not cls._has_transition_columns(frame, lookback_bars):
            return None

        lookback_bars = max(int(lookback_bars), 2)
        window = frame.iloc[-(lookback_bars + 1) :]
        prior = window.iloc[:-1]
        latest = window.iloc[-1]

        current_close = float(latest["close"])
        current_low = float(latest["low"])
        current_ema_20 = float(latest["ema_20"])
        current_hist = float(latest["macd_hist"])
        atr = float(latest["atr"])
        if atr <= 0.0:
            return None

        prior_hist = pd.to_numeric(prior["macd_hist"], errors="coerce")
        prior_low = pd.to_numeric(prior["low"], errors="coerce")
        if prior_hist.isna().any() or prior_low.isna().any():
            return None

        prior_negative_hist_abs_max = abs(float(prior_hist.clip(upper=0.0).min()))
        prior_low_min = float(prior_low.min())
        hist_ratio = (
            abs(current_hist) / prior_negative_hist_abs_max
            if prior_negative_hist_abs_max > 0.0
            else None
        )

        entry_extension_atr = max((current_ema_20 - current_close) / atr, 0.0)
        price_breakdown_active = prior_low_min > 0.0 and current_low <= prior_low_min
        hist_exhaustion_active = (
            current_hist < 0.0
            and prior_negative_hist_abs_max >= float(prior_negative_hist_min)
            and hist_ratio is not None
            and hist_ratio <= float(hist_ratio_max)
        )
        weak_tape_context_active = price_breakdown_active and hist_exhaustion_active

        return {
            "entry_ema_20": current_ema_20,
            "entry_extension_atr": entry_extension_atr,
            "weak_tape_context_active": weak_tape_context_active,
            "weak_tape_transition_breakdown_active": price_breakdown_active,
            "weak_tape_transition_hist_exhaustion_active": hist_exhaustion_active,
            "weak_tape_transition_lookback_bars": lookback_bars,
            "weak_tape_transition_current_hist": current_hist,
            "weak_tape_transition_prior_negative_hist_abs_max": prior_negative_hist_abs_max,
            "weak_tape_transition_hist_ratio": hist_ratio,
            "weak_tape_transition_hist_ratio_max": float(hist_ratio_max),
            "weak_tape_transition_prior_negative_hist_min": float(
                prior_negative_hist_min
            ),
            "weak_tape_transition_prior_low_min": prior_low_min,
            "weak_tape_transition_entry_low": current_low,
        }

    @staticmethod
    def _has_entry_columns(frame: pd.DataFrame) -> bool:
        required = {"macd", "macd_signal", "atr", "close"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-2:].notna().all().all()
        )

    @staticmethod
    def _has_trend_columns(frame: pd.DataFrame) -> bool:
        required = {"ema_20", "ema_50"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy.trend_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )

    @staticmethod
    def _has_giveback_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "ema_20"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingDown4hStagedDeriskGivebackPartial67TransitionAwareTightenedLateEntryFilterStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )

    @classmethod
    def _has_transition_columns(
        cls,
        frame: pd.DataFrame,
        lookback_bars: int,
    ) -> bool:
        required = {"close", "low", "ema_20", "atr", "macd_hist"}
        min_len = max(cls.entry_min_bars, max(int(lookback_bars), 2) + 1)
        return (
            frame is not None
            and len(frame) >= min_len
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-min_len:].notna().all().all()
        )
