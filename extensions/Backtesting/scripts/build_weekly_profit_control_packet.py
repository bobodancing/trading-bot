"""Build Phase 3 weekly-profit control packets from promoted portfolio artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = SCRIPT_ROOT.parents[0]
REPO_ROOT = BACKTEST_ROOT.parents[1]
for path in (SCRIPT_ROOT, BACKTEST_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from analyze_promoted_three_leg_weekly_feasibility import (  # noqa: E402
    DEFAULT_FEE_RATE,
    PRIMARY_MATRIX,
    PRIMARY_WINDOW,
    SOURCE_SUMMARY,
    TARGET_VARIANT,
    _analysis_payload,
    _fmt,
    _read_json,
)
from weekly_profit_control import build_weekly_control_packets  # noqa: E402


DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_control_packets.json"
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase3_control_packet.md"
DEFAULT_REVIEW_CAPITAL_USDT = 10000.0
CONTRACT_PATH = REPO_ROOT / "plans" / "weekly_profit_kpi_contract.md"


def _operational_inputs_for_weeks(
    weeks: list[dict[str, Any]],
    *,
    execution_attempt_count_weekly: int,
    execution_failure_count_weekly: int,
    config_drift_events_weekly: int,
    unprotected_position_events_weekly: int,
) -> dict[str, dict[str, int]]:
    return {
        str(row["week_start"]): {
            "execution_attempt_count_weekly": execution_attempt_count_weekly,
            "execution_failure_count_weekly": execution_failure_count_weekly,
            "config_drift_events_weekly": config_drift_events_weekly,
            "unprotected_position_events_weekly": unprotected_position_events_weekly,
        }
        for row in weeks
    }


def build_weekly_profit_control_payload(
    *,
    source_path: Path = SOURCE_SUMMARY,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    execution_attempt_count_weekly: int = 0,
    execution_failure_count_weekly: int = 0,
    config_drift_events_weekly: int = 0,
    unprotected_position_events_weekly: int = 0,
) -> dict[str, Any]:
    source = _read_json(source_path)
    feasibility = _analysis_payload(source, source_path=source_path, fee_rate=fee_rate)
    primary = feasibility["primary_window"]
    portfolio_ref = dict(primary.get("portfolio_reference") or {})
    portfolio_max_drawdown = float(portfolio_ref.get("max_dd_pct") or 0.0)
    operational_by_week = _operational_inputs_for_weeks(
        primary["weeks"],
        execution_attempt_count_weekly=execution_attempt_count_weekly,
        execution_failure_count_weekly=execution_failure_count_weekly,
        config_drift_events_weekly=config_drift_events_weekly,
        unprotected_position_events_weekly=unprotected_position_events_weekly,
    )
    packets = build_weekly_control_packets(
        primary["weeks"],
        review_start=str(primary["start"]),
        review_end=str(primary["end"]),
        review_capital_usdt=review_capital_usdt,
        portfolio_max_drawdown_pct_review_window=portfolio_max_drawdown,
        operational_by_week_start=operational_by_week,
    )

    latest_packet = packets[-1] if packets else None
    state_counts: dict[str, int] = {}
    contract_grade_state_counts: dict[str, int] = {}
    for packet in packets:
        state = str(packet["decision"]["state"])
        state_counts[state] = state_counts.get(state, 0) + 1
        if bool(packet["decision"]["contract_grade"]):
            contract_grade_state_counts[state] = contract_grade_state_counts.get(state, 0) + 1
    latest_contract_grade_packet = next(
        (
            packet
            for packet in reversed(packets)
            if bool(packet["decision"]["contract_grade"])
        ),
        None,
    )

    return {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "version": "weekly_profit_kpi_contract.v1",
            "path": str(CONTRACT_PATH),
        },
        "source": {
            "summary": str(source_path),
            "source_generated_at": source.get("generated_at"),
            "variant": TARGET_VARIANT,
            "primary_window_key": f"{PRIMARY_MATRIX}/{PRIMARY_WINDOW}",
            "primary_window_start": primary["start"],
            "primary_window_end": primary["end"],
            "trade_artifact": primary["artifacts"]["trades"],
        },
        "method": {
            "week_boundary": "UTC ISO weeks anchored on Monday",
            "participation_basis": "entry week",
            "economic_outcome_basis": "exit week realized PnL",
            "rolling_4w": "warning signal",
            "rolling_8w": "contract-grade decision basis when complete",
            "fee_rate_per_side_estimate": fee_rate,
            "review_capital_usdt": review_capital_usdt,
            "execution_failure_rate_unit": "percent",
            "operational_input_source": (
                "CLI-supplied uniform weekly inputs; defaults are zero for ignored "
                "backtest artifacts and must be replaced by runtime observability for live packets."
            ),
        },
        "portfolio_reference": portfolio_ref,
        "packet_count": len(packets),
        "state_counts": dict(sorted(state_counts.items())),
        "contract_grade_state_counts": dict(sorted(contract_grade_state_counts.items())),
        "latest_packet": latest_packet,
        "latest_contract_grade_packet": latest_contract_grade_packet,
        "packets": packets,
    }


def _table_row(packet: dict[str, Any]) -> str:
    kpis = packet["kpis"]
    decision = packet["decision"]
    return (
        f"| `{packet['week_start']}` | `{decision['state']}` | "
        f"{str(decision['contract_grade'])} | "
        f"{_fmt(kpis['active_entry_week_ratio_8w'])} | "
        f"{kpis['rolling_8w_entry_trade_count']} | "
        f"{kpis['zero_entry_week_streak']} | "
        f"{_fmt(kpis['positive_week_ratio_all_8w_after_fee'])} | "
        f"{_fmt(kpis['positive_week_ratio_exit_active_8w_after_fee'])} | "
        f"{_fmt(kpis['rolling_8w_net_after_fee_pnl'])} | "
        f"{_fmt(kpis['worst_week_after_fee_pnl_pct_equity_8w']) if kpis['worst_week_after_fee_pnl_pct_equity_8w'] is not None else 'null'} | "
        f"{', '.join(decision['pause_triggers'] or decision['reopen_triggers'] or decision['investigate_triggers'] or decision['notes'] or ['none'])} |"
    )


def _latest_kpi_rows(packet: dict[str, Any]) -> list[str]:
    kpis = packet["kpis"]
    keys = [
        "rolling_8w_complete",
        "rolling_8w_has_partial_review_week",
        "active_entry_week_ratio_8w",
        "rolling_8w_entry_trade_count",
        "zero_entry_week_streak",
        "positive_week_ratio_all_8w_after_fee",
        "positive_week_ratio_exit_active_8w_after_fee",
        "rolling_4w_net_after_fee_pnl",
        "rolling_8w_net_after_fee_pnl",
        "rolling_8w_realized_exit_count",
        "exit_active_week_count_8w",
        "meets_economic_sample_floor",
        "worst_week_after_fee_pnl_pct_equity_8w",
        "max_consecutive_losing_weeks_after_fee_8w",
        "portfolio_max_drawdown_pct_review_window",
        "execution_attempt_count_weekly",
        "execution_failure_count_weekly",
        "execution_failure_rate_weekly",
        "config_drift_events_weekly",
        "unprotected_position_events_weekly",
    ]
    rows = []
    for key in keys:
        value = kpis.get(key)
        if isinstance(value, float):
            rendered = _fmt(value)
        elif value is None:
            rendered = "`null`"
        else:
            rendered = f"`{value}`" if isinstance(value, bool) else str(value)
        rows.append(f"| `{key}` | {rendered} |")
    return rows


def render_report(payload: dict[str, Any]) -> str:
    latest = payload["latest_packet"]
    latest_contract_grade = payload["latest_contract_grade_packet"]
    latest_decision_packet = latest_contract_grade or latest
    latest_decision = (
        latest_decision_packet["decision"]
        if latest_decision_packet
        else {
            "state": "none",
            "contract_grade": False,
            "pause_triggers": [],
            "reopen_triggers": [],
            "investigate_triggers": [],
            "notes": ["no_packets"],
        }
    )
    packets = payload["packets"]
    generated_date = datetime.now(timezone.utc).date().isoformat()
    latest_raw_note = ""
    if latest and latest_contract_grade and latest["week_start"] != latest_contract_grade["week_start"]:
        latest_raw_note = (
            f" Latest raw packet `{latest['week_start']}` is partial-window "
            "observe-only; the executive read uses the latest contract-grade packet."
        )

    lines = [
        "# Weekly Profit Phase 3 Control Packet",
        "",
        f"Date: {generated_date}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `PHASE_3_WEEKLY_CONTROL_PACKET_IMPLEMENTED`",
        "",
        "## Executive Read",
        "",
        (
            f"Latest contract-grade packet state is `{latest_decision['state']}`. "
            "The evaluator is now machine-readable and follows the Phase 2 KPI contract precedence: "
            "`pause > reopen_research > investigate > continue`."
            f"{latest_raw_note}"
        ),
        "",
        "This is a control-packet implementation over existing backtest artifacts. It does not alter runtime defaults, scanner activation, strategy thresholds, or credentials.",
        "",
        "## Source",
        "",
        f"- Contract: `{payload['contract']['path']}`",
        f"- Source summary: `{payload['source']['summary']}`",
        f"- Primary window: `{payload['source']['primary_window_key']}`",
        f"- Review dates: `{payload['source']['primary_window_start']}..{payload['source']['primary_window_end']}`",
        f"- Review capital: `{payload['method']['review_capital_usdt']}` USDT",
        f"- Fee estimate: `{payload['method']['fee_rate_per_side_estimate']}` per side",
        (
            "- Operational input source: backtest-control defaults. Live/dry-run packets "
            "must replace these with runtime observability."
        ),
        "",
        "## Latest Contract-Grade Packet KPIs",
        "",
        "| KPI | value |",
        "| --- | ---: |",
        *(
            _latest_kpi_rows(latest_decision_packet)
            if latest_decision_packet
            else ["| `none` | `none` |"]
        ),
        "",
        "## Latest Contract-Grade Decision",
        "",
        "| item | value |",
        "| --- | --- |",
        f"| state | `{latest_decision['state']}` |",
        f"| week_start | `{latest_decision_packet['week_start'] if latest_decision_packet else 'none'}` |",
        f"| contract grade | `{latest_decision['contract_grade']}` |",
        f"| pause triggers | `{', '.join(latest_decision['pause_triggers']) or 'none'}` |",
        f"| reopen triggers | `{', '.join(latest_decision['reopen_triggers']) or 'none'}` |",
        f"| investigate triggers | `{', '.join(latest_decision['investigate_triggers']) or 'none'}` |",
        f"| notes | `{', '.join(latest_decision['notes']) or 'none'}` |",
        "",
        "## Weekly Packet States",
        "",
        "| week_start | state | contract_grade | active-entry ratio 8w | entries 8w | zero-entry streak | positive all 8w | positive active-exit 8w | net 8w | worst week pct equity 8w | primary trigger/note |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        *[_table_row(packet) for packet in packets],
        "",
        "## Machine-Readable Artifact",
        "",
        f"- JSON packet series: `{DEFAULT_JSON}`",
        "",
        "## Phase 4 Readiness",
        "",
        "- If live/dry-run packet data confirms the same participation gap, open one bounded frequency-complement trigger review.",
        "- Do not loosen existing strategy thresholds just to create volume.",
        "- Do not promote new runtime defaults from this packet alone.",
    ]
    return "\n".join(lines) + "\n"


def write_weekly_profit_control_packet(
    *,
    source_path: Path = SOURCE_SUMMARY,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    execution_attempt_count_weekly: int = 0,
    execution_failure_count_weekly: int = 0,
    config_drift_events_weekly: int = 0,
    unprotected_position_events_weekly: int = 0,
) -> dict[str, Any]:
    payload = build_weekly_profit_control_payload(
        source_path=source_path,
        fee_rate=fee_rate,
        review_capital_usdt=review_capital_usdt,
        execution_attempt_count_weekly=execution_attempt_count_weekly,
        execution_failure_count_weekly=execution_failure_count_weekly,
        config_drift_events_weekly=config_drift_events_weekly,
        unprotected_position_events_weekly=unprotected_position_events_weekly,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(render_report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build weekly-profit Phase 3 control packets from existing artifacts."
    )
    parser.add_argument("--source", type=Path, default=SOURCE_SUMMARY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital", type=float, default=DEFAULT_REVIEW_CAPITAL_USDT)
    parser.add_argument("--execution-attempts", type=int, default=0)
    parser.add_argument("--execution-failures", type=int, default=0)
    parser.add_argument("--config-drift-events", type=int, default=0)
    parser.add_argument("--unprotected-position-events", type=int, default=0)
    args = parser.parse_args()
    write_weekly_profit_control_packet(
        source_path=args.source,
        json_path=args.json_out,
        report_path=args.report_out,
        fee_rate=args.fee_rate,
        review_capital_usdt=args.review_capital,
        execution_attempt_count_weekly=args.execution_attempts,
        execution_failure_count_weekly=args.execution_failures,
        config_drift_events_weekly=args.config_drift_events,
        unprotected_position_events_weekly=args.unprotected_position_events,
    )


if __name__ == "__main__":
    main()
