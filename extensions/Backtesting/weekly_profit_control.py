"""Weekly-profit KPI contract evaluator.

The evaluator turns weekly trade/economics rows into machine-readable control
packets. It deliberately keeps decision rules separate from report rendering so
Phase 3 automation can test the contract directly.
"""

from __future__ import annotations

from datetime import date
from typing import Any


SCHEMA = "strategy_plugin_weekly_profit_control_packet.v1"
CONTRACT = "weekly_profit_kpi_contract.v1"
STATE_CONTINUE = "continue"
STATE_INVESTIGATE = "investigate"
STATE_PAUSE = "pause"
STATE_REOPEN_RESEARCH = "reopen_research"


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


def _round4(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0.0:
        return None
    return round(numerator / denominator * 100.0, 4)


def _longest_streak(values: list[bool]) -> int:
    current = 0
    longest = 0
    for value in values:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _zero_entry_streak(week_rows: list[dict[str, Any]], end_index: int) -> int:
    current = 0
    for row in reversed(week_rows[: end_index + 1]):
        if _safe_int(row.get("entry_trades")) == 0:
            current += 1
        else:
            break
    return current


def _week_is_partial(row: dict[str, Any], *, review_start: str, review_end: str) -> bool:
    week_start = date.fromisoformat(str(row["week_start"]))
    week_end = date.fromisoformat(str(row["week_end"]))
    return week_start < date.fromisoformat(review_start) or week_end > date.fromisoformat(review_end)


def classify_execution_integrity(
    *,
    execution_attempt_count_weekly: int = 0,
    execution_failure_count_weekly: int = 0,
) -> dict[str, Any]:
    """Classify execution integrity using the Phase 2 composite rule."""

    attempts = max(0, int(execution_attempt_count_weekly))
    failures = max(0, int(execution_failure_count_weekly))
    failure_rate = _pct(failures, attempts)
    reasons: list[str] = []

    if attempts == 0:
        reasons.append("execution_rate_not_applicable_no_attempts")
        status = STATE_CONTINUE if failures == 0 else STATE_INVESTIGATE
    elif failures == 0:
        reasons.append("execution_clean")
        status = STATE_CONTINUE
    elif attempts < 20 and failures >= 2:
        reasons.append("execution_repeated_sparse_failures")
        status = STATE_PAUSE
    elif attempts >= 20 and failures >= 2 and failure_rate is not None and failure_rate > 3.0:
        reasons.append("execution_denominator_qualified_rate_breach")
        status = STATE_PAUSE
    else:
        reasons.append("execution_failure_watch")
        status = STATE_INVESTIGATE

    return {
        "execution_attempt_count_weekly": attempts,
        "execution_failure_count_weekly": failures,
        "execution_failure_rate_weekly": failure_rate,
        "execution_failure_rate_unit": "percent",
        "status": status,
        "reasons": reasons,
    }


def _window_kpis(
    week_rows: list[dict[str, Any]],
    *,
    end_index: int,
    review_start: str,
    review_end: str,
    review_capital_usdt: float,
    portfolio_max_drawdown_pct_review_window: float,
) -> dict[str, Any]:
    rolling_8w = week_rows[max(0, end_index - 7) : end_index + 1]
    rolling_4w = week_rows[max(0, end_index - 3) : end_index + 1]

    entry_counts = [_safe_int(row.get("entry_trades")) for row in rolling_8w]
    exit_counts = [_safe_int(row.get("exit_trades")) for row in rolling_8w]
    after_fee_pnls = [_safe_float(row.get("net_after_fee_est_usdt")) for row in rolling_8w]
    rolling_4w_pnl = sum(_safe_float(row.get("net_after_fee_est_usdt")) for row in rolling_4w)

    active_entry_weeks = sum(count > 0 for count in entry_counts)
    active_exit_weeks = sum(count > 0 for count in exit_counts)
    after_fee_positive_weeks = sum(pnl > 0.0 for pnl in after_fee_pnls)

    rolling_8w_entry_trade_count = sum(entry_counts)
    rolling_8w_realized_exit_count = sum(exit_counts)
    active_entry_week_ratio_8w = _ratio(active_entry_weeks, len(rolling_8w))
    positive_all = _ratio(after_fee_positive_weeks, len(rolling_8w))
    positive_exit_active = _ratio(after_fee_positive_weeks, active_exit_weeks)
    rolling_8w_net = round(sum(after_fee_pnls), 4)
    worst_week = min(after_fee_pnls) if after_fee_pnls else 0.0
    worst_week_pct = _pct(worst_week, review_capital_usdt)

    participation_not_dominant = (
        active_entry_week_ratio_8w >= 0.5 and rolling_8w_entry_trade_count >= 6
    )
    realized_sample_ready = rolling_8w_realized_exit_count >= 8 or active_exit_weeks >= 4
    meets_economic_sample_floor = participation_not_dominant and realized_sample_ready

    return {
        "rolling_4w_completed_week_count": len(rolling_4w),
        "rolling_4w_complete": len(rolling_4w) == 4,
        "rolling_4w_has_partial_review_week": any(
            _week_is_partial(row, review_start=review_start, review_end=review_end)
            for row in rolling_4w
        ),
        "rolling_4w_net_after_fee_pnl": round(rolling_4w_pnl, 4),
        "rolling_8w_completed_week_count": len(rolling_8w),
        "rolling_8w_complete": len(rolling_8w) == 8,
        "rolling_8w_has_partial_review_week": any(
            _week_is_partial(row, review_start=review_start, review_end=review_end)
            for row in rolling_8w
        ),
        "active_entry_week_ratio_8w": active_entry_week_ratio_8w,
        "rolling_8w_entry_trade_count": rolling_8w_entry_trade_count,
        "zero_entry_week_streak": _zero_entry_streak(week_rows, end_index),
        "positive_week_ratio_all_8w_after_fee": positive_all,
        "positive_week_ratio_exit_active_8w_after_fee": positive_exit_active,
        "rolling_8w_net_after_fee_pnl": rolling_8w_net,
        "rolling_8w_realized_exit_count": rolling_8w_realized_exit_count,
        "exit_active_week_count_8w": active_exit_weeks,
        "worst_week_after_fee_pnl_usdt_8w": round(worst_week, 4),
        "worst_week_after_fee_pnl_pct_equity_8w": worst_week_pct,
        "max_consecutive_losing_weeks_after_fee_8w": _longest_streak(
            [pnl < 0.0 for pnl in after_fee_pnls]
        ),
        "portfolio_max_drawdown_pct_review_window": round(
            float(portfolio_max_drawdown_pct_review_window), 4
        ),
        "participation_not_dominant": participation_not_dominant,
        "realized_sample_ready": realized_sample_ready,
        "meets_economic_sample_floor": meets_economic_sample_floor,
    }


def evaluate_weekly_packet(kpis: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one weekly KPI snapshot into the contract state."""

    pause_triggers: list[str] = []
    reopen_triggers: list[str] = []
    investigate_triggers: list[str] = []
    notes: list[str] = []

    execution_status = str(kpis.get("execution_integrity_status") or STATE_CONTINUE)
    if execution_status == STATE_PAUSE:
        pause_triggers.append("execution_integrity_weekly")
    elif execution_status == STATE_INVESTIGATE:
        investigate_triggers.append("execution_integrity_weekly")

    if _safe_int(kpis.get("config_drift_events_weekly")) >= 1:
        pause_triggers.append("config_drift_events_weekly")
    if _safe_int(kpis.get("unprotected_position_events_weekly")) >= 1:
        pause_triggers.append("unprotected_position_events_weekly")

    worst_week_pct = kpis.get("worst_week_after_fee_pnl_pct_equity_8w")
    if worst_week_pct is not None and float(worst_week_pct) < -7.0:
        pause_triggers.append("worst_week_after_fee_pnl_pct_equity_8w")

    drawdown_pct = _safe_float(kpis.get("portfolio_max_drawdown_pct_review_window"))
    if drawdown_pct > 8.0:
        pause_triggers.append("portfolio_max_drawdown_pct_review_window")
    elif drawdown_pct > 6.0:
        investigate_triggers.append("portfolio_max_drawdown_pct_review_window")

    if worst_week_pct is not None and -7.0 <= float(worst_week_pct) <= -5.0:
        investigate_triggers.append("worst_week_after_fee_pnl_pct_equity_8w")

    rolling_8w_complete = bool(kpis.get("rolling_8w_complete"))
    rolling_4w_complete = bool(kpis.get("rolling_4w_complete"))
    rolling_8w_has_partial = bool(kpis.get("rolling_8w_has_partial_review_week"))
    rolling_4w_has_partial = bool(kpis.get("rolling_4w_has_partial_review_week"))
    rolling_8w_decision_ready = rolling_8w_complete and not rolling_8w_has_partial
    rolling_4w_warning_ready = rolling_4w_complete and not rolling_4w_has_partial

    if not rolling_8w_complete:
        notes.append("rolling_8w_not_complete_observe_only")
    elif rolling_8w_has_partial:
        notes.append("rolling_8w_contains_partial_review_week_observe_only")

    operational_clean = execution_status == STATE_CONTINUE and not pause_triggers

    if operational_clean and rolling_8w_decision_ready:
        if _safe_float(kpis.get("active_entry_week_ratio_8w")) < 0.5:
            reopen_triggers.append("active_entry_week_ratio_8w")
        if _safe_int(kpis.get("rolling_8w_entry_trade_count")) <= 5:
            reopen_triggers.append("rolling_8w_entry_trade_count")
        if _safe_int(kpis.get("zero_entry_week_streak")) >= 3:
            reopen_triggers.append("zero_entry_week_streak")

        if bool(kpis.get("participation_not_dominant")):
            if _safe_float(kpis.get("positive_week_ratio_all_8w_after_fee")) < 0.375:
                reopen_triggers.append("positive_week_ratio_all_8w_after_fee")
            if _safe_float(kpis.get("positive_week_ratio_exit_active_8w_after_fee")) < 0.5:
                reopen_triggers.append("positive_week_ratio_exit_active_8w_after_fee")
            if (
                _safe_float(kpis.get("rolling_8w_net_after_fee_pnl")) <= 0.0
                and bool(kpis.get("meets_economic_sample_floor"))
            ):
                reopen_triggers.append("rolling_8w_net_after_fee_pnl")
            if _safe_int(kpis.get("max_consecutive_losing_weeks_after_fee_8w")) >= 3:
                reopen_triggers.append("max_consecutive_losing_weeks_after_fee_8w")

    if not pause_triggers and not reopen_triggers and rolling_8w_decision_ready:
        active_ratio = _safe_float(kpis.get("active_entry_week_ratio_8w"))
        entry_count = _safe_int(kpis.get("rolling_8w_entry_trade_count"))
        zero_streak = _safe_int(kpis.get("zero_entry_week_streak"))
        positive_all = _safe_float(kpis.get("positive_week_ratio_all_8w_after_fee"))
        positive_active = _safe_float(kpis.get("positive_week_ratio_exit_active_8w_after_fee"))
        losing_streak = _safe_int(kpis.get("max_consecutive_losing_weeks_after_fee_8w"))

        if 0.5 <= active_ratio < 0.625:
            investigate_triggers.append("active_entry_week_ratio_8w")
        if 6 <= entry_count <= 7:
            investigate_triggers.append("rolling_8w_entry_trade_count")
        if zero_streak == 2:
            investigate_triggers.append("zero_entry_week_streak")
        if 0.375 <= positive_all < 0.5:
            investigate_triggers.append("positive_week_ratio_all_8w_after_fee")
        if bool(kpis.get("participation_not_dominant")) and 0.5 <= positive_active < 0.6:
            investigate_triggers.append("positive_week_ratio_exit_active_8w_after_fee")
        if _safe_float(kpis.get("rolling_8w_net_after_fee_pnl")) <= 0.0:
            investigate_triggers.append("rolling_8w_net_after_fee_pnl")
        if losing_streak == 2:
            investigate_triggers.append("max_consecutive_losing_weeks_after_fee_8w")

    if not pause_triggers and not reopen_triggers and rolling_4w_warning_ready:
        if _safe_float(kpis.get("rolling_4w_net_after_fee_pnl")) <= 0.0:
            investigate_triggers.append("rolling_4w_net_after_fee_pnl")

    if pause_triggers:
        state = STATE_PAUSE
    elif reopen_triggers:
        state = STATE_REOPEN_RESEARCH
    elif investigate_triggers:
        state = STATE_INVESTIGATE
    else:
        state = STATE_CONTINUE

    return {
        "state": state,
        "contract_grade": rolling_8w_decision_ready or bool(pause_triggers),
        "pause_triggers": sorted(set(pause_triggers)),
        "reopen_triggers": sorted(set(reopen_triggers)),
        "investigate_triggers": sorted(set(investigate_triggers)),
        "notes": notes,
    }


def build_weekly_control_packets(
    week_rows: list[dict[str, Any]],
    *,
    review_start: str,
    review_end: str,
    review_capital_usdt: float,
    portfolio_max_drawdown_pct_review_window: float,
    operational_by_week_start: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build one control packet per weekly row."""

    packets: list[dict[str, Any]] = []
    operational_by_week_start = operational_by_week_start or {}

    for idx, row in enumerate(week_rows):
        week_start = str(row["week_start"])
        operational = operational_by_week_start.get(week_start, {})
        execution = classify_execution_integrity(
            execution_attempt_count_weekly=_safe_int(
                operational.get("execution_attempt_count_weekly")
            ),
            execution_failure_count_weekly=_safe_int(
                operational.get("execution_failure_count_weekly")
            ),
        )
        kpis = _window_kpis(
            week_rows,
            end_index=idx,
            review_start=review_start,
            review_end=review_end,
            review_capital_usdt=review_capital_usdt,
            portfolio_max_drawdown_pct_review_window=portfolio_max_drawdown_pct_review_window,
        )
        kpis.update(
            {
                "execution_attempt_count_weekly": execution[
                    "execution_attempt_count_weekly"
                ],
                "execution_failure_count_weekly": execution[
                    "execution_failure_count_weekly"
                ],
                "execution_failure_rate_weekly": execution[
                    "execution_failure_rate_weekly"
                ],
                "execution_failure_rate_unit": execution["execution_failure_rate_unit"],
                "execution_integrity_status": execution["status"],
                "config_drift_events_weekly": _safe_int(
                    operational.get("config_drift_events_weekly")
                ),
                "unprotected_position_events_weekly": _safe_int(
                    operational.get("unprotected_position_events_weekly")
                ),
            }
        )
        decision = evaluate_weekly_packet(kpis)
        packets.append(
            {
                "schema": SCHEMA,
                "contract": CONTRACT,
                "week_start": week_start,
                "week_end": str(row["week_end"]),
                "is_partial_review_week": _week_is_partial(
                    row, review_start=review_start, review_end=review_end
                ),
                "weekly_inputs": {
                    "entry_trades": _safe_int(row.get("entry_trades")),
                    "exit_trades": _safe_int(row.get("exit_trades")),
                    "gross_pnl_usdt": _round4(_safe_float(row.get("gross_pnl_usdt"))),
                    "fees_est_usdt": _round4(_safe_float(row.get("fees_est_usdt"))),
                    "net_after_fee_est_usdt": _round4(
                        _safe_float(row.get("net_after_fee_est_usdt"))
                    ),
                },
                "kpis": kpis,
                "execution_integrity": execution,
                "decision": decision,
            }
        )

    return packets
