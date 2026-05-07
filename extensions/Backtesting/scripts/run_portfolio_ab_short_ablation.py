"""Run focused SHORT-side ablation matrices for the Slot A+B portfolio."""

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
from report_generator import ReportGenerator

from extensions.Backtesting.scripts import run_portfolio_ab_bidirectional_matrix as bidir
from extensions.Backtesting.scripts import run_portfolio_ab_matrix as portfolio_ab
from trader.config import Config


DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "portfolio_ab_bidirectional" / "short_ablation"
REPORT_PATH = REPO_ROOT / "reports" / "portfolio_a_b_short_ablation_research.md"
SUMMARY_PATH = DEFAULT_RESULTS_ROOT / "portfolio_ab_short_ablation_summary.json"

BASELINE_LONG_ONLY_SUMMARY = (
    BACKTEST_ROOT / "results" / "portfolio_ab" / "slot_a_b" / "portfolio_ab_matrix_summary.json"
)
BASELINE_BIDIRECTIONAL_SUMMARY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "slot_a_b_long_short"
    / "portfolio_ab_bidirectional_matrix_summary.json"
)

SLOT_A_LONG = bidir.SLOT_A_LONG
SLOT_A_SHORT = bidir.SLOT_A_SHORT
SLOT_B_LONG = bidir.SLOT_B_LONG
SLOT_B_SHORT = bidir.SLOT_B_SHORT

VARIANTS: dict[str, dict[str, Any]] = {
    "slot_a_short_overlay": {
        "label": "A+B plus Slot A SHORT",
        "strategies": [SLOT_A_LONG, SLOT_A_SHORT, SLOT_B_LONG],
        "read": "Tests whether Slot A SHORT can be added without Slot B SHORT masking its risk.",
    },
    "slot_b_short_overlay": {
        "label": "A+B plus Slot B SHORT",
        "strategies": [SLOT_A_LONG, SLOT_B_LONG, SLOT_B_SHORT],
        "read": "Tests whether Slot B SHORT is the cleaner first SHORT leg.",
    },
    "short_only": {
        "label": "Slot A SHORT plus Slot B SHORT",
        "strategies": [SLOT_A_SHORT, SLOT_B_SHORT],
        "read": "Isolates standalone SHORT-side behavior without long-side slot occupancy.",
    },
}

