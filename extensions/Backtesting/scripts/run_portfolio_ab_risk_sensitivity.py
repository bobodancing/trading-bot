"""Run risk-per-trade sensitivity for the Slot A+B portfolio candidate."""

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

from extensions.Backtesting.scripts import run_portfolio_ab_matrix as portfolio_ab


DEFAULT_BASELINE_SUMMARY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab"
    / "slot_a_b"
    / "portfolio_ab_matrix_summary.json"
)
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "portfolio_ab_risk_sensitivity"
DEFAULT_REPORT = REPO_ROOT / "reports" / "portfolio_a_b_risk_sensitivity.md"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "portfolio_ab_risk_sensitivity_summary.json"
DEFAULT_RISKS = (0.014, 0.017, 0.020)


def _risk_label(risk: float) -> str:
    return f"risk_{risk:.3f}".replace(".", "p")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _matrix_totals(payload: dict[str, Any], matrix_name: str) -> dict[str, Any]:
    matrix = payload.get("matrices", {}).get(matrix_name, {})
    return {
        "trades": sum(cell["portfolio"]["trades"] for cell in matrix.values()),
        "net_pnl": round(sum(cell["portfolio"]["net_pnl"] for cell in matrix.values()), 4),
        "max_dd_pct": round(
            max((cell["portfolio"]["max_dd_pct"] for cell in matrix.values()), default=0.0),
            4,
        ),
        "run_errors": sum(cell["portfolio"]["run_errors"] for cell in matrix.values()),
        "max_overlap": max(
            (
                cell["same_symbol_same_candle_overlaps"]["count"]
                for cell in matrix.values()
            ),
            default=0,
        ),
        "entry_stop_violations": sum(
            cell["portfolio"].get("entry_stop_violations", 0) for cell in matrix.values()
        ),
    }


