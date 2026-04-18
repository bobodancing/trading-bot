"""Regime-aware strategy-id router."""

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
DEFAULT_POLICY = "fail_closed"


@dataclass(frozen=True)
class StrategyRoute:
    strategy_ids: frozenset[str] = frozenset()
    strategy_tags: frozenset[str] = frozenset()
    allowed_labels: frozenset[str] = frozenset({"TRENDING_UP", "TRENDING_DOWN", "RANGING"})
    priority: int = 100
    min_confidence: float = 0.0
    enabled: bool = True
    allowed_sides: frozenset[str] = frozenset({"LONG", "SHORT"})

    def __post_init__(self):
        object.__setattr__(self, "strategy_ids", frozenset(self.strategy_ids))
        object.__setattr__(self, "strategy_tags", frozenset(self.strategy_tags))
        object.__setattr__(self, "allowed_labels", frozenset(self.allowed_labels))
        object.__setattr__(self, "allowed_sides", frozenset(self.allowed_sides))
        invalid_labels = self.allowed_labels - RUNTIME_LABELS
        if invalid_labels:
            raise ValueError(f"invalid runtime labels: {sorted(invalid_labels)}")
        if not self.strategy_ids and not self.strategy_tags:
            raise ValueError("route must define strategy_ids or strategy_tags")

    def matches(self, *, label: str, strategy_id: str, tags: set[str], side: str) -> bool:
        id_match = strategy_id in self.strategy_ids if self.strategy_ids else False
        tag_match = bool(self.strategy_tags & tags) if self.strategy_tags else False
        return (
            self.enabled
            and (id_match or tag_match)
            and side in self.allowed_sides
            and label in self.allowed_labels
        )


@dataclass(frozen=True)
class RouterDecision:
    allowed: bool
    selected_strategy: Optional[str]
    reason: str
    policy: str
    strategy_id: str
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
    def __init__(
        self,
        routes: Optional[Iterable[StrategyRoute]] = None,
        *,
        policy: Optional[str] = None,
    ):
        self.policy = policy or getattr(Config, "STRATEGY_ROUTER_POLICY", DEFAULT_POLICY)
        self.routes = tuple(routes) if routes is not None else tuple()
        self._validate_routes()

    def route(
        self,
        snapshot,
        *,
        strategy_id: str,
        strategy_tags: Iterable[str] = (),
        signal_side: str,
    ) -> RouterDecision:
        label = getattr(snapshot, "label", "UNKNOWN") or "UNKNOWN"
        confidence = float(getattr(snapshot, "confidence", 0.0) or 0.0)
        tags = set(strategy_tags or ())

        if label not in RUNTIME_LABELS:
            return self._block(snapshot, strategy_id, signal_side, f"invalid_runtime_label:{label}")
        if label in FREEZE_LABELS or not getattr(snapshot, "entry_allowed", False):
            reason = getattr(snapshot, "reason", None) or f"{label.lower()}_freeze_new_entries"
            return self._block(snapshot, strategy_id, signal_side, reason)

        macro_reason = self._macro_block(snapshot, signal_side)
        if macro_reason is not None:
            return self._block(snapshot, strategy_id, signal_side, macro_reason)

        candidates = sorted(
            (
                route
                for route in self.routes
                if route.matches(
                    label=label,
                    strategy_id=strategy_id,
                    tags=tags,
                    side=signal_side,
                )
            ),
            key=lambda route: route.priority,
        )
        if not candidates:
            return self._block(snapshot, strategy_id, signal_side, f"no_route:{strategy_id}:{label}:{signal_side}")

        route = candidates[0]
        if confidence < route.min_confidence:
            return self._block(snapshot, strategy_id, signal_side, "route_confidence_below_min")

        return RouterDecision(
            allowed=True,
            selected_strategy=strategy_id,
            reason=f"route:{strategy_id}",
            policy=self.policy,
            strategy_id=strategy_id,
            signal_side=signal_side,
            arbiter_label=label,
            arbiter_confidence=confidence,
        )

    def _validate_routes(self) -> None:
        seen: set[tuple[str, str, int]] = set()
        for route in self.routes:
            if not route.enabled:
                continue
            keys = set(route.strategy_ids) | {f"tag:{tag}" for tag in route.strategy_tags}
            for key in keys:
                for label in route.allowed_labels:
                    marker = (key, label, route.priority)
                    if marker in seen:
                        raise ValueError(f"ambiguous route priority: {marker}")
                    seen.add(marker)

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

    def _block(self, snapshot, strategy_id: str, signal_side: str, reason: str) -> RouterDecision:
        return RouterDecision(
            allowed=False,
            selected_strategy=None,
            reason=reason,
            policy=self.policy,
            strategy_id=strategy_id,
            signal_side=signal_side,
            arbiter_label=getattr(snapshot, "label", "UNKNOWN") or "UNKNOWN",
            arbiter_confidence=float(getattr(snapshot, "confidence", 0.0) or 0.0),
        )
