"""Run fixed supplemental-window matrix for a StrategyRuntime plugin."""

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
from report_generator import ReportGenerator


DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "custom_windows"
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


def _symbol_slug(symbol: str) -> str:
    return str(symbol).replace("/", "").replace(":", "").upper()


def _build_config(
    candidate_id: str,
    start: str,
    end: str,
    symbols: list[str],
    *,
    strategy_params: dict | None = None,
) -> BacktestConfig:
    return BacktestConfig(
        symbols=list(symbols),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=[candidate_id],
        allowed_plugin_ids=[candidate_id],
        config_overrides=explicit_symbol_universe(plugin_runtime_defaults()),
        strategy_params_override=(
            {candidate_id: dict(strategy_params)} if strategy_params else {}
        ),
    )


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _net_pnl(cell_dir: Path, summary: dict) -> float:
    if "net_pnl" in summary:
        return float(summary.get("net_pnl") or 0.0)
    trades_path = cell_dir / "trades.csv"
    if not trades_path.exists():
        return 0.0
    with trades_path.open(newline="", encoding="utf-8") as f:
        return sum(float(row.get("pnl_usdt") or 0.0) for row in csv.DictReader(f))


def _summary_row(cell_dir: Path) -> dict:
    summary = _read_json(cell_dir / "summary.json")
    return {
        "trades": int(summary.get("total_trades", 0) or 0),
        "net_pnl": round(_net_pnl(cell_dir, summary), 4),
        "max_dd_pct": round(float(summary.get("max_drawdown_pct", 0.0) or 0.0), 4),
        "run_errors": int(summary.get("backtest_run_error_count", 0) or 0),
    }


def _run_cell(
    candidate_id: str,
    window_name: str,
    start: str,
    end: str,
    symbols: list[str],
    output_dir: Path,
    *,
    strategy_params: dict | None = None,
) -> dict:
    print(
        "[SupplementalMatrix] "
        f"{candidate_id} {window_name} symbols={','.join(symbols)} "
        f"params={dict(strategy_params or {})} {start}->{end}"
    )
    cfg = _build_config(
        candidate_id,
        start,
        end,
        symbols,
        strategy_params=strategy_params,
    )
    result = BacktestEngine(cfg).run()
    ReportGenerator().generate(result, output_dir)
    return _summary_row(output_dir)


def run_supplemental_matrix(
    candidate_id: str,
    *,
    symbols: list[str] | None = None,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    include_symbol_slices: bool = True,
) -> Path:
    symbols = list(symbols or DEFAULT_SYMBOLS)
    candidate_dir = Path(results_root) / candidate_id
    matrix: dict[str, dict] = {}

    for window_name, (start, end) in SUPPLEMENTAL_WINDOWS.items():
        window_payload: dict[str, dict] = {
            "window": {"start": start, "end": end},
        }
        combined_dir = candidate_dir / window_name
        window_payload["combined"] = _run_cell(
            candidate_id,
            window_name,
            start,
            end,
            symbols,
            combined_dir,
        )
        if include_symbol_slices:
            slices = {}
            for symbol in symbols:
                slice_dir = candidate_dir / "symbol_slices" / _symbol_slug(symbol) / window_name
                # Keep the full market universe available so BTC regime/arbiter
                # context stays identical; only target plugin emission by symbol.
                slices[symbol] = _run_cell(
                    candidate_id,
                    window_name,
                    start,
                    end,
                    symbols,
                    slice_dir,
                    strategy_params={"symbol": symbol},
                )
            window_payload["symbol_slices"] = slices
        matrix[window_name] = window_payload

    summary_path = candidate_dir / "supplemental_matrix_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema": "strategy_plugin_supplemental_matrix.v1",
                "candidate_id": candidate_id,
                "symbols": symbols,
                "results_root": str(candidate_dir),
                "windows": matrix,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[SupplementalMatrix] summary={summary_path}")
    return summary_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run plugin supplemental matrix")
    parser.add_argument("--candidate", required=True, help="Strategy plugin id to review")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument(
        "--no-symbol-slices",
        action="store_true",
        help="Only run the combined-symbol matrix",
    )
    args = parser.parse_args(argv)
    run_supplemental_matrix(
        args.candidate,
        symbols=list(args.symbols),
        results_root=Path(args.results_root),
        include_symbol_slices=not args.no_symbol_slices,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
