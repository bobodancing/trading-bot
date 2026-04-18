"""Deterministic fixture strategies for kernel and backtest validation."""

from __future__ import annotations

from trader.strategies.base import (
    Action,
    PositionDecision,
    SignalIntent,
    StopHint,
    StrategyContext,
    StrategyPlugin,
)


class FixtureLongStrategy(StrategyPlugin):
    id = "fixture_long"
    version = "1.0.0"
    tags = {"fixture", "long_only"}
    required_timeframes = {"1h": 60}
    required_indicators = {"atr", "rsi"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "emit_once": "bool",
        "stop_pct": "float",
    }

    def __init__(self, params=None):
        super().__init__(params)
        self._emitted_keys: set[str] = set()

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        symbol = str(self.params.get("symbol") or (context.symbols[0] if context.symbols else ""))
        timeframe = str(self.params.get("timeframe") or "1h")
        if not symbol:
            return []

        frame = context.snapshot.get(symbol, timeframe)
        if frame.empty:
            return []
        candle_ts = context.snapshot.latest_timestamp(symbol, timeframe)
        entry_price = context.snapshot.latest_close(symbol, timeframe)
        if candle_ts is None or entry_price is None:
            return []

        key = f"{symbol}|{timeframe}|{candle_ts.isoformat()}"
        if bool(self.params.get("emit_once", True)) and key in self._emitted_keys:
            return []
        self._emitted_keys.add(key)

        stop_pct = float(self.params.get("stop_pct", 0.01))
        return [
            SignalIntent(
                strategy_id=self.id,
                symbol=symbol,
                side="LONG",
                timeframe=timeframe,
                candle_ts=candle_ts,
                entry_type="fixture_market",
                stop_hint=StopHint(price=entry_price * (1.0 - stop_pct), reason="fixture_stop"),
                confidence=1.0,
                metadata={"fixture": True},
                entry_price=entry_price,
            )
        ]


class FixtureExitStrategy(StrategyPlugin):
    id = "fixture_exit"
    version = "1.0.0"
    tags = {"fixture", "exit_only"}
    required_timeframes = {"1h": 20}
    required_indicators = set()
    params_schema = {"close_after_updates": "int"}

    def update_position(self, context: StrategyContext, position) -> PositionDecision:
        close_after = int(self.params.get("close_after_updates", 1))
        state = dict(getattr(position, "plugin_state", {}) or {})
        updates = int(state.get("updates", 0)) + 1
        state["updates"] = updates
        position.plugin_state = state
        if updates >= close_after:
            position.exit_reason = "fixture_exit"
            return PositionDecision(action=Action.CLOSE, reason="FIXTURE_EXIT")
        return PositionDecision()
