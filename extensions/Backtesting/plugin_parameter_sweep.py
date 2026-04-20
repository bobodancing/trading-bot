"""Backtest-only parameter sweep helpers for StrategyRuntime plugins.

Sweeps are second-pass research artifacts. They compare a small explicit grid
of plugin params without changing runtime Config defaults or the plugin
catalog source.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterable, Mapping
from itertools import product
from pathlib import Path
from typing import Any


MAX_SWEEP_CELLS = 25
SWEEP_REVIEW_STATUS = "RESEARCH_SWEEP_ONLY"


def slugify(value: str) -> str:
    """Return a stable filesystem/report slug."""
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip()).strip("_")
    return slug or "sweep"


def normalize_sweep_grid(grid: Mapping[str, Iterable[Any]]) -> dict[str, list[Any]]:
    """Validate the explicit small-grid schema."""
    if not isinstance(grid, Mapping):
        raise ValueError("sweep grid must be a mapping")
    normalized: dict[str, list[Any]] = {}
    for key, values in (grid or {}).items():
        key = str(key)
        if not key:
            raise ValueError("sweep grid param names must be non-empty")
        if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
            raise ValueError(f"sweep grid param {key} must be a non-empty list")
        items = list(values)
        if not items:
            raise ValueError(f"sweep grid param {key} must be a non-empty list")
        normalized[key] = items
    if not normalized:
        raise ValueError("sweep grid must contain at least one param")
    return normalized


def build_sweep_cells(grid: Mapping[str, Iterable[Any]], *, max_cells: int = MAX_SWEEP_CELLS) -> list[dict]:
    """Expand an explicit grid into deterministic cell descriptors."""
    normalized = normalize_sweep_grid(grid)
    keys = list(normalized)
    cells = [
        {
            "cell_id": f"cell_{idx:03d}",
            "params": dict(zip(keys, combo)),
        }
        for idx, combo in enumerate(product(*(normalized[key] for key in keys)), start=1)
    ]
    if len(cells) > max_cells:
        raise ValueError(f"sweep grid has {len(cells)} cells; max allowed is {max_cells}")
    return cells


def write_sweep_manifest(
    sweep_dir: Path,
    *,
    sweep_id: str,
    candidate_id: str,
    grid: Mapping[str, Iterable[Any]],
    cells: list[dict],
    windows: Mapping[str, tuple[str, str]],
    symbols: Iterable[str],
) -> Path:
    """Write an artifact trace that maps cell ids back to exact params."""
    sweep_dir = Path(sweep_dir)
    sweep_dir.mkdir(parents=True, exist_ok=True)
    path = sweep_dir / "sweep_manifest.json"
    payload = {
        "schema": "strategy_plugin_parameter_sweep.v1",
        "sweep_id": sweep_id,
        "candidate_id": candidate_id,
        "status": SWEEP_REVIEW_STATUS,
        "grid": normalize_sweep_grid(grid),
        "cells": cells,
        "windows": {name: {"start": start, "end": end} for name, (start, end) in windows.items()},
        "symbols": list(symbols),
        "promotion_eligible": False,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_parameter_sweep_report(
    repo_root: Path,
    sweep_dir: Path,
    *,
    sweep_id: str,
    candidate_id: str,
    cells: list[dict],
    windows: Mapping[str, tuple[str, str]],
) -> Path:
    """Write a research-only parameter sweep report outside the baseline report."""
    repo_root = Path(repo_root)
    sweep_dir = Path(sweep_dir)
    report_path = repo_root / "reports" / f"strategy_plugin_parameter_sweep_{slugify(sweep_id)}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows = _sweep_summary_rows(sweep_dir, candidate_id, cells, windows)
    lines = [
        "# Strategy Plugin Parameter Sweep",
        "",
        "## Executive read",
        "",
        f"- Status: `{SWEEP_REVIEW_STATUS}`.",
        "- This is second-pass research for an existing cartridge, not an optimizer.",
        "- Results do not modify runtime `Config` defaults or `_catalog.py`.",
        "- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.",
        "",
        "## Sweep settings",
        "",
        f"- Sweep id: `{sweep_id}`.",
        f"- Candidate: `{candidate_id}`.",
        f"- Results root: `{sweep_dir}`.",
        f"- Windows: {', '.join(f'`{name}`' for name in windows)}.",
        "",
        "## Cell Summary",
        "",
        "| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *rows,
        "",
        "## Interpretation Guardrails",
        "",
        "- Compare cells as diagnostics only; there is no objective-function winner.",
        "- A cleaner cell may justify another locked candidate review, not promotion.",
        "- Any run errors or invariant failures keep the cell in investigation status.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _sweep_summary_rows(
    sweep_dir: Path,
    candidate_id: str,
    cells: list[dict],
    windows: Mapping[str, tuple[str, str]],
) -> list[str]:
    rows = []
    for cell in cells:
        cell_id = str(cell["cell_id"])
        trades = 0
        net_pnl = 0.0
        max_dd = 0.0
        completed = 0
        run_errors = 0
        entry_stop_violations = 0
        for window_name in windows:
            cell_dir = sweep_dir / cell_id / window_name
            summary = _json_load(cell_dir / "summary.json")
            if not summary:
                continue
            completed += 1
            trades += int(summary.get("total_trades", 0) or 0)
            net_pnl += _net_pnl(cell_dir, summary)
            max_dd = max(max_dd, float(summary.get("max_drawdown_pct", 0.0) or 0.0))
            run_errors += int(summary.get("backtest_run_error_count", 0) or 0)
            entry_stop_violations += _entry_stop_violations(cell_dir / "trades.csv")
        params = json.dumps(cell.get("params", {}), sort_keys=True, ensure_ascii=False)
        rows.append(
            f"| `{cell_id}` | `{params}` | {completed} | {trades} | "
            f"{net_pnl:.4f} | {max_dd:.4f} | {run_errors} | {entry_stop_violations} |"
        )
    return rows


def _json_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


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
