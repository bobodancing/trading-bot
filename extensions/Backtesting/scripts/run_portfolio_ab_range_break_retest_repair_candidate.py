"""Run A+B plus the Phase 4D repaired range-break retest candidate."""

from __future__ import annotations

import argparse
import json
import sys
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

from extensions.Backtesting.scripts.run_portfolio_ab_range_break_retest_candidate import (
    CANDIDATE,
    DEFAULT_END,
    DEFAULT_START,
    DEFAULT_SYMBOLS,
    DEFAULT_WINDOW,
    STRATEGIES,
    _summary_row,
)
from extensions.Backtesting.scripts.analyze_weekly_profit_range_break_retest_repair_filter import (
    DEFAULT_JSON as DEFAULT_REPAIR_FILTER_JSON,
)


REPAIR_VARIANT = "slot_a_b_promoted_plus_range_break_retest_quality_repair"
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "portfolio_ab_range_break_retest_repair_candidate"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "portfolio_ab_range_break_retest_repair_candidate_summary.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4d_range_break_retest_repair_candidate_backtest.md"
FALLBACK_REPAIR_PARAMS = {"breakout_close_quality_min": 0.8325}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _repair_params(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    params = ((payload.get("recommended") or {}).get("params") or {})
    return dict(params or FALLBACK_REPAIR_PARAMS)


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
    repair_params: dict[str, Any],
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
        strategy_params_override={CANDIDATE: dict(repair_params)},
    )


def _candidate_read(candidate: dict[str, Any]) -> str:
    if int(candidate["trades"]) == 0:
        return "The repaired candidate emitted no closed trades in the combined run."
    if float(candidate["net_pnl"]) >= 0.0:
        return "The repaired candidate preserved positive standalone economics in the combined run."
    return "The repaired candidate still added realized trades with negative standalone economics."


def _render_report(payload: dict[str, Any]) -> str:
    cell = payload["matrices"][REPAIR_VARIANT]["custom"][DEFAULT_WINDOW]
    portfolio = cell["portfolio"]
    candidate = cell["per_strategy"][CANDIDATE]
    repair_params = payload["repair_params"]
    lines = [
        "# Weekly Profit Phase 4D Range-Break Retest Repair Candidate Backtest",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `RESEARCH_ONLY_A_B_PLUS_REPAIRED_RANGE_BREAK_RETEST_BACKTEST_COMPLETE`",
        "",
        "## Scope",
        "",
        f"- Candidate: `{CANDIDATE}`",
        f"- Repair params: `{json.dumps(repair_params, sort_keys=True)}`",
        f"- Window: `{payload['window']['start']}..{payload['window']['end']}`",
        f"- Symbols: {', '.join(f'`{symbol}`' for symbol in payload['symbols'])}",
        "- Runtime defaults remain unchanged; params are a backtest-only catalog overlay.",
        "",
        "## Combined Portfolio",
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
        _candidate_read(candidate),
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| realized trades | {candidate['trades']} |",
        f"| net pnl | {candidate['net_pnl']:.4f} |",
        f"| win rate | {candidate['win_rate']:.4f} |",
        f"| avg realized r | {candidate['avg_realized_r']:.4f} |",
        "",
        "## Artifact",
        "",
        f"- Summary JSON: `{DEFAULT_SUMMARY}`",
    ]
    return "\n".join(lines) + "\n"


def run_range_break_retest_repair_candidate(
    *,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    window_name: str = DEFAULT_WINDOW,
    symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    repair_filter_path: Path = DEFAULT_REPAIR_FILTER_JSON,
    repair_params: dict[str, Any] | None = None,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    summary_path: Path = DEFAULT_SUMMARY,
    report_path: Path = DEFAULT_REPORT,
    rerun: bool = False,
) -> tuple[Path, Path]:
    symbols = list(symbols or DEFAULT_SYMBOLS)
    active_repair_params = dict(repair_params or _repair_params(repair_filter_path))
    cell_dir = Path(results_root) / REPAIR_VARIANT / "custom" / window_name
    if rerun or not (cell_dir / "summary.json").exists():
        print(
            "[PortfolioABRangeBreakRetestRepairCandidate] "
            f"custom/{window_name}: {start}->{end} params={active_repair_params}"
        )
        cfg = _build_config(
            start,
            end,
            symbols=symbols,
            risk_per_trade=risk_per_trade,
            repair_params=active_repair_params,
        )
        result = BacktestEngine(cfg).run()
        ReportGenerator().generate(result, cell_dir)
    else:
        print(
            "[PortfolioABRangeBreakRetestRepairCandidate] "
            f"reuse custom/{window_name}: {cell_dir}"
        )

    cell = _summary_row(cell_dir)
    cell["window"] = {"start": start, "end": end}
    payload = {
        "schema": "strategy_plugin_portfolio_ab_range_break_retest_repair_candidate.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "RESEARCH_ONLY_A_B_PLUS_REPAIRED_RANGE_BREAK_RETEST_BACKTEST_COMPLETE",
        "variant": REPAIR_VARIANT,
        "candidate": CANDIDATE,
        "repair_filter_source": str(repair_filter_path),
        "repair_params": active_repair_params,
        "strategies": list(STRATEGIES),
        "symbols": symbols,
        "risk_per_trade": float(risk_per_trade),
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": float(Config.MAX_TOTAL_RISK),
        "window": {"name": window_name, "start": start, "end": end},
        "matrices": {REPAIR_VARIANT: {"custom": {window_name: cell}}},
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload), encoding="utf-8")
    print(f"[PortfolioABRangeBreakRetestRepairCandidate] summary={summary_path}")
    print(f"[PortfolioABRangeBreakRetestRepairCandidate] report={report_path}")
    return summary_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run A+B promoted baseline plus repaired range-break retest candidate."
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--window-name", default=DEFAULT_WINDOW)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--repair-filter", type=Path, default=DEFAULT_REPAIR_FILTER_JSON)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args(argv)
    run_range_break_retest_repair_candidate(
        start=args.start,
        end=args.end,
        window_name=args.window_name,
        symbols=list(args.symbols),
        risk_per_trade=args.risk_per_trade,
        repair_filter_path=args.repair_filter,
        results_root=args.results_root,
        summary_path=args.summary_path,
        report_path=args.report_path,
        rerun=bool(args.rerun),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
