"""Plugin-candidate backtest review helpers.

This module replaces the old EMA/VB lane report path. It only aggregates
artifacts produced by StrategyRuntime plugin backtests; it does not create or
promote runtime Config defaults.
"""

from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Iterable


DEFAULT_WINDOWS = {
    "TRENDING_UP": ("2023-10-01", "2024-03-31"),
    "RANGING": ("2024-12-31", "2025-03-31"),
    "MIXED": ("2025-02-01", "2025-08-31"),
}

REQUIRED_FILES = (
    "summary.json",
    "trades.csv",
    "signal_audit_summary.json",
    "signal_entries.csv",
)

PROMOTION_VERDICTS = {
    "PROMOTE_PLUGIN",
    "KEEP_RESEARCH_ONLY",
    "NEEDS_SECOND_PASS",
}

MISSING_VALUE = "\u2014"


def _json_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _json_load_or_none(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _candidate_ids(candidate_ids: Iterable[str]) -> list[str]:
    ids = [str(item) for item in candidate_ids]
    if not ids:
        raise ValueError("candidate_ids must contain at least one plugin id")
    return ids


def _validate_matrix_completeness(
    output_dir: Path,
    candidate_ids: Iterable[str],
    windows: Iterable[str],
) -> list[dict]:
    missing = []
    for candidate_id in _candidate_ids(candidate_ids):
        for window in windows:
            cell = output_dir / candidate_id / window
            missing_files = [
                name for name in REQUIRED_FILES
                if not (cell / name).exists()
            ]
            if missing_files:
                missing.append({
                    "candidate_id": candidate_id,
                    "window": window,
                    "missing_files": missing_files,
                })
    return missing


def _collect_backtest_run_errors(
    output_dir: Path,
    candidate_ids: Iterable[str],
    windows: Iterable[str],
) -> list[dict]:
    errors = []
    for candidate_id in _candidate_ids(candidate_ids):
        for window in windows:
            summary = _json_load(output_dir / candidate_id / window / "summary.json")
            for error in summary.get("backtest_run_errors") or []:
                payload = dict(error)
                payload["candidate_id"] = candidate_id
                payload["window"] = window
                errors.append(payload)
    return errors


def _collect_trade_invariant_failures(
    output_dir: Path,
    candidate_ids: Iterable[str],
    windows: Iterable[str],
) -> list[dict]:
    failures = []
    for candidate_id in _candidate_ids(candidate_ids):
        for window in windows:
            trades_path = output_dir / candidate_id / window / "trades.csv"
            if not trades_path.exists():
                continue
            with trades_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = {"side", "entry_price", "entry_initial_sl"}
                if not required.issubset(set(reader.fieldnames or [])):
                    continue
                for row_num, row in enumerate(reader, start=2):
                    side = str(row.get("side") or "").upper()
                    try:
                        entry_price = float(row.get("entry_price") or 0.0)
                        entry_sl = float(row.get("entry_initial_sl") or 0.0)
                    except ValueError:
                        continue
                    failed = (
                        side == "LONG" and entry_sl >= entry_price
                    ) or (
                        side == "SHORT" and entry_sl <= entry_price
                    )
                    if failed:
                        failures.append({
                            "candidate_id": candidate_id,
                            "window": window,
                            "row": row_num,
                            "symbol": row.get("symbol"),
                            "side": side,
                            "entry_price": entry_price,
                            "entry_initial_sl": entry_sl,
                        })
    return failures


def _validity_warning_lines(
    incomplete_cells: list[dict],
    run_errors: list[dict],
    trade_invariant_failures: list[dict],
    *,
    allow_incomplete: bool,
) -> list[str]:
    if not incomplete_cells and not run_errors and not trade_invariant_failures:
        return []

    lines = [
        "## Report validity",
        "",
        "- Warning: this report is not promotion-eligible; verdict is forced to `NEEDS_SECOND_PASS`.",
    ]
    if allow_incomplete:
        lines.append("- `--allow-incomplete` was used for debug reporting; promotion remains disabled.")

    if incomplete_cells:
        lines.append(f"- Incomplete matrix: missing {len(incomplete_cells)} candidate/window cells.")
        for cell in incomplete_cells:
            files = ", ".join(cell["missing_files"])
            lines.append(f"  - `{cell['candidate_id']}/{cell['window']}` missing: {files}")

    if run_errors:
        lines.append(f"- Backtest run errors: {len(run_errors)}.")
        for error in run_errors:
            lines.append(
                "  - "
                f"`{error.get('candidate_id')}/{error.get('window')}` "
                f"{error.get('timestamp')} {error.get('stage')} "
                f"{error.get('exc_type')}: {error.get('message')}"
            )

    if trade_invariant_failures:
        lines.append(f"- Trade invariant failures: {len(trade_invariant_failures)}.")
        for failure in trade_invariant_failures[:10]:
            lines.append(
                "  - "
                f"`{failure.get('candidate_id')}/{failure.get('window')}` "
                f"row {failure.get('row')} {failure.get('symbol')} {failure.get('side')} "
                f"entry={failure.get('entry_price'):.8g} "
                f"entry_initial_sl={failure.get('entry_initial_sl'):.8g}"
            )
        if len(trade_invariant_failures) > 10:
            lines.append(f"  - ... {len(trade_invariant_failures) - 10} more")

    lines.append("")
    return lines


def _candidate_summary_rows(output_dir: Path, candidate_ids: Iterable[str], windows: Iterable[str]) -> list[str]:
    rows = ["| candidate_id | windows | trades | net_pnl | max_dd_pct |", "| --- | ---: | ---: | ---: | ---: |"]
    for candidate_id in _candidate_ids(candidate_ids):
        trades = 0
        net_pnl = 0.0
        max_dd = 0.0
        completed = 0
        for window in windows:
            summary = _json_load(output_dir / candidate_id / window / "summary.json")
            if not summary:
                continue
            completed += 1
            trades += int(summary.get("total_trades", 0) or 0)
            net_pnl += _net_pnl(output_dir / candidate_id / window, summary)
            max_dd = max(max_dd, float(summary.get("max_drawdown_pct", 0.0) or 0.0))
        rows.append(f"| `{candidate_id}` | {completed} | {trades} | {net_pnl:.4f} | {max_dd:.4f} |")
    return rows


def _candidate_per_window_rows(output_dir: Path, candidate_ids: Iterable[str], windows: Iterable[str]) -> list[str]:
    rows = [
        "| candidate_id | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for candidate_id in _candidate_ids(candidate_ids):
        for window in windows:
            cell_dir = output_dir / candidate_id / window
            summary = _json_load_or_none(cell_dir / "summary.json")
            if not summary:
                rows.append(
                    f"| `{candidate_id}` | {window} (missing) | "
                    f"{MISSING_VALUE} | {MISSING_VALUE} | {MISSING_VALUE} | {MISSING_VALUE} | {MISSING_VALUE} |"
                )
                continue

            trades = int(summary.get("total_trades", 0) or 0)
            net_pnl = _net_pnl(cell_dir, summary)
            max_dd = float(summary.get("max_drawdown_pct", 0.0) or 0.0)
            run_errors = int(summary.get("backtest_run_error_count", 0) or 0)
            entry_stop_violations = _entry_stop_violations(cell_dir / "trades.csv")
            rows.append(
                f"| `{candidate_id}` | {window} | {trades} | {net_pnl:.4f} | "
                f"{max_dd:.4f} | {run_errors} | {entry_stop_violations} |"
            )
    return rows


def _net_pnl(cell_dir: Path, summary: dict) -> float:
    if "net_pnl" in summary:
        return float(summary.get("net_pnl") or 0.0)
    if "total_pnl" in summary:
        return float(summary.get("total_pnl") or 0.0)

    trades_path = cell_dir / "trades.csv"
    if not trades_path.exists():
        return 0.0
    with trades_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return sum(float(row.get("pnl_usdt") or 0.0) for row in reader)


def _entry_stop_violations(trades_path: Path) -> int:
    if not trades_path.exists():
        return 0
    with trades_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"side", "entry_price", "entry_initial_sl"}
        if not required.issubset(set(reader.fieldnames or [])):
            return 0
        violations = 0
        for row in reader:
            try:
                entry_price = float(row.get("entry_price") or 0.0)
                entry_sl = float(row.get("entry_initial_sl") or 0.0)
            except ValueError:
                continue
            side = str(row.get("side") or "").upper()
            if side == "LONG" and entry_sl >= entry_price:
                violations += 1
            if side == "SHORT" and entry_sl <= entry_price:
                violations += 1
        return violations


def write_candidate_review_report(
    repo_root: Path,
    output_dir: Path,
    candidate_ids: Iterable[str],
    *,
    windows: dict[str, tuple[str, str]] | None = None,
    allow_incomplete: bool = False,
) -> str:
    """Write a promotion-gated report for StrategyRuntime plugin candidates."""
    windows = windows or DEFAULT_WINDOWS
    window_names = list(windows)
    candidate_ids = _candidate_ids(candidate_ids)
    incomplete_cells = _validate_matrix_completeness(output_dir, candidate_ids, window_names)
    run_errors = _collect_backtest_run_errors(output_dir, candidate_ids, window_names)
    trade_invariant_failures = _collect_trade_invariant_failures(
        output_dir,
        candidate_ids,
        window_names,
    )
    verdict = (
        "NEEDS_SECOND_PASS"
        if incomplete_cells or run_errors or trade_invariant_failures
        else "KEEP_RESEARCH_ONLY"
    )

    report_path = repo_root / "reports" / "strategy_plugin_candidate_review.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Strategy Plugin Candidate Review",
        "",
        "## Executive read",
        "",
        f"- Verdict: `{verdict}`.",
        "- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.",
        "- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.",
        "- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.",
        "",
        *_validity_warning_lines(
            incomplete_cells,
            run_errors,
            trade_invariant_failures,
            allow_incomplete=allow_incomplete,
        ),
        "## Candidate summary",
        "",
        *_candidate_summary_rows(output_dir, candidate_ids, window_names),
        "",
        "## Per-Window Detail",
        "",
        *_candidate_per_window_rows(output_dir, candidate_ids, window_names),
        "",
        "## Run settings",
        "",
        f"- Results root: `{output_dir}`.",
        "- Backtests must use per-run Config overrides and StrategyRuntime central risk path.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdict
