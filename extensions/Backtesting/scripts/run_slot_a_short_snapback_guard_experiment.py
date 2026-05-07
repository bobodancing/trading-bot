"""Run a focused Slot A SHORT snapback-guard repair experiment."""

from __future__ import annotations

import argparse
import csv
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


SLOT_A_LONG = bidir.SLOT_A_LONG
SLOT_A_SHORT = bidir.SLOT_A_SHORT
SLOT_A_SHORT_SNAPBACK_GUARD = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "snapback_guard"
)
SLOT_A_SHORT_FOLLOWTHROUGH_GUARD = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "snapback_followthrough_guard"
)
SLOT_B_LONG = bidir.SLOT_B_LONG

WINDOWS = {
    "classic_rollercoaster_2021_2022": ("2021-01-01", "2022-12-31"),
    "stress_2022_01": ("2022-01-01", "2022-01-31"),
    "stress_2022_02": ("2022-02-01", "2022-02-28"),
    "stress_2022_09": ("2022-09-01", "2022-09-30"),
    "bull_recovery_2026": ("2026-01-01", "2026-02-28"),
}

DEFAULT_RESULTS_ROOT = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "slot_a_short_snapback_guard"
)
REPORT_PATH = REPO_ROOT / "reports" / "slot_a_short_snapback_guard_experiment.md"
SUMMARY_PATH = DEFAULT_RESULTS_ROOT / "slot_a_short_snapback_guard_summary.json"

BASELINE_SOURCE_ROOT = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "slot_a_short_overlay"
    / "supplemental"
)

VARIANTS = {
    "slot_a_short_overlay_baseline": {
        "label": "A+B plus Slot A SHORT baseline",
        "strategies": [SLOT_A_LONG, SLOT_A_SHORT, SLOT_B_LONG],
        "slot_a_short_id": SLOT_A_SHORT,
        "baseline_source": BASELINE_SOURCE_ROOT,
    },
    "slot_a_short_snapback_guard_overlay": {
        "label": "A+B plus Slot A SHORT snapback guard",
        "strategies": [SLOT_A_LONG, SLOT_A_SHORT_SNAPBACK_GUARD, SLOT_B_LONG],
        "slot_a_short_id": SLOT_A_SHORT_SNAPBACK_GUARD,
        "baseline_source": None,
    },
    "slot_a_short_followthrough_guard_overlay": {
        "label": "A+B plus Slot A SHORT snapback follow-through guard",
        "strategies": [SLOT_A_LONG, SLOT_A_SHORT_FOLLOWTHROUGH_GUARD, SLOT_B_LONG],
        "slot_a_short_id": SLOT_A_SHORT_FOLLOWTHROUGH_GUARD,
        "baseline_source": None,
    },
}


def _read_json(path: Path) -> dict[str, Any]:
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


def _net_pnl(cell_dir: Path, summary: dict[str, Any]) -> float:
    if "net_pnl" in summary:
        return _safe_float(summary.get("net_pnl"))
    return sum(_safe_float(row.get("pnl_usdt")) for row in _read_csv(cell_dir / "trades.csv"))


def _trade_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    pnls = [_safe_float(row.get("pnl_usdt")) for row in rows]
    wins = [value for value in pnls if value > 0.0]
    losses = [value for value in pnls if value < 0.0]
    trades = len(rows)
    sl_hits = [row for row in rows if row.get("exit_reason") == "sl_hit"]
    zero_hour_sl_hits = [
        row
        for row in sl_hits
        if _safe_float(row.get("holding_hours")) <= 0.0
    ]
    return {
        "trades": trades,
        "net_pnl": round(sum(pnls), 4),
        "win_rate": round(len(wins) / trades, 4) if trades else 0.0,
        "profit_factor": round(sum(wins) / abs(sum(losses)), 4)
        if losses
        else None,
        "avg_realized_r": round(
            sum(_safe_float(row.get("realized_r")) for row in rows) / trades,
            4,
        )
        if trades
        else 0.0,
        "avg_mfe_pct": round(
            sum(_safe_float(row.get("mfe_pct")) for row in rows) / trades,
            4,
        )
        if trades
        else 0.0,
        "avg_mae_pct": round(
            sum(_safe_float(row.get("mae_pct")) for row in rows) / trades,
            4,
        )
        if trades
        else 0.0,
        "sl_hit_trades": len(sl_hits),
        "zero_hour_sl_hit_trades": len(zero_hour_sl_hits),
        "giveback_exit_trades": sum(
            1 for row in rows if row.get("exit_reason") == "GIVEBACK_EXIT"
        ),
    }


