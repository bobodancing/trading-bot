"""Baseline 4h MACD continuation cartridge with an underwater EMA20 exit."""

from __future__ import annotations

import pandas as pd

from trader.strategies.base import Action, PositionDecision
from trader.strategies.plugins.macd_signal_trending_up_4h import (
    MacdSignalTrendingUp4hStrategy,
)


class MacdSignalTrendingUp4hUnderwaterEmaExitStrategy(
    MacdSignalTrendingUp4hStrategy
):
    id = "macd_signal_btc_4h_trending_up_underwater_ema_exit"
    version = "0.1.0"
    tags = MacdSignalTrendingUp4hStrategy.tags | {"underwater_ema_exit"}
    params_schema = {
        **MacdSignalTrendingUp4hStrategy.params_schema,
        "underwater_ema_exit_bars": "int",
    }

    def update_position(self, context, position) -> PositionDecision:
        decision = super().update_position(context, position)
        if decision.action != Action.HOLD:
            return decision

        symbol = getattr(position, "symbol", self.params.get("symbol", "BTC/USDT"))
        entry_timeframe = str(self.params.get("entry_timeframe") or "4h")
        entry_frame = context.snapshot.get(symbol, entry_timeframe)
        if not self._has_underwater_exit_columns(entry_frame):
            return PositionDecision()

        latest_candle_ts = context.snapshot.latest_timestamp(symbol, entry_timeframe)
        entry_time = getattr(position, "entry_time", None)
        entry_price = float(
            getattr(position, "entry_price", getattr(position, "avg_entry", 0.0)) or 0.0
        )
        if latest_candle_ts is None or entry_time is None or entry_price <= 0:
            return PositionDecision()

        bars_since_entry = self._bars_since_entry(
            latest_candle_ts, entry_time, entry_timeframe
        )
        underwater_ema_exit_bars = int(
            self.params.get("underwater_ema_exit_bars", 1)
        )
        if bars_since_entry < underwater_ema_exit_bars:
            return PositionDecision()

        latest_entry = entry_frame.iloc[-1]
        current_close = float(latest_entry["close"])
        current_ema_20 = float(latest_entry["ema_20"])
        if current_close < entry_price and current_close <= current_ema_20:
            return PositionDecision(
                action=Action.CLOSE,
                reason="UNDERWATER_EMA20_EXIT",
                metadata={
                    "bars_since_entry": bars_since_entry,
                    "underwater_ema_exit_bars": underwater_ema_exit_bars,
                    "current_close": current_close,
                    "entry_price": entry_price,
                    "entry_ema_20": current_ema_20,
                },
            )
        return PositionDecision()

    @staticmethod
    def _has_underwater_exit_columns(frame: pd.DataFrame) -> bool:
        required = {"close", "ema_20"}
        return (
            frame is not None
            and len(frame) >= MacdSignalTrendingUp4hUnderwaterEmaExitStrategy.entry_min_bars
            and required.issubset(frame.columns)
            and frame[list(required)].iloc[-1:].notna().all().all()
        )

    @staticmethod
    def _bars_since_entry(latest_candle_ts, entry_time, timeframe: str) -> int:
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
        timeframe_seconds = (
            MacdSignalTrendingUp4hUnderwaterEmaExitStrategy._timeframe_seconds(
                timeframe
            )
        )
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
        raise ValueError(
            f"unsupported timeframe for underwater EMA exit: {timeframe}"
        )
