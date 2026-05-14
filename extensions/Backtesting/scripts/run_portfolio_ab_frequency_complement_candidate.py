"""Run A+B promoted baseline plus the Phase 4A BTC recovery-band candidate."""

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
from extensions.Backtesting.scripts import run_portfolio_ab_short_ablation as short_ablation


SLOT_A_LONG = short_ablation.SLOT_A_LONG
SLOT_B_LONG = short_ablation.SLOT_B_LONG
SLOT_B_SHORT = short_ablation.SLOT_B_SHORT
CANDIDATE = "btc_recovery_band_trend_breadth_4h"
VARIANT = "slot_a_b_promoted_plus_btc_recovery_band"
STRATEGIES = (SLOT_A_LONG, SLOT_B_LONG, SLOT_B_SHORT, CANDIDATE)
STRATEGY_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
    CANDIDATE: "BTC Recovery-Band Candidate",
}
DEFAULT_SYMBOLS = portfolio_ab.DEFAULT_SYMBOLS
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "portfolio_ab_frequency_complement_candidate"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "portfolio_ab_frequency_complement_candidate_summary.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4b_frequency_complement_candidate_backtest.md"
DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-04-30"
DEFAULT_WINDOW = "2026_01_01_2026_04_30"
REJECT_REASONS = portfolio_ab.REJECT_REASONS


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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
        precompute_indicators=True,
        config_overrides=_research_overrides(risk_per_trade),
    )


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
        wins += int(pnl > 0)
        gross_profit += max(pnl, 0.0)
        gross_loss += min(pnl, 0.0)
        realized_r += _safe_float(row.get("realized_r"))
    trades = len(rows)
    loss_abs = abs(gross_loss)
    return {
        "trades": trades,
        "win_rate": round(wins / trades, 4) if trades else 0.0,
        "net_pnl": round(sum(_safe_float(row.get("pnl_usdt")) for row in rows), 4),
        "profit_factor": round(gross_profit / loss_abs, 4) if loss_abs else None,
        "avg_realized_r": round(realized_r / trades, 4) if trades else 0.0,
        "entry_stop_violations": _entry_stop_violations(rows),
    }


