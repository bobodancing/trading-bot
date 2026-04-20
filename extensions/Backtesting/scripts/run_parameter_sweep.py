"""Run a small backtest-only parameter sweep for one StrategyRuntime plugin."""

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
from config_presets import apply_strategy_params_override, explicit_symbol_universe, plugin_runtime_defaults
from plugin_candidate_review import DEFAULT_WINDOWS
from plugin_parameter_sweep import (
    build_sweep_cells,
    slugify,
    write_parameter_sweep_report,
    write_sweep_manifest,
)
from report_generator import ReportGenerator
from trader.strategies.plugins._catalog import get_strategy_catalog


DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "sweeps"


def _build_config(
    candidate_id: str,
    start: str,
    end: str,
    *,
    symbols: list[str],
    params: dict[str, Any],
) -> BacktestConfig:
    return BacktestConfig(
        symbols=list(symbols),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=[candidate_id],
        allowed_plugin_ids=[candidate_id],
        config_overrides=explicit_symbol_universe(plugin_runtime_defaults()),
        strategy_params_override={candidate_id: dict(params)},
    )


def _parse_param_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _grid_from_params(params: list[str] | None) -> dict[str, list[Any]]:
    grid: dict[str, list[Any]] = {}
    for raw in params or []:
        if "=" not in raw:
            raise ValueError(f"--param must use name=value1,value2 format: {raw}")
        key, values = raw.split("=", 1)
        key = key.strip()
        parsed_values = [_parse_param_value(item.strip()) for item in values.split(",") if item.strip()]
        if not key or not parsed_values:
            raise ValueError(f"--param must use name=value1,value2 format: {raw}")
        grid[key] = parsed_values
    return grid


def _grid_from_file(path: Path) -> dict[str, list[Any]]:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    grid = spec.get("grid") or spec.get("parameters")
    if not isinstance(grid, dict):
        raise ValueError("grid file must contain a 'grid' or 'parameters' object")
    return {str(key): values for key, values in grid.items()}


def _default_sweep_id(candidate_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{slugify(candidate_id)}_{ts}"


def _selected_windows(names: list[str] | None) -> dict[str, tuple[str, str]]:
    if not names:
        return dict(DEFAULT_WINDOWS)
    unknown = sorted(set(names) - set(DEFAULT_WINDOWS))
    if unknown:
        raise ValueError(f"Unknown review window(s): {', '.join(unknown)}")
    return {name: DEFAULT_WINDOWS[name] for name in names}


def run_parameter_sweep(
    candidate_id: str,
    grid: dict[str, list[Any]],
    *,
    sweep_id: str | None = None,
    symbols: list[str] | None = None,
    windows: dict[str, tuple[str, str]] | None = None,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    repo_root: Path = REPO_ROOT,
) -> tuple[Path, Path]:
    """Run all grid cells and write a research-only sweep report."""
    symbols = list(symbols or DEFAULT_SYMBOLS)
    windows = dict(windows or DEFAULT_WINDOWS)
    sweep_id = sweep_id or _default_sweep_id(candidate_id)
    cells = build_sweep_cells(grid)

    # Fail fast before loading market data if params do not match plugin schema.
    base_catalog = get_strategy_catalog([candidate_id])
    for cell in cells:
        apply_strategy_params_override(base_catalog, {candidate_id: cell["params"]})

    sweep_dir = Path(results_root) / slugify(candidate_id) / slugify(sweep_id)
    manifest_path = write_sweep_manifest(
        sweep_dir,
        sweep_id=sweep_id,
        candidate_id=candidate_id,
        grid=grid,
        cells=cells,
        windows=windows,
        symbols=symbols,
    )

    for cell in cells:
        cell_id = str(cell["cell_id"])
        params = dict(cell["params"])
        for window_name, (start, end) in windows.items():
            output_dir = sweep_dir / cell_id / window_name
            cfg = _build_config(candidate_id, start, end, symbols=symbols, params=params)
            print(
                "[ParameterSweep] "
                f"{sweep_id} {cell_id} {window_name}: params={params} "
                f"{start}->{end}"
            )
            result = BacktestEngine(cfg).run()
            ReportGenerator().generate(result, output_dir)

    report_path = write_parameter_sweep_report(
        Path(repo_root),
        sweep_dir,
        sweep_id=sweep_id,
        candidate_id=candidate_id,
        cells=cells,
        windows=windows,
    )
    print(f"[ParameterSweep] manifest={manifest_path}")
    print(f"[ParameterSweep] report={report_path}")
    return report_path, manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a plugin parameter sweep")
    parser.add_argument("--candidate", required=True, help="Strategy plugin id to sweep")
    parser.add_argument("--sweep-id", default=None, help="Stable id for artifacts/report")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--windows", nargs="+", choices=list(DEFAULT_WINDOWS), default=None)
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--grid-file", help="JSON file containing {'grid': {'param': [values]}}")
    source.add_argument(
        "--param",
        action="append",
        help="Param grid item, e.g. atr_mult=1.0,1.5. Repeat for Cartesian grid.",
    )
    args = parser.parse_args(argv)

    grid = _grid_from_file(Path(args.grid_file)) if args.grid_file else _grid_from_params(args.param)
    run_parameter_sweep(
        args.candidate,
        grid,
        sweep_id=args.sweep_id,
        symbols=list(args.symbols),
        windows=_selected_windows(args.windows),
        results_root=Path(args.results_root),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
