"""Run Phase 5/4E-Repair Slot B symbol-universe admission review."""

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
from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion import (  # noqa: E402
    BASELINE_SYMBOLS,
    BASELINE_SUMMARY,
    CANDIDATE_LONG,
    CANDIDATE_SHORT,
    DEFAULT_CANDIDATE_SYMBOLS,
    DEFAULT_END,
    DEFAULT_START,
    DEFAULT_SUMMARY as SOURCE_EXPANSION_SUMMARY,
    DEFAULT_WINDOW,
    SLOT_A_LONG,
    SLOT_B_LONG,
    SLOT_B_SHORT,
    _attribution_rows,
    _availability_probe,
    _compare_latest_contracts,
    _csv_attribution_rows,
    _gate_read,
    _latest_contract_grade,
    _load_baseline,
    _run_cell,
    _safe_float,
    _safe_int,
    _weekly_csv_rows,
    _write_csv,
)
from weekly_profit_control import build_weekly_control_packets  # noqa: E402


REPAIR_LONG = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion_repair"
REPAIR_SHORT = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion_repair"
VARIANT = "slot_a_b_promoted_plus_slot_b_symbol_universe_expansion_repair"
STATUS = "RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_REPAIR_EVALUATED"

STRATEGIES_REPAIR_COMBINED = (
    SLOT_A_LONG,
    SLOT_B_LONG,
    SLOT_B_SHORT,
    REPAIR_LONG,
    REPAIR_SHORT,
)
PROMOTED_STRATEGIES = {SLOT_A_LONG, SLOT_B_LONG, SLOT_B_SHORT}
SOURCE_CANDIDATE_STRATEGIES = {CANDIDATE_LONG, CANDIDATE_SHORT}
REPAIR_CANDIDATE_STRATEGIES = {REPAIR_LONG, REPAIR_SHORT}

STRATEGY_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
    CANDIDATE_LONG: "Slot B LONG Expansion",
    CANDIDATE_SHORT: "Slot B SHORT Expansion",
    REPAIR_LONG: "Slot B LONG Expansion Repair",
    REPAIR_SHORT: "Slot B SHORT Expansion Repair",
}

DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "slot_b_symbol_universe_expansion_repair"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_summary.json"
DEFAULT_PACKET_JSON = DEFAULT_RESULTS_ROOT / "weekly_profit_slot_b_symbol_universe_expansion_repair_packets.json"
DEFAULT_VARIANTS_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_variants.csv"
DEFAULT_ATTRIBUTION_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_symbol_attribution.csv"
DEFAULT_WEEKLY_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_weekly_rows.csv"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase5_4e_slot_b_symbol_universe_expansion_repair.md"


def _all_admission(symbols: list[str]) -> dict[str, set[str]]:
    return {symbol: {CANDIDATE_LONG, CANDIDATE_SHORT} for symbol in symbols}


def _drop_admission(
    symbols: list[str],
    drops: set[tuple[str, str]],
) -> dict[str, set[str]]:
    admission = _all_admission(symbols)
    for symbol, strategy_id in drops:
        admission.setdefault(symbol, set()).discard(strategy_id)
    return admission


def _selected_admission(
    symbols: list[str],
    *,
    full_symbols: set[str],
    long_only_symbols: set[str] | None = None,
    short_only_symbols: set[str] | None = None,
) -> dict[str, set[str]]:
    long_only_symbols = long_only_symbols or set()
    short_only_symbols = short_only_symbols or set()
    admission: dict[str, set[str]] = {}
    for symbol in symbols:
        sides: set[str] = set()
        if symbol in full_symbols or symbol in long_only_symbols:
            sides.add(CANDIDATE_LONG)
        if symbol in full_symbols or symbol in short_only_symbols:
            sides.add(CANDIDATE_SHORT)
        admission[symbol] = sides
    return admission


def _repair_admission_variants(symbols: list[str]) -> list[dict[str, Any]]:
    top3 = {"SOL/USDT", "BNB/USDT", "XRP/USDT"} & set(symbols)
    return [
        {
            "variant": "all_expanded_reference",
            "description": "Keep all Phase 5/4E expanded symbol/side admissions.",
            "admission": _all_admission(symbols),
        },
        {
            "variant": "drop_link_short",
            "description": "Keep all admissions except LINK/USDT SHORT.",
            "admission": _drop_admission(symbols, {("LINK/USDT", CANDIDATE_SHORT)}),
        },
        {
            "variant": "drop_ada_long",
            "description": "Keep all admissions except ADA/USDT LONG.",
            "admission": _drop_admission(symbols, {("ADA/USDT", CANDIDATE_LONG)}),
        },
        {
            "variant": "drop_link_short_ada_long",
            "description": "Keep all positive-side admissions; drop LINK/USDT SHORT and ADA/USDT LONG.",
            "admission": _drop_admission(
                symbols,
                {
                    ("LINK/USDT", CANDIDATE_SHORT),
                    ("ADA/USDT", CANDIDATE_LONG),
                },
            ),
        },
        {
            "variant": "drop_link_all",
            "description": "Drop LINK/USDT entirely.",
            "admission": _selected_admission(
                symbols,
                full_symbols=(set(symbols) - {"LINK/USDT"}),
            ),
        },
        {
            "variant": "sol_bnb_xrp_all",
            "description": "Admit only SOL/USDT, BNB/USDT, XRP/USDT on both sides.",
            "admission": _selected_admission(symbols, full_symbols=top3),
        },
        {
            "variant": "sol_bnb_xrp_ada_all",
            "description": "Admit SOL/USDT, BNB/USDT, XRP/USDT, ADA/USDT on both sides.",
            "admission": _selected_admission(
                symbols,
                full_symbols=top3 | ({"ADA/USDT"} & set(symbols)),
            ),
        },
        {
            "variant": "sol_bnb_xrp_link_long",
            "description": "Admit top three symbols on both sides plus LINK/USDT LONG.",
            "admission": _selected_admission(
                symbols,
                full_symbols=top3,
                long_only_symbols={"LINK/USDT"} & set(symbols),
            ),
        },
        {
            "variant": "sol_bnb_xrp_ada_short_link_long",
            "description": "Admit top three both sides, ADA/USDT SHORT, and LINK/USDT LONG.",
            "admission": _selected_admission(
                symbols,
                full_symbols=top3,
                long_only_symbols={"LINK/USDT"} & set(symbols),
                short_only_symbols={"ADA/USDT"} & set(symbols),
            ),
        },
    ]


def _admitted_candidate_trade(
    row: dict[str, str],
    admission: dict[str, set[str]],
    *,
    candidate_strategies: set[str],
) -> bool:
    strategy_id = str(row.get("strategy_id") or "")
    if strategy_id not in candidate_strategies:
        return False
    return strategy_id in admission.get(str(row.get("symbol") or ""), set())


def _filter_trade_rows(
    rows: list[dict[str, str]],
    admission: dict[str, set[str]],
    *,
    promoted_strategies: set[str],
    candidate_strategies: set[str],
) -> list[dict[str, str]]:
    output = []
    for row in rows:
        strategy_id = str(row.get("strategy_id") or "")
        if strategy_id in promoted_strategies or _admitted_candidate_trade(
            row,
            admission,
            candidate_strategies=candidate_strategies,
        ):
            output.append(row)
    return output


def _weekly_payload_from_trades(
    *,
    trades: list[dict[str, str]],
    cell: dict[str, Any],
    baseline: dict[str, Any],
    fee_rate: float,
    review_capital_usdt: float,
    variant: str,
    schema: str,
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
    latest_contract = _latest_contract_grade({"packets": packets})
    baseline_latest = baseline.get("latest_contract_grade_packet") or {}
    return {
        "schema": schema,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "variant": variant,
            "primary_window_key": f"custom/{DEFAULT_WINDOW}",
            "primary_window_start": window["start"],
            "primary_window_end": window["end"],
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
        "latest_contract_grade_packet": latest_contract,
        "baseline_latest_contract_grade_packet": baseline_latest,
        "baseline_comparison": _compare_latest_contracts(latest_contract, baseline_latest),
        "packets": packets,
        "weeks": weeks,
    }


def _evaluate_admission_variant(
    *,
    variant: str,
    description: str,
    admission: dict[str, set[str]],
    source_trades: list[dict[str, str]],
    source_cell: dict[str, Any],
    baseline: dict[str, Any],
    symbols: list[str],
    fee_rate: float,
    review_capital_usdt: float,
) -> dict[str, Any]:
    trades = _filter_trade_rows(
        source_trades,
        admission,
        promoted_strategies=PROMOTED_STRATEGIES,
        candidate_strategies=SOURCE_CANDIDATE_STRATEGIES,
    )
    candidate_trades = [
        row for row in trades if row.get("strategy_id") in SOURCE_CANDIDATE_STRATEGIES
    ]
    weekly_payload = _weekly_payload_from_trades(
        trades=trades,
        cell=source_cell,
        baseline=baseline,
        fee_rate=fee_rate,
        review_capital_usdt=review_capital_usdt,
        variant=variant,
        schema="strategy_plugin_weekly_profit_slot_b_symbol_universe_expansion_repair_ablation_packets.v1",
        trade_artifact=str(_repo_path(source_cell["artifacts"]["trades"])),
    )
    attribution = _attribution_rows(
        candidate_trades,
        scope="repair_admission_replay",
        symbols=symbols,
        strategies=[CANDIDATE_LONG, CANDIDATE_SHORT],
        start=str(source_cell["window"]["start"]),
        end=str(source_cell["window"]["end"]),
        fee_rate=fee_rate,
        baseline_trades=baseline["trades"],
    )
    gate = _gate_read(
        weekly_payload=weekly_payload,
        combined_cell=source_cell,
        candidate_attribution=attribution,
    )
    comparison = weekly_payload["baseline_comparison"]
    return {
        "variant": variant,
        "description": description,
        "admitted_long_symbols": sorted(
            symbol for symbol, strategies in admission.items() if CANDIDATE_LONG in strategies
        ),
        "admitted_short_symbols": sorted(
            symbol for symbol, strategies in admission.items() if CANDIDATE_SHORT in strategies
        ),
        "synthetic_admission_replay": True,
        "replay_source_trade_artifact": str(_repo_path(source_cell["artifacts"]["trades"])),
        "candidate_slot_trades": gate["candidate_slot_trades"],
        "candidate_slot_after_fee_pnl_usdt": gate["candidate_slot_after_fee_pnl_usdt"],
        "losing_symbol_trade_share": gate["losing_symbol_trade_share"],
        "baseline_comparison": comparison,
        "gate_read": gate,
    }


def _rank_repair_variants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            bool(row["gate_read"]["all_hard_gates_pass"]),
            _safe_float(row["baseline_comparison"].get("active_entry_week_ratio_8w_delta")),
            _safe_float(
                row["baseline_comparison"].get(
                    "positive_week_ratio_exit_active_8w_after_fee_delta"
                )
            ),
            _safe_float(row.get("candidate_slot_after_fee_pnl_usdt")),
            _safe_float(row["baseline_comparison"].get("rolling_8w_net_after_fee_pnl_delta")),
        ),
        reverse=True,
    )


def _variant_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        comparison = row["baseline_comparison"]
        output.append(
            {
                "rank": row.get("rank", ""),
                "variant": row["variant"],
                "all_hard_gates_pass": row["gate_read"]["all_hard_gates_pass"],
                "candidate_slot_trades": row["candidate_slot_trades"],
                "candidate_slot_after_fee_pnl_usdt": row["candidate_slot_after_fee_pnl_usdt"],
                "losing_symbol_trade_share": row["losing_symbol_trade_share"],
                "active_entry_week_ratio_8w_delta": comparison.get(
                    "active_entry_week_ratio_8w_delta"
                ),
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
                "admitted_long_symbols": ",".join(row["admitted_long_symbols"]),
                "admitted_short_symbols": ",".join(row["admitted_short_symbols"]),
                "description": row["description"],
            }
        )
    return output


def _repair_candidate_trade_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("strategy_id") in REPAIR_CANDIDATE_STRATEGIES]


def _write_trade_artifact(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    _write_csv(path, rows, fieldnames=fieldnames)


def _strict_read(gate: dict[str, Any]) -> str:
    if gate["all_hard_gates_pass"]:
        return (
            "The Phase 5/4E-Repair candidate passes this research hard-gate packet. "
            "This does not authorize runtime promotion."
        )
    failed = [key for key, value in gate["gates"].items() if not value]
    return (
        "The Phase 5/4E-Repair candidate does not pass the hard gates. Failed gate(s): "
        + ", ".join(f"`{item}`" for item in failed)
        + "."
    )


def _comparison_row(comparison: dict[str, Any], field: str) -> str:
    return (
        f"| `{field}` | {_fmt(comparison.get(f'baseline_{field}', 0.0))} | "
        f"{_fmt(comparison.get(f'candidate_{field}', 0.0))} | "
        f"{_fmt(comparison.get(f'{field}_delta', 0.0))} |"
    )


def _render_report(payload: dict[str, Any], weekly_payload: dict[str, Any]) -> str:
    gate = payload["gate_read"]
    comparison = weekly_payload["baseline_comparison"]
    baseline = payload["baseline"]["weekly_summary"]
    repair_weekly = weekly_payload["weekly_summary"]
    latest = weekly_payload["latest_contract_grade_packet"] or {}
    decision = latest.get("decision", {"state": "none"})
    top_variants = payload["admission_ablation"]["ranked_variants"][:5]
    candidate_rows = [
        row for row in payload["combined"]["candidate_symbol_attribution"] if row["strategy_id"] == "ALL"
    ]

    lines = [
        "# Weekly Profit Phase 5 / 4E-Repair Slot B Symbol-Universe Expansion",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Status: `{STATUS}`",
        "",
        "## Executive Read",
        "",
        (
            f"Latest contract-grade packet state is `{decision['state']}` for the "
            "A+B+Slot-B-repair-symbols combined run."
        ),
        "",
        _strict_read(gate),
        "",
        "Repair admission is side-specific: LONG admits `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `LINK/USDT`; SHORT admits `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `ADA/USDT`.",
        "",
        "Runtime defaults remain unchanged. Slot A was not expanded. Scanner runtime universe remains disabled. Thresholds are unchanged from promoted Slot B.",
        "",
        "## Admission Ablation Read",
        "",
        "Ablation is a trade-admission replay over the full-expanded combined artifact, then the selected repair was rerun through `BacktestEngine` as a research-only plugin pair.",
        "",
        "| rank | variant | pass | trades | candidate after-fee | active 8w delta | exit-active positive 8w delta | rolling 8w pnl delta |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_variants:
        comp = row["baseline_comparison"]
        lines.append(
            f"| {row['rank']} | `{row['variant']}` | `{row['gate_read']['all_hard_gates_pass']}` | "
            f"{row['candidate_slot_trades']} | {_fmt(row['candidate_slot_after_fee_pnl_usdt'])} | "
            f"{_fmt(comp.get('active_entry_week_ratio_8w_delta'))} | "
            f"{_fmt(comp.get('positive_week_ratio_exit_active_8w_after_fee_delta'))} | "
            f"{_fmt(comp.get('rolling_8w_net_after_fee_pnl_delta'))} |"
        )

    lines.extend(
        [
            "",
            "## Baseline vs Repair Weekly Packet",
            "",
            "| metric | baseline | repair | delta |",
            "| --- | ---: | ---: | ---: |",
            _comparison_row(comparison, "active_entry_week_ratio_8w"),
            _comparison_row(comparison, "rolling_8w_entry_trade_count"),
            _comparison_row(comparison, "positive_week_ratio_all_8w_after_fee"),
            _comparison_row(comparison, "positive_week_ratio_exit_active_8w_after_fee"),
            _comparison_row(comparison, "rolling_8w_net_after_fee_pnl"),
            _comparison_row(comparison, "portfolio_max_drawdown_pct_review_window"),
            "",
            "## Primary Window Summary",
            "",
            "| metric | baseline | repair |",
            "| --- | ---: | ---: |",
            f"| entry trades | {baseline['entry_trades']} | {repair_weekly['entry_trades']} |",
            f"| exit trades | {baseline['exit_trades']} | {repair_weekly['exit_trades']} |",
            f"| active entry weeks | {baseline['active_entry_weeks']} | {repair_weekly['active_entry_weeks']} |",
            f"| after-fee positive week ratio all | {_fmt(baseline['after_fee_positive_week_ratio_all'])} | {_fmt(repair_weekly['after_fee_positive_week_ratio_all'])} |",
            f"| net after fee estimate | {_fmt(baseline['net_after_fee_est_usdt'])} | {_fmt(repair_weekly['net_after_fee_est_usdt'])} |",
            f"| worst after-fee week | {_fmt(baseline['worst_week_after_fee_pnl_est_usdt'])} | {_fmt(repair_weekly['worst_week_after_fee_pnl_est_usdt'])} |",
            f"| portfolio max DD pct | {_fmt(payload['baseline']['cell']['portfolio']['max_dd_pct'])} | {_fmt(payload['combined']['cell']['portfolio']['max_dd_pct'])} |",
            "",
            "## Candidate Symbol Attribution",
            "",
            "| symbol | trades | gross pnl | fees est | after-fee pnl | win rate | active entry weeks | worst week | same-time overlap | entry-week overlap |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in candidate_rows:
        worst_week = row["worst_week"].get("net_after_fee_est_usdt", 0.0)
        lines.append(
            f"| `{row['symbol']}` | {row['trades']} | {_fmt(row['gross_pnl_usdt'])} | "
            f"{_fmt(row['fees_est_usdt'])} | {_fmt(row['after_fee_pnl_usdt'])} | "
            f"{_fmt(row['win_rate'])} | {row['active_entry_weeks']} | "
            f"{_fmt(worst_week)} | {row['same_entry_time_overlap_with_baseline']} | "
            f"{row['entry_week_overlap_with_baseline']} |"
        )

    lines.extend(["", "## Hard Gate Read", "", "| gate | pass |", "| --- | --- |"])
    for key, value in gate["gates"].items():
        lines.append(f"| `{key}` | `{bool(value)}` |")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Summary JSON: `{payload['artifact']['summary_json']}`",
            f"- Weekly packet JSON: `{payload['artifact']['weekly_packet_json']}`",
            f"- Admission variants CSV: `{payload['artifact']['variants_csv']}`",
            f"- Symbol attribution CSV: `{payload['artifact']['attribution_csv']}`",
            f"- Weekly rows CSV: `{payload['artifact']['weekly_csv']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_slot_b_symbol_universe_expansion_repair(
    *,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    window_name: str = DEFAULT_WINDOW,
    candidate_symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    summary_path: Path = DEFAULT_SUMMARY,
    packet_json_path: Path = DEFAULT_PACKET_JSON,
    variants_csv_path: Path = DEFAULT_VARIANTS_CSV,
    attribution_csv_path: Path = DEFAULT_ATTRIBUTION_CSV,
    weekly_csv_path: Path = DEFAULT_WEEKLY_CSV,
    report_path: Path = DEFAULT_REPORT,
    source_expansion_summary_path: Path = SOURCE_EXPANSION_SUMMARY,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    rerun: bool = False,
) -> tuple[Path, Path]:
    candidate_symbols = list(candidate_symbols or DEFAULT_CANDIDATE_SYMBOLS)
    availability = _availability_probe(
        start=start,
        end=end,
        candidate_symbols=candidate_symbols,
    )
    selected_symbols = list(availability["candidate_symbols_selected"])
    if not selected_symbols:
        raise RuntimeError("No candidate symbols passed availability for repair evaluation.")

    source_payload = _read_json(source_expansion_summary_path)
    source_cell = source_payload["combined"]["cell"]
    source_trades = _read_csv(_repo_path(source_cell["artifacts"]["trades"]))
    baseline = _load_baseline(fee_rate)

    ablation_rows = [
        _evaluate_admission_variant(
            variant=item["variant"],
            description=item["description"],
            admission=item["admission"],
            source_trades=source_trades,
            source_cell=source_cell,
            baseline=baseline,
            symbols=selected_symbols,
            fee_rate=fee_rate,
            review_capital_usdt=review_capital_usdt,
        )
        for item in _repair_admission_variants(selected_symbols)
    ]
    ranked_variants = _rank_repair_variants(ablation_rows)
    for index, row in enumerate(ranked_variants, start=1):
        row["rank"] = index

    repair_symbols = list(BASELINE_SYMBOLS) + selected_symbols
    repair_cell = _run_cell(
        start=start,
        end=end,
        symbols=repair_symbols,
        strategies=list(STRATEGIES_REPAIR_COMBINED),
        risk_per_trade=risk_per_trade,
        output_dir=Path(results_root) / VARIANT / "custom" / window_name,
        rerun=rerun,
        label=VARIANT,
    )
    repair_trades = _read_csv(_repo_path(repair_cell["artifacts"]["trades"]))
    repair_candidate_trades = _repair_candidate_trade_rows(repair_trades)
    repair_trade_artifact = Path(results_root) / VARIANT / "custom" / window_name / "trades.csv"
    _write_trade_artifact(
        repair_trade_artifact,
        repair_trades,
        fieldnames=list(repair_trades[0].keys()) if repair_trades else [],
    )

    weekly_payload = _weekly_payload_from_trades(
        trades=repair_trades,
        cell=repair_cell,
        baseline=baseline,
        fee_rate=fee_rate,
        review_capital_usdt=review_capital_usdt,
        variant=VARIANT,
        schema="strategy_plugin_weekly_profit_slot_b_symbol_universe_expansion_repair_packets.v1",
        trade_artifact=str(repair_trade_artifact),
    )
    candidate_attribution = _attribution_rows(
        repair_candidate_trades,
        scope="combined_repair_candidate",
        symbols=selected_symbols,
        strategies=[REPAIR_LONG, REPAIR_SHORT],
        start=start,
        end=end,
        fee_rate=fee_rate,
        baseline_trades=baseline["trades"],
    )
    gate_read = _gate_read(
        weekly_payload=weekly_payload,
        combined_cell=repair_cell,
        candidate_attribution=candidate_attribution,
    )

    _write_csv(
        variants_csv_path,
        _variant_csv_rows(ranked_variants),
        fieldnames=[
            "rank",
            "variant",
            "all_hard_gates_pass",
            "candidate_slot_trades",
            "candidate_slot_after_fee_pnl_usdt",
            "losing_symbol_trade_share",
            "active_entry_week_ratio_8w_delta",
            "positive_week_ratio_all_8w_after_fee_delta",
            "positive_week_ratio_exit_active_8w_after_fee_delta",
            "rolling_8w_net_after_fee_pnl_delta",
            "portfolio_max_drawdown_pct_review_window_delta",
            "admitted_long_symbols",
            "admitted_short_symbols",
            "description",
        ],
    )
    _write_csv(
        attribution_csv_path,
        _csv_attribution_rows(candidate_attribution),
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
    weekly_csv_rows = _weekly_csv_rows(weekly_payload["weeks"])
    weekly_fieldnames = sorted({key for row in weekly_csv_rows for key in row})
    preferred_weekly_fields = [
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
    _write_csv(weekly_csv_path, weekly_csv_rows, fieldnames=weekly_fieldnames)

    payload = {
        "schema": "strategy_plugin_slot_b_symbol_universe_expansion_repair.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": STATUS,
        "variant": VARIANT,
        "window": {"name": window_name, "start": start, "end": end},
        "baseline_symbols": list(BASELINE_SYMBOLS),
        "candidate_symbols_requested": candidate_symbols,
        "candidate_symbols_selected": selected_symbols,
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
            "repair_long_excluded_symbols": ["ADA/USDT"],
            "repair_short_excluded_symbols": ["LINK/USDT"],
        },
        "risk_per_trade": float(risk_per_trade),
        "fee_rate_per_side_estimate": fee_rate,
        "data_availability": availability,
        "baseline": {
            "summary_source": str(BASELINE_SUMMARY),
            "cell": baseline["cell"],
            "weekly_summary": baseline["weekly_summary"],
            "latest_contract_grade_packet": baseline["latest_contract_grade_packet"],
        },
        "admission_ablation": {
            "source_summary": str(source_expansion_summary_path),
            "method": "artifact-level trade-admission replay over full-expanded combined run",
            "ranked_variants": ranked_variants,
        },
        "combined": {
            "symbols": repair_symbols,
            "cell": repair_cell,
            "candidate_symbol_attribution": candidate_attribution,
        },
        "gate_read": gate_read,
        "artifact": {
            "summary_json": str(summary_path),
            "weekly_packet_json": str(packet_json_path),
            "variants_csv": str(variants_csv_path),
            "attribution_csv": str(attribution_csv_path),
            "weekly_csv": str(weekly_csv_path),
            "report": str(report_path),
        },
    }

    packet_json_path.parent.mkdir(parents=True, exist_ok=True)
    packet_json_path.write_text(json.dumps(weekly_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload, weekly_payload), encoding="utf-8")
    print(f"[SlotBSymbolUniverseExpansionRepair] summary={summary_path}")
    print(f"[SlotBSymbolUniverseExpansionRepair] weekly_packet={packet_json_path}")
    print(f"[SlotBSymbolUniverseExpansionRepair] report={report_path}")
    return summary_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Phase 5/4E-Repair Slot B symbol-universe admission review."
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--window-name", default=DEFAULT_WINDOW)
    parser.add_argument("--candidate-symbols", nargs="+", default=list(DEFAULT_CANDIDATE_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--packet-json-path", type=Path, default=DEFAULT_PACKET_JSON)
    parser.add_argument("--variants-csv-path", type=Path, default=DEFAULT_VARIANTS_CSV)
    parser.add_argument("--attribution-csv-path", type=Path, default=DEFAULT_ATTRIBUTION_CSV)
    parser.add_argument("--weekly-csv-path", type=Path, default=DEFAULT_WEEKLY_CSV)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-expansion-summary-path", type=Path, default=SOURCE_EXPANSION_SUMMARY)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital-usdt", type=float, default=DEFAULT_REVIEW_CAPITAL_USDT)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args(argv)
    run_slot_b_symbol_universe_expansion_repair(
        start=args.start,
        end=args.end,
        window_name=args.window_name,
        candidate_symbols=list(args.candidate_symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=args.results_root,
        summary_path=args.summary_path,
        packet_json_path=args.packet_json_path,
        variants_csv_path=args.variants_csv_path,
        attribution_csv_path=args.attribution_csv_path,
        weekly_csv_path=args.weekly_csv_path,
        report_path=args.report_path,
        source_expansion_summary_path=args.source_expansion_summary_path,
        fee_rate=args.fee_rate,
        review_capital_usdt=args.review_capital_usdt,
        rerun=bool(args.rerun),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
