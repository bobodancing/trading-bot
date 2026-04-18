"""Strategy runtime contracts.

The strategy reset keeps alpha logic behind typed plugin boundaries. Plugins
can describe trade intent and position management, but sizing, portfolio caps,
and execution remain centralized in the bot runtime.
"""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional

import pandas as pd


class Action(str, Enum):
    HOLD = "HOLD"
    CLOSE = "CLOSE"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    UPDATE_SL = "UPDATE_SL"


DecisionDict = dict[str, Any]


@dataclass(frozen=True)
class StopHint:
    price: float
    reason: str = "strategy_stop"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalIntent:
    strategy_id: str
    symbol: str
    side: str
    timeframe: str
    candle_ts: datetime
    entry_type: str
    stop_hint: Optional[StopHint]
    confidence: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    entry_price: Optional[float] = None

    def __post_init__(self) -> None:
        side = self.side.upper()
        if side not in {"LONG", "SHORT"}:
            raise ValueError(f"invalid side: {self.side!r}")
        object.__setattr__(self, "side", side)


@dataclass(frozen=True)
class PositionDecision:
    action: Action = Action.HOLD
    reason: str = "NONE"
    new_sl: Optional[float] = None
    close_pct: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> DecisionDict:
        return {
            "action": self.action,
            "reason": self.reason,
            "new_sl": self.new_sl,
            "close_pct": self.close_pct,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RiskPlan:
    entry_price: float
    stop_loss: float
    position_size: float
    max_loss_usdt: float
    risk_pct: float
    hard_stop_required: bool
    reject_reason: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.reject_reason is None and self.position_size > 0


@dataclass(frozen=True)
class StrategyRiskProfile:
    sizing_mode: str = "fixed_risk_pct"
    risk_pct: Optional[float] = None

    @classmethod
    def fixed_risk_pct(cls, risk_pct: Optional[float] = None) -> "StrategyRiskProfile":
        return cls(sizing_mode="fixed_risk_pct", risk_pct=risk_pct)


@dataclass(frozen=True)
class ExecutableOrderPlan:
    intent: SignalIntent
    risk_plan: RiskPlan
    strategy_version: str
    router_reason: str = "route:direct"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketSnapshot:
    frames: dict[str, dict[str, pd.DataFrame]]
    generated_at: datetime

    def get(self, symbol: str, timeframe: str) -> pd.DataFrame:
        return self.frames.get(symbol, {}).get(timeframe, pd.DataFrame())

    def latest_close(self, symbol: str, timeframe: str) -> Optional[float]:
        frame = self.get(symbol, timeframe)
        if frame.empty or "close" not in frame.columns:
            return None
        return float(frame["close"].iloc[-1])

    def latest_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        frame = self.get(symbol, timeframe)
        if frame.empty:
            return None
        if isinstance(frame.index, pd.DatetimeIndex):
            ts = frame.index[-1]
        elif "timestamp" in frame.columns:
            ts = pd.to_datetime(frame["timestamp"].iloc[-1], utc=True, errors="coerce")
        else:
            return None
        if pd.isna(ts):
            return None
        return ts.to_pydatetime()


@dataclass
class StrategyContext:
    snapshot: MarketSnapshot
    symbols: list[str]
    active_positions: Mapping[str, Any]
    config: Any
    now: datetime


class StrategyPlugin(ABC):
    id: str = ""
    version: str = "0.1.0"
    tags: set[str] = set()
    required_timeframes: dict[str, int] = {"1h": 100}
    required_indicators: set[str] = set()
    params_schema: dict[str, Any] = {}
    allowed_symbols: set[str] = set()
    max_concurrent_positions: Optional[int] = 1
    risk_profile: StrategyRiskProfile = StrategyRiskProfile.fixed_risk_pct()

    def __init__(self, params: Optional[dict[str, Any]] = None):
        self.params = params or {}

    @abstractmethod
    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        """Return candidate entries. Plugins must not size or execute."""

    def update_position(self, context: StrategyContext, position: Any) -> PositionDecision:
        return PositionDecision()

    def get_state(self) -> dict[str, Any]:
        return {}

    def load_state(self, state: dict[str, Any]) -> None:
        return None


class StrategyRegistry:
    def __init__(self):
        self._plugins: dict[str, StrategyPlugin] = {}

    @property
    def plugins(self) -> dict[str, StrategyPlugin]:
        return dict(self._plugins)

    def register(self, plugin: StrategyPlugin) -> None:
        if not plugin.id:
            raise ValueError("strategy plugin id is required")
        if plugin.id in self._plugins:
            raise ValueError(f"duplicate strategy id: {plugin.id}")
        self._plugins[plugin.id] = plugin

    def get(self, strategy_id: str) -> Optional[StrategyPlugin]:
        return self._plugins.get(strategy_id)

    def require(self, strategy_id: str) -> StrategyPlugin:
        plugin = self.get(strategy_id)
        if plugin is None:
            raise KeyError(f"strategy not registered: {strategy_id}")
        return plugin

    @classmethod
    def from_config(
        cls,
        catalog: Mapping[str, Mapping[str, Any]] | None,
        enabled: list[str] | tuple[str, ...] | set[str] | None,
    ) -> "StrategyRegistry":
        registry = cls()
        catalog = catalog or {}
        enabled_set = set(enabled or [])
        if not enabled_set:
            return registry

        for strategy_key in enabled_set:
            entry = catalog.get(strategy_key)
            if entry is None:
                raise ValueError(f"enabled strategy missing from catalog: {strategy_key}")
            if not bool(entry.get("enabled", False)):
                continue
            module_name = entry.get("module")
            class_name = entry.get("class")
            if not module_name or not class_name:
                raise ValueError(f"strategy catalog entry incomplete: {strategy_key}")
            module = importlib.import_module(str(module_name))
            plugin_cls = getattr(module, str(class_name))
            plugin = plugin_cls(params=dict(entry.get("params") or {}))
            if plugin.id != strategy_key:
                raise ValueError(
                    f"strategy id mismatch for {strategy_key}: plugin exposes {plugin.id}"
                )
            registry.register(plugin)
        return registry


def _apply_common_pre(*_args, **_kwargs) -> None:
    """Removed legacy strategy helper retained only for import compatibility."""
    return None