def _per_strategy_metrics(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {
        strategy_id: _trade_metrics(
            [row for row in rows if row.get("strategy_id") == strategy_id]
        )
        for strategy_id in STRATEGIES
    }


def _per_side_metrics(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {
        side: _trade_metrics(
            [row for row in rows if str(row.get("side") or "").upper() == side]
        )
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


def _same_symbol_same_entry_side_collisions(rows: list[dict[str, str]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], set[str]] = {}
    for row in rows:
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
    return {"count": len(collisions), "examples": collisions[:10]}


def _summary_row(cell_dir: Path) -> dict[str, Any]:
    summary = _read_json(cell_dir / "summary.json")
    trades = _read_csv(cell_dir / "trades.csv")
    return {
        "portfolio": {
            "trades": _safe_int(summary.get("total_trades")),
            "net_pnl": round(
                sum(_safe_float(row.get("pnl_usdt")) for row in trades),
                4,
            ),
            "max_dd_pct": round(_safe_float(summary.get("max_drawdown_pct")), 4),
            "run_errors": _safe_int(summary.get("backtest_run_error_count")),
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


def _render_report(payload: dict[str, Any]) -> str:
    cell = payload["matrices"][VARIANT]["custom"][DEFAULT_WINDOW]
    portfolio = cell["portfolio"]
    candidate = cell["per_strategy"][CANDIDATE]
    reject = cell["reject_mix"][CANDIDATE]
    lines = [
        "# Weekly Profit Phase 4B Frequency Complement Candidate Backtest",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `RESEARCH_ONLY_A_B_PLUS_CANDIDATE_BACKTEST_COMPLETE`",
        "",
        "## Scope",
        "",
        f"- Slot A LONG: `{SLOT_A_LONG}`",
        f"- Slot B LONG: `{SLOT_B_LONG}`",
        f"- Slot B SHORT: `{SLOT_B_SHORT}`",
        f"- Candidate: `{CANDIDATE}`",
        f"- Window: `{payload['window']['start']}..{payload['window']['end']}`",
        f"- Symbols: {', '.join(f'`{symbol}`' for symbol in payload['symbols'])}",
        "- Runtime defaults remain unchanged; the candidate is catalog-disabled outside this backtest-only run.",
        "",
        "## Combined Portfolio",
        "",
        "The combined run is not promotion-ready: the candidate raises participation but makes the contiguous-window economics negative.",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| trades | {portfolio['trades']} |",
        f"| net pnl | {portfolio['net_pnl']:.4f} |",
        f"| max drawdown pct | {portfolio['max_dd_pct']:.4f} |",
        f"| run errors | {portfolio['run_errors']} |",
        f"| entry stop violations | {portfolio['entry_stop_violations']} |",
        "",
        "## Candidate Read",
        "",
        "The candidate is the loss source in this run and must stay research-only.",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| realized trades | {candidate['trades']} |",
        f"| net pnl | {candidate['net_pnl']:.4f} |",
        f"| win rate | {candidate['win_rate']:.4f} |",
        f"| avg realized r | {candidate['avg_realized_r']:.4f} |",
        f"| emitted intents | {reject['emitted_intents']} |",
        f"| accepted entries | {reject['entries']} |",
        f"| rejects | {reject['rejects']} |",
        f"| router block rate | {reject['strategy_router_block_rate']:.4f} |",
        "",
        "## Artifact",
        "",
        f"- Summary JSON: `{DEFAULT_SUMMARY}`",
    ]
    return "\n".join(lines) + "\n"


def run_frequency_complement_candidate(
    *,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    window_name: str = DEFAULT_WINDOW,
    symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    summary_path: Path = DEFAULT_SUMMARY,
    report_path: Path = DEFAULT_REPORT,
    rerun: bool = False,
) -> tuple[Path, Path]:
    symbols = list(symbols or DEFAULT_SYMBOLS)
    cell_dir = Path(results_root) / VARIANT / "custom" / window_name
    if rerun or not (cell_dir / "summary.json").exists():
        print(
            "[PortfolioABFrequencyComplementCandidate] "
            f"custom/{window_name}: {start}->{end} strategies={','.join(STRATEGIES)}"
        )
        cfg = _build_config(start, end, symbols=symbols, risk_per_trade=risk_per_trade)
        result = BacktestEngine(cfg).run()
        ReportGenerator().generate(result, cell_dir)
    else:
        print(
            "[PortfolioABFrequencyComplementCandidate] "
            f"reuse custom/{window_name}: {cell_dir}"
        )

    cell = _summary_row(cell_dir)
    cell["window"] = {"start": start, "end": end}
    payload = {
        "schema": "strategy_plugin_portfolio_ab_frequency_complement_candidate.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "RESEARCH_ONLY_A_B_PLUS_CANDIDATE_BACKTEST_COMPLETE",
        "variant": VARIANT,
        "slot_a_long": SLOT_A_LONG,
        "slot_b_long": SLOT_B_LONG,
        "slot_b_short": SLOT_B_SHORT,
        "candidate": CANDIDATE,
        "strategies": list(STRATEGIES),
        "symbols": symbols,
        "risk_per_trade": float(risk_per_trade),
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": float(Config.MAX_TOTAL_RISK),
        "window": {"name": window_name, "start": start, "end": end},
        "matrices": {VARIANT: {"custom": {window_name: cell}}},
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload), encoding="utf-8")
    print(f"[PortfolioABFrequencyComplementCandidate] summary={summary_path}")
    print(f"[PortfolioABFrequencyComplementCandidate] report={report_path}")
    return summary_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run A+B promoted baseline plus BTC recovery-band candidate."
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--window-name", default=DEFAULT_WINDOW)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args(argv)
    run_frequency_complement_candidate(
        start=args.start,
        end=args.end,
        window_name=args.window_name,
        symbols=list(args.symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=args.results_root,
        summary_path=args.summary_path,
        report_path=args.report_path,
        rerun=bool(args.rerun),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