REFERENCE_VARIANTS: dict[str, dict[str, Any]] = {
    "long_only_reference": {
        "label": "A+B LONG-only reference",
        "source": BASELINE_LONG_ONLY_SUMMARY,
    },
    "bidirectional_reference": {
        "label": "A+B LONG/SHORT reference",
        "source": BASELINE_BIDIRECTIONAL_SUMMARY,
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


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
    overrides = bidir._research_overrides(risk_per_trade)
    overrides["RISK_PER_TRADE"] = float(risk_per_trade)
    return overrides


def _build_config(
    start: str,
    end: str,
    *,
    symbols: list[str],
    strategies: list[str],
    risk_per_trade: float,
) -> BacktestConfig:
    return BacktestConfig(
        symbols=list(symbols),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=list(strategies),
        allowed_plugin_ids=list(strategies),
        precompute_indicators=True,
        config_overrides=_research_overrides(risk_per_trade),
    )


def _run_cell(
    matrix_name: str,
    variant_name: str,
    window_name: str,
    start: str,
    end: str,
    *,
    output_dir: Path,
    symbols: list[str],
    strategies: list[str],
    risk_per_trade: float,
    reuse_existing: bool,
) -> dict[str, Any]:
    if reuse_existing and (output_dir / "summary.json").exists():
        print(
            "[PortfolioABShortAblation] "
            f"reuse {matrix_name}/{variant_name}/{window_name}: {output_dir}"
        )
        cell = bidir._summary_row(output_dir)
        cell["window"] = {"start": start, "end": end}
        return cell

    print(
        "[PortfolioABShortAblation] "
        f"{matrix_name}/{variant_name}/{window_name}: {start}->{end} "
        f"strategies={','.join(strategies)}"
    )
    cfg = _build_config(
        start,
        end,
        symbols=symbols,
        strategies=strategies,
        risk_per_trade=risk_per_trade,
    )
    result = BacktestEngine(cfg).run()
    ReportGenerator().generate(result, output_dir)
    cell = bidir._summary_row(output_dir)
    cell["window"] = {"start": start, "end": end}
    return cell


def _selected_matrices(matrix: str) -> list[tuple[str, dict[str, tuple[str, str]]]]:
    selected = []
    if matrix in {"default", "all"}:
        selected.append(("default", portfolio_ab.DEFAULT_WINDOWS))
    if matrix in {"supplemental", "all"}:
        selected.append(("supplemental", portfolio_ab.SUPPLEMENTAL_WINDOWS))
    if matrix == "custom":
        raise ValueError("custom matrix requires --custom-start and --custom-end")
    if not selected:
        raise ValueError("matrix must be one of: default, supplemental, all, custom")
    return selected


def _matrix_selection(
    matrix: str,
    *,
    custom_start: str | None,
    custom_end: str | None,
    custom_name: str,
) -> list[tuple[str, dict[str, tuple[str, str]]]]:
    if matrix != "custom":
        return _selected_matrices(matrix)
    if not custom_start or not custom_end:
        raise ValueError("custom matrix requires --custom-start and --custom-end")
    return [("custom", {custom_name: (custom_start, custom_end)})]


def _filter_windows(
    matrices: list[tuple[str, dict[str, tuple[str, str]]]],
    window_names: list[str] | None,
) -> list[tuple[str, dict[str, tuple[str, str]]]]:
    if not window_names:
        return matrices
    wanted = set(window_names)
    filtered = []
    available = set()
    for matrix_name, windows in matrices:
        available.update(windows)
        selected = {name: window for name, window in windows.items() if name in wanted}
        if selected:
            filtered.append((matrix_name, selected))
    missing = sorted(wanted - available)
    if missing:
        raise ValueError(f"unknown window(s): {', '.join(missing)}")
    return filtered


def _load_long_only_reference() -> dict[str, Any]:
    payload = _read_json(BASELINE_LONG_ONLY_SUMMARY)
    return payload.get("matrices", {}) if payload else {}


def _load_bidirectional_reference() -> dict[str, Any]:
    payload = _read_json(BASELINE_BIDIRECTIONAL_SUMMARY)
    return payload.get("matrices", {}) if payload else {}


def _reference_cell_from_long_only(cell: dict[str, Any]) -> dict[str, Any]:
    p = cell.get("portfolio", {})
    trades = _safe_int(p.get("trades"))
    return {
        "portfolio": {
            "trades": trades,
            "net_pnl": _safe_float(p.get("net_pnl")),
            "max_dd_pct": _safe_float(p.get("max_dd_pct")),
            "run_errors": _safe_int(p.get("run_errors")),
        },
        "per_side": {
            "LONG": {"trades": trades, "net_pnl": _safe_float(p.get("net_pnl"))},
            "SHORT": {"trades": 0, "net_pnl": 0.0},
        },
        "per_strategy": cell.get("per_strategy", {}),
    }


def _reference_matrices() -> dict[str, dict[str, dict[str, Any]]]:
    references: dict[str, dict[str, dict[str, Any]]] = {}

    long_only = _load_long_only_reference()
    if long_only:
        references["long_only_reference"] = {
            matrix_name: {
                window_name: _reference_cell_from_long_only(cell)
                for window_name, cell in matrix_payload.items()
            }
            for matrix_name, matrix_payload in long_only.items()
        }

    bidirectional = _load_bidirectional_reference()
    if bidirectional:
        references["bidirectional_reference"] = {
            matrix_name: dict(matrix_payload)
            for matrix_name, matrix_payload in bidirectional.items()
        }

    return references


def _cell_side_trades(cell: dict[str, Any], side: str) -> int:
    per_side = cell.get("per_side") or {}
    return _safe_int(per_side.get(side, {}).get("trades"))


def _cell_strategy_pnl(cell: dict[str, Any], strategy_id: str) -> float:
    per_strategy = cell.get("per_strategy") or {}
    return _safe_float(per_strategy.get(strategy_id, {}).get("net_pnl"))


def _matrix_totals_for_variant(matrix_payload: dict[str, Any]) -> dict[str, Any]:
    cells = list(matrix_payload.values())
    return {
        "trades": sum(_safe_int(cell.get("portfolio", {}).get("trades")) for cell in cells),
        "long_trades": sum(_cell_side_trades(cell, "LONG") for cell in cells),
        "short_trades": sum(_cell_side_trades(cell, "SHORT") for cell in cells),
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
        "run_errors": sum(_safe_int(cell.get("portfolio", {}).get("run_errors")) for cell in cells),
        "slot_a_short_net_pnl": round(sum(_cell_strategy_pnl(cell, SLOT_A_SHORT) for cell in cells), 4),
        "slot_b_short_net_pnl": round(sum(_cell_strategy_pnl(cell, SLOT_B_SHORT) for cell in cells), 4),
    }


def _matrix_totals(payload: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    totals: dict[str, dict[str, dict[str, Any]]] = {}
    for variant_name, variant_payload in payload.items():
        totals[variant_name] = {
            matrix_name: _matrix_totals_for_variant(matrix_payload)
            for matrix_name, matrix_payload in variant_payload.items()
        }
    return totals


def _matching_long_only_totals(
    matrices: dict[str, Any],
    *,
    matrix_name: str,
    variant_name: str,
) -> dict[str, Any]:
    long_only = matrices.get("long_only_reference", {}).get(matrix_name, {})
    variant_payload = matrices.get(variant_name, {}).get(matrix_name, {})
    if not long_only or not variant_payload:
        return {}
    matching = {
        window_name: long_only[window_name]
        for window_name in variant_payload
        if window_name in long_only
    }
    return _matrix_totals_for_variant(matching)


def _window_label(matrix_payload: dict[str, Any]) -> str:
    names = list(matrix_payload)
    if len(names) <= 2:
        return ",".join(names)
    return f"{len(names)} windows"


def _portfolio_rows(
    matrices: dict[str, Any],
    totals: dict[str, dict[str, dict[str, Any]]],
    *,
    matrix_name: str,
) -> list[str]:
    rows = []
    for variant_name in [
        "long_only_reference",
        "slot_a_short_overlay",
        "slot_b_short_overlay",
        "short_only",
        "bidirectional_reference",
    ]:
        item = totals.get(variant_name, {}).get(matrix_name)
        if not item:
            continue
        matrix_payload = matrices.get(variant_name, {}).get(matrix_name, {})
        long_ref = _matching_long_only_totals(
            matrices,
            matrix_name=matrix_name,
            variant_name=variant_name,
        )
        has_matching_ref = bool(long_ref)
        pnl_delta = (
            f"{item['net_pnl'] - _safe_float(long_ref.get('net_pnl')):.4f}"
            if has_matching_ref
            else "n/a"
        )
        dd_delta = (
            f"{item['max_dd_pct'] - _safe_float(long_ref.get('max_dd_pct')):.4f}"
            if has_matching_ref
            else "n/a"
        )
        rows.append(
            f"| `{matrix_name}` | `{variant_name}` | `{_window_label(matrix_payload)}` | "
            f"{item['trades']} | "
            f"{item['long_trades']} | {item['short_trades']} | "
            f"{item['net_pnl']:.4f} | {pnl_delta} | "
            f"{item['max_dd_pct']:.4f} | {dd_delta} | "
            f"{item['slot_a_short_net_pnl']:.4f} | {item['slot_b_short_net_pnl']:.4f} | "
            f"{item['run_errors']} |"
        )
    return rows


def _matrix_sections(matrices: dict[str, Any]) -> list[str]:
    names = []
    for variant_payload in matrices.values():
        for matrix_name in variant_payload:
            if matrix_name not in names:
                names.append(matrix_name)
    preferred = [name for name in ("default", "supplemental", "custom") if name in names]
    return preferred + [name for name in names if name not in preferred]


def _window_rows(
    payload: dict[str, Any],
    *,
    matrix_name: str,
) -> list[str]:
    rows = []
    for variant_name in ["slot_a_short_overlay", "slot_b_short_overlay", "short_only"]:
        matrix_payload = payload.get(variant_name, {}).get(matrix_name, {})
        for window_name, cell in matrix_payload.items():
            p = cell["portfolio"]
            rows.append(
                f"| `{variant_name}` | `{window_name}` | {p['trades']} | "
                f"{_cell_side_trades(cell, 'LONG')} | {_cell_side_trades(cell, 'SHORT')} | "
                f"{_safe_float(p.get('net_pnl')):.4f} | "
                f"{_safe_float(p.get('max_dd_pct')):.4f} | "
                f"{_cell_strategy_pnl(cell, SLOT_A_SHORT):.4f} | "
                f"{_cell_strategy_pnl(cell, SLOT_B_SHORT):.4f} | "
                f"{_safe_int(p.get('run_errors'))} |"
            )
    return rows


def _critical_stress_rows(matrices: dict[str, Any]) -> list[str]:
    matrix_name = "supplemental"
    window_name = "classic_rollercoaster_2021_2022"
    rows = []
    for variant_name in [
        "long_only_reference",
        "slot_a_short_overlay",
        "slot_b_short_overlay",
        "bidirectional_reference",
    ]:
        cell = matrices.get(variant_name, {}).get(matrix_name, {}).get(window_name)
        if not cell:
            continue
        p = cell["portfolio"]
        rows.append(
            f"| `{variant_name}` | {_safe_int(p.get('trades'))} | "
            f"{_cell_side_trades(cell, 'LONG')} | {_cell_side_trades(cell, 'SHORT')} | "
            f"{_safe_float(p.get('net_pnl')):.4f} | "
            f"{_safe_float(p.get('max_dd_pct')):.4f} | "
            f"{_cell_strategy_pnl(cell, SLOT_A_SHORT):.4f} | "
            f"{_cell_strategy_pnl(cell, SLOT_B_SHORT):.4f} |"
        )
    return rows


def _write_report(payload: dict[str, Any], summary_path: Path, report_path: Path) -> Path:
    totals = payload["matrix_totals"]
    variant_total_rows: list[str] = []
    for matrix_name in _matrix_sections(payload["matrices"]):
        variant_total_rows.extend(
            _portfolio_rows(payload["matrices"], totals, matrix_name=matrix_name)
        )
    lines = [
        "# Portfolio A+B SHORT Ablation Research",
        "",
        f"Date: {payload['date']}",
        "Status: `RESEARCH_ONLY_SHORT_ABLATION_SECOND_PASS`",
        "",
        "## Scope",
        "",
        f"- Slot A LONG: `{SLOT_A_LONG}`",
        f"- Slot A SHORT: `{SLOT_A_SHORT}`",
        f"- Slot B LONG: `{SLOT_B_LONG}`",
        f"- Slot B SHORT: `{SLOT_B_SHORT}`",
        f"- Symbols: {', '.join(f'`{symbol}`' for symbol in payload['symbols'])}",
        f"- `RISK_PER_TRADE`: `{payload['risk_per_trade']}`",
        f"- `MAX_TOTAL_RISK`: Config default `{payload['max_total_risk']}`; intentionally not overridden.",
        f"- Summary artifact: `{summary_path}`",
        "- Research direction: include SHORT side in the Slot A+B portfolio, but identify which SHORT leg can survive promotion-style risk review.",
        "- This pass does not change scanner defaults, credentials, router policy, thresholds, or live/testnet service state.",
        "",
        "## Variant Totals",
        "",
        "| matrix | variant | windows | trades | long_trades | short_trades | net_pnl | pnl_delta_vs_matching_long_only | max_dd_pct | dd_delta_vs_matching_long_only | slot_a_short_net_pnl | slot_b_short_net_pnl | run_errors |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *variant_total_rows,
        "",
        "## Critical Stress Read",
        "",
        "`classic_rollercoaster_2021_2022` is the stress window that exposed the all-four bidirectional drawdown problem.",
        "",
        "| variant | trades | long_trades | short_trades | net_pnl | max_dd_pct | slot_a_short_net_pnl | slot_b_short_net_pnl |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_critical_stress_rows(payload["matrices"]),
        "",
        "## Custom Window Detail",
        "",
        "| variant | window | trades | long_trades | short_trades | net_pnl | max_dd_pct | slot_a_short_net_pnl | slot_b_short_net_pnl | run_errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_window_rows(payload["matrices"], matrix_name="custom"),
        "",
        "## Supplemental Window Detail",
        "",
        "| variant | window | trades | long_trades | short_trades | net_pnl | max_dd_pct | slot_a_short_net_pnl | slot_b_short_net_pnl | run_errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_window_rows(payload["matrices"], matrix_name="supplemental"),
        "",
        "## Read",
        "",
        "- `slot_b_short_overlay` is the cleanest first promotion candidate if it adds PnL while keeping drawdown close to long-only A+B.",
        "- `slot_a_short_overlay` must explain and repair Slot A SHORT drawdown before it can be considered runtime-ready.",
        "- `short_only` is diagnostic only; it measures standalone SHORT behavior without long-side slot occupancy.",
        "- References use existing long-only and all-four bidirectional summaries when present; ablation variants are rerun in this pass.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_short_ablation(
    *,
    matrix: str = "all",
    variants: list[str] | None = None,
    windows: list[str] | None = None,
    symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    report_path: Path = REPORT_PATH,
    rerun: bool = False,
    custom_start: str | None = None,
    custom_end: str | None = None,
    custom_name: str = "custom_window",
) -> tuple[Path, Path]:
    symbols = list(symbols or portfolio_ab.DEFAULT_SYMBOLS)
    selected_variants = list(variants or VARIANTS.keys())
    unknown = [variant for variant in selected_variants if variant not in VARIANTS]
    if unknown:
        raise ValueError(f"unknown variant(s): {', '.join(unknown)}")

    summary_path = Path(results_root) / "portfolio_ab_short_ablation_summary.json"
    existing_payload = _read_json(summary_path)
    matrices: dict[str, dict[str, dict[str, Any]]] = dict(existing_payload.get("matrices", {}))
    references = _reference_matrices()
    for variant_name, matrix_payload in references.items():
        matrices[variant_name] = matrix_payload

    selected_matrices = _matrix_selection(
        matrix,
        custom_start=custom_start,
        custom_end=custom_end,
        custom_name=custom_name,
    )
    for matrix_name, selected_windows in _filter_windows(selected_matrices, windows):
        for variant_name in selected_variants:
            variant = VARIANTS[variant_name]
            variant_matrices = dict(matrices.get(variant_name, {}))
            matrix_payload: dict[str, Any] = {}
            for window_name, (start, end) in selected_windows.items():
                output_dir = Path(results_root) / variant_name / matrix_name / window_name
                matrix_payload[window_name] = _run_cell(
                    matrix_name,
                    variant_name,
                    window_name,
                    start,
                    end,
                    output_dir=output_dir,
                    symbols=symbols,
                    strategies=list(variant["strategies"]),
                    risk_per_trade=risk_per_trade,
                    reuse_existing=not rerun,
                )
            variant_matrices[matrix_name] = matrix_payload
            matrices[variant_name] = variant_matrices

    payload = {
        "schema": "strategy_plugin_portfolio_ab_short_ablation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": "2026-05-07",
        "status": "RESEARCH_ONLY_SHORT_ABLATION_SECOND_PASS",
        "symbols": symbols,
        "risk_per_trade": float(risk_per_trade),
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": float(Config.MAX_TOTAL_RISK),
        "variants": VARIANTS,
        "reference_variants": {
            name: {"label": item["label"], "source": str(item["source"])}
            for name, item in REFERENCE_VARIANTS.items()
        },
        "matrices": matrices,
        "matrix_totals": _matrix_totals(matrices),
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = _write_report(payload, summary_path, Path(report_path))
    print(f"[PortfolioABShortAblation] summary={summary_path}")
    print(f"[PortfolioABShortAblation] report={report}")
    return summary_path, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Slot A+B SHORT ablation research")
    parser.add_argument("--matrix", choices=["default", "supplemental", "all", "custom"], default="all")
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--windows", nargs="+", default=None)
    parser.add_argument("--symbols", nargs="+", default=list(portfolio_ab.DEFAULT_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--custom-start", default=None)
    parser.add_argument("--custom-end", default=None)
    parser.add_argument("--custom-name", default="custom_window")
    args = parser.parse_args(argv)
    run_short_ablation(
        matrix=args.matrix,
        variants=list(args.variants),
        windows=args.windows,
        symbols=list(args.symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=Path(args.results_root),
        report_path=Path(args.report_path),
        rerun=bool(args.rerun),
        custom_start=args.custom_start,
        custom_end=args.custom_end,
        custom_name=args.custom_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
