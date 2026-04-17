"""Regime-aware signal-to-strategy router.

The arbiter owns confidence and freeze-state decisions. This router only maps
an arbiter snapshot plus a signal to the strategy that may handle it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from trader.config import Config


RUNTIME_LABELS = {
    "TRENDING_UP",
    "TRENDING_DOWN",
    "RANGING",
    "SQUEEZE",
    "NEUTRAL",
    "UNKNOWN",
}
FREEZE_LABELS = {"SQUEEZE", "NEUTRAL", "UNKNOWN"}
TREND_LABELS = {"TRENDING_UP", "TRENDING_DOWN"}
DEFAULT_POLICY = "v54_fallback_current"


@dataclass(frozen=True)
class StrategyRoute:
    strategy_name: str
    signal_types: frozenset[str]
    allowed_labels: frozenset[str]
    priority: int = 100
    min_confidence: float = 0.0
    enabled: bool = True
    allowed_sides: frozenset[str] = frozenset({"LONG", "SHORT"})

    def __post_init__(self):
        object.__setattr__(self, "signal_types", frozenset(self.signal_types))
        object.__setattr__(self, "allowed_labels", frozenset(self.allowed_labels))
        object.__setattr__(self, "allowed_sides", frozenset(self.allowed_sides))

        invalid_labels = self.allowed_labels - RUNTIME_LABELS
        if invalid_labels:
            raise ValueError(
                f"invalid runtime labels for {self.strategy_name}: {sorted(invalid_labels)}"
            )

    def matches(self, *, label: str, signal_type: str, signal_side: str) -> bool:
        return (
            self.enabled
            and signal_type in self.signal_types
            and signal_side in self.allowed_sides
            and label in self.allowed_labels
        )


@dataclass(frozen=True)
class RouterDecision:
    allowed: bool
    selected_strategy: Optional[str]
    reason: str
    policy: str
    signal_type: str
    signal_side: str
    arbiter_label: str
    arbiter_confidence: float

    def audit_fields(self) -> dict[str, object]:
        return {
            "router_allowed": self.allowed,
            "router_selected_strategy": self.selected_strategy,
            "router_reason": self.reason,
            "router_policy": self.policy,
        }


class RegimeRouter:
    """Deterministic strategy selector for already-scored arbiter snapshots."""

    def __init__(
        self,
        routes: Optional[Iterable[StrategyRoute]] = None,
        *,
        policy: Optional[str] = None,
    ):
        self.policy = policy or getattr(Config, "REGIME_ROUTER_POLICY", DEFAULT_POLICY)
        self.routes = tuple(routes) if routes is not None else self._default_routes()
        self._validate_routes()

    @staticmethod
    def _default_routes() -> tuple[StrategyRoute, ...]:
        return (
            StrategyRoute(
                strategy_name="v54_noscale",
                signal_types=frozenset({"2B"}),
                allowed_labels=frozenset({"TRENDING_UP", "TRENDING_DOWN", "RANGING"}),
                priority=100,
                min_confidence=0.0,
            ),
        )

    def route(self, snapshot, signal_type: str, signal_side: str) -> RouterDecision:
        label = getattr(snapshot, "label", "UNKNOWN") or "UNKNOWN"
        confidence = float(getattr(snapshot, "confidence", 0.0) or 0.0)

        if label not in RUNTIME_LABELS:
            return self._block(
                snapshot, signal_type, signal_side, f"invalid_runtime_label:{label}"
            )

        if label in FREEZE_LABELS or not getattr(snapshot, "entry_allowed", False):
            reason = getattr(snapshot, "reason", None) or f"{label.lower()}_freeze_new_entries"
            return self._block(snapshot, signal_type, signal_side, reason)

        macro_reason = self._macro_block(snapshot, signal_side)
        if macro_reason is not None:
            return self._block(snapshot, signal_type, signal_side, macro_reason)

        candidates = sorted(
            (
                route
                for route in self.routes
                if route.matches(
                    label=label,
                    signal_type=signal_type,
                    signal_side=signal_side,
                )
            ),
            key=lambda route: (route.priority, route.strategy_name),
        )
        if not candidates:
            return self._block(
                snapshot,
                signal_type,
                signal_side,
                f"no_route:{signal_type}:{label}:{signal_side}",
            )

        route = candidates[0]
        if confidence < route.min_confidence:
            return self._block(
                snapshot,
                signal_type,
                signal_side,
                f"route_confidence_below_min:{route.strategy_name}",
            )

        return RouterDecision(
            allowed=True,
            selected_strategy=route.strategy_name,
            reason=f"route:{route.strategy_name}",
            policy=self.policy,
            signal_type=signal_type,
            signal_side=signal_side,
            arbiter_label=label,
            arbiter_confidence=confidence,
        )

    def _validate_routes(self) -> None:
        seen: dict[tuple[str, str, str, int], str] = {}
        for route in self.routes:
            if not route.enabled:
                continue
            for signal_type in route.signal_types:
                for label in route.allowed_labels:
                    for side in route.allowed_sides:
                        key = (signal_type, label, side, route.priority)
                        existing = seen.get(key)
                        if existing is not None and existing != route.strategy_name:
                            raise ValueError(
                                "ambiguous route priority: "
                                f"signal={signal_type} label={label} side={side} "
                                f"priority={route.priority} strategies="
                                f"{existing},{route.strategy_name}"
                            )
                        seen[key] = route.strategy_name

    @staticmethod
    def _macro_block(snapshot, signal_side: str) -> Optional[str]:
        if not getattr(Config, "MACRO_OVERLAY_ENABLED", False):
            return None

        if getattr(snapshot, "label", "UNKNOWN") not in TREND_LABELS:
            return None

        macro_state = getattr(snapshot, "macro_state", None) or "UNKNOWN"
        if macro_state in {"UNKNOWN", "MACRO_STALLED"}:
            return f"macro_overlay_blocked:{macro_state.lower()}"
        if macro_state == "MACRO_BULL" and signal_side == "SHORT":
            return "macro_overlay_blocked:bull_blocks_short"
        if macro_state == "MACRO_BEAR" and signal_side == "LONG":
            return "macro_overlay_blocked:bear_blocks_long"
        return None

    def _block(self, snapshot, signal_type: str, signal_side: str, reason: str) -> RouterDecision:
        return RouterDecision(
            allowed=False,
            selected_strategy=None,
            reason=reason,
            policy=self.policy,
            signal_type=signal_type,
            signal_side=signal_side,
            arbiter_label=getattr(snapshot, "label", "UNKNOWN") or "UNKNOWN",
            arbiter_confidence=float(getattr(snapshot, "confidence", 0.0) or 0.0),
        )
