"""Run research-only Slot A+B LONG/SHORT combined portfolio matrices."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backtest_engine import BacktestConfig, BacktestEngine
from config_presets import explicit_symbol_universe, plugin_runtime_defaults
from report_generator import ReportGenerator
from trader.config import Config

from extensions.Backtesting.scripts import run_portfolio_ab_matrix as portfolio_ab


SLOT_A_LONG = portfolio_ab.SLOT_A
SLOT_B_LONG = portfolio_ab.SLOT_B
SLOT_A_SHORT = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_B_SHORT = "donchian_range_fade_4h_range_width_cv_013_short"
STRATEGIES = (SLOT_A_LONG, SLOT_A_SHORT, SLOT_B_LONG, SLOT_B_SHORT)
STRATEGY_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_A_SHORT: "Slot A SHORT",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
}
DEFAULT_SYMBOLS = portfolio_ab.DEFAULT_SYMBOLS
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "portfolio_ab_bidirectional"
REPORT_PATH = REPO_ROOT / "reports" / "portfolio_a_b_bidirectional_research.md"
BASELINE_SUMMARY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab"
    / "slot_a_b"
    / "portfolio_ab_matrix_summary.json"
)
REJECT_REASONS = portfolio_ab.REJECT_REASONS


def _research_overrides(risk_per_trade: float) -> dict[str, Any]:
    overrides = plugin_runtime_defaults()
    overrides["RISK_PER_TRADE"] = float(risk_per_trade)
    return explicit_symbol_universe(overrides)


def _build_config(
    start: str,
    end: str,
    *,
    symbols: list[str],
    risk_per_trade: float,
) -> BacktestConfig:
    strategies = list(STRATEGIES)
    return BacktestConfig(
        symbols=list(symbols),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=strategies,
        allowed_plugin_ids=strategies,
        config_overrides=_research_overrides(risk_per_trade),
    )


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _net_pnl(cell_dir: Path, summary: dict) -> float:
    if "net_pnl" in summary:
        return _safe_float(summary.get("net_pnl"))
    return sum(_safe_float(row.get("pnl_usdt")) for row in _read_csv(cell_dir / "trades.csv"))


def _realized_trade_dd_pct(rows: list[dict[str, str]], *, initial_balance: float = 10000.0) -> float:
    if not rows:
        return 0.0
    ordered = sorted(rows, key=lambda row: row.get("exit_time") or row.get("entry_time") or "")
    equity = float(initial_balance)
    peak = equity
    max_dd = 0.0
    for row in ordered:
        equity += _safe_float(row.get("pnl_usdt"))
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return round(max_dd, 4)


def _entry_stop_violations(rows: list[dict[str, str]]) -> int:
    violations = 0
    for row in rows:
        side = str(row.get("side") or "").upper()
        entry_price = _safe_float(row.get("entry_price"))
        entry_sl = _safe_float(row.get("entry_initial_sl"))
        if side == "LONG" and entry_sl >= entry_price:
            violations += 1
        if side == "SHORT" and entry_sl <= entry_price:
            violations += 1
    return violations


def _trade_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    realized_r = 0.0
    for row in rows:
        pnl = _safe_float(row.get("pnl_usdt"))
        wins += 1 if pnl > 0 else 0
        gross_profit += max(pnl, 0.0)
        gross_loss += min(pnl, 0.0)
        realized_r += _safe_float(row.get("realized_r"))
    trades = len(rows)
    gross_loss_abs = abs(gross_loss)
    return {
        "trades": trades,
        "win_rate": round(wins / trades, 4) if trades else 0.0,
        "net_pnl": round(sum(_safe_float(row.get("pnl_usdt")) for row in rows), 4),
        "profit_factor": round(gross_profit / gross_loss_abs, 4)
        if gross_loss_abs
        else None,
        "avg_realized_r": round(realized_r / trades, 4) if trades else 0.0,
        "realized_trade_dd_pct": _realized_trade_dd_pct(rows),
        "entry_stop_violations": _entry_stop_violations(rows),
    }


def _per_strategy_metrics(trades: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {
        strategy_id: _trade_metrics(
            [row for row in trades if row.get("strategy_id") == strategy_id]
        )
        for strategy_id in STRATEGIES
    }


def _per_side_metrics(trades: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {
        side: _trade_metrics([row for row in trades if str(row.get("side") or "").upper() == side])
        for side in ("LONG", "SHORT")
    }


def _reject_metrics(cell_dir: Path) -> dict[str, dict[str, Any]]:
    rejects = _read_csv(cell_dir / "signal_rejects.csv")
    entries = _read_csv(cell_dir / "signal_entries.csv")
    payload: dict[str, dict[str, Any]] = {}
    for strategy_id in STRATEGIES:
        strategy_rejects = [row for row in rejects if row.get("signal_type") == strategy_id]
        strategy_entries = [row for row in entries if row.get("signal_type") == strategy_id]
        reason_counts = Counter(row.get("reject_reason") or "unknown" for row in strategy_rejects)
        emitted = len(strategy_entries) + len(strategy_rejects)
        router_blocked = int(reason_counts.get("strategy_router_blocked", 0))
        row = {
            "entries": len(strategy_entries),
            "rejects": len(strategy_rejects),
            "emitted_intents": emitted,
            "strategy_router_block_rate": round(router_blocked / emitted, 4) if emitted else 0.0,
            "rejects_by_reason": dict(reason_counts),
        }
        for reason in REJECT_REASONS:
            row[reason] = int(reason_counts.get(reason, 0))
        payload[strategy_id] = row
    return payload


def _same_symbol_same_entry_side_collisions(trades: list[dict[str, str]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], set[str]] = {}
    for row in trades:
        symbol = row.get("symbol")
        entry_time = row.get("entry_time")
        side = str(row.get("side") or "").upper()
        if symbol and entry_time and side:
            grouped.setdefault((entry_time, symbol), set()).add(side)

    collisions = [
        {"entry_time": entry_time, "symbol": symbol}
        for (entry_time, symbol), sides in grouped.items()
        if {"LONG", "SHORT"}.issubset(sides)
    ]
    collisions.sort(key=lambda row: (row["entry_time"], row["symbol"]))
    return {
        "count": len(collisions),
        "examples": collisions[:10],
    }


def _summary_row(cell_dir: Path) -> dict[str, Any]:
    summary = _read_json(cell_dir / "summary.json")
    trades = _read_csv(cell_dir / "trades.csv")
    return {
        "portfolio": {
            "trades": int(summary.get("total_trades", 0) or 0),
            "net_pnl": round(_net_pnl(cell_dir, summary), 4),
            "max_dd_pct": round(_safe_float(summary.get("max_drawdown_pct")), 4),
            "run_errors": int(summary.get("backtest_run_error_count", 0) or 0),
            "entry_stop_violations": _entry_stop_violations(trades),
        },
        "per_strategy": _per_strategy_metrics(trades),
        "per_side": _per_side_metrics(trades),
        "reject_mix": _reject_metrics(cell_dir),
        "same_symbol_same_entry_long_short": _same_symbol_same_entry_side_collisions(trades),
        "artifacts": {
            "summary": str(cell_dir / "summary.json"),
            "trades": str(cell_dir / "trades.csv"),
            "signal_rejects": str(cell_dir / "signal_rejects.csv"),
            "signal_entries": str(cell_dir / "signal_entries.csv"),
        },
    }


def _run_cell(
    matrix_name: str,
    window_name: str,
    start: str,
    end: str,
    *,
    output_dir: Path,
    symbols: list[str],
    risk_per_trade: float,
) -> dict[str, Any]:
    print(
        "[PortfolioABBidirectional] "
        f"{matrix_name}/{window_name}: {start}->{end} "
        f"symbols={','.join(symbols)} risk_per_trade={risk_per_trade}"
    )
    cfg = _build_config(start, end, symbols=symbols, risk_per_trade=risk_per_trade)
    result = BacktestEngine(cfg).run()
    ReportGenerator().generate(result, output_dir)
    return _summary_row(output_dir)


def run_portfolio_ab_bidirectional_matrix(
    *,
    matrix: str = "all",
    symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    report_path: Path | None = None,
) -> tuple[Path, Path]:
    symbols = list(symbols or DEFAULT_SYMBOLS)
    selected = []
    if matrix in {"default", "all"}:
        selected.append(("default", portfolio_ab.DEFAULT_WINDOWS))
    if matrix in {"supplemental", "all"}:
        selected.append(("supplemental", portfolio_ab.SUPPLEMENTAL_WINDOWS))
    if not selected:
        raise ValueError("matrix must be one of: default, supplemental, all")

    run_dir = Path(results_root) / "slot_a_b_long_short"
    summary_path = run_dir / "portfolio_ab_bidirectional_matrix_summary.json"
    existing_payload = _read_json(summary_path)
    matrices: dict[str, dict[str, Any]] = dict(existing_payload.get("matrices", {}))
    for matrix_name, windows in selected:
        matrix_payload = {}
        for window_name, (start, end) in windows.items():
            cell_dir = run_dir / matrix_name / window_name
            cell = _run_cell(
                matrix_name,
                window_name,
                start,
                end,
                output_dir=cell_dir,
                symbols=symbols,
                risk_per_trade=risk_per_trade,
            )
            cell["window"] = {"start": start, "end": end}
            matrix_payload[window_name] = cell
        matrices[matrix_name] = matrix_payload

    baseline_payload = _read_json(BASELINE_SUMMARY)
    payload = {
        "schema": "strategy_plugin_portfolio_ab_bidirectional_matrix.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "RESEARCH_ONLY_BIDIRECTIONAL_FIRST_PASS",
        "slot_a_long": SLOT_A_LONG,
        "slot_a_short": SLOT_A_SHORT,
        "slot_b_long": SLOT_B_LONG,
        "slot_b_short": SLOT_B_SHORT,
        "symbols": symbols,
        "risk_per_trade": float(risk_per_trade),
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": float(Config.MAX_TOTAL_RISK),
        "results_root": str(run_dir),
        "baseline_long_only_summary": str(BASELINE_SUMMARY) if baseline_payload else None,
        "baseline_long_only_matrix_totals": _matrix_totals(
            baseline_payload.get("matrices", {})
        )
        if baseline_payload
        else {},
        "bidirectional_matrix_totals": _matrix_totals(matrices),
        "matrices": matrices,
    }
    summary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(payload, summary_path, report_path=report_path)
    print(f"[PortfolioABBidirectional] summary={summary_path}")
    print(f"[PortfolioABBidirectional] report={report_path}")
    return summary_path, report_path


def _matrix_totals(matrices: dict[str, Any]) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for matrix_name, matrix_payload in matrices.items():
        cells = list(matrix_payload.values())
        totals[matrix_name] = {
            "trades": sum(_safe_int(cell.get("portfolio", {}).get("trades")) for cell in cells),
            "net_pnl": round(
                sum(_safe_float(cell.get("portfolio", {}).get("net_pnl")) for cell in cells),
                4,
            ),
            "max_dd_pct": round(
                max(
                    (
                        _safe_float(cell.get("portfolio", {}).get("max_dd_pct"))
                        for cell in cells
                    ),
                    default=0.0,
                ),
                4,
            ),
            "run_errors": sum(
                _safe_int(cell.get("portfolio", {}).get("run_errors")) for cell in cells
            ),
            "long_trades": sum(_matrix_side_trades(cell, "LONG") for cell in cells),
            "short_trades": sum(_matrix_side_trades(cell, "SHORT") for cell in cells),
        }
    return totals


def _matrix_side_trades(cell: dict[str, Any], side: str) -> int:
    per_side = cell.get("per_side")
    if isinstance(per_side, dict) and per_side:
        return _safe_int(per_side.get(side, {}).get("trades"))

    # Older A+B long-only baseline summaries predate per-side attribution.
    if side == "LONG":
        return _safe_int(cell.get("portfolio", {}).get("trades"))
    return 0


def _matrix_summary_rows(matrix_payload: dict[str, Any]) -> list[str]:
    rows = []
    for window_name, cell in matrix_payload.items():
        p = cell["portfolio"]
        long_trades = cell["per_side"]["LONG"]["trades"]
        short_trades = cell["per_side"]["SHORT"]["trades"]
        rows.append(
            f"| `{window_name}` | {p['trades']} | {long_trades} | {short_trades} | "
            f"{p['net_pnl']:.4f} | {p['max_dd_pct']:.4f} | {p['run_errors']} | "
            f"{cell['same_symbol_same_entry_long_short']['count']} |"
        )
    return rows


def _strategy_rows(matrix_payload: dict[str, Any]) -> list[str]:
    rows = []
    for window_name, cell in matrix_payload.items():
        for strategy_id in STRATEGIES:
            s = cell["per_strategy"][strategy_id]
            rows.append(
                f"| `{window_name}` | {STRATEGY_LABELS[strategy_id]} | {s['trades']} | "
                f"{s['win_rate']:.4f} | {s['net_pnl']:.4f} | "
                f"{_fmt_optional(s['profit_factor'])} | {s['avg_realized_r']:.4f} | "
                f"{s['realized_trade_dd_pct']:.4f} | {s['entry_stop_violations']} |"
            )
    return rows


def _reject_rows(matrix_payload: dict[str, Any]) -> list[str]:
    rows = []
    for window_name, cell in matrix_payload.items():
        for strategy_id in STRATEGIES:
            r = cell["reject_mix"][strategy_id]
            rows.append(
                f"| `{window_name}` | {STRATEGY_LABELS[strategy_id]} | {r['entries']} | "
                f"{r['rejects']} | {r['position_slot_occupied']} | "
                f"{r['strategy_router_blocked']} | {r['cooldown']} | "
                f"{r['central_risk_blocked']} | {r['total_risk_limit']} | "
                f"{r['strategy_router_block_rate']:.4f} |"
            )
    return rows


def _totals_rows(
    baseline_totals: dict[str, Any],
    bidirectional_totals: dict[str, Any],
) -> list[str]:
    rows = []
    for matrix_name in ("default", "supplemental"):
        base = baseline_totals.get(matrix_name, {})
        current = bidirectional_totals.get(matrix_name, {})
        if not base and not current:
            continue
        base_pnl = _safe_float(base.get("net_pnl"))
        current_pnl = _safe_float(current.get("net_pnl"))
        rows.append(
            f"| `{matrix_name}` | {base.get('trades', '')} | {base_pnl:.4f} | "
            f"{_safe_float(base.get('max_dd_pct')):.4f} | {current.get('trades', '')} | "
            f"{current.get('long_trades', '')} | {current.get('short_trades', '')} | "
            f"{current_pnl:.4f} | {current_pnl - base_pnl:.4f} | "
            f"{_safe_float(current.get('max_dd_pct')):.4f} |"
        )
    return rows


def _fmt_optional(value: Any) -> str:
    if value is None:
        return "inf"
    return f"{_safe_float(value):.4f}"


def _write_report(
    payload: dict[str, Any],
    summary_path: Path,
    *,
    report_path: Path | None = None,
) -> Path:
    matrices = payload["matrices"]
    baseline_totals = payload.get("baseline_long_only_matrix_totals") or {}
    bidirectional_totals = payload.get("bidirectional_matrix_totals") or {}
    default_payload = matrices.get("default", {})
    supplemental_payload = matrices.get("supplemental", {})
    lines = [
        "# Portfolio A+B Bidirectional Research",
        "",
        "Date: 2026-05-06",
        "Status: `RESEARCH_ONLY_BIDIRECTIONAL_FIRST_PASS`",
        "",
        "## Scope",
        "",
        f"- Slot A LONG: `{payload['slot_a_long']}`",
        f"- Slot A SHORT: `{payload['slot_a_short']}`",
        f"- Slot B LONG: `{payload['slot_b_long']}`",
        f"- Slot B SHORT: `{payload['slot_b_short']}`",
        f"- Symbols: {', '.join(f'`{symbol}`' for symbol in payload['symbols'])}",
        f"- `RISK_PER_TRADE`: `{payload['risk_per_trade']}`",
        f"- `MAX_TOTAL_RISK`: Config default `{payload['max_total_risk']}`; intentionally not overridden.",
        f"- Summary artifact: `{summary_path}`",
        "- This is research-only. The two SHORT plugins are catalog-disabled by default and no runtime defaults were changed.",
        "- Current StrategyRuntime does not enforce `BTC_TREND_FILTER_ENABLED` or side-to-regime matching on plugin entries; this run measures current arbiter/runtime behavior, not SHORT promotion readiness.",
        "",
        "## Long-Only Baseline vs Bidirectional",
        "",
        "| matrix | baseline_trades | baseline_net_pnl | baseline_max_dd_pct | bidir_trades | bidir_long_trades | bidir_short_trades | bidir_net_pnl | pnl_delta | bidir_max_dd_pct |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_totals_rows(baseline_totals, bidirectional_totals),
        "",
        "## Default Windows Portfolio",
        "",
        "| window | trades | long_trades | short_trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_entry_long_short |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_matrix_summary_rows(default_payload),
        "",
        "## Default Windows Per Strategy",
        "",
        "| window | slot_side | trades | win_rate | net_pnl | profit_factor | avg_r | realized_trade_dd_pct | entry_stop_violations |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_strategy_rows(default_payload),
        "",
        "## Default Windows Reject Mix",
        "",
        "| window | slot_side | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_reject_rows(default_payload),
        "",
        "## Supplemental Portfolio",
        "",
        "| window | trades | long_trades | short_trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_entry_long_short |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_matrix_summary_rows(supplemental_payload),
        "",
        "## Supplemental Per Strategy",
        "",
        "| window | slot_side | trades | win_rate | net_pnl | profit_factor | avg_r | realized_trade_dd_pct | entry_stop_violations |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_strategy_rows(supplemental_payload),
        "",
        "## Supplemental Reject Mix",
        "",
        "| window | slot_side | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_reject_rows(supplemental_payload),
        "",
        "## Read",
        "",
        "- SHORT side adds raw coverage only if it improves portfolio PnL without increasing max drawdown or crowding LONG entries through `position_slot_occupied`.",
        "- `same_symbol_same_entry_long_short` uses actual trade `entry_time`, not wall-clock signal audit timestamps.",
        "- Validation windows overlap; totals are research attribution, not live expectancy estimates.",
        "- No production scanner defaults, credentials, router policy, runtime defaults, or live/testnet service state were changed.",
    ]
    output_path = Path(report_path or REPORT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Slot A+B LONG/SHORT research matrix")
    parser.add_argument("--matrix", choices=["default", "supplemental", "all"], default="all")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    run_portfolio_ab_bidirectional_matrix(
        matrix=args.matrix,
        symbols=list(args.symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=Path(args.results_root),
        report_path=Path(args.report_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
