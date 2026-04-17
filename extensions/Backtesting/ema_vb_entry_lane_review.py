#!/usr/bin/env python3
"""Run the 2026-04-15 EMA/VB entry-lane review plan."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


BACKTEST_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKTEST_ROOT.parents[1]
os.environ.setdefault("TRADING_BOT_ROOT", str(REPO_ROOT))
sys.path.insert(0, str(BACKTEST_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from backtest_engine import BacktestConfig, BacktestEngine  # noqa: E402
from report_generator import ReportGenerator  # noqa: E402


SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT"]
LANES = ["2B", "EMA_PULLBACK", "VOLUME_BREAKOUT"]

WINDOWS = {
    "TRENDING_UP": ("2023-10-01", "2024-03-31"),
    "TRENDING_DOWN": ("2025-10-07", "2026-04-06"),
    "RANGING": ("2024-12-31", "2025-03-31"),
    "MIXED": ("2025-02-01", "2025-08-31"),
}

RUN_MATRIX = {
    "BASE_2B_ONLY": ["2B"],
    "EMA_ONLY": ["EMA_PULLBACK"],
    "VB_ONLY": ["VOLUME_BREAKOUT"],
    "EMA_VB_ONLY": ["EMA_PULLBACK", "VOLUME_BREAKOUT"],
    "2B_EMA": ["2B", "EMA_PULLBACK"],
    "2B_VB": ["2B", "VOLUME_BREAKOUT"],
    "2B_EMA_VB": ["2B", "EMA_PULLBACK", "VOLUME_BREAKOUT"],
}

MATRIX_REQUIRED_FILES = (
    "summary.json",
    "trades.csv",
    "signal_audit_summary.json",
    "signal_entries.csv",
    "lane_race_audit.csv",
)

RUNTIME_PARITY_OVERRIDES = {
    "V7_MIN_SIGNAL_TIER": "A",
    "REGIME_ARBITER_ENABLED": True,
    "ARBITER_NEUTRAL_THRESHOLD": 0.5,
    "ARBITER_NEUTRAL_EXIT_THRESHOLD": 0.5,
    "ARBITER_NEUTRAL_MIN_BARS": 1,
    "MACRO_OVERLAY_ENABLED": False,
    "BTC_TREND_FILTER_ENABLED": True,
    "BTC_COUNTER_TREND_MULT": 0.0,
    "USE_SCANNER_SYMBOLS": False,
    "REGIME_ROUTER_ENABLED": False,
    "REGIME_ROUTER_TRACE_ENABLED": True,
    "TELEGRAM_ENABLED": False,
}


@dataclass(frozen=True)
class RunOutput:
    run_id: str
    window: str
    path: Path


def _json_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _csv_load(path: Path, *, parse_dates: Iterable[str] = ()) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    for col in parse_dates:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def _run_backtest(
    *,
    output_dir: Path,
    window: str,
    run_id: str,
    allowed_signal_types: list[str],
    dry_count_only: bool,
    skip_existing: bool,
) -> RunOutput:
    start, end = WINDOWS[window]
    out = output_dir / run_id / window
    if skip_existing and (out / "summary.json").exists() and (out / "signal_audit_summary.json").exists():
        print(f"[skip] {run_id}/{window}")
        return RunOutput(run_id, window, out)

    cfg = BacktestConfig(
        symbols=SYMBOLS,
        start=start,
        end=end,
        strategy="v54",
        allowed_signal_types=allowed_signal_types,
        dry_count_only=dry_count_only,
        precompute_indicators=True,
        config_overrides=RUNTIME_PARITY_OVERRIDES,
    )
    print(f"[run] {run_id}/{window} lanes={','.join(allowed_signal_types)} dry={dry_count_only}")
    result = BacktestEngine(cfg).run_single(verbose=False)
    ReportGenerator().generate(result, out)

    meta = {
        "run_id": run_id,
        "window": window,
        "start": start,
        "end": end,
        "symbols": SYMBOLS,
        "strategy": "v54",
        "allowed_signal_types": allowed_signal_types,
        "dry_count_only": dry_count_only,
        "precompute_indicators": cfg.precompute_indicators,
        "config_overrides": RUNTIME_PARITY_OVERRIDES,
        "fee_rate": cfg.fee_rate,
        "initial_balance": cfg.initial_balance,
        "warmup_bars": cfg.warmup_bars,
    }
    (out / "run_metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return RunOutput(run_id, window, out)


def _run_task(task: dict) -> tuple[str, str, str]:
    result = _run_backtest(**task)
    return result.run_id, result.window, str(result.path)


def _run_tasks(tasks: list[dict], *, jobs: int) -> None:
    if jobs <= 1:
        for task in tasks:
            _run_task(task)
        return

    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {executor.submit(_run_task, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                run_id, window, path = future.result()
                print(f"[done] {run_id}/{window} -> {path}")
            except Exception as exc:
                print(f"[failed] {task.get('run_id')}/{task.get('window')}: {exc}")
                raise


def _profit_factor(pnls: pd.Series) -> float:
    if pnls.empty:
        return 0.0
    gross_profit = pnls[pnls > 0].sum()
    gross_loss = abs(pnls[pnls < 0].sum())
    if gross_loss <= 0:
        return math.inf if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def _max_losing_streak(pnls: pd.Series) -> int:
    streak = 0
    max_streak = 0
    for pnl in pnls.fillna(0.0):
        if pnl < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def _trade_key(df: pd.DataFrame) -> pd.Series:
    for col in ("entry_time", "symbol", "signal_type"):
        if col not in df.columns:
            df[col] = ""
    return df[["entry_time", "symbol", "signal_type"]].astype(str).apply(tuple, axis=1)


def _symbol_time_key(df: pd.DataFrame) -> pd.Series:
    for col in ("entry_time", "symbol"):
        if col not in df.columns:
            df[col] = ""
    return df[["entry_time", "symbol"]].astype(str).apply(tuple, axis=1)


def _dedup_trades(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["_trade_key"] = _trade_key(out)
    return out.drop_duplicates("_trade_key").drop(columns=["_trade_key"])


def _aggregate_trade_metrics(trades: pd.DataFrame, summaries: list[dict]) -> dict:
    if trades.empty:
        return {
            "total_trades": 0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "max_drawdown_pct": max((s.get("max_drawdown_pct", 0.0) for s in summaries), default=0.0),
            "sharpe": 0.0,
            "net_pnl": 0.0,
            "avg_r": 0.0,
            "max_losing_streak": 0,
        }
    pnls = pd.to_numeric(trades.get("pnl_usdt", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    realized_r = pd.to_numeric(trades.get("realized_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    return {
        "total_trades": int(len(trades)),
        "profit_factor": round(_profit_factor(pnls), 4),
        "win_rate": round(float((pnls > 0).mean()), 4),
        "max_drawdown_pct": round(max((s.get("max_drawdown_pct", 0.0) for s in summaries), default=0.0), 4),
        "sharpe": round(float(pd.Series([s.get("sharpe", 0.0) for s in summaries]).mean()), 4),
        "net_pnl": round(float(pnls.sum()), 4),
        "avg_r": round(float(realized_r.mean()) if len(realized_r) else 0.0, 4),
        "max_losing_streak": _max_losing_streak(pnls),
    }


def _load_run_trades(output_dir: Path, run_id: str) -> pd.DataFrame:
    frames = []
    for window in WINDOWS:
        path = output_dir / run_id / window / "trades.csv"
        df = _csv_load(path, parse_dates=["entry_time", "exit_time"])
        if df.empty:
            continue
        df["run_id"] = run_id
        df["window"] = window
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _validate_matrix_completeness(output_dir: Path) -> list[dict]:
    missing = []
    for run_id in RUN_MATRIX:
        for window in WINDOWS:
            cell = output_dir / run_id / window
            missing_files = [
                name for name in MATRIX_REQUIRED_FILES
                if not (cell / name).exists()
            ]
            if missing_files:
                missing.append({
                    "run_id": run_id,
                    "window": window,
                    "missing_files": missing_files,
                })
    return missing


def _collect_backtest_run_errors(output_dir: Path) -> list[dict]:
    errors = []
    for run_id in RUN_MATRIX:
        for window in WINDOWS:
            summary = _json_load(output_dir / run_id / window / "summary.json")
            for error in summary.get("backtest_run_errors") or []:
                payload = dict(error)
                payload["run_id"] = run_id
                payload["window"] = window
                errors.append(payload)
    return errors


def _matrix_summary(output_dir: Path) -> pd.DataFrame:
    rows = []
    for run_id in RUN_MATRIX:
        summaries = [
            _json_load(output_dir / run_id / window / "summary.json")
            for window in WINDOWS
        ]
        trades = _dedup_trades(_load_run_trades(output_dir, run_id))
        rows.append({"run_id": run_id, **_aggregate_trade_metrics(trades, summaries)})
    return pd.DataFrame(rows)


def _by_window_summary(output_dir: Path) -> pd.DataFrame:
    rows = []
    for run_id in RUN_MATRIX:
        for window in WINDOWS:
            summary = _json_load(output_dir / run_id / window / "summary.json")
            trades = _csv_load(output_dir / run_id / window / "trades.csv")
            net_pnl = 0.0
            if not trades.empty and "pnl_usdt" in trades.columns:
                net_pnl = float(pd.to_numeric(trades["pnl_usdt"], errors="coerce").fillna(0.0).sum())
            rows.append({
                "run_id": run_id,
                "window": window,
                "trades": int(summary.get("total_trades", 0)),
                "pf": summary.get("profit_factor", 0.0),
                "max_dd_pct": summary.get("max_drawdown_pct", 0.0),
                "net_pnl": round(net_pnl, 4),
            })
    return pd.DataFrame(rows)


def _dry_count_rows(output_dir: Path) -> pd.DataFrame:
    rows = []
    for window in WINDOWS:
        for lane in LANES:
            path = output_dir / "DRY_COUNT" / lane / window
            entries = _csv_load(path / "signal_entries.csv")
            rejects = _csv_load(path / "signal_rejects.csv")
            races = _csv_load(path / "lane_race_audit.csv")

            lane_entries = entries[entries.get("signal_type", pd.Series(dtype=str)) == lane] if not entries.empty else pd.DataFrame()
            lane_rejects = rejects[rejects.get("signal_type", pd.Series(dtype=str)) == lane] if not rejects.empty else pd.DataFrame()
            lane_races = races[races.get("candidate_signal_type", pd.Series(dtype=str)) == lane] if not races.empty else pd.DataFrame()
            post = pd.concat([lane_entries, lane_rejects], ignore_index=True)

            tier_counts = post.get("signal_tier", pd.Series(dtype=str)).value_counts().to_dict() if not post.empty else {}
            mtf_aligned = 0
            if "mtf_aligned" in post.columns:
                mtf_aligned = int(post["mtf_aligned"].astype(str).str.lower().isin(["true", "1"]).sum())

            rows.append({
                "window": window,
                "lane": lane,
                "raw_signal_count": int(len(lane_races)),
                "market_filter_pass_count": int(len(lane_races)),
                "trend_filter_pass_count": int(len(post) - (post.get("reject_reason", pd.Series(dtype=str)) == "trend_filter").sum()),
                "mtf_aligned_count": mtf_aligned,
                "tier_A_count": int(tier_counts.get("A", 0)),
                "tier_B_count": int(tier_counts.get("B", 0)),
                "tier_C_count": int(tier_counts.get("C", 0)),
                "final_candidate_count": int(len(lane_entries)),
            })
    return pd.DataFrame(rows)


def _by_regime_table(output_dir: Path) -> pd.DataFrame:
    rows = []
    for run_id in RUN_MATRIX:
        trades = _dedup_trades(_load_run_trades(output_dir, run_id))
        if trades.empty:
            rows.append({"run_id": run_id, "regime": "NO_TRADES", "trades": 0, "pf": 0.0, "net_pnl": 0.0})
            continue
        regime_col = "entry_regime" if "entry_regime" in trades.columns else "market_regime"
        trades[regime_col] = trades[regime_col].fillna("UNKNOWN")
        for regime, group in trades.groupby(regime_col, dropna=False):
            pnls = pd.to_numeric(group.get("pnl_usdt", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
            rows.append({
                "run_id": run_id,
                "regime": str(regime),
                "trades": int(len(group)),
                "pf": round(_profit_factor(pnls), 4),
                "net_pnl": round(float(pnls.sum()), 4),
            })
    return pd.DataFrame(rows)


def _incremental_table(output_dir: Path) -> pd.DataFrame:
    base = _dedup_trades(_load_run_trades(output_dir, "BASE_2B_ONLY"))
    base_key = set(_symbol_time_key(base)) if not base.empty else set()
    base_trade_key = set(_trade_key(base)) if not base.empty else set()
    rows = []
    for run_id in ("2B_EMA", "2B_VB", "2B_EMA_VB"):
        trades = _dedup_trades(_load_run_trades(output_dir, run_id))
        if trades.empty:
            rows.append({
                "run_id": run_id,
                "new_trades": 0,
                "new_pf": 0.0,
                "new_net_pnl": 0.0,
                "pure_new": 0,
                "replaced": 0,
                "unchanged_2b": 0,
                "priority_suppressed": 0,
                "overlap_ratio": 0.0,
            })
            continue

        trades["_sym_time_key"] = _symbol_time_key(trades)
        trades["_trade_key"] = _trade_key(trades)
        new_group = trades[~trades["_trade_key"].isin(base_trade_key)]
        pure_new = new_group[~new_group["_sym_time_key"].isin(base_key)]
        replaced = new_group[new_group["_sym_time_key"].isin(base_key)]
        unchanged = trades[trades["_trade_key"].isin(base_trade_key)]
        pnls = pd.to_numeric(new_group.get("pnl_usdt", pd.Series(dtype=float)), errors="coerce").fillna(0.0)

        suppressed = 0
        for window in WINDOWS:
            races = _csv_load(output_dir / run_id / window / "lane_race_audit.csv")
            if not races.empty and "suppressed_by" in races.columns:
                suppressed += int((races["suppressed_by"] == "priority").sum())

        rows.append({
            "run_id": run_id,
            "new_trades": int(len(new_group)),
            "new_pf": round(_profit_factor(pnls), 4),
            "new_net_pnl": round(float(pnls.sum()), 4),
            "pure_new": int(len(pure_new)),
            "replaced": int(len(replaced)),
            "unchanged_2b": int(len(unchanged)),
            "priority_suppressed": suppressed,
            "overlap_ratio": round(float(len(unchanged) / len(base)) if len(base) else 0.0, 4),
        })
    return pd.DataFrame(rows)


def _exit_compat_table(output_dir: Path) -> pd.DataFrame:
    rows = []
    for run_id in RUN_MATRIX:
        trades = _dedup_trades(_load_run_trades(output_dir, run_id))
        if trades.empty or "signal_type" not in trades.columns:
            continue
        for signal_type, group in trades.groupby("signal_type", dropna=False):
            capture = pd.to_numeric(group.get("capture_ratio", pd.Series(dtype=float)), errors="coerce")
            timeout_col = group.get("exit_reason", pd.Series(dtype=str)).astype(str)
            near_zero_timeout = (
                timeout_col.str.contains("timeout", case=False, na=False)
                & (pd.to_numeric(group.get("realized_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0).abs() <= 0.25)
            )
            protection = group.get("protection_state", pd.Series(dtype=str)).fillna("NONE").replace("", "NONE")
            rows.append({
                "run_id": run_id,
                "signal_type": str(signal_type),
                "trades": int(len(group)),
                "avg_capture_ratio": round(float(capture.dropna().mean()) if capture.notna().any() else 0.0, 4),
                "near_0r_timeout_count": int(near_zero_timeout.sum()),
                "v54_lock_15r": int((protection == "V54_LOCK_15R").sum()),
                "v54_lock_20r": int((protection == "V54_LOCK_20R").sum()),
                "exit_reasons": "; ".join(f"{k}:{v}" for k, v in timeout_col.value_counts().to_dict().items()),
            })
    return pd.DataFrame(rows)


def _failure_rows(output_dir: Path) -> list[str]:
    lines = []
    by_window = _by_window_summary(output_dir)
    if by_window.empty:
        return ["No window data available."]
    worst_window = by_window.sort_values("net_pnl").head(1).iloc[0]
    lines.append(
        f"- Worst run/window: `{worst_window['run_id']}/{worst_window['window']}` "
        f"net_pnl={worst_window['net_pnl']}, PF={worst_window['pf']}, trades={worst_window['trades']}."
    )

    all_trades = []
    for run_id in RUN_MATRIX:
        trades = _dedup_trades(_load_run_trades(output_dir, run_id))
        if not trades.empty:
            trades["run_id"] = run_id
            all_trades.append(trades)
    if not all_trades:
        lines.append("- No closed trades; symbol-level failure mode is inconclusive.")
        return lines

    trades = pd.concat(all_trades, ignore_index=True)
    trades["pnl_usdt"] = pd.to_numeric(trades.get("pnl_usdt", 0.0), errors="coerce").fillna(0.0)
    by_symbol = trades.groupby(["run_id", "symbol"])["pnl_usdt"].sum().reset_index().sort_values("pnl_usdt")
    worst_symbol = by_symbol.head(1).iloc[0]
    worst_trade = trades.sort_values("pnl_usdt").head(1).iloc[0]
    lines.append(
        f"- Worst symbol: `{worst_symbol['run_id']}` `{worst_symbol['symbol']}` "
        f"net_pnl={round(float(worst_symbol['pnl_usdt']), 4)}."
    )
    lines.append(
        f"- Worst single trade: `{worst_trade['run_id']}` `{worst_trade['symbol']}` "
        f"{worst_trade.get('signal_type', '')} pnl={round(float(worst_trade['pnl_usdt']), 4)} "
        f"exit={worst_trade.get('exit_reason', '')}."
    )
    return lines


def _fmt(value) -> str:
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def _markdown_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    if df.empty:
        return "_No rows._"
    view = df[columns] if columns else df
    if max_rows is not None:
        view = view.head(max_rows)
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = [
        "| " + " | ".join(_fmt(row[col]) for col in view.columns) + " |"
        for _, row in view.iterrows()
    ]
    return "\n".join([header, sep, *rows])


def _candidate_passes(
    candidate: str,
    matrix: pd.DataFrame,
    incremental: pd.DataFrame,
    by_regime: pd.DataFrame,
) -> tuple[bool, list[str]]:
    base = matrix[matrix["run_id"] == "BASE_2B_ONLY"].iloc[0].to_dict()
    row = matrix[matrix["run_id"] == candidate].iloc[0].to_dict()
    inc = incremental[incremental["run_id"] == candidate].iloc[0].to_dict()
    failures = []

    base_pf = float(base.get("profit_factor", 0.0) or 0.0)
    base_dd = float(base.get("max_drawdown_pct", 0.0) or 0.0)
    if base_pf > 0 and float(row.get("profit_factor", 0.0)) < base_pf * 0.90:
        failures.append("PF below 90% of BASE_2B_ONLY")
    if base_dd > 0 and float(row.get("max_drawdown_pct", 0.0)) > base_dd * 1.25:
        failures.append("MaxDD above 1.25x BASE_2B_ONLY")
    if int(row.get("total_trades", 0)) < int(base.get("total_trades", 0)) * 1.30:
        failures.append("trade count increase below 30%")
    if float(inc.get("new_pf", 0.0)) <= 1.2:
        failures.append("incremental new trade PF <= 1.2")
    if float(row.get("net_pnl", 0.0)) < float(base.get("net_pnl", 0.0)):
        failures.append("net PnL below BASE_2B_ONLY")
    if int(inc.get("pure_new", 0)) < int(inc.get("replaced", 0)):
        failures.append("incremental PnL not mainly pure new trades")

    risk_regimes = by_regime[
        (by_regime["run_id"] == candidate)
        & (by_regime["regime"].astype(str).isin(["RANGING", "MIXED"]))
    ]
    for _, risk_row in risk_regimes.iterrows():
        if (
            float(risk_row.get("pf", 0.0)) < 1.0
            and int(risk_row.get("trades", 0)) >= 20
            and float(risk_row.get("net_pnl", 0.0)) < 0
        ):
            failures.append(f"{risk_row['regime']} bucket has systematic loss")

    return not failures, failures


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
        lines.append("- `--allow-incomplete` was used for debug reporting; promotion verdict remains disabled.")

    if incomplete_cells:
        total_cells = len(RUN_MATRIX) * len(WINDOWS)
        lines.append(f"- Incomplete matrix: missing {len(incomplete_cells)}/{total_cells} cells.")
        for cell in incomplete_cells:
            files = ", ".join(cell["missing_files"])
            lines.append(f"  - `{cell['run_id']}/{cell['window']}` missing: {files}")

    if run_errors:
        lines.append(f"- Backtest run errors: {len(run_errors)}.")
        for error in run_errors:
            lines.append(
                "  - "
                f"`{error.get('run_id')}/{error.get('window')}` "
                f"{error.get('timestamp')} {error.get('stage')} "
                f"{error.get('exc_type')}: {error.get('message')}"
            )

    lines.append("")
    return lines


def _write_tier_count_report(repo_root: Path, output_dir: Path, dry_counts: pd.DataFrame) -> None:
    report_path = repo_root / "reports" / "ema_vb_tier_count_dry_run.md"
    pivot = dry_counts.groupby("lane")[[
        "raw_signal_count",
        "tier_A_count",
        "tier_B_count",
        "tier_C_count",
        "final_candidate_count",
    ]].sum().reset_index()

    lines = [
        "# EMA/VB Tier Count Dry Run",
        "",
        "Runtime-parity dry count: Tier A, Neutral Arbiter on, Macro Overlay off, BTC trend filter on.",
        "",
        "Caveat: `market_filter_pass_count` is counted after market filter because lane detection only runs once market filter passes.",
        "",
        "## Aggregate By Lane",
        "",
        _markdown_table(pivot),
        "",
        "## By Window",
        "",
        _markdown_table(dry_counts),
        "",
        f"CSV: `{output_dir / 'tier_count_summary.csv'}`",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_entry_lane_report(repo_root: Path, output_dir: Path, *, allow_incomplete: bool = False) -> str:
    incomplete_cells = _validate_matrix_completeness(output_dir)
    run_errors = _collect_backtest_run_errors(output_dir)
    force_second_pass = bool(incomplete_cells or run_errors)

    matrix = _matrix_summary(output_dir)
    by_window = _by_window_summary(output_dir)
    by_regime = _by_regime_table(output_dir)
    incremental = _incremental_table(output_dir)
    exit_compat = _exit_compat_table(output_dir)

    verdict_candidates = []
    candidate_failures = {}
    for candidate in ("2B_EMA", "2B_VB", "2B_EMA_VB"):
        passed, failures = _candidate_passes(candidate, matrix, incremental, by_regime)
        if passed:
            verdict_candidates.append(candidate)
        candidate_failures[candidate] = failures

    if not verdict_candidates:
        verdict = "KEEP_2B_ONLY"
    elif verdict_candidates == ["2B_EMA"]:
        verdict = "PROMOTE_EMA_ONLY"
    elif verdict_candidates == ["2B_VB"]:
        verdict = "PROMOTE_VB_ONLY"
    elif "2B_EMA_VB" in verdict_candidates:
        verdict = "PROMOTE_EMA_AND_VB"
    else:
        verdict = "NEEDS_SECOND_PASS"

    if force_second_pass:
        verdict = "NEEDS_SECOND_PASS"

    report_path = repo_root / "reports" / "ema_vb_entry_lane_review.md"
    lines = [
        "# EMA/VB Entry Lane Review",
        "",
        "## Executive read",
        "",
        f"- Verdict: `{verdict}`.",
        "- Runtime EMA/VB remains off; this report does not modify `bot_config.json`.",
        "- Matrix used V54 exits for all tested lanes under runtime-parity filters.",
        "- `RANGING` and `MIXED` windows overlap; aggregate trade counts are deduped by entry time / symbol / signal type.",
        "- Any promotion still requires Ruei decision and second-pass stress windows.",
        "",
        *_validity_warning_lines(
            incomplete_cells,
            run_errors,
            allow_incomplete=allow_incomplete,
        ),
        "## Matrix summary",
        "",
        _markdown_table(matrix),
        "",
        "## By-window table",
        "",
        _markdown_table(by_window),
        "",
        "## By-regime table",
        "",
        _markdown_table(by_regime),
        "",
        "## Incremental contribution",
        "",
        _markdown_table(incremental),
        "",
        "## Exit compatibility",
        "",
        _markdown_table(exit_compat),
        "",
        "## Failure modes",
        "",
        *(_failure_rows(output_dir)),
        "",
        "## Acceptance checks",
        "",
    ]

    for candidate, failures in candidate_failures.items():
        if failures:
            lines.append(f"- `{candidate}` failed: " + "; ".join(failures) + ".")
        else:
            lines.append(f"- `{candidate}` passed first-round acceptance checks.")

    lines.extend([
        "",
        "## Run settings",
        "",
        "- Symbols: `BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT DOGE/USDT`.",
        "- Fee rate: `0.0004`; initial balance: `10000`; warmup bars: `100`.",
        "- Runtime parity: Tier A, neutral arbiter on, macro overlay off, BTC trend filter on, counter-trend multiplier 0.",
        f"- Results root: `{output_dir}`.",
    ])

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdict


def _write_tooling_notes(repo_root: Path, output_dir: Path) -> None:
    notes = [
        "# EMA/VB Tooling Notes",
        "",
        "- Fixed Backtesting bot-root resolution for the isolated `feat-regime-router` folder.",
        "- Added backtest-only `allowed_signal_types` support via `BacktestConfig.allowed_signal_types` and CLI `--allowed-signal-types`.",
        "- Added backtest-only `dry_count_only` support so dry runs can count final candidates without opening positions.",
        "- Added optional precomputed-indicator replay for the review harness to avoid recalculating the same indicator windows on every 1H scan.",
        "- Added `lane_race_audit.csv` with priority and allowlist suppression fields.",
        "- The tooling sets a backtest-only `SIGNAL_STRATEGY_MAP` from `--strategy v54`; runtime `bot_config.json` is not edited.",
        "- Dry count `market_filter_pass_count` is post-market by construction because signal detectors run after market filter in the runtime scanner.",
        f"- Review harness: `{BACKTEST_ROOT / 'ema_vb_entry_lane_review.py'}`.",
        f"- Results root: `{output_dir}`.",
    ]
    (repo_root / "reports" / "ema_vb_tooling_notes.md").write_text(
        "\n".join(notes) + "\n",
        encoding="utf-8",
    )


def run_plan(*, phase: str, skip_existing: bool, jobs: int, allow_incomplete: bool = False) -> None:
    output_dir = BACKTEST_ROOT / "results" / "ema_vb_entry_lane_review_20260415"
    output_dir.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "reports").mkdir(parents=True, exist_ok=True)

    if phase in ("all", "dry"):
        tasks = []
        for window in WINDOWS:
            for lane in LANES:
                tasks.append({
                    "output_dir": output_dir / "DRY_COUNT",
                    "window": window,
                    "run_id": lane,
                    "allowed_signal_types": [lane],
                    "dry_count_only": True,
                    "skip_existing": skip_existing,
                })
        _run_tasks(tasks, jobs=jobs)

        dry_counts = _dry_count_rows(output_dir)
        dry_counts.to_csv(output_dir / "tier_count_summary.csv", index=False)
        _write_tier_count_report(REPO_ROOT, output_dir, dry_counts)

    if phase in ("all", "matrix"):
        tasks = []
        for run_id, lanes in RUN_MATRIX.items():
            for window in WINDOWS:
                tasks.append({
                    "output_dir": output_dir,
                    "window": window,
                    "run_id": run_id,
                    "allowed_signal_types": lanes,
                    "dry_count_only": False,
                    "skip_existing": skip_existing,
                })
        _run_tasks(tasks, jobs=jobs)

    if phase in ("all", "report"):
        dry_counts = _dry_count_rows(output_dir)
        if not dry_counts.empty:
            dry_counts.to_csv(output_dir / "tier_count_summary.csv", index=False)
            _write_tier_count_report(REPO_ROOT, output_dir, dry_counts)
        verdict = _write_entry_lane_report(
            REPO_ROOT,
            output_dir,
            allow_incomplete=allow_incomplete,
        )
        _write_tooling_notes(REPO_ROOT, output_dir)
        print(f"[done] verdict={verdict}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EMA/VB entry-lane review plan.")
    parser.add_argument(
        "--phase",
        choices=["all", "dry", "matrix", "report"],
        default="all",
        help="Run all phases or resume a specific phase.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Reuse existing run folders when summary/audit files already exist.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Parallel run/window workers. Use 1 for serial execution.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Write a debug report even when matrix artifacts are incomplete; verdict remains NEEDS_SECOND_PASS.",
    )
    args = parser.parse_args()
    run_plan(
        phase=args.phase,
        skip_existing=args.skip_existing,
        jobs=max(1, args.jobs),
        allow_incomplete=args.allow_incomplete,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
