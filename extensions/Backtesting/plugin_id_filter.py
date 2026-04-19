"""Backtest-only plugin-id allowlist tooling.

This module patches the already-created backtest bot instance. It does not
change production scanner or runtime defaults.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


def normalize_allowed_plugin_ids(plugin_ids: Iterable[str] | None) -> tuple[str, ...] | None:
    if plugin_ids is None:
        return None
    allowed = tuple(dict.fromkeys(str(item) for item in plugin_ids))
    if not allowed:
        raise ValueError("allowed_plugin_ids must contain at least one plugin id")
    return allowed


def install_backtest_plugin_id_filter(bot, allowed_plugin_ids: Iterable[str] | None) -> None:
    """Install a per-run allowlist on the strategy runtime pipeline."""
    allowed = normalize_allowed_plugin_ids(allowed_plugin_ids)
    if allowed is None:
        return

    runtime = getattr(bot, "strategy_runtime", None)
    if runtime is None or not hasattr(runtime, "_process_intent"):
        raise AttributeError("backtest bot has no strategy runtime intent processor")

    allowed_set = set(allowed)
    original_process_intent = runtime._process_intent
    bot._backtest_allowed_plugin_ids = allowed

    def _filtered_process_intent(plugin, intent, context):
        plugin_id = str(getattr(intent, "strategy_id", getattr(plugin, "id", "")))
        selected = plugin_id if plugin_id in allowed_set else None
        _record_lane_race(bot, intent, plugin_id, selected)
        if selected is None:
            _record_allowlist_reject(bot, intent, plugin_id, allowed)
            return None
        return original_process_intent(plugin, intent, context)

    runtime._process_intent = _filtered_process_intent


def _intent_timestamp(intent) -> str:
    candle_ts = getattr(intent, "candle_ts", None)
    if candle_ts is not None:
        return str(candle_ts)
    return datetime.now(timezone.utc).isoformat()


def _record_lane_race(bot, intent, plugin_id: str, selected_plugin_id: str | None) -> None:
    audit = getattr(bot, "_signal_audit", None)
    if audit is None:
        return
    suppressed_by = None if selected_plugin_id else "allowlist"
    block_reason = None if selected_plugin_id else "backtest_plugin_id_allowlist"
    audit.record_lane_race(
        timestamp=_intent_timestamp(intent),
        symbol=getattr(intent, "symbol", "*"),
        candidate_signal_type=plugin_id,
        selected_signal_type=selected_plugin_id,
        suppressed_by=suppressed_by,
        block_reason=block_reason,
        candidate_signal_side=getattr(intent, "side", None),
    )


def _record_allowlist_reject(bot, intent, plugin_id: str, allowed: tuple[str, ...]) -> None:
    audit = getattr(bot, "_signal_audit", None)
    if audit is None:
        return
    audit.record_reject(
        timestamp=_intent_timestamp(intent),
        symbol=getattr(intent, "symbol", "*"),
        stage="backtest_allowlist",
        reject_reason="backtest_plugin_id_allowlist",
        signal_type=plugin_id,
        signal_side=getattr(intent, "side", None),
        detail="allowed_plugin_ids=" + ",".join(allowed),
    )
