"""Build runtime weekly-control packets from dry-run/testnet evidence.

This adapter is read-only. It maps StrategyRuntime observability JSONL,
performance.db closed trades, positions.json, and scanner diagnostics into the
same weekly KPI contract used by the Phase 3 backtest-control packet.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from extensions.Backtesting.weekly_profit_control import (  # noqa: E402
    build_weekly_control_packets,
)
from trader.config import Config  # noqa: E402
from trader.runtime_observability import config_snapshot_hash  # noqa: E402


SCHEMA = "strategy_runtime_weekly_control_packets.v1"
DEFAULT_FEE_RATE = 0.0004
DEFAULT_REVIEW_CAPITAL_USDT = 10000.0
DEFAULT_WEEKS = 12
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".log" / "weekly_control"
DEFAULT_JSON = DEFAULT_OUTPUT_DIR / "runtime_weekly_control_packets.json"
DEFAULT_CSV = DEFAULT_OUTPUT_DIR / "runtime_weekly_control_packets.csv"
DEFAULT_REPORT = DEFAULT_OUTPUT_DIR / "runtime_weekly_control_packet.md"
DEFAULT_SCANNER_REPORT = REPO_ROOT / str(getattr(Config, "RUNTIME_SCANNER_JSON_PATH", "runtime_scanner.json"))

RUNTIME_CONFIG_CONTRACT_KEYS = (
    "STRATEGY_RUNTIME_ENABLED",
    "STRATEGY_RUNTIME_SIDE_FILTER",
    "ENABLED_STRATEGIES",
    "SYMBOLS",
    "USE_SCANNER_SYMBOLS",
    "SCANNER_UNIVERSE_ENABLED",
    "REGIME_ARBITER_ENABLED",
    "REGIME_ROUTER_ENABLED",
    "STRATEGY_ROUTER_POLICY",
    "MACRO_OVERLAY_ENABLED",
    "BTC_TREND_FILTER_ENABLED",
    "BTC_TREND_FILTER_RUNTIME_MODE",
    "BTC_COUNTER_TREND_MULT",
    "RISK_PER_TRADE",
    "MAX_TOTAL_RISK",
)

CONFIG_PROFILE_ALL = "all"
CONFIG_PROFILE_PROMOTED_BASELINE = "promoted_baseline"
CONFIG_PROFILE_CHOICES = (
    CONFIG_PROFILE_ALL,
    CONFIG_PROFILE_PROMOTED_BASELINE,
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        ts = raw
    else:
        text = str(raw).strip()
        if not text:
            return None
        try:
            ts = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _parse_as_of(raw: str | None) -> date:
    if raw is None:
        return datetime.now(timezone.utc).date()
    ts = _parse_ts(raw)
    if ts is not None:
        return ts.date()
    return date.fromisoformat(str(raw))


def _week_start_for_date(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _week_start_for_ts(raw: Any) -> date | None:
    ts = _parse_ts(raw)
    if ts is None:
        return None
    return _week_start_for_date(ts.date())


def _review_weeks(*, as_of: date, weeks: int, completed_only: bool) -> tuple[list[date], str, str]:
    if weeks <= 0:
        raise ValueError("weeks must be positive")
    end_week = _week_start_for_date(as_of)
    if completed_only:
        end_week -= timedelta(days=7)
        review_end = end_week + timedelta(days=6)
    else:
        review_end = as_of
    start_week = end_week - timedelta(days=7 * (weeks - 1))
    week_starts = [start_week + timedelta(days=7 * idx) for idx in range(weeks)]
    return week_starts, week_starts[0].isoformat(), review_end.isoformat()


def _week_key_in_review(raw_ts: Any, buckets: dict[date, dict[str, Any]]) -> date | None:
    week = _week_start_for_ts(raw_ts)
    return week if week in buckets else None


def _new_week_row(week_start: date) -> dict[str, Any]:
    week_end = week_start + timedelta(days=6)
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "entry_trades": 0,
        "exit_trades": 0,
        "gross_pnl_usdt": 0.0,
        "fees_est_usdt": 0.0,
        "net_after_fee_est_usdt": 0.0,
    }


def _new_runtime_week_detail(week_start: date) -> dict[str, Any]:
    week_end = week_start + timedelta(days=6)
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "scan_cycle_count": 0,
        "scan_cycle_status_counts": {},
        "plugin_candidate_event_count": 0,
        "plugin_candidate_total": 0,
        "plugin_zero_candidate_counts": {},
        "strategy_entry_ready_count": 0,
        "strategy_reject_count": 0,
        "strategy_reject_reason_counts": {},
        "execution_filled_count": 0,
        "execution_failure_count": 0,
        "execution_skipped_count": 0,
        "dry_run_execution_skipped_count": 0,
        "execution_attempt_count_weekly": 0,
        "config_snapshot_count": 0,
        "config_drift_events_weekly": 0,
        "config_drift_keys": [],
        "unprotected_position_events_weekly": 0,
        "unprotected_position_symbols": [],
        "active_position_count_snapshot": 0,
    }


def _read_json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return json.load(handle), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _read_runtime_events(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quality = {
        "runtime_events_path": str(path),
        "runtime_events_file_exists": path.exists(),
        "runtime_event_count": 0,
        "malformed_runtime_event_count": 0,
    }
    if not path.exists():
        return [], quality

    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                quality["malformed_runtime_event_count"] += 1
                continue
            if isinstance(payload, dict):
                events.append(payload)
            else:
                quality["malformed_runtime_event_count"] += 1
    quality["runtime_event_count"] = len(events)
    return events, quality


def _runtime_baseline() -> dict[str, Any]:
    return {
        key: _json_safe(getattr(Config, key))
        for key in RUNTIME_CONFIG_CONTRACT_KEYS
        if hasattr(Config, key)
    }


def _config_snapshot_drift(snapshot: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    drift: dict[str, Any] = {}
    for key, expected in baseline.items():
        if key not in snapshot:
            continue
        observed = _json_safe(snapshot.get(key))
        if json.dumps(observed, sort_keys=True) != json.dumps(expected, sort_keys=True):
            drift[key] = {"expected": expected, "observed": observed}
    return drift


def _config_profile(snapshot: dict[str, Any], baseline: dict[str, Any]) -> str:
    enabled = snapshot.get("ENABLED_STRATEGIES")
    runtime_enabled = snapshot.get("STRATEGY_RUNTIME_ENABLED")

    if not _config_snapshot_drift(snapshot, baseline) and all(
        key in snapshot
        for key in ("ENABLED_STRATEGIES", "SYMBOLS", "STRATEGY_RUNTIME_ENABLED")
    ):
        return CONFIG_PROFILE_PROMOTED_BASELINE
    if enabled == ["fixture_long"]:
        return "test_fixture_long"
    if enabled == [] or runtime_enabled is False:
        return "runtime_disabled_or_empty"
    if isinstance(enabled, list) and any("symbol_universe_expansion_repair" in item for item in enabled):
        return "research_4e_repair"
    if isinstance(enabled, list) and any("symbol_universe_expansion" in item for item in enabled):
        return "research_4e_expansion"
    if isinstance(enabled, list):
        return "research_or_nonbaseline"
    return "unknown"


def _scope_runtime_events(
    events: list[dict[str, Any]],
    *,
    baseline: dict[str, Any],
    run_id: str | None,
    config_hash: str | None,
    config_profile: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if config_profile not in CONFIG_PROFILE_CHOICES:
        raise ValueError(f"config_profile must be one of {CONFIG_PROFILE_CHOICES}, got {config_profile}")

    selected: list[dict[str, Any]] = []
    profile_counts: Counter[str] = Counter()
    current_config_hash: str | None = None
    current_profile: str | None = None
    selected_without_hard_scope = 0
    selected_config_snapshots = 0

    for event in events:
        event_name = str(event.get("event") or "unknown")
        event_config_hash = event.get("config_hash")
        if event_name == "config_snapshot":
            snapshot = event.get("config") if isinstance(event.get("config"), dict) else {}
            current_config_hash = str(event_config_hash or config_snapshot_hash(snapshot))
            current_profile = _config_profile(snapshot, baseline)
            profile_counts[current_profile] += 1
            if "config_hash" not in event:
                event = {
                    **event,
                    "config_hash": current_config_hash,
                    "config_hash_algo": "sha256",
                }
        elif event_config_hash:
            current_config_hash = str(event_config_hash)

        event_run_id = event.get("run_id")
        effective_hash = str(event.get("config_hash") or current_config_hash or "")
        effective_profile = current_profile or "no_config_context"

        matches = True
        if run_id is not None:
            matches = str(event_run_id or "") == run_id
        if matches and config_hash is not None:
            matches = effective_hash == config_hash
        if matches and config_profile == CONFIG_PROFILE_PROMOTED_BASELINE:
            matches = effective_profile == CONFIG_PROFILE_PROMOTED_BASELINE

        if matches:
            selected.append(event)
            if event_name == "config_snapshot":
                selected_config_snapshots += 1
            if not event_run_id and not event.get("config_hash"):
                selected_without_hard_scope += 1

    hard_scope = run_id is not None or config_hash is not None
    scope_mode = []
    if run_id is not None:
        scope_mode.append("run_id")
    if config_hash is not None:
        scope_mode.append("config_hash")
    if config_profile != CONFIG_PROFILE_ALL:
        scope_mode.append(f"config_profile:{config_profile}")
    if not scope_mode:
        scope_mode.append("unfiltered")

    return selected, {
        "scope_mode": "+".join(scope_mode),
        "scope_run_id": run_id,
        "scope_config_hash": config_hash,
        "scope_config_profile": config_profile,
        "scope_hard_boundary": hard_scope,
        "scope_uses_legacy_config_context": not hard_scope and config_profile != CONFIG_PROFILE_ALL,
        "runtime_event_count_before_scope": len(events),
        "runtime_event_count_after_scope": len(selected),
        "runtime_event_count_dropped_by_scope": len(events) - len(selected),
        "selected_event_without_run_or_config_hash_count": selected_without_hard_scope,
        "selected_config_snapshot_count": selected_config_snapshots,
        "config_profile_counts": dict(sorted(profile_counts.items())),
    }


def _increment_counter_field(detail: dict[str, Any], field: str, key: str) -> None:
    counts = Counter(detail.get(field) or {})
    counts[str(key)] += 1
    detail[field] = dict(sorted(counts.items()))


def _apply_runtime_events(
    events: list[dict[str, Any]],
    *,
    week_rows: dict[date, dict[str, Any]],
    runtime_details: dict[date, dict[str, Any]],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    quality = {
        "runtime_events_outside_review_window": 0,
        "runtime_event_without_timestamp_count": 0,
        "entry_trade_source": "performance_db_closed_trade_entry_time",
    }
    filled_by_week: dict[date, int] = defaultdict(int)

    for event in events:
        week = _week_key_in_review(event.get("ts"), runtime_details)
        if week is None:
            if event.get("ts"):
                quality["runtime_events_outside_review_window"] += 1
            else:
                quality["runtime_event_without_timestamp_count"] += 1
            continue

        detail = runtime_details[week]
        event_name = str(event.get("event") or "unknown")

        if event_name == "scan_cycle_end":
            detail["scan_cycle_count"] += 1
            _increment_counter_field(detail, "scan_cycle_status_counts", str(event.get("status") or "unknown"))
        elif event_name == "plugin_candidates":
            detail["plugin_candidate_event_count"] += 1
            candidate_count = _safe_int(event.get("candidate_count"))
            detail["plugin_candidate_total"] += candidate_count
            if candidate_count == 0:
                _increment_counter_field(
                    detail,
                    "plugin_zero_candidate_counts",
                    str(event.get("plugin_id") or "unknown"),
                )
        elif event_name == "strategy_entry_ready":
            detail["strategy_entry_ready_count"] += 1
        elif event_name == "strategy_reject":
            detail["strategy_reject_count"] += 1
            _increment_counter_field(
                detail,
                "strategy_reject_reason_counts",
                str(event.get("reason") or "unknown"),
            )
        elif event_name == "execution_filled":
            detail["execution_filled_count"] += 1
            filled_by_week[week] += 1
        elif event_name == "execution_failure":
            detail["execution_failure_count"] += 1
        elif event_name == "execution_skipped":
            detail["execution_skipped_count"] += 1
            if str(event.get("reason") or "").lower() == "dry_run":
                detail["dry_run_execution_skipped_count"] += 1
        elif event_name == "config_snapshot":
            detail["config_snapshot_count"] += 1
            snapshot = event.get("config") if isinstance(event.get("config"), dict) else {}
            drift = _config_snapshot_drift(snapshot, baseline)
            if drift:
                detail["config_drift_events_weekly"] += 1
                detail["config_drift_keys"] = sorted(
                    set(detail["config_drift_keys"]) | set(drift.keys())
                )

        detail["execution_attempt_count_weekly"] = (
            detail["execution_filled_count"] + detail["execution_failure_count"]
        )

    if filled_by_week:
        quality["entry_trade_source"] = "runtime_execution_filled_per_week_with_db_fallback"
        for week, count in filled_by_week.items():
            week_rows[week]["entry_trades"] = count
            week_rows[week]["_entry_from_runtime"] = True

    return quality


def _db_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(trades)").fetchall()
    return {str(row[1]) for row in rows}


def _select_trade_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = _db_columns(conn)
    if not columns:
        return []
    wanted = [
        "trade_id",
        "symbol",
        "side",
        "signal_type",
        "strategy_name",
        "entry_price",
        "exit_price",
        "total_size",
        "original_size",
        "entry_time",
        "exit_time",
        "pnl_usdt",
        "exit_reason",
    ]
    select_parts = [name if name in columns else f"NULL AS {name}" for name in wanted]
    query = f"SELECT {', '.join(select_parts)} FROM trades ORDER BY exit_time ASC"
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(query).fetchall()]


def _fee_estimate(row: dict[str, Any], *, fee_rate: float) -> float:
    size = _safe_float(row.get("total_size")) or _safe_float(row.get("original_size"))
    entry_price = _safe_float(row.get("entry_price"))
    exit_price = _safe_float(row.get("exit_price"))
    return (entry_price * size + exit_price * size) * fee_rate


def _realized_drawdown_pct(rows: list[dict[str, Any]], *, fee_rate: float, capital: float) -> float:
    if capital <= 0.0:
        return 0.0
    equity = capital
    peak = capital
    max_dd = 0.0
    ordered = sorted(rows, key=lambda row: str(row.get("exit_time") or ""))
    for row in ordered:
        net = _safe_float(row.get("pnl_usdt")) - _fee_estimate(row, fee_rate=fee_rate)
        equity += net
        peak = max(peak, equity)
        if peak > 0.0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return round(max_dd, 4)


def _apply_trade_rows(
    rows: list[dict[str, Any]],
    *,
    week_rows: dict[date, dict[str, Any]],
    fee_rate: float,
) -> dict[str, Any]:
    quality = {
        "performance_db_trade_count": len(rows),
        "performance_db_entry_outside_review_window": 0,
        "performance_db_exit_outside_review_window": 0,
    }

    for row in rows:
        entry_week = _week_key_in_review(row.get("entry_time"), week_rows)
        exit_week = _week_key_in_review(row.get("exit_time"), week_rows)

        if entry_week is None:
            quality["performance_db_entry_outside_review_window"] += 1
        elif not week_rows[entry_week].get("_entry_from_runtime"):
            week_rows[entry_week]["entry_trades"] += 1

        if exit_week is None:
            quality["performance_db_exit_outside_review_window"] += 1
            continue

        pnl = _safe_float(row.get("pnl_usdt"))
        fees = _fee_estimate(row, fee_rate=fee_rate)
        bucket = week_rows[exit_week]
        bucket["exit_trades"] += 1
        bucket["gross_pnl_usdt"] += pnl
        bucket["fees_est_usdt"] += fees
        bucket["net_after_fee_est_usdt"] += pnl - fees

    return quality


def _read_trade_rows(db_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quality = {
        "performance_db_path": str(db_path),
        "performance_db_exists": db_path.exists(),
    }
    if not db_path.exists():
        quality["performance_db_trade_count"] = 0
        return [], quality
    try:
        with sqlite3.connect(db_path) as conn:
            rows = _select_trade_rows(conn)
    except sqlite3.Error as exc:
        quality["performance_db_error"] = f"{type(exc).__name__}: {exc}"
        return [], quality
    quality["performance_db_trade_count"] = len(rows)
    return rows, quality


def _positions_payload(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, error = _read_json_file(path)
    quality = {
        "positions_path": str(path),
        "positions_file_exists": path.exists(),
    }
    if error:
        quality["positions_read_error"] = error if error != "missing" else None
        return {}, quality
    if not isinstance(payload, dict):
        quality["positions_read_error"] = "positions_json_not_object"
        return {}, quality
    if "schema_version" in payload:
        positions = payload.get("positions") or {}
    else:
        positions = payload
    return positions if isinstance(positions, dict) else {}, quality


def _unprotected_position_symbols(positions: dict[str, Any]) -> list[str]:
    symbols: list[str] = []
    for key, raw in positions.items():
        if not isinstance(raw, dict):
            symbols.append(str(key))
            continue
        symbol = str(raw.get("symbol") or key)
        side = str(raw.get("side") or "").upper()
        entry = _safe_float(raw.get("avg_entry") or raw.get("entry_price"))
        stop = _safe_float(raw.get("current_sl") or raw.get("stop_loss"))
        hard_stop_required = bool((raw.get("risk_plan") or {}).get("hard_stop_required"))
        stop_order_id = raw.get("stop_order_id")
        invalid_price_stop = (
            entry <= 0.0
            or stop <= 0.0
            or (side == "LONG" and stop >= entry)
            or (side == "SHORT" and stop <= entry)
            or side not in {"LONG", "SHORT"}
        )
        missing_required_hard_stop = hard_stop_required and not stop_order_id
        if invalid_price_stop or missing_required_hard_stop:
            symbols.append(symbol)
    return sorted(set(symbols))


def _apply_positions_snapshot(
    *,
    positions_path: Path,
    as_of_week: date,
    runtime_details: dict[date, dict[str, Any]],
) -> dict[str, Any]:
    positions, quality = _positions_payload(positions_path)
    if as_of_week in runtime_details:
        detail = runtime_details[as_of_week]
        unprotected = _unprotected_position_symbols(positions)
        detail["active_position_count_snapshot"] = len(positions)
        detail["unprotected_position_symbols"] = unprotected
        detail["unprotected_position_events_weekly"] = len(unprotected)
    quality["active_position_count_snapshot"] = len(positions)
    return quality


def _scanner_diagnostics(path: Path) -> dict[str, Any]:
    payload, error = _read_json_file(path)
    result = {
        "scanner_report_path": str(path),
        "scanner_report_exists": path.exists(),
        "scanner_report_error": None if error == "missing" else error,
        "diagnostic_only": True,
    }
    if not isinstance(payload, dict):
        return result
    result.update(
        {
            "scanner_contract_version": payload.get("scanner_contract_version"),
            "scan_time": payload.get("scan_time"),
            "runtime_selection_feeds_trading": payload.get("runtime_selection_feeds_trading"),
            "runtime_symbols": payload.get("runtime_symbols"),
            "symbol_count": len(payload.get("symbols") or {}),
        }
    )
    return result


def _finalize_week_rows(week_rows: dict[date, dict[str, Any]]) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    for week in sorted(week_rows):
        row = dict(week_rows[week])
        row.pop("_entry_from_runtime", None)
        for field in ("gross_pnl_usdt", "fees_est_usdt", "net_after_fee_est_usdt"):
            row[field] = round(float(row[field]), 4)
        finalized.append(row)
    return finalized


def _operational_inputs(runtime_details: dict[date, dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        detail["week_start"]: {
            "execution_attempt_count_weekly": _safe_int(detail["execution_attempt_count_weekly"]),
            "execution_failure_count_weekly": _safe_int(detail["execution_failure_count"]),
            "config_drift_events_weekly": _safe_int(detail["config_drift_events_weekly"]),
            "unprotected_position_events_weekly": _safe_int(
                detail["unprotected_position_events_weekly"]
            ),
        }
        for detail in runtime_details.values()
    }


def _latest_contract_grade_packet(packets: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (packet for packet in reversed(packets) if bool(packet["decision"]["contract_grade"])),
        None,
    )


def build_runtime_weekly_control_payload(
    *,
    events_path: Path | None = None,
    db_path: Path | None = None,
    positions_path: Path | None = None,
    scanner_report_path: Path | None = None,
    run_id: str | None = None,
    config_hash: str | None = None,
    config_profile: str = CONFIG_PROFILE_ALL,
    as_of: str | None = None,
    weeks: int = DEFAULT_WEEKS,
    completed_only: bool = False,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
) -> dict[str, Any]:
    """Build runtime weekly-control payload without mutating runtime state."""

    as_of_date = _parse_as_of(as_of)
    week_starts, review_start, review_end = _review_weeks(
        as_of=as_of_date,
        weeks=weeks,
        completed_only=completed_only,
    )
    week_rows_by_date = {week: _new_week_row(week) for week in week_starts}
    runtime_details_by_date = {week: _new_runtime_week_detail(week) for week in week_starts}

    resolved_events_path = events_path or (
        Path(str(getattr(Config, "STRATEGY_RUNTIME_OBSERVABILITY_DIR")))
        / str(getattr(Config, "STRATEGY_RUNTIME_OBSERVABILITY_JSONL"))
    )
    resolved_db_path = db_path or Path(str(getattr(Config, "DB_PATH", "performance.db")))
    resolved_positions_path = positions_path or Path(str(getattr(Config, "POSITIONS_JSON_PATH")))
    resolved_scanner_path = scanner_report_path or DEFAULT_SCANNER_REPORT

    events, event_quality = _read_runtime_events(resolved_events_path)
    baseline = _runtime_baseline()
    scoped_events, scope_quality = _scope_runtime_events(
        events,
        baseline=baseline,
        run_id=run_id,
        config_hash=config_hash,
        config_profile=config_profile,
    )
    event_apply_quality = _apply_runtime_events(
        scoped_events,
        week_rows=week_rows_by_date,
        runtime_details=runtime_details_by_date,
        baseline=baseline,
    )
    trade_rows, db_quality = _read_trade_rows(resolved_db_path)
    db_apply_quality = _apply_trade_rows(
        trade_rows,
        week_rows=week_rows_by_date,
        fee_rate=fee_rate,
    )
    positions_quality = _apply_positions_snapshot(
        positions_path=resolved_positions_path,
        as_of_week=_week_start_for_date(as_of_date if not completed_only else week_starts[-1]),
        runtime_details=runtime_details_by_date,
    )
    scanner_quality = _scanner_diagnostics(resolved_scanner_path)

    week_rows = _finalize_week_rows(week_rows_by_date)
    runtime_details = [runtime_details_by_date[week] for week in sorted(runtime_details_by_date)]
    portfolio_max_dd = _realized_drawdown_pct(
        trade_rows,
        fee_rate=fee_rate,
        capital=review_capital_usdt,
    )
    packets = build_weekly_control_packets(
        week_rows,
        review_start=review_start,
        review_end=review_end,
        review_capital_usdt=review_capital_usdt,
        portfolio_max_drawdown_pct_review_window=portfolio_max_dd,
        operational_by_week_start=_operational_inputs(runtime_details_by_date),
    )

    state_counts: dict[str, int] = {}
    contract_grade_state_counts: dict[str, int] = {}
    for packet in packets:
        state = str(packet["decision"]["state"])
        state_counts[state] = state_counts.get(state, 0) + 1
        if bool(packet["decision"]["contract_grade"]):
            contract_grade_state_counts[state] = contract_grade_state_counts.get(state, 0) + 1

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract": "weekly_profit_kpi_contract.v1",
        "source_type": "runtime_observability",
        "evidence_scope": {
            "run_id": run_id,
            "config_hash": config_hash,
            "config_profile": config_profile,
            "mode": scope_quality["scope_mode"],
            "hard_boundary": scope_quality["scope_hard_boundary"],
        },
        "review_window": {
            "week_boundary": "UTC ISO weeks anchored on Monday",
            "as_of_date": as_of_date.isoformat(),
            "completed_only": completed_only,
            "review_start": review_start,
            "review_end": review_end,
            "week_count": weeks,
        },
        "method": {
            "participation_basis": (
                "runtime execution_filled entries with performance.db closed-trade "
                "entry_time fallback"
            ),
            "economic_outcome_basis": "performance.db realized exits",
            "fee_rate_per_side_estimate": fee_rate,
            "review_capital_usdt": review_capital_usdt,
            "drawdown_basis": "closed-trade realized after-fee equity proxy",
            "scanner_diagnostics": "observe-only; never feeds runtime universe",
        },
        "runtime_baseline": baseline,
        "source_quality": {
            **event_quality,
            **scope_quality,
            **event_apply_quality,
            **db_quality,
            **db_apply_quality,
            **positions_quality,
            "scanner_diagnostics": scanner_quality,
        },
        "portfolio_reference": {
            "portfolio_max_drawdown_pct_review_window": portfolio_max_dd,
            "drawdown_basis": "closed_trade_realized_after_fee_proxy",
        },
        "packet_count": len(packets),
        "state_counts": dict(sorted(state_counts.items())),
        "contract_grade_state_counts": dict(sorted(contract_grade_state_counts.items())),
        "latest_packet": packets[-1] if packets else None,
        "latest_contract_grade_packet": _latest_contract_grade_packet(packets),
        "runtime_weekly_details": runtime_details,
        "packets": packets,
    }


def _runtime_detail_by_week(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {detail["week_start"]: detail for detail in payload.get("runtime_weekly_details", [])}


def csv_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    details = _runtime_detail_by_week(payload)
    rows: list[dict[str, Any]] = []
    for packet in payload.get("packets", []):
        kpis = packet["kpis"]
        decision = packet["decision"]
        detail = details.get(packet["week_start"], {})
        rows.append(
            {
                "week_start": packet["week_start"],
                "week_end": packet["week_end"],
                "state": decision["state"],
                "contract_grade": decision["contract_grade"],
                "entry_trades": packet["weekly_inputs"]["entry_trades"],
                "exit_trades": packet["weekly_inputs"]["exit_trades"],
                "gross_pnl_usdt": packet["weekly_inputs"]["gross_pnl_usdt"],
                "fees_est_usdt": packet["weekly_inputs"]["fees_est_usdt"],
                "net_after_fee_est_usdt": packet["weekly_inputs"]["net_after_fee_est_usdt"],
                "active_entry_week_ratio_8w": kpis["active_entry_week_ratio_8w"],
                "rolling_8w_entry_trade_count": kpis["rolling_8w_entry_trade_count"],
                "positive_week_ratio_all_8w_after_fee": kpis[
                    "positive_week_ratio_all_8w_after_fee"
                ],
                "positive_week_ratio_exit_active_8w_after_fee": kpis[
                    "positive_week_ratio_exit_active_8w_after_fee"
                ],
                "rolling_8w_net_after_fee_pnl": kpis["rolling_8w_net_after_fee_pnl"],
                "portfolio_max_drawdown_pct_review_window": kpis[
                    "portfolio_max_drawdown_pct_review_window"
                ],
                "strategy_entry_ready_count": detail.get("strategy_entry_ready_count", 0),
                "strategy_reject_count": detail.get("strategy_reject_count", 0),
                "execution_filled_count": detail.get("execution_filled_count", 0),
                "execution_failure_count": detail.get("execution_failure_count", 0),
                "dry_run_execution_skipped_count": detail.get(
                    "dry_run_execution_skipped_count", 0
                ),
                "config_drift_events_weekly": detail.get("config_drift_events_weekly", 0),
                "unprotected_position_events_weekly": detail.get(
                    "unprotected_position_events_weekly", 0
                ),
            }
        )
    return rows


def write_csv(payload: dict[str, Any], path: Path) -> None:
    rows = csv_rows(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_report(payload: dict[str, Any]) -> str:
    latest = payload.get("latest_packet")
    latest_contract = payload.get("latest_contract_grade_packet") or latest
    latest_decision = latest_contract.get("decision") if latest_contract else {"state": "none"}
    details = _runtime_detail_by_week(payload)
    quality = payload["source_quality"]
    scanner = quality.get("scanner_diagnostics") or {}

    lines = [
        "# Runtime Weekly Control Packet",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Status: `RUNTIME_WEEKLY_CONTROL_PACKET_GENERATED`",
        "",
        "## Executive Read",
        "",
        (
            f"Latest contract-grade state is `{latest_decision['state']}`. "
            "This packet is operational evidence; it does not authorize runtime-default "
            "changes, scanner universe activation, or strategy promotion."
        ),
        "",
        "## Sources",
        "",
        f"- Runtime observability JSONL: `{quality['runtime_events_path']}`",
        f"- Evidence scope: `{quality.get('scope_mode')}`",
        f"- performance.db: `{quality['performance_db_path']}`",
        f"- positions.json: `{quality['positions_path']}`",
        f"- runtime scanner report: `{scanner.get('scanner_report_path')}`",
        f"- scanner feeds runtime: `{scanner.get('runtime_selection_feeds_trading')}`",
        "",
        "## Source Quality",
        "",
        "| item | value |",
        "| --- | ---: |",
        f"| runtime events | {quality.get('runtime_event_count', 0)} |",
        f"| runtime events after scope | {quality.get('runtime_event_count_after_scope', 0)} |",
        f"| runtime events dropped by scope | {quality.get('runtime_event_count_dropped_by_scope', 0)} |",
        f"| selected config snapshots | {quality.get('selected_config_snapshot_count', 0)} |",
        f"| malformed runtime events | {quality.get('malformed_runtime_event_count', 0)} |",
        f"| runtime events outside review | {quality.get('runtime_events_outside_review_window', 0)} |",
        f"| performance db trades | {quality.get('performance_db_trade_count', 0)} |",
        f"| active positions snapshot | {quality.get('active_position_count_snapshot', 0)} |",
        f"| scanner symbols | {scanner.get('symbol_count', 0)} |",
        "",
        "## Latest Packet",
        "",
        "| KPI | value |",
        "| --- | ---: |",
    ]
    if latest_contract:
        kpis = latest_contract["kpis"]
        for key in (
            "active_entry_week_ratio_8w",
            "rolling_8w_entry_trade_count",
            "zero_entry_week_streak",
            "positive_week_ratio_all_8w_after_fee",
            "positive_week_ratio_exit_active_8w_after_fee",
            "rolling_4w_net_after_fee_pnl",
            "rolling_8w_net_after_fee_pnl",
            "worst_week_after_fee_pnl_pct_equity_8w",
            "portfolio_max_drawdown_pct_review_window",
            "execution_attempt_count_weekly",
            "execution_failure_count_weekly",
            "config_drift_events_weekly",
            "unprotected_position_events_weekly",
        ):
            lines.append(f"| `{key}` | {_fmt(kpis.get(key))} |")
    else:
        lines.append("| `none` | `none` |")

    lines.extend(
        [
            "",
            "## Weekly States",
            "",
            "| week_start | state | contract_grade | entries | exits | net after fee | ready | rejects | fills | failures | dry-run skips | drift | unprotected | trigger/note |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for packet in payload.get("packets", []):
        decision = packet["decision"]
        detail = details.get(packet["week_start"], {})
        trigger = ", ".join(
            decision["pause_triggers"]
            or decision["reopen_triggers"]
            or decision["investigate_triggers"]
            or decision["notes"]
            or ["none"]
        )
        lines.append(
            "| "
            f"`{packet['week_start']}` | `{decision['state']}` | "
            f"{decision['contract_grade']} | "
            f"{packet['weekly_inputs']['entry_trades']} | "
            f"{packet['weekly_inputs']['exit_trades']} | "
            f"{_fmt(packet['weekly_inputs']['net_after_fee_est_usdt'])} | "
            f"{detail.get('strategy_entry_ready_count', 0)} | "
            f"{detail.get('strategy_reject_count', 0)} | "
            f"{detail.get('execution_filled_count', 0)} | "
            f"{detail.get('execution_failure_count', 0)} | "
            f"{detail.get('dry_run_execution_skipped_count', 0)} | "
            f"{detail.get('config_drift_events_weekly', 0)} | "
            f"{detail.get('unprotected_position_events_weekly', 0)} | "
            f"{trigger} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- Dry-run `execution_skipped: dry_run` counts as opportunity handoff, not a submitted execution attempt.",
            "- `performance.db` realized exits are the economic source; missing DB means economics are observe-only.",
            "- Runtime scanner data is diagnostic only and does not feed `StrategyRuntime` symbol selection.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_runtime_weekly_control_packet(
    *,
    json_path: Path = DEFAULT_JSON,
    csv_path: Path = DEFAULT_CSV,
    report_path: Path = DEFAULT_REPORT,
    **kwargs: Any,
) -> dict[str, Any]:
    payload = build_runtime_weekly_control_payload(**kwargs)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_csv(payload, csv_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build runtime weekly-profit control packets from local evidence."
    )
    parser.add_argument("--events", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--positions", type=Path, default=None)
    parser.add_argument("--scanner-report", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--config-hash", default=None)
    parser.add_argument(
        "--config-profile",
        choices=CONFIG_PROFILE_CHOICES,
        default=CONFIG_PROFILE_ALL,
    )
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--weeks", type=int, default=DEFAULT_WEEKS)
    parser.add_argument("--completed-only", action="store_true")
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital", type=float, default=DEFAULT_REVIEW_CAPITAL_USDT)
    args = parser.parse_args()

    write_runtime_weekly_control_packet(
        events_path=args.events,
        db_path=args.db,
        positions_path=args.positions,
        scanner_report_path=args.scanner_report,
        run_id=args.run_id,
        config_hash=args.config_hash,
        config_profile=args.config_profile,
        json_path=args.json_out,
        csv_path=args.csv_out,
        report_path=args.report_out,
        as_of=args.as_of,
        weeks=args.weeks,
        completed_only=args.completed_only,
        fee_rate=args.fee_rate,
        review_capital_usdt=args.review_capital,
    )


if __name__ == "__main__":
    main()