def _summary_row(cell_dir: Path, strategies: list[str]) -> dict[str, Any]:
    summary = _read_json(cell_dir / "summary.json")
    trades = _read_csv(cell_dir / "trades.csv")
    return {
        "portfolio": {
            "trades": _safe_int(summary.get("total_trades")),
            "net_pnl": round(_net_pnl(cell_dir, summary), 4),
            "max_dd_pct": round(_safe_float(summary.get("max_drawdown_pct")), 4),
            "run_errors": _safe_int(summary.get("backtest_run_error_count")),
        },
        "per_strategy": {
            strategy_id: _trade_metrics(
                [row for row in trades if row.get("strategy_id") == strategy_id]
            )
            for strategy_id in strategies
        },
        "per_side": {
            side: _trade_metrics(
                [
                    row
                    for row in trades
                    if str(row.get("side") or "").upper() == side
                ]
            )
            for side in ("LONG", "SHORT")
        },
        "artifacts": {
            "summary": str(cell_dir / "summary.json"),
            "trades": str(cell_dir / "trades.csv"),
        },
    }


def _run_cell(
    variant_name: str,
    window_name: str,
    start: str,
    end: str,
    *,
    variant: dict[str, Any],
    output_dir: Path,
    symbols: list[str],
    risk_per_trade: float,
    reuse_existing: bool,
) -> dict[str, Any]:
    baseline_root = variant.get("baseline_source")
    if baseline_root:
        baseline_dir = Path(baseline_root) / window_name
        if (baseline_dir / "summary.json").exists():
            print(
                "[SlotAShortSnapbackGuard] "
                f"reuse baseline {variant_name}/{window_name}: {baseline_dir}"
            )
            cell = _summary_row(baseline_dir, list(variant["strategies"]))
            cell["window"] = {"start": start, "end": end}
            return cell

    if reuse_existing and (output_dir / "summary.json").exists():
        print(
            "[SlotAShortSnapbackGuard] "
            f"reuse {variant_name}/{window_name}: {output_dir}"
        )
        cell = _summary_row(output_dir, list(variant["strategies"]))
        cell["window"] = {"start": start, "end": end}
        return cell

    print(
        "[SlotAShortSnapbackGuard] "
        f"{variant_name}/{window_name}: {start}->{end} "
        f"strategies={','.join(variant['strategies'])}"
    )
    cfg = _build_config(
        start,
        end,
        symbols=symbols,
        strategies=list(variant["strategies"]),
        risk_per_trade=risk_per_trade,
    )
    result = BacktestEngine(cfg).run()
    ReportGenerator().generate(result, output_dir)
    cell = _summary_row(output_dir, list(variant["strategies"]))
    cell["window"] = {"start": start, "end": end}
    return cell


def _fmt_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _variant_rows(payload: dict[str, Any]) -> list[str]:
    rows = []
    for variant_name, variant_payload in payload["matrices"].items():
        slot_a_short_id = payload["variants"][variant_name]["slot_a_short_id"]
        for window_name, cell in variant_payload.items():
            p = cell["portfolio"]
            s = cell["per_strategy"][slot_a_short_id]
            rows.append(
                f"| `{variant_name}` | `{window_name}` | {p['trades']} | "
                f"{p['net_pnl']:.4f} | {p['max_dd_pct']:.4f} | "
                f"{s['trades']} | {s['net_pnl']:.4f} | {s['win_rate']:.4f} | "
                f"{_fmt_optional(s['profit_factor'])} | {s['avg_realized_r']:.4f} | "
                f"{s['avg_mfe_pct']:.4f} | {s['avg_mae_pct']:.4f} | "
                f"{s['sl_hit_trades']} | {s['zero_hour_sl_hit_trades']} | "
                f"{p['run_errors']} |"
            )
    return rows


def _comparison_rows(payload: dict[str, Any]) -> list[str]:
    baseline = payload["matrices"].get("slot_a_short_overlay_baseline", {})
    rows = []
    for variant_name, guard in payload["matrices"].items():
        if variant_name == "slot_a_short_overlay_baseline":
            continue
        for window_name, guard_cell in guard.items():
            base_cell = baseline.get(window_name)
            if not base_cell:
                continue
            base_id = payload["variants"]["slot_a_short_overlay_baseline"]["slot_a_short_id"]
            guard_id = payload["variants"][variant_name]["slot_a_short_id"]
            base_s = base_cell["per_strategy"][base_id]
            guard_s = guard_cell["per_strategy"][guard_id]
            rows.append(
                f"| `{variant_name}` | `{window_name}` | "
                f"{guard_cell['portfolio']['net_pnl'] - base_cell['portfolio']['net_pnl']:.4f} | "
                f"{guard_cell['portfolio']['max_dd_pct'] - base_cell['portfolio']['max_dd_pct']:.4f} | "
                f"{guard_s['trades'] - base_s['trades']} | "
                f"{guard_s['net_pnl'] - base_s['net_pnl']:.4f} | "
                f"{guard_s['zero_hour_sl_hit_trades'] - base_s['zero_hour_sl_hit_trades']} |"
            )
    return rows