def _reject_totals(payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    totals = {
        portfolio_ab.SLOT_A: {reason: 0 for reason in portfolio_ab.REJECT_REASONS},
        portfolio_ab.SLOT_B: {reason: 0 for reason in portfolio_ab.REJECT_REASONS},
    }
    for strategy_id in totals:
        totals[strategy_id].update({"entries": 0, "rejects": 0, "emitted_intents": 0})
    for matrix in payload.get("matrices", {}).values():
        for cell in matrix.values():
            for strategy_id in (portfolio_ab.SLOT_A, portfolio_ab.SLOT_B):
                row = cell["reject_mix"][strategy_id]
                totals[strategy_id]["entries"] += int(row.get("entries", 0) or 0)
                totals[strategy_id]["rejects"] += int(row.get("rejects", 0) or 0)
                totals[strategy_id]["emitted_intents"] += int(
                    row.get("emitted_intents", 0) or 0
                )
                for reason in portfolio_ab.REJECT_REASONS:
                    totals[strategy_id][reason] += int(row.get(reason, 0) or 0)
    return totals


def _risk_summary(payload: dict[str, Any], summary_path: Path) -> dict[str, Any]:
    gates = payload.get("decision_gates") or portfolio_ab._aggregate_gate_read(
        payload.get("matrices", {})
    )
    default_totals = _matrix_totals(payload, "default")
    supplemental_totals = _matrix_totals(payload, "supplemental")
    reject_totals = _reject_totals(payload)
    risk_per_trade = float(payload["risk_per_trade"])
    total_validation_pnl = round(
        default_totals["net_pnl"] + supplemental_totals["net_pnl"], 4
    )
    max_dd = round(
        max(default_totals["max_dd_pct"], supplemental_totals["max_dd_pct"]), 4
    )
    run_errors = default_totals["run_errors"] + supplemental_totals["run_errors"]
    max_overlap = max(default_totals["max_overlap"], supplemental_totals["max_overlap"])
    entry_stop_violations = (
        default_totals["entry_stop_violations"]
        + supplemental_totals["entry_stop_violations"]
    )
    return {
        "risk_per_trade": risk_per_trade,
        "summary_path": str(summary_path),
        "default": default_totals,
        "supplemental": supplemental_totals,
        "total_validation_pnl": total_validation_pnl,
        "max_dd_pct": max_dd,
        "run_errors": run_errors,
        "max_overlap": max_overlap,
        "entry_stop_violations": entry_stop_violations,
        "decision_gates": gates,
        "reject_totals": reject_totals,
        "central_risk_blocked": sum(
            row["central_risk_blocked"] for row in reject_totals.values()
        ),
        "total_risk_limit": sum(row["total_risk_limit"] for row in reject_totals.values()),
        "router_rates": gates["strategy_router_block_rates"],
        "gate_pass": bool(
            gates["portfolio_dd_gate_pass"]
            and gates["overlap_gate_pass"]
            and gates["router_gate_pass"]
            and run_errors == 0
            and entry_stop_violations == 0
        ),
    }


def _load_or_run_risk(
    risk: float,
    *,
    results_root: Path,
    reuse_existing: bool,
    reuse_baseline: bool,
    baseline_summary: Path,
) -> tuple[dict[str, Any], Path]:
    if reuse_baseline and abs(risk - 0.017) < 1e-9 and baseline_summary.exists():
        payload = _read_json(baseline_summary)
        return payload, baseline_summary

    label = _risk_label(risk)
    risk_results_root = results_root / label
    summary_path = risk_results_root / "slot_a_b" / "portfolio_ab_matrix_summary.json"
    if reuse_existing and summary_path.exists():
        return _read_json(summary_path), summary_path

    report_path = REPO_ROOT / "reports" / f"portfolio_a_b_risk_sensitivity_{label}_matrix.md"
    summary_path, _ = portfolio_ab.run_portfolio_ab_matrix(
        matrix="all",
        risk_per_trade=risk,
        results_root=risk_results_root,
        report_path=report_path,
    )
    return _read_json(summary_path), summary_path


def run_sensitivity(
    *,
    risks: list[float],
    results_root: Path,
    summary_path: Path,
    report_path: Path,
    baseline_summary: Path,
    reuse_existing: bool = True,
    reuse_baseline: bool = True,
) -> dict[str, Any]:
    risk_rows = []
    for risk in risks:
        payload, per_risk_summary_path = _load_or_run_risk(
            risk,
            results_root=results_root,
            reuse_existing=reuse_existing,
            reuse_baseline=reuse_baseline,
            baseline_summary=baseline_summary,
        )
        risk_rows.append(_risk_summary(payload, per_risk_summary_path))

    risk_rows.sort(key=lambda row: row["risk_per_trade"])
    baseline = min(risk_rows, key=lambda row: abs(row["risk_per_trade"] - 0.017))
    for row in risk_rows:
        risk_ratio = row["risk_per_trade"] / baseline["risk_per_trade"]
        pnl_ratio = (
            row["total_validation_pnl"] / baseline["total_validation_pnl"]
            if baseline["total_validation_pnl"]
            else 0.0
        )
        dd_ratio = row["max_dd_pct"] / baseline["max_dd_pct"] if baseline["max_dd_pct"] else 0.0
        row["risk_ratio_vs_017"] = round(risk_ratio, 4)
        row["pnl_ratio_vs_017"] = round(pnl_ratio, 4)
        row["dd_ratio_vs_017"] = round(dd_ratio, 4)
        row["pnl_linearity_error"] = round(pnl_ratio - risk_ratio, 4)
        row["dd_linearity_error"] = round(dd_ratio - risk_ratio, 4)

    payload = {
        "schema": "strategy_plugin_portfolio_ab_risk_sensitivity.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "slot_a": portfolio_ab.SLOT_A,
        "slot_b": portfolio_ab.SLOT_B,
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": risk_rows[0].get("max_total_risk", 0.0642),
        "risks": risk_rows,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(payload, report_path)
    return payload


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def _write_report(payload: dict[str, Any], report_path: Path) -> None:
    risk_rows = payload["risks"]
    all_pass = all(row["gate_pass"] for row in risk_rows)
    high_risk = max(risk_rows, key=lambda row: row["risk_per_trade"])
    recommended = 0.017 if high_risk["gate_pass"] else 0.014
    if all_pass and high_risk["max_dd_pct"] <= 8.0:
        read = (
            "PASS - risk scaling remains within hard gates across the sensitivity pack; "
            "keep 0.017 as the research baseline unless PM explicitly wants higher risk."
        )
    else:
        read = (
            "REVISIT - at least one risk level failed a hard gate; do not advance promotion "
            "without resizing or policy review."
        )

    lines = [
        "# Portfolio A+B Risk Sensitivity",
        "",
        "Date: 2026-04-29",
        "Status: `RISK_SENSITIVITY`",
        "",
        "## Scope",
        "",
        f"- Slot A: `{payload['slot_a']}`",
        f"- Slot B: `{payload['slot_b']}`",
        "- Symbols: `BTC/USDT`, `ETH/USDT`",
        "- `MAX_TOTAL_RISK`: Config default `0.0642`; intentionally not overridden.",
        "- Approved promotion sizing remains `RISK_PER_TRADE=0.017`; this sensitivity report does not change runtime defaults.",
        "",
        "## Verdict",
        "",
        f"- Decision: `{read}`",
        f"- Recommended promotion-review sizing: `{recommended:.3f}`.",
        "- No runtime defaults or catalog promotion flags are changed by this run.",
        "",
        "## Sensitivity Summary",
        "",
        *_table(
            [
                "risk",
                "default_pnl",
                "supp_pnl",
                "total_pack_pnl",
                "max_dd_pct",
                "overlap",
                "central_risk_blocked",
                "Slot A router",
                "Slot B router",
                "gate",
            ],
            [
                [
                    f"{row['risk_per_trade']:.3f}",
                    f"{row['default']['net_pnl']:.4f}",
                    f"{row['supplemental']['net_pnl']:.4f}",
                    f"{row['total_validation_pnl']:.4f}",
                    f"{row['max_dd_pct']:.4f}",
                    row["max_overlap"],
                    row["central_risk_blocked"],
                    f"{row['router_rates'][portfolio_ab.SLOT_A]:.4f}",
                    f"{row['router_rates'][portfolio_ab.SLOT_B]:.4f}",
                    "PASS" if row["gate_pass"] else "FAIL",
                ]
                for row in risk_rows
            ],
        ),
        "",
        "## Linearity Vs 0.017",
        "",
        "*Validation windows overlap; ratios are stability checks, not expected live scaling.*",
        "",
        *_table(
            [
                "risk",
                "risk_ratio",
                "pnl_ratio",
                "pnl_error",
                "dd_ratio",
                "dd_error",
                "run_errors",
            ],
            [
                [
                    f"{row['risk_per_trade']:.3f}",
                    f"{row['risk_ratio_vs_017']:.4f}",
                    f"{row['pnl_ratio_vs_017']:.4f}",
                    f"{row['pnl_linearity_error']:.4f}",
                    f"{row['dd_ratio_vs_017']:.4f}",
                    f"{row['dd_linearity_error']:.4f}",
                    row["run_errors"],
                ]
                for row in risk_rows
            ],
        ),
        "",
        "## Read",
        "",
        "- The main thing to watch is whether `central_risk_blocked` rises at 0.020 due to the unchanged Config default `MAX_TOTAL_RISK=0.0642`.",
        "- A passing 0.020 result does not automatically justify promotion at 0.020; it only says the portfolio is not fragile around the 0.017 baseline.",
        "- Runtime promotion status is documented in `reports/portfolio_ab_post_promotion_control.md`.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Portfolio A+B risk sensitivity")
    parser.add_argument("--risks", nargs="+", type=float, default=list(DEFAULT_RISKS))
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--baseline-summary", default=str(DEFAULT_BASELINE_SUMMARY))
    parser.add_argument("--no-reuse-existing", action="store_true")
    parser.add_argument("--no-reuse-baseline", action="store_true")
    args = parser.parse_args(argv)
    payload = run_sensitivity(
        risks=list(args.risks),
        results_root=Path(args.results_root),
        summary_path=Path(args.summary),
        report_path=Path(args.report),
        baseline_summary=Path(args.baseline_summary),
        reuse_existing=not args.no_reuse_existing,
        reuse_baseline=not args.no_reuse_baseline,
    )
    print(f"[PortfolioABRiskSensitivity] risks={[row['risk_per_trade'] for row in payload['risks']]}")
    print(f"[PortfolioABRiskSensitivity] report={Path(args.report)}")
    print(f"[PortfolioABRiskSensitivity] summary={Path(args.summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
