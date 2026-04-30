"""Run Slot A + Slot B combined portfolio backtest matrices."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
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
from plugin_candidate_review import DEFAULT_WINDOWS
from report_generator import ReportGenerator
from trader.config import Config


SLOT_A = (
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_B = "donchian_range_fade_4h_range_width_cv_013"
DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "portfolio_ab"
REPORT_PATH = REPO_ROOT / "reports" / "portfolio_a_b_combined_first_pass.md"
SUPPLEMENTAL_WINDOWS = {
    "bull_strong_up_1": ("2024-10-01", "2025-03-31"),
    "bear_persistent_down": ("2025-04-01", "2025-08-31"),
    "range_low_vol": ("2025-09-01", "2025-12-31"),
    "bull_recovery_2026": ("2026-01-01", "2026-02-28"),
    "ftx_style_crash": ("2022-11-01", "2022-12-31"),
    "sideways_transition": ("2023-06-01", "2023-09-30"),
    "classic_rollercoaster_2021_2022": ("2021-01-01", "2022-12-31"),
    "recovery_2023_2024": ("2023-01-01", "2024-12-31"),
}
REJECT_REASONS = (
    "position_slot_occupied",
    "strategy_router_blocked",
    "cooldown",
    "central_risk_blocked",
    "total_risk_limit",
)


def _phase3_overrides(risk_per_trade: float) -> dict[str, Any]:
    overrides = plugin_runtime_defaults()
    overrides["RISK_PER_TRADE"] = float(risk_per_trade)
    # Intentionally do not override MAX_TOTAL_RISK; Phase 3 validates the
    # Config class default interaction.
    return explicit_symbol_universe(overrides)


def _build_config(
    start: str,
    end: str,
    *,
    symbols: list[str],
    risk_per_trade: float,
) -> BacktestConfig:
    strategies = [SLOT_A, SLOT_B]
    return BacktestConfig(
        symbols=list(symbols),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=strategies,
        allowed_plugin_ids=strategies,
        config_overrides=_phase3_overrides(risk_per_trade),
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


def _per_strategy_metrics(trades: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for strategy_id in (SLOT_A, SLOT_B):
        rows = [row for row in trades if row.get("strategy_id") == strategy_id]
        payload[strategy_id] = {
            "trades": len(rows),
            "net_pnl": round(sum(_safe_float(row.get("pnl_usdt")) for row in rows), 4),
            "realized_trade_dd_pct": _realized_trade_dd_pct(rows),
            "entry_stop_violations": _entry_stop_violations(rows),
        }
    return payload


def _reject_metrics(cell_dir: Path) -> dict[str, dict[str, Any]]:
    rejects = _read_csv(cell_dir / "signal_rejects.csv")
    entries = _read_csv(cell_dir / "signal_entries.csv")
    payload: dict[str, dict[str, Any]] = {}
    for strategy_id in (SLOT_A, SLOT_B):
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


def _same_symbol_same_candle_overlaps(cell_dir: Path) -> dict[str, Any]:
    rows = []
    for path in (cell_dir / "signal_entries.csv", cell_dir / "signal_rejects.csv"):
        rows.extend(_read_csv(path))

    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        strategy_id = row.get("signal_type")
        symbol = row.get("symbol")
        timestamp = row.get("timestamp")
        if strategy_id in {SLOT_A, SLOT_B} and symbol and timestamp:
            grouped[(timestamp, symbol)].add(strategy_id)

    overlaps = [
        {"timestamp": timestamp, "symbol": symbol}
        for (timestamp, symbol), strategies in grouped.items()
        if {SLOT_A, SLOT_B}.issubset(strategies)
    ]
    overlaps.sort(key=lambda row: (row["timestamp"], row["symbol"]))
    return {
        "count": len(overlaps),
        "examples": overlaps[:10],
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
        "reject_mix": _reject_metrics(cell_dir),
        "same_symbol_same_candle_overlaps": _same_symbol_same_candle_overlaps(cell_dir),
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
        "[PortfolioAB] "
        f"{matrix_name}/{window_name}: {start}->{end} "
        f"symbols={','.join(symbols)} risk_per_trade={risk_per_trade}"
    )
    cfg = _build_config(start, end, symbols=symbols, risk_per_trade=risk_per_trade)
    result = BacktestEngine(cfg).run()
    ReportGenerator().generate(result, output_dir)
    return _summary_row(output_dir)


def run_portfolio_ab_matrix(
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
        selected.append(("default", DEFAULT_WINDOWS))
    if matrix in {"supplemental", "all"}:
        selected.append(("supplemental", SUPPLEMENTAL_WINDOWS))
    if not selected:
        raise ValueError("matrix must be one of: default, supplemental, all")

    run_dir = Path(results_root) / "slot_a_b"
    matrices: dict[str, dict[str, Any]] = {}
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

    decision_gates = _aggregate_gate_read(matrices)
    payload = {
        "schema": "strategy_plugin_portfolio_ab_matrix.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "slot_a": SLOT_A,
        "slot_b": SLOT_B,
        "symbols": symbols,
        "risk_per_trade": float(risk_per_trade),
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": float(Config.MAX_TOTAL_RISK),
        "results_root": str(run_dir),
        "decision_gates": decision_gates,
        "matrices": matrices,
    }
    summary_path = run_dir / "portfolio_ab_matrix_summary.json"
    summary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(payload, summary_path, report_path=report_path)
    print(f"[PortfolioAB] summary={summary_path}")
    print(f"[PortfolioAB] report={report_path}")
    return summary_path, report_path


def _matrix_summary_rows(matrix_payload: dict[str, Any]) -> list[str]:
    rows = []
    for window_name, cell in matrix_payload.items():
        p = cell["portfolio"]
        rows.append(
            f"| `{window_name}` | {p['trades']} | {p['net_pnl']:.4f} | "
            f"{p['max_dd_pct']:.4f} | {p['run_errors']} | "
            f"{cell['same_symbol_same_candle_overlaps']['count']} |"
        )
    return rows


def _strategy_rows(matrix_payload: dict[str, Any]) -> list[str]:
    rows = []
    for window_name, cell in matrix_payload.items():
        for strategy_id in (SLOT_A, SLOT_B):
            s = cell["per_strategy"][strategy_id]
            label = "Slot A" if strategy_id == SLOT_A else "Slot B"
            rows.append(
                f"| `{window_name}` | {label} | {s['trades']} | {s['net_pnl']:.4f} | "
                f"{s['realized_trade_dd_pct']:.4f} | {s['entry_stop_violations']} |"
            )
    return rows


def _reject_rows(matrix_payload: dict[str, Any]) -> list[str]:
    rows = []
    for window_name, cell in matrix_payload.items():
        for strategy_id in (SLOT_A, SLOT_B):
            r = cell["reject_mix"][strategy_id]
            label = "Slot A" if strategy_id == SLOT_A else "Slot B"
            rows.append(
                f"| `{window_name}` | {label} | {r['entries']} | {r['rejects']} | "
                f"{r['position_slot_occupied']} | {r['strategy_router_blocked']} | "
                f"{r['cooldown']} | {r['central_risk_blocked']} | {r['total_risk_limit']} | "
                f"{r['strategy_router_block_rate']:.4f} |"
            )
    return rows


def _aggregate_gate_read(matrices: dict[str, Any]) -> dict[str, Any]:
    max_portfolio_dd = 0.0
    max_overlap = 0
    router_totals = {
        SLOT_A: {"emitted": 0, "blocked": 0},
        SLOT_B: {"emitted": 0, "blocked": 0},
    }
    for matrix_payload in matrices.values():
        for cell in matrix_payload.values():
            max_portfolio_dd = max(max_portfolio_dd, cell["portfolio"]["max_dd_pct"])
            max_overlap = max(max_overlap, cell["same_symbol_same_candle_overlaps"]["count"])
            for strategy_id in (SLOT_A, SLOT_B):
                r = cell["reject_mix"][strategy_id]
                router_totals[strategy_id]["emitted"] += int(r["emitted_intents"])
                router_totals[strategy_id]["blocked"] += int(r["strategy_router_blocked"])

    router_rates = {}
    for strategy_id, totals in router_totals.items():
        emitted = totals["emitted"]
        router_rates[strategy_id] = round(totals["blocked"] / emitted, 4) if emitted else 0.0
    return {
        "max_portfolio_dd_pct": round(max_portfolio_dd, 4),
        "max_window_overlap_count": int(max_overlap),
        "strategy_router_block_rates": router_rates,
        "portfolio_dd_gate_pass": max_portfolio_dd <= 8.0,
        "overlap_gate_pass": max_overlap <= 5,
        "router_gate_pass": all(rate <= 0.5 for rate in router_rates.values()),
    }


def _write_report(
    payload: dict[str, Any],
    summary_path: Path,
    *,
    report_path: Path | None = None,
) -> Path:
    matrices = payload["matrices"]
    gate = payload.get("decision_gates") or _aggregate_gate_read(matrices)
    all_gates_pass = (
        gate["portfolio_dd_gate_pass"]
        and gate["overlap_gate_pass"]
        and gate["router_gate_pass"]
    )
    verdict = (
        "PASS - A+B portfolio earns first promotion-candidate qualification; "
        "no runtime promotion without Ruei approval."
        if all_gates_pass
        else "FAIL - revisit portfolio construction before promotion review."
    )
    default_payload = matrices.get("default", {})
    supplemental_payload = matrices.get("supplemental", {})
    lines = [
        "# Portfolio A+B Combined First Pass",
        "",
        "Date: 2026-04-29",
        "Status: `PHASE_3_PORTFOLIO_FIRST_PASS`",
        "",
        "## Scope",
        "",
        f"- Slot A: `{payload['slot_a']}`",
        f"- Slot B: `{payload['slot_b']}`",
        f"- Symbols: {', '.join(f'`{symbol}`' for symbol in payload['symbols'])}",
        f"- `RISK_PER_TRADE`: `{payload['risk_per_trade']}`",
        f"- `MAX_TOTAL_RISK`: Config default `{payload['max_total_risk']}`; intentionally not overridden.",
        f"- Summary artifact: `{summary_path}`",
        "- Current StrategyRuntime does not enforce `BTC_TREND_FILTER_ENABLED` on plugin entries; no BTC trend filter reject or size=0 attribution is inferred.",
        "",
        "## Decision Gate",
        "",
        "| gate | value | threshold | result |",
        "| --- | ---: | ---: | --- |",
        f"| portfolio max_dd_pct | {gate['max_portfolio_dd_pct']:.4f} | 8.0000 | {'PASS' if gate['portfolio_dd_gate_pass'] else 'FAIL'} |",
        f"| max window same-symbol same-candle A+B emits | {gate['max_window_overlap_count']} | 5 | {'PASS' if gate['overlap_gate_pass'] else 'FAIL'} |",
        f"| Slot A aggregate router block rate | {gate['strategy_router_block_rates'][SLOT_A]:.4f} | 0.5000 | {'PASS' if gate['strategy_router_block_rates'][SLOT_A] <= 0.5 else 'FAIL'} |",
        f"| Slot B aggregate router block rate | {gate['strategy_router_block_rates'][SLOT_B]:.4f} | 0.5000 | {'PASS' if gate['strategy_router_block_rates'][SLOT_B] <= 0.5 else 'FAIL'} |",
        "",
        f"Verdict: **{verdict}**",
        "",
        "## Default Windows Portfolio",
        "",
        "| window | trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_candle_overlaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        *_matrix_summary_rows(default_payload),
        "",
        "## Default Windows Per-Cartridge",
        "",
        "`realized_trade_dd_pct` is closed-trade attribution only; portfolio max drawdown above is the true equity-curve drawdown.",
        "",
        "| window | slot | trades | net_pnl | realized_trade_dd_pct | entry_stop_violations |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
        *_strategy_rows(default_payload),
        "",
        "## Default Windows Reject Mix",
        "",
        "| window | slot | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_reject_rows(default_payload),
        "",
        "## Supplemental Portfolio",
        "",
        "| window | trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_candle_overlaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        *_matrix_summary_rows(supplemental_payload),
        "",
        "## Supplemental Per-Cartridge",
        "",
        "| window | slot | trades | net_pnl | realized_trade_dd_pct | entry_stop_violations |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
        *_strategy_rows(supplemental_payload),
        "",
        "## Supplemental Reject Mix",
        "",
        "| window | slot | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_reject_rows(supplemental_payload),
        "",
        "## Read",
        "",
        "- This is a combined StrategyRuntime portfolio run; both plugins route through central arbiter, central RiskPlan, and shared position slots.",
        "- `central_risk_blocked` and `total_risk_limit` are reported separately so the Config default `MAX_TOTAL_RISK` interaction is visible.",
        "- Same-symbol same-candle overlaps count any candle where both Slot A and Slot B emitted an entry or reject audit row for the same symbol.",
        "- No runtime defaults or catalog promotion flags were changed.",
    ]
    output_path = Path(report_path or REPORT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Slot A+B portfolio matrix")
    parser.add_argument("--matrix", choices=["default", "supplemental", "all"], default="all")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    run_portfolio_ab_matrix(
        matrix=args.matrix,
        symbols=list(args.symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=Path(args.results_root),
        report_path=Path(args.report_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
