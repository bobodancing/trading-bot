"""Run a one-off plugin review matrix with the shared arbiter disabled."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backtest_engine import BacktestConfig, BacktestEngine
from config_presets import diagnostic_arbiter_off, explicit_symbol_universe
from plugin_candidate_review import DEFAULT_WINDOWS
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
        config_overrides=explicit_symbol_universe(diagnostic_arbiter_off()),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run plugin candidate review matrix with arbiter off")
    parser.add_argument("--candidate", required=True, help="Strategy plugin id to review")
    args = parser.parse_args(argv)

    candidate_results_dir = DEFAULT_RESULTS_ROOT / f"{args.candidate}_arbiter_off"
    for window_name, (start, end) in DEFAULT_WINDOWS.items():
        output_dir = candidate_results_dir / window_name
        print(
            f"[CandidateReviewArbiterOff] {args.candidate} {window_name}: "
            f"{start} -> {end} symbols={','.join(DEFAULT_SYMBOLS)}"
        )
        result = BacktestEngine(_build_config(args.candidate, start, end)).run()
        ReportGenerator().generate(result, output_dir)
        print(f"[CandidateReviewArbiterOff] output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
