"""Run holdout/multi-window robustness review for Slot B expansion repair."""

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
from extensions.Backtesting.scripts import run_portfolio_ab_short_ablation as short_ablation  # noqa: E402
from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion import (  # noqa: E402
    BASELINE_SYMBOLS,
    DEFAULT_CANDIDATE_SYMBOLS,
    SLOT_A_LONG,
    SLOT_B_LONG,
    SLOT_B_SHORT,
    _attribution_rows,
    _availability_probe,
    _compare_latest_contracts,
    _csv_attribution_rows,
    _gate_read,
    _latest_contract_grade,
    _safe_float,
    _safe_int,
    _weekly_csv_rows,
    _write_csv,
)
from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion_repair import (  # noqa: E402
    REPAIR_LONG,
    REPAIR_SHORT,
    STRATEGIES_REPAIR_COMBINED,
    STRATEGY_LABELS,
    _repair_candidate_trade_rows,
    _run_cell,
)
from weekly_profit_control import build_weekly_control_packets  # noqa: E402


STATUS = "RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_REPAIR_HOLDOUT_REVIEWED"
VARIANT = "slot_a_b_promoted_plus_slot_b_symbol_universe_expansion_repair"
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "slot_b_symbol_universe_expansion_repair_holdout"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_summary.json"
DEFAULT_WINDOWS_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_windows.csv"
DEFAULT_ATTRIBUTION_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_attribution.csv"
DEFAULT_WEEKLY_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_weekly_rows.csv"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase5_4e_repair_holdout_robustness.md"

HOLDOUT_WINDOWS: dict[str, dict[str, str]] = {
    "default/TRENDING_UP": {
        "matrix": "default",
        "window": "TRENDING_UP",
        "start": "2023-10-01",
        "end": "2024-03-31",
    },
    "default/RANGING": {
        "matrix": "default",
        "window": "RANGING",
        "start": "2024-12-31",
        "end": "2025-03-31",
    },
    "default/MIXED": {
        "matrix": "default",
        "window": "MIXED",
        "start": "2025-02-01",
        "end": "2025-08-31",
    },
    "supplemental/range_low_vol": {
        "matrix": "supplemental",
        "window": "range_low_vol",
        "start": "2025-09-01",
        "end": "2025-12-31",
    },
}


def _baseline_cell(matrix: str, window: str) -> dict[str, Any]:
    payload = _read_json(short_ablation.SUMMARY_PATH)
    try:
        return payload["matrices"]["slot_b_short_overlay"][matrix][window]
    except KeyError as exc:
        raise KeyError(f"missing promoted baseline cell: {matrix}/{window}") from exc


def _weekly_payload(
    *,
    trades: list[dict[str, str]],
    cell: dict[str, Any],
    window_key: str,
    variant: str,
    baseline_latest: dict[str, Any] | None,
    fee_rate: float,
    review_capital_usdt: float,
    trade_artifact: str,
) -> dict[str, Any]:
    window = cell["window"]
    weeks, overflow = _build_week_rows(
        trades,
        start=str(window["start"]),
        end=str(window["end"]),
        fee_rate=fee_rate,
        slot_labels=STRATEGY_LABELS,
    )
    operational_by_week = {
        str(row["week_start"]): {
            "execution_attempt_count_weekly": 0,
            "execution_failure_count_weekly": 0,
            "config_drift_events_weekly": 0,
            "unprotected_position_events_weekly": 0,
        }
        for row in weeks
    }
    packets = build_weekly_control_packets(
        weeks,
        review_start=str(window["start"]),
        review_end=str(window["end"]),
        review_capital_usdt=review_capital_usdt,
        portfolio_max_drawdown_pct_review_window=float(cell["portfolio"].get("max_dd_pct") or 0.0),
        operational_by_week_start=operational_by_week,
    )
    latest = _latest_contract_grade({"packets": packets})
    return {
        "schema": "strategy_plugin_weekly_profit_slot_b_symbol_universe_expansion_repair_holdout_packets.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "variant": variant,
            "window_key": window_key,
            "window_start": window["start"],
            "window_end": window["end"],
            "trade_artifact": trade_artifact,
        },
        "method": {
            "week_boundary": "UTC ISO weeks anchored on Monday",
            "participation_basis": "entry week",
            "economic_outcome_basis": "exit week realized PnL",
            "fee_rate_per_side_estimate": fee_rate,
            "review_capital_usdt": review_capital_usdt,
            "operational_input_source": "backtest-control defaults",
        },
        "portfolio_reference": dict(cell.get("portfolio") or {}),
        "overflow": overflow,
        "weekly_summary": _summarize_week_rows(weeks),
        "latest_contract_grade_packet": latest,
        "baseline_latest_contract_grade_packet": baseline_latest,
        "baseline_comparison": _compare_latest_contracts(latest, baseline_latest)
        if baseline_latest
        else {"contract_grade_comparable": False},
        "packets": packets,
        "weeks": weeks,
    }


