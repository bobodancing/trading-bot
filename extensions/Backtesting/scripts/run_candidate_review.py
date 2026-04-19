"""Run a StrategyRuntime plugin candidate through the review backtest matrix."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backtest_engine import BacktestConfig, BacktestEngine
from config_presets import explicit_symbol_universe, plugin_runtime_defaults
from plugin_candidate_review import DEFAULT_WINDOWS, write_candidate_review_report
from report_generator import ReportGenerator


DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results"


def _build_config(candidate_id: str, start: str, end: str) -> BacktestConfig:
    return BacktestConfig(
        symbols=list(DEFAULT_SYMBOLS),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=[candidate_id],
        allowed_plugin_ids=[candidate_id],
        config_overrides=explicit_symbol_universe(plugin_runtime_defaults()),
    )


def _summary_line(candidate_id: str, window_name: str, output_dir: Path) -> dict:
    summary_path = output_dir / "summary.json"
    audit_path = output_dir / "signal_audit_summary.json"
    summary = _read_json(summary_path)
    audit = _read_json(audit_path)
    return {
        "candidate_id": candidate_id,
        "window": window_name,
        "total_trades": int(summary.get("total_trades", 0) or 0),
        "backtest_run_error_count": int(summary.get("backtest_run_error_count", 0) or 0),
        "entry_stop_violations": _entry_stop_violations(output_dir / "trades.csv"),
        "rejects_by_reason": audit.get("rejects_by_reason", {}),
    }


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _entry_stop_violations(trades_path: Path) -> int | None:
    if not trades_path.exists():
        return None
    with trades_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"side", "entry_price", "entry_initial_sl"}
        if not required.issubset(set(reader.fieldnames or [])):
            return None
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


def run_candidate_review(
    candidate_id: str,
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
) -> tuple[Path, list[dict], str]:
    """Run all review windows and write the promotion-gated report."""
    results_root = Path(results_root)
    candidate_results_dir = results_root / candidate_id
    rows: list[dict] = []

    for window_name, (start, end) in DEFAULT_WINDOWS.items():
        output_dir = candidate_results_dir / window_name
        cfg = _build_config(candidate_id, start, end)
        print(
            f"[CandidateReview] {candidate_id} {window_name}: "
            f"{start} -> {end} symbols={','.join(DEFAULT_SYMBOLS)}"
        )
        result = BacktestEngine(cfg).run()
        ReportGenerator().generate(result, output_dir)
        row = _summary_line(candidate_id, window_name, output_dir)
        rows.append(row)
        print(
            "[CandidateReview] "
            f"{window_name}: total_trades={row['total_trades']} "
            f"backtest_run_error_count={row['backtest_run_error_count']} "
            f"entry_stop_violations={row['entry_stop_violations']} "
            f"rejects_by_reason={row['rejects_by_reason']}"
        )

    verdict = write_candidate_review_report(
        REPO_ROOT,
        results_root,
        [candidate_id],
        windows=DEFAULT_WINDOWS,
    )
    report_path = REPO_ROOT / "reports" / "strategy_plugin_candidate_review.md"
    print(f"[CandidateReview] report={report_path}")
    print(f"[CandidateReview] verdict={verdict}")
    return report_path, rows, verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run plugin candidate review matrix")
    parser.add_argument("--candidate", required=True, help="Strategy plugin id to review")
    parser.add_argument(
        "--results-root",
        default=str(DEFAULT_RESULTS_ROOT),
        help="Backtest artifact root directory",
    )
    args = parser.parse_args(argv)

    run_candidate_review(args.candidate, results_root=Path(args.results_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
