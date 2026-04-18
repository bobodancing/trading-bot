"""Plugin-candidate backtest review helpers.

This module replaces the old EMA/VB lane report path. It only aggregates
artifacts produced by StrategyRuntime plugin backtests; it does not create or
promote runtime Config defaults.
"""

from __future__ import annotations

import json
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


def _json_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


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


def _validity_warning_lines(
    incomplete_cells: list[dict],
    run_errors: list[dict],
    *,
    allow_incomplete: bool,
) -> list[str]:
    if not incomplete_cells and not run_errors:
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
            net_pnl += float(summary.get("net_pnl", summary.get("total_pnl", 0.0)) or 0.0)
            max_dd = max(max_dd, float(summary.get("max_drawdown_pct", 0.0) or 0.0))
        rows.append(f"| `{candidate_id}` | {completed} | {trades} | {net_pnl:.4f} | {max_dd:.4f} |")
    return rows


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
    verdict = "NEEDS_SECOND_PASS" if incomplete_cells or run_errors else "KEEP_RESEARCH_ONLY"

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
        "",
        *_validity_warning_lines(
            incomplete_cells,
            run_errors,
            allow_incomplete=allow_incomplete,
        ),
        "## Candidate summary",
        "",
        *_candidate_summary_rows(output_dir, candidate_ids, window_names),
        "",
        "## Run settings",
        "",
        f"- Results root: `{output_dir}`.",
        "- Backtests must use per-run Config overrides and StrategyRuntime central risk path.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdict
