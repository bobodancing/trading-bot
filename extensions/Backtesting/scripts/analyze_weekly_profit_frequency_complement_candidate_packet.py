"""Build weekly packet evaluation for A+B plus the Phase 4A recovery candidate."""

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
    _build_week_rows,
    _fmt,
    _read_csv,
    _read_json,
    _repo_path,
    _summarize_week_rows,
)
from build_weekly_profit_control_packet import DEFAULT_REVIEW_CAPITAL_USDT  # noqa: E402
from weekly_profit_control import build_weekly_control_packets  # noqa: E402
from extensions.Backtesting.scripts.run_portfolio_ab_frequency_complement_candidate import (  # noqa: E402
    CANDIDATE,
    DEFAULT_SUMMARY,
    DEFAULT_WINDOW,
    SLOT_A_LONG,
    SLOT_B_LONG,
    SLOT_B_SHORT,
    VARIANT,
)


DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_frequency_complement_candidate"
    / "weekly_profit_frequency_complement_candidate_packets.json"
)
DEFAULT_REPORT = (
    REPO_ROOT / "reports" / "weekly_profit_phase4b_frequency_complement_candidate_packet.md"
)
BASELINE_PACKET_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_control_packets.json"
)

SLOT_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
    CANDIDATE: "BTC Recovery-Band Candidate",
}


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


def _latest_contract_grade(payload: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            packet
            for packet in reversed(payload.get("packets", []))
            if bool(packet.get("decision", {}).get("contract_grade"))
        ),
        None,
    )


def _comparison(
    candidate_payload: dict[str, Any],
    baseline_packet_path: Path,
) -> dict[str, Any]:
    baseline = _read_json(baseline_packet_path) if baseline_packet_path.exists() else {}
    candidate_packet = candidate_payload.get("latest_contract_grade_packet")
    baseline_packet = baseline.get("latest_contract_grade_packet")
    if not candidate_packet or not baseline_packet:
        return {
            "baseline_available": bool(baseline),
            "contract_grade_comparable": False,
        }

    candidate_kpis = candidate_packet["kpis"]
    baseline_kpis = baseline_packet["kpis"]
    return {
        "baseline_available": True,
        "contract_grade_comparable": True,
        "baseline_week_start": baseline_packet["week_start"],
        "candidate_week_start": candidate_packet["week_start"],
        "baseline_state": baseline_packet["decision"]["state"],
        "candidate_state": candidate_packet["decision"]["state"],
        "active_entry_week_ratio_8w_delta": round(
            float(candidate_kpis["active_entry_week_ratio_8w"])
            - float(baseline_kpis["active_entry_week_ratio_8w"]),
            4,
        ),
        "rolling_8w_entry_trade_count_delta": int(
            candidate_kpis["rolling_8w_entry_trade_count"]
        )
        - int(baseline_kpis["rolling_8w_entry_trade_count"]),
        "positive_week_ratio_all_8w_after_fee_delta": round(
            float(candidate_kpis["positive_week_ratio_all_8w_after_fee"])
            - float(baseline_kpis["positive_week_ratio_all_8w_after_fee"]),
            4,
        ),
        "rolling_8w_net_after_fee_pnl_delta": round(
            float(candidate_kpis["rolling_8w_net_after_fee_pnl"])
            - float(baseline_kpis["rolling_8w_net_after_fee_pnl"]),
            4,
        ),
        "candidate_pause_triggers": list(candidate_packet["decision"]["pause_triggers"]),
        "candidate_reopen_triggers": list(candidate_packet["decision"]["reopen_triggers"]),
        "candidate_investigate_triggers": list(candidate_packet["decision"]["investigate_triggers"]),
    }