def _window_row(
    *,
    window_key: str,
    window_spec: dict[str, str],
    baseline_cell: dict[str, Any],
    repair_cell: dict[str, Any],
    baseline_payload: dict[str, Any],
    repair_payload: dict[str, Any],
    gate_read: dict[str, Any],
) -> dict[str, Any]:
    comparison = repair_payload["baseline_comparison"]
    baseline_summary = baseline_payload["weekly_summary"]
    repair_summary = repair_payload["weekly_summary"]
    failed = [key for key, value in gate_read["gates"].items() if not value]
    return {
        "window_key": window_key,
        "matrix": window_spec["matrix"],
        "window": window_spec["window"],
        "start": window_spec["start"],
        "end": window_spec["end"],
        "baseline_entry_trades": baseline_summary["entry_trades"],
        "repair_entry_trades": repair_summary["entry_trades"],
        "baseline_active_entry_weeks": baseline_summary["active_entry_weeks"],
        "repair_active_entry_weeks": repair_summary["active_entry_weeks"],
        "baseline_net_after_fee_est_usdt": baseline_summary["net_after_fee_est_usdt"],
        "repair_net_after_fee_est_usdt": repair_summary["net_after_fee_est_usdt"],
        "candidate_slot_trades": gate_read["candidate_slot_trades"],
        "candidate_slot_after_fee_pnl_usdt": gate_read["candidate_slot_after_fee_pnl_usdt"],
        "baseline_max_dd_pct": baseline_cell["portfolio"]["max_dd_pct"],
        "repair_max_dd_pct": repair_cell["portfolio"]["max_dd_pct"],
        "active_entry_week_ratio_8w_delta": comparison.get("active_entry_week_ratio_8w_delta"),
        "positive_week_ratio_all_8w_after_fee_delta": comparison.get(
            "positive_week_ratio_all_8w_after_fee_delta"
        ),
        "positive_week_ratio_exit_active_8w_after_fee_delta": comparison.get(
            "positive_week_ratio_exit_active_8w_after_fee_delta"
        ),
        "rolling_8w_net_after_fee_pnl_delta": comparison.get(
            "rolling_8w_net_after_fee_pnl_delta"
        ),
        "portfolio_max_drawdown_pct_review_window_delta": comparison.get(
            "portfolio_max_drawdown_pct_review_window_delta"
        ),
        "gate_pass": gate_read["all_hard_gates_pass"],
        "failed_gates": ",".join(failed),
        "baseline_state": comparison.get("baseline_state"),
        "repair_state": comparison.get("candidate_state"),
        "baseline_run_errors": _safe_int(baseline_cell["portfolio"].get("run_errors")),
        "repair_run_errors": _safe_int(repair_cell["portfolio"].get("run_errors")),
    }


def _robustness_summary(window_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(window_rows)
    pass_count = sum(1 for row in window_rows if row["gate_pass"])
    candidate_positive = sum(
        1 for row in window_rows if _safe_float(row["candidate_slot_after_fee_pnl_usdt"]) >= 0.0
    )
    active_improved = sum(
        1 for row in window_rows if _safe_float(row["active_entry_week_ratio_8w_delta"]) > 0.0
    )
    exit_active_not_down = sum(
        1
        for row in window_rows
        if _safe_float(row["positive_week_ratio_exit_active_8w_after_fee_delta"]) >= 0.0
    )
    rolling_not_down = sum(
        1 for row in window_rows if _safe_float(row["rolling_8w_net_after_fee_pnl_delta"]) >= 0.0
    )
    max_dd_clean = sum(
        1
        for row in window_rows
        if _safe_float(row["portfolio_max_drawdown_pct_review_window_delta"]) <= 1.0
    )
    negative_windows = [
        row["window_key"]
        for row in window_rows
        if _safe_float(row["candidate_slot_after_fee_pnl_usdt"]) < 0.0
    ]
    failing_windows = [row["window_key"] for row in window_rows if not row["gate_pass"]]
    return {
        "windows": total,
        "hard_gate_pass_windows": pass_count,
        "candidate_after_fee_non_negative_windows": candidate_positive,
        "active_entry_improved_windows": active_improved,
        "exit_active_positive_not_down_windows": exit_active_not_down,
        "rolling_8w_after_fee_not_below_windows": rolling_not_down,
        "max_dd_not_materially_larger_windows": max_dd_clean,
        "negative_candidate_windows": negative_windows,
        "failing_windows": failing_windows,
        "all_windows_pass": bool(total and pass_count == total),
        "promotion_read": "robust_holdout_pass" if total and pass_count == total else "needs_more_research",
    }


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["robustness_summary"]
    rows = payload["windows"]
    lines = [
        "# Weekly Profit Phase 5 / 4E-Repair Holdout Robustness",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Status: `{STATUS}`",
        "",
        "## Executive Read",
        "",
        (
            f"Holdout robustness read is `{summary['promotion_read']}`: "
            f"{summary['hard_gate_pass_windows']} / {summary['windows']} windows pass the same hard-gate packet."
        ),
        "",
        "This remains research-only. Runtime defaults are unchanged, Slot A is not expanded, scanner runtime universe is disabled, and Slot B thresholds are unchanged.",
        "",
        "## Window Gate Summary",
        "",
        "| window | pass | candidate trades | candidate after-fee | active 8w delta | exit-active positive 8w delta | rolling 8w pnl delta | max DD delta | failed gates |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['window_key']}` | `{row['gate_pass']}` | "
            f"{row['candidate_slot_trades']} | {_fmt(row['candidate_slot_after_fee_pnl_usdt'])} | "
            f"{_fmt(row['active_entry_week_ratio_8w_delta'])} | "
            f"{_fmt(row['positive_week_ratio_exit_active_8w_after_fee_delta'])} | "
            f"{_fmt(row['rolling_8w_net_after_fee_pnl_delta'])} | "
            f"{_fmt(row['portfolio_max_drawdown_pct_review_window_delta'])} | "
            f"`{row['failed_gates'] or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Counts",
            "",
            "| metric | value |",
            "| --- | ---: |",
            f"| hard-gate pass windows | {summary['hard_gate_pass_windows']} / {summary['windows']} |",
            f"| candidate after-fee non-negative windows | {summary['candidate_after_fee_non_negative_windows']} / {summary['windows']} |",
            f"| active-entry improved windows | {summary['active_entry_improved_windows']} / {summary['windows']} |",
            f"| exit-active positive not-down windows | {summary['exit_active_positive_not_down_windows']} / {summary['windows']} |",
            f"| rolling 8w after-fee not-below windows | {summary['rolling_8w_after_fee_not_below_windows']} / {summary['windows']} |",
            f"| max DD not materially larger windows | {summary['max_dd_not_materially_larger_windows']} / {summary['windows']} |",
            "",
            "## Artifacts",
            "",
            f"- Summary JSON: `{payload['artifact']['summary_json']}`",
            f"- Window CSV: `{payload['artifact']['windows_csv']}`",
            f"- Attribution CSV: `{payload['artifact']['attribution_csv']}`",
            f"- Weekly rows CSV: `{payload['artifact']['weekly_csv']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_slot_b_symbol_universe_expansion_repair_holdout(
    *,
    windows: list[str] | None = None,
    candidate_symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    summary_path: Path = DEFAULT_SUMMARY,
    windows_csv_path: Path = DEFAULT_WINDOWS_CSV,
    attribution_csv_path: Path = DEFAULT_ATTRIBUTION_CSV,
    weekly_csv_path: Path = DEFAULT_WEEKLY_CSV,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    rerun: bool = False,
) -> tuple[Path, Path]:
    candidate_symbols = list(candidate_symbols or DEFAULT_CANDIDATE_SYMBOLS)
    selected_windows = {key: HOLDOUT_WINDOWS[key] for key in (windows or list(HOLDOUT_WINDOWS))}

    window_rows: list[dict[str, Any]] = []
    all_attribution: list[dict[str, Any]] = []
    all_weekly_rows: list[dict[str, Any]] = []
    window_payloads: dict[str, Any] = {}
    availability_by_window: dict[str, Any] = {}

    for window_key, spec in selected_windows.items():
        availability = _availability_probe(
            start=spec["start"],
            end=spec["end"],
            candidate_symbols=candidate_symbols,
        )
        availability_by_window[window_key] = availability
        selected_symbols = list(availability["candidate_symbols_selected"])
        if not selected_symbols:
            raise RuntimeError(f"No candidate symbols passed availability for {window_key}.")

        baseline_cell = _baseline_cell(spec["matrix"], spec["window"])
        baseline_trades = _read_csv(_repo_path(baseline_cell["artifacts"]["trades"]))
        baseline_payload = _weekly_payload(
            trades=baseline_trades,
            cell=baseline_cell,
            window_key=window_key,
            variant="slot_a_b_promoted_baseline",
            baseline_latest=None,
            fee_rate=fee_rate,
            review_capital_usdt=review_capital_usdt,
            trade_artifact=str(_repo_path(baseline_cell["artifacts"]["trades"])),
        )
        baseline_latest = baseline_payload["latest_contract_grade_packet"]

        repair_cell = _run_cell(
            start=spec["start"],
            end=spec["end"],
            symbols=list(BASELINE_SYMBOLS) + selected_symbols,
            strategies=list(STRATEGIES_REPAIR_COMBINED),
            risk_per_trade=risk_per_trade,
            output_dir=Path(results_root) / VARIANT / spec["matrix"] / spec["window"],
            rerun=rerun,
            label=f"{VARIANT}/{window_key}",
        )
        repair_trades = _read_csv(_repo_path(repair_cell["artifacts"]["trades"]))
        repair_payload = _weekly_payload(
            trades=repair_trades,
            cell=repair_cell,
            window_key=window_key,
            variant=VARIANT,
            baseline_latest=baseline_latest,
            fee_rate=fee_rate,
            review_capital_usdt=review_capital_usdt,
            trade_artifact=str(_repo_path(repair_cell["artifacts"]["trades"])),
        )
        candidate_trades = _repair_candidate_trade_rows(repair_trades)
        attribution = _attribution_rows(
            candidate_trades,
            scope=f"holdout/{window_key}",
            symbols=selected_symbols,
            strategies=[REPAIR_LONG, REPAIR_SHORT],
            start=spec["start"],
            end=spec["end"],
            fee_rate=fee_rate,
            baseline_trades=baseline_trades,
        )
        gate = _gate_read(
            weekly_payload=repair_payload,
            combined_cell=repair_cell,
            candidate_attribution=attribution,
        )
        row = _window_row(
            window_key=window_key,
            window_spec=spec,
            baseline_cell=baseline_cell,
            repair_cell=repair_cell,
            baseline_payload=baseline_payload,
            repair_payload=repair_payload,
            gate_read=gate,
        )
        window_rows.append(row)
        all_attribution.extend(attribution)
        for weekly_row in _weekly_csv_rows(repair_payload["weeks"]):
            weekly_row["window_key"] = window_key
            all_weekly_rows.append(weekly_row)
        window_payloads[window_key] = {
            "window": spec,
            "availability": availability,
            "baseline": {
                "cell": baseline_cell,
                "weekly_summary": baseline_payload["weekly_summary"],
                "latest_contract_grade_packet": baseline_latest,
            },
            "repair": {
                "cell": repair_cell,
                "weekly_summary": repair_payload["weekly_summary"],
                "latest_contract_grade_packet": repair_payload["latest_contract_grade_packet"],
                "baseline_comparison": repair_payload["baseline_comparison"],
                "gate_read": gate,
                "candidate_symbol_attribution": attribution,
            },
        }

    robustness = _robustness_summary(window_rows)
    _write_csv(
        windows_csv_path,
        window_rows,
        fieldnames=list(window_rows[0].keys()) if window_rows else [],
    )
    _write_csv(
        attribution_csv_path,
        _csv_attribution_rows(all_attribution),
        fieldnames=[
            "scope",
            "symbol",
            "strategy_id",
            "strategy_label",
            "trades",
            "gross_pnl_usdt",
            "fees_est_usdt",
            "after_fee_pnl_usdt",
            "win_rate",
            "active_entry_weeks",
            "worst_trade_after_fee_pnl_usdt",
            "worst_week_start",
            "worst_week_after_fee_pnl_usdt",
            "same_entry_time_overlap_with_baseline",
            "entry_week_overlap_with_baseline",
        ],
    )
    weekly_fieldnames = sorted({key for row in all_weekly_rows for key in row})
    preferred_weekly_fields = [
        "window_key",
        "week_start",
        "week_end",
        "entry_trades",
        "exit_trades",
        "gross_pnl_usdt",
        "fees_est_usdt",
        "net_after_fee_est_usdt",
    ]
    weekly_fieldnames = preferred_weekly_fields + [
        key for key in weekly_fieldnames if key not in preferred_weekly_fields
    ]
    _write_csv(weekly_csv_path, all_weekly_rows, fieldnames=weekly_fieldnames)

    payload = {
        "schema": "strategy_plugin_slot_b_symbol_universe_expansion_repair_holdout.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": STATUS,
        "variant": VARIANT,
        "baseline_variant": "slot_b_short_overlay",
        "strategies": {
            "slot_a_long": SLOT_A_LONG,
            "slot_b_long": SLOT_B_LONG,
            "slot_b_short": SLOT_B_SHORT,
            "candidate_long_repair": REPAIR_LONG,
            "candidate_short_repair": REPAIR_SHORT,
        },
        "research_controls": {
            "runtime_defaults_changed": False,
            "slot_a_expanded": False,
            "scanner_runtime_universe_enabled": False,
            "thresholds_changed": False,
            "primary_selection_window_excluded": True,
        },
        "candidate_symbols_requested": candidate_symbols,
        "fee_rate_per_side_estimate": fee_rate,
        "robustness_summary": robustness,
        "windows": window_rows,
        "window_payloads": window_payloads,
        "data_availability": availability_by_window,
        "artifact": {
            "summary_json": str(summary_path),
            "windows_csv": str(windows_csv_path),
            "attribution_csv": str(attribution_csv_path),
            "weekly_csv": str(weekly_csv_path),
            "report": str(report_path),
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload), encoding="utf-8")
    print(f"[SlotBRepairHoldout] summary={summary_path}")
    print(f"[SlotBRepairHoldout] report={report_path}")
    return summary_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Phase 5/4E-Repair holdout robustness review."
    )
    parser.add_argument("--windows", nargs="+", choices=sorted(HOLDOUT_WINDOWS), default=None)
    parser.add_argument("--candidate-symbols", nargs="+", default=list(DEFAULT_CANDIDATE_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--windows-csv-path", type=Path, default=DEFAULT_WINDOWS_CSV)
    parser.add_argument("--attribution-csv-path", type=Path, default=DEFAULT_ATTRIBUTION_CSV)
    parser.add_argument("--weekly-csv-path", type=Path, default=DEFAULT_WEEKLY_CSV)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital-usdt", type=float, default=DEFAULT_REVIEW_CAPITAL_USDT)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args(argv)
    run_slot_b_symbol_universe_expansion_repair_holdout(
        windows=args.windows,
        candidate_symbols=list(args.candidate_symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=args.results_root,
        summary_path=args.summary_path,
        windows_csv_path=args.windows_csv_path,
        attribution_csv_path=args.attribution_csv_path,
        weekly_csv_path=args.weekly_csv_path,
        report_path=args.report_path,
        fee_rate=args.fee_rate,
        review_capital_usdt=args.review_capital_usdt,
        rerun=bool(args.rerun),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
