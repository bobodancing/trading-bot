"""Baseline 4h MACD continuation cartridge with staged de-risk and give-back exits."""

from __future__ import annotations

import pandas as pd

from trader.strategies.base import Action, PositionDecision
from trader.strategies.plugins.macd_signal_trending_up_4h import (
    MacdSignalTrendingUp4hStrategy,
)


class MacdSignalTrendingUp4hStagedDeriskGivebackStrategy(
    MacdSignalTrendingUp4hStrategy
):
    id = "macd_signal_btc_4h_trending_up_staged_derisk_giveback"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStrategy.tags | {
        "staged_derisk",
        "giveback_exit",
    }
    params_schema = {
        **MacdSignalTrendingUp4hStrategy.params_schema,
        "derisk_arm_r": "float",
        "derisk_giveback_r": "float",
        "derisk_close_pct": "float",
        "giveback_exit_arm_r": "float",
        "giveback_exit_floor_r": "float",
    }

    def update_position(self, context, position) -> PositionDecision:
        decision = super().update_position(context, position)
        if decision.action == Action.CLOSE and decision.reason == "TREND_GATE_LOST":
            return decision

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

        risk_dist = entry_price - initial_sl
        if risk_dist <= 0:
            return PositionDecision()

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        highest_price = float(getattr(position, "highest_price", entry_price) or entry_price)
        max_favorable_r = max((highest_price - entry_price) / risk_dist, 0.0)
        current_r = (current_close - entry_price) / risk_dist
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
            return PositionDecision(
                action=Action.PARTIAL_CLOSE,
                reason="DERISK_PARTIAL_GIVEBACK",
                new_sl=max(float(getattr(position, "current_sl", 0.0) or 0.0), entry_price),
                close_pct=float(self.params.get("derisk_close_pct", 0.5)),
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

        if decision.action != Action.HOLD:
            return decision
        return PositionDecision()

    def _position_state(self, position) -> dict:
        state = dict(getattr(position, "plugin_state", {}) or {})
        return dict(state.get(self.id, {}) or {})

    def _store_position_state(self, position, own_state: dict) -> None:
        state = dict(getattr(position, "plugin_state", {}) or {})
        state[self.id] = dict(own_state)
        position.plugin_state = state

    @staticmethod
    def _has_giveback_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "ema_20"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingUp4hStagedDeriskGivebackStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )
