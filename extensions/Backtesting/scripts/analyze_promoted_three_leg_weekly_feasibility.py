"""Build weekly feasibility evidence for the promoted three-leg portfolio."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


SOURCE_SUMMARY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "portfolio_ab_short_ablation_summary.json"
)
DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "promoted_three_leg_weekly_feasibility_summary.json"
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "promoted_three_leg_weekly_feasibility_review.md"

TARGET_VARIANT = "slot_b_short_overlay"
PRIMARY_MATRIX = "custom"
PRIMARY_WINDOW = "2026_01_01_2026_04_30"
DEFAULT_FEE_RATE = 0.0004
PARTICIPATION_SCREEN_RATIO = 0.5
POSITIVE_WEEK_SCREEN_RATIO = 0.5

SLOT_A_LONG = (
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_B_LONG = "donchian_range_fade_4h_range_width_cv_013"
SLOT_B_SHORT = "donchian_range_fade_4h_range_width_cv_013_short"

SLOT_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _repo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


def _parse_date(raw: str) -> date:
    return date.fromisoformat(str(raw))


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _week_start_for_date(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _week_start_for_ts(raw: Any) -> date | None:
    ts = _parse_ts(raw)
    return None if ts is None else _week_start_for_date(ts.date())


def _week_keys(start: str, end: str) -> list[date]:
    current = _week_start_for_date(_parse_date(start))
    last = _week_start_for_date(_parse_date(end))
    weeks: list[date] = []
    while current <= last:
        weeks.append(current)
        current += timedelta(days=7)
    return weeks


def _fee_estimate(row: dict[str, Any], *, fee_rate: float) -> float:
    total_size = _safe_float(row.get("total_size")) or _safe_float(row.get("original_size"))
    entry_price = _safe_float(row.get("entry_price"))
    exit_price = _safe_float(row.get("exit_price"))
    return (entry_price * total_size + exit_price * total_size) * fee_rate


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
        "slot_gross_pnl_usdt": defaultdict(float),
        "slot_fees_est_usdt": defaultdict(float),
        "slot_net_after_fee_est_usdt": defaultdict(float),
        "symbol_gross_pnl_usdt": defaultdict(float),
        "symbol_fees_est_usdt": defaultdict(float),
        "symbol_net_after_fee_est_usdt": defaultdict(float),
    }


def _round_nested(values: dict[str, float]) -> dict[str, float]:
    return {str(key): round(float(value), 4) for key, value in sorted(values.items())}


def _finalize_week_row(row: dict[str, Any]) -> dict[str, Any]:
    row["gross_pnl_usdt"] = round(float(row["gross_pnl_usdt"]), 4)
    row["fees_est_usdt"] = round(float(row["fees_est_usdt"]), 4)
    row["net_after_fee_est_usdt"] = round(float(row["net_after_fee_est_usdt"]), 4)
    row["slot_gross_pnl_usdt"] = _round_nested(row["slot_gross_pnl_usdt"])
    row["slot_fees_est_usdt"] = _round_nested(row["slot_fees_est_usdt"])
    row["slot_net_after_fee_est_usdt"] = _round_nested(row["slot_net_after_fee_est_usdt"])
    row["symbol_gross_pnl_usdt"] = _round_nested(row["symbol_gross_pnl_usdt"])
    row["symbol_fees_est_usdt"] = _round_nested(row["symbol_fees_est_usdt"])
    row["symbol_net_after_fee_est_usdt"] = _round_nested(row["symbol_net_after_fee_est_usdt"])
    row["gross_positive_week"] = row["gross_pnl_usdt"] > 0.0
    row["after_fee_positive_week"] = row["net_after_fee_est_usdt"] > 0.0
    row["after_fee_losing_week"] = row["net_after_fee_est_usdt"] < 0.0
    return row


def _build_week_rows(
    rows: list[dict[str, Any]],
    *,
    start: str,
    end: str,
    fee_rate: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    weeks = _week_keys(start, end)
    buckets = {week: _new_week_row(week) for week in weeks}
    overflow = {"entry_outside_window": 0, "exit_outside_window": 0}

    for row in rows:
        entry_week = _week_start_for_ts(row.get("entry_time"))
        exit_week = _week_start_for_ts(row.get("exit_time"))
        if entry_week in buckets:
            buckets[entry_week]["entry_trades"] += 1
        else:
            overflow["entry_outside_window"] += 1

        if exit_week not in buckets:
            overflow["exit_outside_window"] += 1
            continue

        pnl = _safe_float(row.get("pnl_usdt"))
        fees_est = _fee_estimate(row, fee_rate=fee_rate)
        net_after_fee = pnl - fees_est
        slot = SLOT_LABELS.get(str(row.get("strategy_id") or ""), "Unknown")
        symbol = str(row.get("symbol") or "UNKNOWN")
        bucket = buckets[exit_week]

        bucket["exit_trades"] += 1
        bucket["gross_pnl_usdt"] += pnl
        bucket["fees_est_usdt"] += fees_est
        bucket["net_after_fee_est_usdt"] += net_after_fee
        bucket["slot_gross_pnl_usdt"][slot] += pnl
        bucket["slot_fees_est_usdt"][slot] += fees_est
        bucket["slot_net_after_fee_est_usdt"][slot] += net_after_fee
        bucket["symbol_gross_pnl_usdt"][symbol] += pnl
        bucket["symbol_fees_est_usdt"][symbol] += fees_est
        bucket["symbol_net_after_fee_est_usdt"][symbol] += net_after_fee

    return ([_finalize_week_row(buckets[week]) for week in weeks], overflow)


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


def _median(values: list[float]) -> float:
    return round(float(median(values)), 4) if values else 0.0


def _distribution(values: list[int]) -> dict[str, int]:
    counts = Counter(values)
    return {str(key): int(counts[key]) for key in sorted(counts)}


def _aggregate_nested(
    week_rows: list[dict[str, Any]],
    field: str,
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in week_rows:
        for key, value in row[field].items():
            totals[str(key)] += _safe_float(value)
    return _round_nested(totals)


def _summarize_week_rows(week_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_weeks = len(week_rows)
    entry_counts = [int(row["entry_trades"]) for row in week_rows]
    exit_counts = [int(row["exit_trades"]) for row in week_rows]
    gross_pnls = [_safe_float(row["gross_pnl_usdt"]) for row in week_rows]
    after_fee_pnls = [_safe_float(row["net_after_fee_est_usdt"]) for row in week_rows]
    entry_active = [count > 0 for count in entry_counts]
    exit_active = [count > 0 for count in exit_counts]
    gross_positive = [pnl > 0.0 for pnl in gross_pnls]
    after_fee_positive = [pnl > 0.0 for pnl in after_fee_pnls]
    after_fee_losing = [pnl < 0.0 for pnl in after_fee_pnls]
    after_fee_nonpositive = [pnl <= 0.0 for pnl in after_fee_pnls]

    active_entry_weeks = sum(entry_active)
    active_exit_weeks = sum(exit_active)
    gross_positive_weeks = sum(gross_positive)
    after_fee_positive_weeks = sum(after_fee_positive)

    return {
        "weeks": total_weeks,
        "entry_trades": sum(entry_counts),
        "exit_trades": sum(exit_counts),
        "gross_pnl_usdt": round(sum(gross_pnls), 4),
        "fees_est_usdt": round(sum(_safe_float(row["fees_est_usdt"]) for row in week_rows), 4),
        "net_after_fee_est_usdt": round(sum(after_fee_pnls), 4),
        "active_entry_weeks": active_entry_weeks,
        "active_exit_weeks": active_exit_weeks,
        "zero_entry_week_count": total_weeks - active_entry_weeks,
        "zero_exit_week_count": total_weeks - active_exit_weeks,
        "active_entry_week_ratio": round(active_entry_weeks / total_weeks, 4)
        if total_weeks
        else 0.0,
        "active_exit_week_ratio": round(active_exit_weeks / total_weeks, 4)
        if total_weeks
        else 0.0,
        "gross_positive_week_count": gross_positive_weeks,
        "after_fee_positive_week_count": after_fee_positive_weeks,
        "gross_positive_week_ratio_all": round(gross_positive_weeks / total_weeks, 4)
        if total_weeks
        else 0.0,
        "after_fee_positive_week_ratio_all": round(after_fee_positive_weeks / total_weeks, 4)
        if total_weeks
        else 0.0,
        "gross_positive_week_ratio_exit_active": round(
            gross_positive_weeks / active_exit_weeks, 4
        )
        if active_exit_weeks
        else 0.0,
        "after_fee_positive_week_ratio_exit_active": round(
            after_fee_positive_weeks / active_exit_weeks, 4
        )
        if active_exit_weeks
        else 0.0,
        "median_entry_trades_per_week_all": _median([float(value) for value in entry_counts]),
        "median_exit_trades_per_week_all": _median([float(value) for value in exit_counts]),
        "weekly_entry_trade_count_distribution": _distribution(entry_counts),
        "weekly_exit_trade_count_distribution": _distribution(exit_counts),
        "median_weekly_gross_pnl_usdt": _median(gross_pnls),
        "median_weekly_after_fee_pnl_est_usdt": _median(after_fee_pnls),
        "worst_week_gross_pnl_usdt": round(min(gross_pnls), 4) if gross_pnls else 0.0,
        "worst_week_after_fee_pnl_est_usdt": round(min(after_fee_pnls), 4)
        if after_fee_pnls
        else 0.0,
        "best_week_gross_pnl_usdt": round(max(gross_pnls), 4) if gross_pnls else 0.0,
        "best_week_after_fee_pnl_est_usdt": round(max(after_fee_pnls), 4)
        if after_fee_pnls
        else 0.0,
        "max_consecutive_losing_weeks_after_fee_est": _longest_streak(after_fee_losing),
        "max_consecutive_nonpositive_weeks_after_fee_est": _longest_streak(
            after_fee_nonpositive
        ),
        "slot_gross_pnl_usdt": _aggregate_nested(week_rows, "slot_gross_pnl_usdt"),
        "slot_fees_est_usdt": _aggregate_nested(week_rows, "slot_fees_est_usdt"),
        "slot_net_after_fee_est_usdt": _aggregate_nested(
            week_rows, "slot_net_after_fee_est_usdt"
        ),
        "symbol_gross_pnl_usdt": _aggregate_nested(week_rows, "symbol_gross_pnl_usdt"),
        "symbol_fees_est_usdt": _aggregate_nested(week_rows, "symbol_fees_est_usdt"),
        "symbol_net_after_fee_est_usdt": _aggregate_nested(
            week_rows, "symbol_net_after_fee_est_usdt"
        ),
    }


def _window_payload(
    matrix: str,
    window_name: str,
    cell: dict[str, Any],
    *,
    fee_rate: float,
) -> dict[str, Any]:
    window = cell.get("window") or {}
    start = str(window.get("start") or "")
    end = str(window.get("end") or "")
    if not start or not end:
        raise ValueError(f"missing window bounds for {matrix}/{window_name}")

    artifacts = cell.get("artifacts") or {}
    trade_path = _repo_path(str(artifacts.get("trades") or ""))
    rows = _read_csv(trade_path)
    weekly_rows, overflow = _build_week_rows(rows, start=start, end=end, fee_rate=fee_rate)

    return {
        "matrix": matrix,
        "window": window_name,
        "start": start,
        "end": end,
        "artifacts": {
            "trades": str(trade_path),
            "summary": str(_repo_path(str(artifacts.get("summary") or ""))),
        },
        "portfolio_reference": dict(cell.get("portfolio") or {}),
        "overflow": overflow,
        "summary": _summarize_week_rows(weekly_rows),
        "weeks": weekly_rows,
    }


def _analysis_payload(
    source: dict[str, Any],
    *,
    source_path: Path,
    fee_rate: float,
) -> dict[str, Any]:
    variant_matrices = source.get("matrices", {}).get(TARGET_VARIANT, {})
    if not variant_matrices:
        raise ValueError(f"missing matrices for variant: {TARGET_VARIANT}")

    windows: list[dict[str, Any]] = []
    for matrix in ("custom", "default", "supplemental"):
        for window_name, cell in (variant_matrices.get(matrix) or {}).items():
            windows.append(_window_payload(matrix, window_name, cell, fee_rate=fee_rate))

    primary = next(
        (
            window
            for window in windows
            if window["matrix"] == PRIMARY_MATRIX and window["window"] == PRIMARY_WINDOW
        ),
        None,
    )
    if primary is None:
        raise ValueError(f"missing primary feasibility window: {PRIMARY_MATRIX}/{PRIMARY_WINDOW}")

    return {
        "schema": "strategy_plugin_promoted_three_leg_weekly_feasibility.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_summary": str(source_path),
        "source_generated_at": source.get("generated_at"),
        "variant": TARGET_VARIANT,
        "fee_rate_per_side_estimate": fee_rate,
        "decision_screen": {
            "status": "exploratory_only_not_a_phase_2_kpi_contract",
            "participation_screen_ratio": PARTICIPATION_SCREEN_RATIO,
            "positive_week_screen_ratio_all": POSITIVE_WEEK_SCREEN_RATIO,
        },
        "method": {
            "week_boundary": "UTC ISO weeks anchored on Monday",
            "participation_basis": "entry week",
            "economic_outcome_basis": "exit week realized pnl",
            "fee_estimate": (
                "entry_price * total_size + exit_price * total_size, multiplied by fee_rate"
            ),
            "pooling_rule": (
                "Default and supplemental matrices are overlapping scenario windows and are "
                "reported per window only; they are not merged into one continuous weekly series."
            ),
        },
        "primary_window_key": f"{PRIMARY_MATRIX}/{PRIMARY_WINDOW}",
        "primary_window": primary,
        "windows": windows,
    }


def _fmt(value: Any, *, places: int = 4) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{places}f}"
    return str(value)


def _summary_row(window: dict[str, Any]) -> str:
    summary = window["summary"]
    return (
        f"| `{window['matrix']}` | `{window['window']}` | {summary['weeks']} | "
        f"{summary['entry_trades']} | {summary['exit_trades']} | "
        f"{_fmt(summary['active_entry_week_ratio'])} | "
        f"{_fmt(summary['after_fee_positive_week_ratio_all'])} | "
        f"{_fmt(summary['after_fee_positive_week_ratio_exit_active'])} | "
        f"{_fmt(summary['net_after_fee_est_usdt'])} | "
        f"{_fmt(summary['worst_week_after_fee_pnl_est_usdt'])} | "
        f"{summary['max_consecutive_nonpositive_weeks_after_fee_est']} |"
    )


def _kv_rows(values: dict[str, float]) -> list[str]:
    if not values:
        return ["| `none` | 0.0000 |"]
    return [f"| `{key}` | {_fmt(value)} |" for key, value in sorted(values.items())]


def _decision_profile(primary: dict[str, Any]) -> dict[str, Any]:
    summary = primary["summary"]
    participation_low = summary["active_entry_week_ratio"] < PARTICIPATION_SCREEN_RATIO
    positive_all_low = (
        summary["after_fee_positive_week_ratio_all"] < POSITIVE_WEEK_SCREEN_RATIO
    )
    net_positive = summary["net_after_fee_est_usdt"] > 0.0
    if participation_low and net_positive:
        return {
            "label": "Participation gap dominates.",
            "read": (
                "Participation gap dominates. The contiguous 2026 window remains "
                "net-positive after the fee estimate, but the portfolio does not "
                "touch enough calendar weeks to support the weekly-machine objective."
            ),
            "why": [
                (
                    "The contiguous 2026 read remains positive after the fee estimate, "
                    "so the promoted three-leg baseline is not failing first on outright expectancy."
                ),
                (
                    "The same contiguous read still has too many zero-entry weeks to "
                    "support a weekly-profit operating claim."
                ),
                (
                    "Positive-week density improves when measured only on active exit "
                    "weeks, which suggests the first business gap is cadence coverage "
                    "rather than immediate alpha collapse."
                ),
            ],
        }
    if positive_all_low:
        return {
            "label": "Weekly outcome stability gap dominates.",
            "read": (
                "Weekly outcome stability is the first visible gap. The portfolio "
                "participates, but after-fee positive-week density is not yet strong "
                "enough for a weekly-profit operating claim."
            ),
            "why": [
                (
                    "The weekly cadence clears the initial participation screen more "
                    "comfortably than the all-week positive-rate screen."
                ),
                (
                    "The first formal KPI contract should therefore define loss-week "
                    "tolerance before activating a frequency-complement lane."
                ),
            ],
        }
    return {
        "label": "Baseline is directionally viable.",
        "read": (
            "The baseline is directionally viable for the weekly objective, subject "
            "to Phase 2 converting this read into formal KPI gates."
        ),
        "why": [
            (
                "The primary contiguous read does not immediately fail the soft "
                "participation or positive-week screens used by this Phase 1 memo."
            ),
            (
                "Phase 2 should still formalize acceptance thresholds before anyone "
                "claims the portfolio is production-ready for the weekly objective."
            ),
        ],
    }


def _report_text(payload: dict[str, Any]) -> str:
    primary = payload["primary_window"]
    summary = primary["summary"]
    decision = _decision_profile(primary)
    scenario_windows = [
        window
        for window in payload["windows"]
        if window["matrix"] in {"default", "supplemental"}
    ]

    lines = [
        "# Promoted Three-Leg Weekly Feasibility Review",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `PHASE_1_WEEKLY_FEASIBILITY_REVIEW_COMPLETE`",
        "",
        "## Executive Read",
        "",
        decision["read"],
        "",
        "The promoted runtime portfolio remains:",
        "",
        f"- Slot A LONG: `{SLOT_A_LONG}`",
        f"- Slot B LONG: `{SLOT_B_LONG}`",
        f"- Slot B SHORT: `{SLOT_B_SHORT}`",
        "",
        "## Method",
        "",
        f"- Source summary: `{payload['source_summary']}`",
        f"- Primary cadence anchor: `{payload['primary_window_key']}`",
        "- Calendar slicing uses UTC ISO weeks anchored on Monday.",
        "- Participation uses entry week; realized weekly outcome uses exit week.",
        (
        "- Week buckets overlap the requested date window; the first and last "
            "calendar buckets can therefore be partial weeks."
        ),
        (
            "- The Phase 1 decision label uses exploratory screens only, not the "
            "Phase 2 KPI contract: active-entry week ratio `< 0.5000` and all-week "
            "after-fee positive ratio `< 0.5000` flag the first visible gap."
        ),
        (
            "- Fee estimate uses the existing backtest convention: "
            f"`{payload['fee_rate_per_side_estimate']}` per side on entry and exit notional."
        ),
        "- Default and supplemental matrices overlap by design, so they are reviewed per window only.",
        "",
        "## Primary Contiguous Read",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| weeks | {summary['weeks']} |",
        f"| entry trades | {summary['entry_trades']} |",
        f"| exit trades | {summary['exit_trades']} |",
        f"| active entry weeks | {summary['active_entry_weeks']} |",
        f"| zero-entry weeks | {summary['zero_entry_week_count']} |",
        f"| active entry week ratio | {_fmt(summary['active_entry_week_ratio'])} |",
        f"| after-fee positive week ratio, all weeks | {_fmt(summary['after_fee_positive_week_ratio_all'])} |",
        f"| after-fee positive week ratio, exit-active weeks | {_fmt(summary['after_fee_positive_week_ratio_exit_active'])} |",
        f"| gross pnl | {_fmt(summary['gross_pnl_usdt'])} |",
        f"| fee estimate | {_fmt(summary['fees_est_usdt'])} |",
        f"| net after fee estimate | {_fmt(summary['net_after_fee_est_usdt'])} |",
        f"| worst after-fee week | {_fmt(summary['worst_week_after_fee_pnl_est_usdt'])} |",
        f"| longest losing-week streak, after fee | {summary['max_consecutive_losing_weeks_after_fee_est']} |",
        (
            f"| longest non-positive-week streak, after fee | "
            f"{summary['max_consecutive_nonpositive_weeks_after_fee_est']} |"
        ),
        "",
        "## Primary Weekly Count Distribution",
        "",
        "| trade count in week | entry-week count | exit-week count |",
        "| ---: | ---: | ---: |",
    ]

    entry_dist = summary["weekly_entry_trade_count_distribution"]
    exit_dist = summary["weekly_exit_trade_count_distribution"]
    dist_keys = sorted({int(key) for key in entry_dist} | {int(key) for key in exit_dist})
    for key in dist_keys:
        lines.append(
            f"| {key} | {entry_dist.get(str(key), 0)} | {exit_dist.get(str(key), 0)} |"
        )

    lines.extend(
        [
            "",
            "## Primary Contribution Attribution",
            "",
            "### Slot Net After Fee Estimate",
            "",
            "| slot | net after fee estimate |",
            "| --- | ---: |",
            *_kv_rows(summary["slot_net_after_fee_est_usdt"]),
            "",
            "### Symbol Net After Fee Estimate",
            "",
            "| symbol | net after fee estimate |",
            "| --- | ---: |",
            *_kv_rows(summary["symbol_net_after_fee_est_usdt"]),
            "",
            "## Scenario Window Feasibility",
            "",
            "| matrix | window | weeks | entry trades | exit trades | active-entry ratio | positive-week ratio, all | positive-week ratio, active exits | net after fee est | worst week est | longest non-positive streak |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(_summary_row(window) for window in scenario_windows)

    lines.extend(
        [
            "",
            "## Phase 1 Decision",
            "",
            "Phase 1 answers the roadmap gate as:",
            "",
        f"> **{decision['label']}**",
        "",
        "Why:",
        "",
        *[f"- {item}" for item in decision["why"]],
            "",
            "## Phase 2 Input",
            "",
            "The KPI contract should now formalize:",
            "",
            "- minimum acceptable active-entry week ratio",
            "- maximum acceptable zero-entry week streak",
            "- all-week versus active-week positive-rate distinction",
            "- after-fee weekly loss tolerance",
            "- whether Phase 4 research should target frequency complement before edge repair",
            "",
            "## Artifacts",
            "",
            (
                f"- Machine-readable local summary: `{DEFAULT_JSON}` "
                "(generated under the ignored `extensions/Backtesting/results/*` tree)"
            ),
            f"- Source promotion summary: `{payload['source_summary']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def analyze_weekly_feasibility(
    *,
    source_path: Path = SOURCE_SUMMARY,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> dict[str, Any]:
    source = _read_json(source_path)
    payload = _analysis_payload(source, source_path=source_path, fee_rate=fee_rate)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(_report_text(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze promoted three-leg weekly feasibility from existing artifacts."
    )
    parser.add_argument("--source", type=Path, default=SOURCE_SUMMARY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    args = parser.parse_args()
    analyze_weekly_feasibility(
        source_path=args.source,
        json_path=args.json_out,
        report_path=args.report_out,
        fee_rate=args.fee_rate,
    )


if __name__ == "__main__":
    main()
