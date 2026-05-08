"""Lightweight StrategyRuntime funnel observability for live/testnet runs."""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class RuntimeFunnelRecorder:
    """Append-only runtime funnel recorder plus a small latest summary."""

    CONFIG_SNAPSHOT_KEYS = (
        "SANDBOX_MODE",
        "TRADING_MODE",
        "TRADING_DIRECTION",
        "DRY_RUN",
        "STRATEGY_RUNTIME_ENABLED",
        "STRATEGY_RUNTIME_SIDE_FILTER",
        "ENABLED_STRATEGIES",
        "REGIME_ARBITER_ENABLED",
        "REGIME_ROUTER_ENABLED",
        "STRATEGY_ROUTER_POLICY",
        "BTC_TREND_FILTER_ENABLED",
        "BTC_COUNTER_TREND_MULT",
        "USE_SCANNER_SYMBOLS",
        "SCANNER_JSON_PATH",
        "SCANNER_MAX_AGE_MINUTES",
        "SCANNER_UNIVERSE_ENABLED",
        "SCANNER_UNIVERSE_JSON_PATH",
        "SCANNER_UNIVERSE_MAX_AGE_MINUTES",
        "SYMBOLS",
        "CHECK_INTERVAL",
        "MAX_TOTAL_RISK",
        "MAX_POSITION_PERCENT",
        "MAX_SL_DISTANCE_PCT",
        "RISK_PER_TRADE",
    )

    def __init__(self, jsonl_path: str | os.PathLike[str], latest_path: str | os.PathLike[str]):
        self.jsonl_path = Path(jsonl_path)
        self.latest_path = Path(latest_path)
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._event_counts: Counter[str] = Counter()
        self._reject_counts: Counter[str] = Counter()
        self._plugin_zero_candidate_counts: Counter[str] = Counter()
        self._entry_counts: Counter[str] = Counter()
        self._last_event: dict[str, Any] | None = None
        self._last_cycle: dict[str, Any] | None = None

    @classmethod
    def from_config(cls, config: Any) -> "RuntimeFunnelRecorder | None":
        if not bool(getattr(config, "STRATEGY_RUNTIME_OBSERVABILITY_ENABLED", False)):
            return None
        base_dir = Path(os.path.expanduser(str(getattr(config, "STRATEGY_RUNTIME_OBSERVABILITY_DIR"))))
        if not base_dir.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent / base_dir
        jsonl_path = base_dir / str(getattr(config, "STRATEGY_RUNTIME_OBSERVABILITY_JSONL"))
        latest_path = base_dir / str(getattr(config, "STRATEGY_RUNTIME_OBSERVABILITY_LATEST"))
        return cls(jsonl_path=jsonl_path, latest_path=latest_path)

    def record_config_snapshot(self, config: Any, **fields: Any) -> None:
        snapshot = {
            key: getattr(config, key)
            for key in self.CONFIG_SNAPSHOT_KEYS
            if hasattr(config, key)
        }
        self.record_event("config_snapshot", config=snapshot, **fields)

    def record_event(self, event: str, **fields: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = _json_safe({"ts": now, "event": event, **fields})
        try:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with self.jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
            self._update_summary(payload)
            self._write_latest(now)
        except Exception as exc:
            logger.warning("runtime observability write failed: %s", exc)

    def _update_summary(self, payload: dict[str, Any]) -> None:
        event = str(payload.get("event", "unknown"))
        self._event_counts[event] += 1
        self._last_event = payload

        if event == "strategy_reject":
            reason = str(payload.get("reason") or "unknown")
            self._reject_counts[reason] += 1
        elif event == "plugin_candidates" and int(payload.get("candidate_count") or 0) == 0:
            plugin_id = str(payload.get("plugin_id") or "unknown")
            self._plugin_zero_candidate_counts[plugin_id] += 1
        elif event == "strategy_entry_ready":
            strategy_id = str(payload.get("strategy_id") or "unknown")
            self._entry_counts[strategy_id] += 1
        elif event == "scan_cycle_end":
            self._last_cycle = payload

    def _write_latest(self, now: str) -> None:
        summary = {
            "generated_at": now,
            "started_at": self.started_at,
            "jsonl_path": str(self.jsonl_path),
            "event_counts": dict(sorted(self._event_counts.items())),
            "reject_counts": dict(sorted(self._reject_counts.items())),
            "plugin_zero_candidate_counts": dict(sorted(self._plugin_zero_candidate_counts.items())),
            "entry_counts": dict(sorted(self._entry_counts.items())),
            "last_cycle": self._last_cycle,
            "last_event": self._last_event,
        }
        self.latest_path.parent.mkdir(parents=True, exist_ok=True)
        self.latest_path.write_text(
            json.dumps(_json_safe(summary), ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