def _write_report(payload: dict[str, Any], report_path: Path) -> Path:
    lines = [
        "# Slot A SHORT Snapback Guard Experiment",
        "",
        f"Date: {payload['date']}",
        "Status: `RESEARCH_ONLY_REPAIR_EXPERIMENT_SECOND_PASS`",
        "",
        "## Scope",
        "",
        "- Goal: falsify or validate the late-breakdown / snapback guard direction from Slot A SHORT failure attribution.",
        "- This is not a promotion review and does not change runtime defaults.",
        "- The baseline row reuses existing Slot A SHORT overlay artifacts when present; guard rows run disabled research plugins.",
        "- The full `classic_rollercoaster_2021_2022` guard backtest timed out before writing artifacts, so this first pass uses targeted failure-month diagnostics plus one positive-control window.",
        f"- Summary artifact: `{payload['summary_path']}`",
        "",
        "## Verdict",
        "",
        "Verdict: `V2_EXHAUSTION_GUARD_MATCHES_V1_ON_DIAGNOSTICS_NOT_PROMOTION_READY`.",
        "",
        "V1 materially improves the known failure-month signature but is blunt. The first vote-only V2 was too permissive, so the current V2 requires follow-through votes plus no overextension exhaustion. On the targeted diagnostics it matches V1's defensive result; this validates the exhaustion guard direction but still does not prove that V2 preserves profitable late bearish continuation.",
        "",
        "## Results",
        "",
        "| variant | window | portfolio_trades | portfolio_net_pnl | max_dd_pct | slot_a_short_trades | slot_a_short_net_pnl | slot_a_short_win_rate | slot_a_short_pf | slot_a_short_avg_r | slot_a_short_avg_mfe_pct | slot_a_short_avg_mae_pct | slot_a_short_sl_hits | slot_a_short_zero_h_sl_hits | run_errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_variant_rows(payload),
        "",
        "## Delta Vs Baseline",
        "",
        "| variant | window | portfolio_net_pnl_delta | max_dd_pct_delta | slot_a_short_trade_delta | slot_a_short_net_pnl_delta | zero_h_sl_hit_delta |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        *_comparison_rows(payload),
        "",
        "## Read",
        "",
        "- V1 answers whether late-breakdown blocking can remove the failure signature; these diagnostics say yes.",
        "- V2 now blocks late breakdowns unless follow-through is confirmed and the breakdown is not overextended by close-through, downside move, or entry extension.",
        "- In this diagnostic matrix V2 matches V1, so the repair is defensive but not yet differentiated from the blunt guard.",
        "- The follow-up dry classifier completed and found V2 is not meaningfully differentiated from V1; a full `classic_rollercoaster_2021_2022` run is not recommended while this remains true.",
        "- Any positive result here is repair-direction evidence only; it is not promotion evidence.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_snapback_guard_experiment(
    *,
    windows: list[str] | None = None,
    symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    report_path: Path = REPORT_PATH,
    rerun: bool = False,
) -> tuple[Path, Path]:
    symbols = list(symbols or portfolio_ab.DEFAULT_SYMBOLS)
    selected_windows = dict(WINDOWS)
    if windows:
        unknown = sorted(set(windows) - set(WINDOWS))
        if unknown:
            raise ValueError(f"unknown window(s): {', '.join(unknown)}")
        selected_windows = {name: WINDOWS[name] for name in windows}

    matrices: dict[str, dict[str, Any]] = {}
    for variant_name, variant in VARIANTS.items():
        variant_payload: dict[str, Any] = {}
        for window_name, (start, end) in selected_windows.items():
            output_dir = Path(results_root) / variant_name / window_name
            variant_payload[window_name] = _run_cell(
                variant_name,
                window_name,
                start,
                end,
                variant=variant,
                output_dir=output_dir,
                symbols=symbols,
                risk_per_trade=risk_per_trade,
                reuse_existing=not rerun,
            )
        matrices[variant_name] = variant_payload

    summary_path = Path(results_root) / "slot_a_short_snapback_guard_summary.json"
    payload = {
        "schema": "strategy_plugin_slot_a_short_snapback_guard_experiment.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": "2026-05-07",
        "status": "RESEARCH_ONLY_REPAIR_EXPERIMENT_SECOND_PASS",
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "symbols": symbols,
        "risk_per_trade": float(risk_per_trade),
        "variants": {
            name: {
                "label": item["label"],
                "strategies": item["strategies"],
                "slot_a_short_id": item["slot_a_short_id"],
                "baseline_source": str(item["baseline_source"])
                if item["baseline_source"]
                else None,
            }
            for name, item in VARIANTS.items()
        },
        "matrices": matrices,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report = _write_report(payload, Path(report_path))
    print(f"[SlotAShortSnapbackGuard] summary={summary_path}")
    print(f"[SlotAShortSnapbackGuard] report={report}")
    return summary_path, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Slot A SHORT snapback guard repair experiment"
    )
    parser.add_argument(
        "--windows",
        nargs="+",
        default=[
            "stress_2022_01",
            "stress_2022_02",
            "stress_2022_09",
            "bull_recovery_2026",
        ],
    )
    parser.add_argument("--symbols", nargs="+", default=list(portfolio_ab.DEFAULT_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args(argv)
    run_snapback_guard_experiment(
        windows=args.windows,
        symbols=list(args.symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=Path(args.results_root),
        report_path=Path(args.report_path),
        rerun=bool(args.rerun),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
