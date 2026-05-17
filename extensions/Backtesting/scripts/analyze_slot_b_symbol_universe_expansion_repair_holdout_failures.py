"""Attribute Phase 5/4E Slot B repair holdout failures."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
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
    _fee_estimate,
    _fmt,
    _read_csv,
    _read_json,
    _repo_path,
    _week_start_for_ts,
)
from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion import (  # noqa: E402
    _safe_float,
    _safe_int,
    _write_csv,
)
from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion_repair_holdout import (  # noqa: E402
    DEFAULT_SUMMARY as HOLDOUT_SUMMARY,
)


STATUS = (
    "RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_REPAIR_HOLDOUT_FAILURE_"
    "ATTRIBUTED_AND_PARKED"
)
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "slot_b_symbol_universe_expansion_repair_holdout"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_failure_attribution_summary.json"
DEFAULT_SYMBOL_SIDE_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_failure_symbol_side.csv"
DEFAULT_WEEKLY_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_failure_weekly.csv"
DEFAULT_DRAWDOWN_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_repair_holdout_failure_drawdown.csv"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase5_4e_repair_holdout_failure_attribution.md"
REVIEW_CAPITAL_USDT = 10000.0


def _strategy_side(strategy_id: str) -> str:
    if "_short_" in strategy_id:
        return "SHORT"
    return "LONG"


def _trade_after_fee(row: dict[str, str], *, fee_rate: float) -> float:
    return _safe_float(row.get("pnl_usdt")) - _fee_estimate(row, fee_rate=fee_rate)


def _candidate_rows(rows: list[dict[str, str]], candidate_ids: set[str]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("strategy_id") in candidate_ids]


def _trade_metrics(rows: list[dict[str, str]], *, fee_rate: float) -> dict[str, Any]:
    gross = sum(_safe_float(row.get("pnl_usdt")) for row in rows)
    fees = sum(_fee_estimate(row, fee_rate=fee_rate) for row in rows)
    after_fee = gross - fees
    wins = sum(1 for row in rows if _trade_after_fee(row, fee_rate=fee_rate) > 0.0)
    worst = min(
        rows,
        key=lambda row: _trade_after_fee(row, fee_rate=fee_rate),
        default={},
    )
    return {
        "trades": len(rows),
        "gross_pnl_usdt": round(gross, 4),
        "fees_est_usdt": round(fees, 4),
        "after_fee_pnl_usdt": round(after_fee, 4),
        "win_rate_after_fee": round(wins / len(rows), 4) if rows else 0.0,
        "worst_trade_after_fee_usdt": round(_trade_after_fee(worst, fee_rate=fee_rate), 4)
        if worst
        else 0.0,
        "worst_trade_symbol": worst.get("symbol", ""),
        "worst_trade_side": _strategy_side(str(worst.get("strategy_id") or "")) if worst else "",
        "worst_trade_entry_time": worst.get("entry_time", ""),
        "worst_trade_exit_time": worst.get("exit_time", ""),
    }


def _symbol_side_rows(
    *,
    window_key: str,
    candidate_trades: list[dict[str, str]],
    candidate_ids: set[str],
    fee_rate: float,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in candidate_trades:
        strategy_id = str(row.get("strategy_id") or "")
        grouped[(str(row.get("symbol") or ""), _strategy_side(strategy_id), strategy_id)].append(row)

    rows = []
    for (symbol, side, strategy_id), trades in sorted(grouped.items()):
        metrics = _trade_metrics(trades, fee_rate=fee_rate)
        rows.append(
            {
                "window_key": window_key,
                "symbol": symbol,
                "side": side,
                "strategy_id": strategy_id,
                **metrics,
                "losing_symbol_side": metrics["after_fee_pnl_usdt"] < 0.0,
            }
        )

    for strategy_id in sorted(candidate_ids):
        strategy_rows = [row for row in candidate_trades if row.get("strategy_id") == strategy_id]
        metrics = _trade_metrics(strategy_rows, fee_rate=fee_rate)
        rows.append(
            {
                "window_key": window_key,
                "symbol": "ALL",
                "side": _strategy_side(strategy_id),
                "strategy_id": strategy_id,
                **metrics,
                "losing_symbol_side": metrics["after_fee_pnl_usdt"] < 0.0,
            }
        )

    metrics = _trade_metrics(candidate_trades, fee_rate=fee_rate)
    rows.append(
        {
            "window_key": window_key,
            "symbol": "ALL",
            "side": "ALL",
            "strategy_id": "ALL",
            **metrics,
            "losing_symbol_side": metrics["after_fee_pnl_usdt"] < 0.0,
        }
    )
    return rows


def _weekly_net_map(
    rows: list[dict[str, str]],
    *,
    start: str,
    end: str,
    fee_rate: float,
) -> dict[str, dict[str, Any]]:
    weeks, _overflow = _build_week_rows(rows, start=start, end=end, fee_rate=fee_rate)
    return {str(row["week_start"]): row for row in weeks}


def _candidate_weekly_symbol_net(
    rows: list[dict[str, str]],
    *,
    fee_rate: float,
) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        week = _week_start_for_ts(row.get("exit_time"))
        if week is None:
            continue
        key = week.isoformat()
        symbol_side = f"{row.get('symbol')}:{_strategy_side(str(row.get('strategy_id') or ''))}"
        output[key][symbol_side] += _trade_after_fee(row, fee_rate=fee_rate)
    return {
        week: {symbol_side: round(value, 4) for symbol_side, value in sorted(values.items())}
        for week, values in output.items()
    }


def _weekly_rows(
    *,
    window_key: str,
    start: str,
    end: str,
    baseline_trades: list[dict[str, str]],
    repair_trades: list[dict[str, str]],
    candidate_trades: list[dict[str, str]],
    fee_rate: float,
) -> list[dict[str, Any]]:
    baseline = _weekly_net_map(baseline_trades, start=start, end=end, fee_rate=fee_rate)
    repair = _weekly_net_map(repair_trades, start=start, end=end, fee_rate=fee_rate)
    candidate = _weekly_net_map(candidate_trades, start=start, end=end, fee_rate=fee_rate)
    candidate_symbol_net = _candidate_weekly_symbol_net(candidate_trades, fee_rate=fee_rate)
    week_keys = sorted(set(baseline) | set(repair) | set(candidate))
    rows = []
    for week in week_keys:
        baseline_week = baseline.get(week, {})
        repair_week = repair.get(week, {})
        candidate_week = candidate.get(week, {})
        candidate_net = _safe_float(candidate_week.get("net_after_fee_est_usdt"))
        repair_net = _safe_float(repair_week.get("net_after_fee_est_usdt"))
        baseline_net = _safe_float(baseline_week.get("net_after_fee_est_usdt"))
        candidate_symbols = candidate_symbol_net.get(week, {})
        worst_symbol_side = ""
        worst_symbol_side_net = 0.0
        if candidate_symbols:
            worst_symbol_side, worst_symbol_side_net = min(
                candidate_symbols.items(),
                key=lambda item: item[1],
            )
        rows.append(
            {
                "window_key": window_key,
                "week_start": week,
                "baseline_exit_trades": _safe_int(baseline_week.get("exit_trades")),
                "repair_exit_trades": _safe_int(repair_week.get("exit_trades")),
                "candidate_exit_trades": _safe_int(candidate_week.get("exit_trades")),
                "baseline_net_after_fee_usdt": round(baseline_net, 4),
                "repair_net_after_fee_usdt": round(repair_net, 4),
                "candidate_net_after_fee_usdt": round(candidate_net, 4),
                "candidate_week_negative": candidate_net < 0.0,
                "repair_exit_active_negative": _safe_int(repair_week.get("exit_trades")) > 0
                and repair_net <= 0.0,
                "baseline_exit_active_positive": _safe_int(baseline_week.get("exit_trades")) > 0
                and baseline_net > 0.0,
                "candidate_turns_week_negative": repair_net <= 0.0
                and candidate_net < 0.0
                and (baseline_net - candidate_net) > 0.0,
                "worst_candidate_symbol_side": worst_symbol_side,
                "worst_candidate_symbol_side_net_after_fee_usdt": round(worst_symbol_side_net, 4),
                "candidate_symbol_side_net_after_fee_json": json.dumps(
                    candidate_symbols,
                    sort_keys=True,
                ),
            }
        )
    return rows


def _drawdown_proxy(
    *,
    window_key: str,
    repair_trades: list[dict[str, str]],
    candidate_ids: set[str],
    fee_rate: float,
    review_capital_usdt: float,
) -> dict[str, Any]:
    ordered = sorted(
        repair_trades,
        key=lambda row: row.get("exit_time") or row.get("entry_time") or "",
    )
    equity = float(review_capital_usdt)
    peak = equity
    current_segment: list[dict[str, Any]] = []
    worst: dict[str, Any] = {
        "window_key": window_key,
        "max_realized_trade_dd_pct": 0.0,
        "dd_start_time": "",
        "dd_trough_time": "",
        "segment_trades": 0,
        "segment_candidate_trades": 0,
        "segment_net_after_fee_usdt": 0.0,
        "segment_candidate_net_after_fee_usdt": 0.0,
        "segment_candidate_negative_usdt": 0.0,
        "worst_candidate_symbol": "",
        "worst_candidate_side": "",
        "worst_candidate_after_fee_usdt": 0.0,
    }
    segment_start_time = ""
    for row in ordered:
        after_fee = _trade_after_fee(row, fee_rate=fee_rate)
        before = equity
        equity += after_fee
        is_candidate = row.get("strategy_id") in candidate_ids
        item = {
            "row": row,
            "after_fee": after_fee,
            "is_candidate": is_candidate,
            "before": before,
            "after": equity,
        }
        if before >= peak:
            peak = before
            current_segment = []
            segment_start_time = row.get("exit_time") or row.get("entry_time") or ""
        current_segment.append(item)
        if equity >= peak:
            peak = equity
            current_segment = []
            segment_start_time = row.get("exit_time") or row.get("entry_time") or ""
            continue
        dd_pct = (peak - equity) / peak * 100.0 if peak else 0.0
        if dd_pct > _safe_float(worst["max_realized_trade_dd_pct"]):
            candidate_items = [entry for entry in current_segment if entry["is_candidate"]]
            worst_candidate = min(
                candidate_items,
                key=lambda entry: entry["after_fee"],
                default=None,
            )
            worst = {
                "window_key": window_key,
                "max_realized_trade_dd_pct": round(dd_pct, 4),
                "dd_start_time": segment_start_time,
                "dd_trough_time": row.get("exit_time") or row.get("entry_time") or "",
                "segment_trades": len(current_segment),
                "segment_candidate_trades": len(candidate_items),
                "segment_net_after_fee_usdt": round(sum(entry["after_fee"] for entry in current_segment), 4),
                "segment_candidate_net_after_fee_usdt": round(
                    sum(entry["after_fee"] for entry in candidate_items),
                    4,
                ),
                "segment_candidate_negative_usdt": round(
                    sum(entry["after_fee"] for entry in candidate_items if entry["after_fee"] < 0.0),
                    4,
                ),
                "worst_candidate_symbol": worst_candidate["row"].get("symbol", "")
                if worst_candidate
                else "",
                "worst_candidate_side": _strategy_side(
                    str(worst_candidate["row"].get("strategy_id") or "")
                )
                if worst_candidate
                else "",
                "worst_candidate_after_fee_usdt": round(worst_candidate["after_fee"], 4)
                if worst_candidate
                else 0.0,
            }
    return worst


def _window_verdict(
    *,
    window_row: dict[str, Any],
    symbol_side_rows: list[dict[str, Any]],
    weekly_rows: list[dict[str, Any]],
    drawdown_row: dict[str, Any],
) -> dict[str, Any]:
    all_row = next(row for row in symbol_side_rows if row["symbol"] == "ALL" and row["side"] == "ALL")
    losing_symbol_sides = [
        f"{row['symbol']}:{row['side']}"
        for row in symbol_side_rows
        if row["symbol"] != "ALL" and row["losing_symbol_side"]
    ]
    negative_weeks = [row["week_start"] for row in weekly_rows if row["candidate_week_negative"]]
    turn_weeks = [row["week_start"] for row in weekly_rows if row["candidate_turns_week_negative"]]
    failed_gates = str(window_row.get("failed_gates") or "")
    if _safe_float(all_row["after_fee_pnl_usdt"]) < 0.0:
        verdict = "PARK_WINDOW_NEGATIVE_EXPECTANCY"
    elif "max_dd_not_materially_larger" in failed_gates:
        verdict = "PARK_DD_UNSTABLE"
    elif "positive_exit_active_8w_ratio_not_down" in failed_gates:
        verdict = "PARK_WEEKLY_QUALITY_UNSTABLE"
    else:
        verdict = "PARK_HARD_GATE_FAIL"
    return {
        "window_key": window_row["window_key"],
        "failed_gates": failed_gates,
        "candidate_after_fee_pnl_usdt": all_row["after_fee_pnl_usdt"],
        "candidate_trades": all_row["trades"],
        "losing_symbol_sides": losing_symbol_sides,
        "negative_candidate_weeks": negative_weeks,
        "candidate_turns_week_negative_weeks": turn_weeks,
        "max_realized_trade_dd_pct": drawdown_row["max_realized_trade_dd_pct"],
        "dd_candidate_net_after_fee_usdt": drawdown_row["segment_candidate_net_after_fee_usdt"],
        "dd_worst_candidate": (
            f"{drawdown_row['worst_candidate_symbol']}:{drawdown_row['worst_candidate_side']}"
            if drawdown_row["worst_candidate_symbol"]
            else ""
        ),
        "verdict": verdict,
    }


def _render_report(payload: dict[str, Any]) -> str:
    verdicts = payload["window_verdicts"]
    lines = [
        "# Weekly Profit Phase 5 / 4E-Repair Holdout Failure Attribution",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Status: `{STATUS}`",
        "",
        "## Executive Read",
        "",
        "The Slot B symbol-expansion repair should stay parked. The holdout failure is not a single removable bad trade: it combines weekly-quality instability, drawdown expansion, and one fully negative range-low-vol window.",
        "",
        "No runtime defaults, promoted symbols, scanner runtime settings, risk defaults, or thresholds are changed by this attribution.",
        "",
        "## Formal Park Decision",
        "",
        "| item | decision |",
        "| --- | --- |",
        "| 4E lane status | `PARKED_UNLESS_PRE_REGISTERED_REGIME_FILTER_EXISTS` |",
        "| promotion eligibility | `NO` |",
        "| runtime symbol expansion | `NO` |",
        "| static symbol/side admission repair | `INSUFFICIENT` |",
        "| next allowed research action | `PRE_REGISTERED_REGIME_FILTER_ONLY` |",
        "",
        "Reopen condition: a new 4E pass must pre-register a regime/window filter before any rerun, use only runtime-available non-outcome features, and pass the same primary plus holdout hard gates without changing promoted thresholds or runtime defaults.",
        "",
        "## Window Verdicts",
        "",
        "| window | verdict | failed gates | candidate after-fee | losing symbol/sides | negative candidate weeks | DD proxy | DD worst candidate |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | --- |",
    ]
    for row in verdicts:
        lines.append(
            f"| `{row['window_key']}` | `{row['verdict']}` | `{row['failed_gates']}` | "
            f"{_fmt(row['candidate_after_fee_pnl_usdt'])} | "
            f"`{', '.join(row['losing_symbol_sides']) or 'none'}` | "
            f"{len(row['negative_candidate_weeks'])} | "
            f"{_fmt(row['max_realized_trade_dd_pct'])}% | "
            f"`{row['dd_worst_candidate'] or 'none'}` |"
        )

    lines.extend(
        [
            "",
            "## Symbol / Side Failures",
            "",
            "| window | symbol | side | trades | after-fee | win rate | worst trade |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["symbol_side_rows"]:
        if row["symbol"] == "ALL" or not row["losing_symbol_side"]:
            continue
        lines.append(
            f"| `{row['window_key']}` | `{row['symbol']}` | `{row['side']}` | "
            f"{row['trades']} | {_fmt(row['after_fee_pnl_usdt'])} | "
            f"{_fmt(row['win_rate_after_fee'])} | {_fmt(row['worst_trade_after_fee_usdt'])} |"
        )

    lines.extend(
        [
            "",
            "## Worst Weekly Damage",
            "",
            "| window | week | candidate after-fee | repair after-fee | worst candidate symbol/side |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    worst_week_rows = sorted(
        payload["weekly_rows"],
        key=lambda row: _safe_float(row["candidate_net_after_fee_usdt"]),
    )[:8]
    for row in worst_week_rows:
        lines.append(
            f"| `{row['window_key']}` | `{row['week_start']}` | "
            f"{_fmt(row['candidate_net_after_fee_usdt'])} | "
            f"{_fmt(row['repair_net_after_fee_usdt'])} | "
            f"`{row['worst_candidate_symbol_side'] or 'none'}` |"
        )

    lines.extend(
        [
            "",
            "## Closeout Read",
            "",
            "- `range_low_vol` is a hard park signal: all added candidate symbol/sides in that holdout are negative in aggregate.",
            "- `MIXED` keeps positive total candidate PnL, but drawdown expansion is too large for promotion.",
            "- `TRENDING_UP` keeps positive total candidate PnL, but added trades reduce exit-active weekly quality.",
            "- The failure is regime/window-sensitive, so a simple static symbol list is not enough evidence for runtime expansion.",
            "",
            "## Artifacts",
            "",
            f"- Summary JSON: `{payload['artifact']['summary_json']}`",
            f"- Symbol/side CSV: `{payload['artifact']['symbol_side_csv']}`",
            f"- Weekly CSV: `{payload['artifact']['weekly_csv']}`",
            f"- Drawdown CSV: `{payload['artifact']['drawdown_csv']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_failure_attribution(
    *,
    holdout_summary_path: Path = HOLDOUT_SUMMARY,
    summary_path: Path = DEFAULT_SUMMARY,
    symbol_side_csv_path: Path = DEFAULT_SYMBOL_SIDE_CSV,
    weekly_csv_path: Path = DEFAULT_WEEKLY_CSV,
    drawdown_csv_path: Path = DEFAULT_DRAWDOWN_CSV,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = REVIEW_CAPITAL_USDT,
) -> tuple[Path, Path]:
    holdout = _read_json(holdout_summary_path)
    candidate_ids = {
        holdout["strategies"]["candidate_long_repair"],
        holdout["strategies"]["candidate_short_repair"],
    }
    window_rows_by_key = {row["window_key"]: row for row in holdout["windows"]}
    symbol_side_rows: list[dict[str, Any]] = []
    weekly_rows: list[dict[str, Any]] = []
    drawdown_rows: list[dict[str, Any]] = []
    window_verdicts: list[dict[str, Any]] = []

    for window_key, window_payload in holdout["window_payloads"].items():
        baseline_cell = window_payload["baseline"]["cell"]
        repair_cell = window_payload["repair"]["cell"]
        baseline_trades = _read_csv(_repo_path(baseline_cell["artifacts"]["trades"]))
        repair_trades = _read_csv(_repo_path(repair_cell["artifacts"]["trades"]))
        candidate_trades = _candidate_rows(repair_trades, candidate_ids)
        spec = window_payload["window"]
        current_symbol_side = _symbol_side_rows(
            window_key=window_key,
            candidate_trades=candidate_trades,
            candidate_ids=candidate_ids,
            fee_rate=fee_rate,
        )
        current_weekly = _weekly_rows(
            window_key=window_key,
            start=spec["start"],
            end=spec["end"],
            baseline_trades=baseline_trades,
            repair_trades=repair_trades,
            candidate_trades=candidate_trades,
            fee_rate=fee_rate,
        )
        current_drawdown = _drawdown_proxy(
            window_key=window_key,
            repair_trades=repair_trades,
            candidate_ids=candidate_ids,
            fee_rate=fee_rate,
            review_capital_usdt=review_capital_usdt,
        )
        symbol_side_rows.extend(current_symbol_side)
        weekly_rows.extend(current_weekly)
        drawdown_rows.append(current_drawdown)
        window_verdicts.append(
            _window_verdict(
                window_row=window_rows_by_key[window_key],
                symbol_side_rows=current_symbol_side,
                weekly_rows=current_weekly,
                drawdown_row=current_drawdown,
            )
        )

    payload = {
        "schema": "strategy_plugin_slot_b_symbol_universe_expansion_repair_holdout_failure_attribution.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": STATUS,
        "source_summary": str(holdout_summary_path),
        "fee_rate_per_side_estimate": fee_rate,
        "review_capital_usdt": review_capital_usdt,
        "candidate_strategy_ids": sorted(candidate_ids),
        "formal_decision": {
            "lane": "Phase 5 / 4E Slot B symbol-universe expansion",
            "status": "PARKED_UNLESS_PRE_REGISTERED_REGIME_FILTER_EXISTS",
            "promotion_eligible": False,
            "runtime_symbol_expansion_allowed": False,
            "static_symbol_side_admission_repair_sufficient": False,
            "next_allowed_research_action": "PRE_REGISTERED_REGIME_FILTER_ONLY",
            "reopen_conditions": [
                "pre-register the regime/window filter before rerun",
                "use runtime-available non-outcome features only",
                "pass the same primary and holdout hard gates",
                "do not change promoted thresholds or runtime defaults",
            ],
        },
        "window_verdicts": window_verdicts,
        "symbol_side_rows": symbol_side_rows,
        "weekly_rows": weekly_rows,
        "drawdown_rows": drawdown_rows,
        "artifact": {
            "summary_json": str(summary_path),
            "symbol_side_csv": str(symbol_side_csv_path),
            "weekly_csv": str(weekly_csv_path),
            "drawdown_csv": str(drawdown_csv_path),
            "report": str(report_path),
        },
    }

    _write_csv(
        symbol_side_csv_path,
        symbol_side_rows,
        fieldnames=list(symbol_side_rows[0].keys()) if symbol_side_rows else [],
    )
    _write_csv(
        weekly_csv_path,
        weekly_rows,
        fieldnames=list(weekly_rows[0].keys()) if weekly_rows else [],
    )
    _write_csv(
        drawdown_csv_path,
        drawdown_rows,
        fieldnames=list(drawdown_rows[0].keys()) if drawdown_rows else [],
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload), encoding="utf-8")
    print(f"[SlotBRepairFailureAttribution] summary={summary_path}")
    print(f"[SlotBRepairFailureAttribution] report={report_path}")
    return summary_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Attribute Slot B repair holdout failures by symbol/side/week/DD."
    )
    parser.add_argument("--holdout-summary-path", type=Path, default=HOLDOUT_SUMMARY)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--symbol-side-csv-path", type=Path, default=DEFAULT_SYMBOL_SIDE_CSV)
    parser.add_argument("--weekly-csv-path", type=Path, default=DEFAULT_WEEKLY_CSV)
    parser.add_argument("--drawdown-csv-path", type=Path, default=DEFAULT_DRAWDOWN_CSV)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital-usdt", type=float, default=REVIEW_CAPITAL_USDT)
    args = parser.parse_args(argv)
    run_failure_attribution(
        holdout_summary_path=args.holdout_summary_path,
        summary_path=args.summary_path,
        symbol_side_csv_path=args.symbol_side_csv_path,
        weekly_csv_path=args.weekly_csv_path,
        drawdown_csv_path=args.drawdown_csv_path,
        report_path=args.report_path,
        fee_rate=args.fee_rate,
        review_capital_usdt=args.review_capital_usdt,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