def build_candidate_packet_payload(
    *,
    source_path: Path = DEFAULT_SUMMARY,
    baseline_packet_path: Path = BASELINE_PACKET_JSON,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    execution_attempt_count_weekly: int = 0,
    execution_failure_count_weekly: int = 0,
    config_drift_events_weekly: int = 0,
    unprotected_position_events_weekly: int = 0,
) -> dict[str, Any]:
    source = _read_json(source_path)
    cell = source["matrices"][VARIANT]["custom"][DEFAULT_WINDOW]
    window = cell["window"]
    trade_path = _repo_path(str(cell["artifacts"]["trades"]))
    trade_rows = _read_csv(trade_path)
    weeks, overflow = _build_week_rows(
        trade_rows,
        start=str(window["start"]),
        end=str(window["end"]),
        fee_rate=fee_rate,
        slot_labels=SLOT_LABELS,
    )
    summary = _summarize_week_rows(weeks)
    portfolio_ref = dict(cell.get("portfolio") or {})
    operational_by_week = _operational_inputs_for_weeks(
        weeks,
        execution_attempt_count_weekly=execution_attempt_count_weekly,
        execution_failure_count_weekly=execution_failure_count_weekly,
        config_drift_events_weekly=config_drift_events_weekly,
        unprotected_position_events_weekly=unprotected_position_events_weekly,
    )
    packets = build_weekly_control_packets(
        weeks,
        review_start=str(window["start"]),
        review_end=str(window["end"]),
        review_capital_usdt=review_capital_usdt,
        portfolio_max_drawdown_pct_review_window=float(portfolio_ref.get("max_dd_pct") or 0.0),
        operational_by_week_start=operational_by_week,
    )
    latest_packet = packets[-1] if packets else None
    latest_contract_grade_packet = _latest_contract_grade({"packets": packets})
    state_counts: dict[str, int] = {}
    contract_grade_state_counts: dict[str, int] = {}
    for packet in packets:
        state = str(packet["decision"]["state"])
        state_counts[state] = state_counts.get(state, 0) + 1
        if bool(packet["decision"]["contract_grade"]):
            contract_grade_state_counts[state] = contract_grade_state_counts.get(state, 0) + 1

    payload = {
        "schema": "strategy_plugin_weekly_profit_frequency_complement_candidate_packets.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "summary": str(source_path),
            "source_generated_at": source.get("generated_at"),
            "variant": VARIANT,
            "primary_window_key": f"custom/{DEFAULT_WINDOW}",
            "primary_window_start": window["start"],
            "primary_window_end": window["end"],
            "trade_artifact": str(trade_path),
        },
        "method": {
            "week_boundary": "UTC ISO weeks anchored on Monday",
            "participation_basis": "entry week",
            "economic_outcome_basis": "exit week realized PnL",
            "fee_rate_per_side_estimate": fee_rate,
            "review_capital_usdt": review_capital_usdt,
            "operational_input_source": "backtest-control defaults",
        },
        "portfolio_reference": portfolio_ref,
        "overflow": overflow,
        "weekly_summary": summary,
        "packet_count": len(packets),
        "state_counts": dict(sorted(state_counts.items())),
        "contract_grade_state_counts": dict(sorted(contract_grade_state_counts.items())),
        "latest_packet": latest_packet,
        "latest_contract_grade_packet": latest_contract_grade_packet,
        "packets": packets,
    }
    payload["baseline_comparison"] = _comparison(payload, baseline_packet_path)
    return payload


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["weekly_summary"]
    comparison = payload["baseline_comparison"]
    latest = payload["latest_contract_grade_packet"] or payload["latest_packet"]
    decision = latest["decision"] if latest else {"state": "none"}
    comparable = bool(comparison.get("contract_grade_comparable"))
    active_delta = float(comparison.get("active_entry_week_ratio_8w_delta") or 0.0)
    net_delta = float(comparison.get("rolling_8w_net_after_fee_pnl_delta") or 0.0)
    if comparable and active_delta > 0.0 and net_delta < 0.0:
        strict_read = (
            "The candidate fixes cadence but damages economics. It should not be promoted; "
            "the next review must repair feature parity and loss attribution before another "
            "combined packet run."
        )
    elif comparable:
        strict_read = (
            "The candidate packet is comparable to the Phase 3 baseline; use the deltas below "
            "as the research decision input."
        )
    else:
        strict_read = (
            "The candidate packet was generated, but no comparable Phase 3 baseline packet "
            "was available."
        )
    lines = [
        "# Weekly Profit Phase 4B Frequency Complement Candidate Packet",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `A_B_PLUS_CANDIDATE_WEEKLY_PACKET_EVALUATED`",
        "",
        "## Executive Read",
        "",
        (
            f"Latest contract-grade packet state is `{decision['state']}` for the A+B+candidate "
            "combined run."
        ),
        "",
        strict_read,
        "",
        "This is a research packet over backtest artifacts. Runtime defaults remain unchanged.",
        "",
        "## Combined Weekly Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| entry trades | {summary['entry_trades']} |",
        f"| exit trades | {summary['exit_trades']} |",
        f"| active entry weeks | {summary['active_entry_weeks']} |",
        f"| active entry week ratio | {_fmt(summary['active_entry_week_ratio'])} |",
        f"| after-fee positive week ratio, all weeks | {_fmt(summary['after_fee_positive_week_ratio_all'])} |",
        f"| net after fee estimate | {_fmt(summary['net_after_fee_est_usdt'])} |",
        f"| worst after-fee week | {_fmt(summary['worst_week_after_fee_pnl_est_usdt'])} |",
        "",
        "## Latest Contract-Grade Decision",
        "",
        "| item | value |",
        "| --- | --- |",
        f"| week_start | `{latest['week_start'] if latest else 'none'}` |",
        f"| state | `{decision['state']}` |",
        f"| pause triggers | `{', '.join(decision.get('pause_triggers', [])) or 'none'}` |",
        f"| reopen triggers | `{', '.join(decision.get('reopen_triggers', [])) or 'none'}` |",
        f"| investigate triggers | `{', '.join(decision.get('investigate_triggers', [])) or 'none'}` |",
        "",
        "## Baseline Packet Delta",
        "",
    ]
    if comparable:
        lines.extend(
            [
                "| metric | delta vs Phase 3 baseline |",
                "| --- | ---: |",
                f"| active-entry week ratio 8w | {_fmt(comparison['active_entry_week_ratio_8w_delta'])} |",
                f"| rolling 8w entry trade count | {comparison['rolling_8w_entry_trade_count_delta']} |",
                f"| positive all-week ratio 8w | {_fmt(comparison['positive_week_ratio_all_8w_after_fee_delta'])} |",
                f"| rolling 8w net after-fee pnl | {_fmt(comparison['rolling_8w_net_after_fee_pnl_delta'])} |",
                f"| baseline state -> candidate state | `{comparison['baseline_state']} -> {comparison['candidate_state']}` |",
            ]
        )
    else:
        lines.append("No contract-grade baseline packet was available for an apples-to-apples delta.")
    lines.extend(
        [
            "",
            "## Artifact",
            "",
            f"- Candidate packet JSON: `{DEFAULT_JSON}`",
            f"- Source combined summary: `{payload['source']['summary']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_candidate_packet(
    *,
    source_path: Path = DEFAULT_SUMMARY,
    baseline_packet_path: Path = BASELINE_PACKET_JSON,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    execution_attempt_count_weekly: int = 0,
    execution_failure_count_weekly: int = 0,
    config_drift_events_weekly: int = 0,
    unprotected_position_events_weekly: int = 0,
) -> dict[str, Any]:
    payload = build_candidate_packet_payload(
        source_path=source_path,
        baseline_packet_path=baseline_packet_path,
        fee_rate=fee_rate,
        review_capital_usdt=review_capital_usdt,
        execution_attempt_count_weekly=execution_attempt_count_weekly,
        execution_failure_count_weekly=execution_failure_count_weekly,
        config_drift_events_weekly=config_drift_events_weekly,
        unprotected_position_events_weekly=unprotected_position_events_weekly,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build A+B+candidate weekly packet evaluation."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--baseline-packets", type=Path, default=BASELINE_PACKET_JSON)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital", type=float, default=DEFAULT_REVIEW_CAPITAL_USDT)
    parser.add_argument("--execution-attempts", type=int, default=0)
    parser.add_argument("--execution-failures", type=int, default=0)
    parser.add_argument("--config-drift-events", type=int, default=0)
    parser.add_argument("--unprotected-position-events", type=int, default=0)
    args = parser.parse_args()
    write_candidate_packet(
        source_path=args.source,
        baseline_packet_path=args.baseline_packets,
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
