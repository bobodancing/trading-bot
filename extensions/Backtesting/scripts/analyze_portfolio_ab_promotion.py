"""Build promotion-review attribution for the Slot A+B portfolio candidate."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
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
from trader.config import Config


DEFAULT_SUMMARY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab"
    / "slot_a_b"
    / "portfolio_ab_matrix_summary.json"
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "portfolio_ab_promotion_review.md"
DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab"
    / "slot_a_b"
    / "portfolio_ab_promotion_review.json"
)
PROMOTION_COMMIT_1 = "5dee878 chore(runtime): enable frozen portfolio catalog entries"
PROMOTION_COMMIT_2 = "1933e65 feat(runtime): promote frozen portfolio strategies"
RECOVERY_BACKLOG_COMMIT = "827b5a7 docs(research): schedule recovery backlog after promotion"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _repo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


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


def _flatten_cells(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for matrix_name, matrix in payload.get("matrices", {}).items():
        for window_name, cell in matrix.items():
            rows.append(
                {
                    "matrix": matrix_name,
                    "window": window_name,
                    "cell": cell,
                }
            )
    return rows


def _all_trade_rows(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in cells:
        trade_path = _repo_path(item["cell"]["artifacts"]["trades"])
        for row in _read_csv(trade_path):
            row["_matrix"] = item["matrix"]
            row["_window"] = item["window"]
            row["_pnl_usdt_float"] = _safe_float(row.get("pnl_usdt"))
            row["_realized_r_float"] = _safe_float(row.get("realized_r"))
            rows.append(row)
    return rows


def _aggregate_by(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(str(row.get(k) or "unknown") for k in keys)
        if key not in groups:
            groups[key] = {k: v for k, v in zip(keys, key)}
            groups[key].update(
                {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "net_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "realized_r": 0.0,
                    "mae_pct_sum": 0.0,
                    "mfe_pct_sum": 0.0,
                }
            )
        group = groups[key]
        pnl = _safe_float(row.get("pnl_usdt"))
        group["trades"] += 1
        group["wins"] += 1 if pnl > 0 else 0
        group["losses"] += 1 if pnl < 0 else 0
        group["net_pnl"] += pnl
        group["gross_profit"] += max(pnl, 0.0)
        group["gross_loss"] += min(pnl, 0.0)
        group["realized_r"] += _safe_float(row.get("realized_r"))
        group["mae_pct_sum"] += _safe_float(row.get("mae_pct"))
        group["mfe_pct_sum"] += _safe_float(row.get("mfe_pct"))

    output = []
    for group in groups.values():
        trades = group["trades"]
        gross_loss_abs = abs(group["gross_loss"])
        output.append(
            {
                **{k: group[k] for k in keys},
                "trades": trades,
                "win_rate": round(group["wins"] / trades, 4) if trades else 0.0,
                "net_pnl": round(group["net_pnl"], 4),
                "profit_factor": round(group["gross_profit"] / gross_loss_abs, 4)
                if gross_loss_abs
                else None,
                "avg_realized_r": round(group["realized_r"] / trades, 4)
                if trades
                else 0.0,
                "avg_mae_pct": round(group["mae_pct_sum"] / trades, 4)
                if trades
                else 0.0,
                "avg_mfe_pct": round(group["mfe_pct_sum"] / trades, 4)
                if trades
                else 0.0,
            }
        )
    output.sort(key=lambda item: item["net_pnl"], reverse=True)
    return output


def _reject_totals(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in cells:
        for strategy_id, row in item["cell"].get("reject_mix", {}).items():
            totals[strategy_id]["entries"] += _safe_int(row.get("entries"))
            totals[strategy_id]["rejects"] += _safe_int(row.get("rejects"))
            totals[strategy_id]["emitted_intents"] += _safe_int(row.get("emitted_intents"))
            for reason in portfolio_ab.REJECT_REASONS:
                totals[strategy_id][reason] += _safe_int(row.get(reason))

    output = []
    for strategy_id in (portfolio_ab.SLOT_A, portfolio_ab.SLOT_B):
        row = totals[strategy_id]
        emitted = row["emitted_intents"]
        output.append(
            {
                "strategy_id": strategy_id,
                "slot": "Slot A" if strategy_id == portfolio_ab.SLOT_A else "Slot B",
                "entries": row["entries"],
                "rejects": row["rejects"],
                "emitted_intents": emitted,
                "router_block_rate": round(row["strategy_router_blocked"] / emitted, 4)
                if emitted
                else 0.0,
                **{reason: row[reason] for reason in portfolio_ab.REJECT_REASONS},
            }
        )
    return output


def _portfolio_totals(cells: list[dict[str, Any]]) -> dict[str, Any]:
    by_matrix: dict[str, dict[str, Any]] = {}
    for matrix_name in ("default", "supplemental"):
        selected = [item for item in cells if item["matrix"] == matrix_name]
        by_matrix[matrix_name] = {
            "trades": sum(item["cell"]["portfolio"]["trades"] for item in selected),
            "net_pnl": round(
                sum(item["cell"]["portfolio"]["net_pnl"] for item in selected), 4
            ),
            "max_dd_pct": round(
                max(
                    (item["cell"]["portfolio"]["max_dd_pct"] for item in selected),
                    default=0.0,
                ),
                4,
            ),
            "run_errors": sum(item["cell"]["portfolio"]["run_errors"] for item in selected),
            "max_overlap": max(
                (
                    item["cell"]["same_symbol_same_candle_overlaps"]["count"]
                    for item in selected
                ),
                default=0,
            ),
        }
    return by_matrix


def _window_risk_rows(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in cells:
        portfolio = item["cell"]["portfolio"]
        rows.append(
            {
                "matrix": item["matrix"],
                "window": item["window"],
                "trades": portfolio["trades"],
                "net_pnl": portfolio["net_pnl"],
                "max_dd_pct": portfolio["max_dd_pct"],
                "run_errors": portfolio["run_errors"],
                "same_symbol_same_candle_overlaps": item["cell"][
                    "same_symbol_same_candle_overlaps"
                ]["count"],
            }
        )
    rows.sort(key=lambda item: item["max_dd_pct"], reverse=True)
    return rows


def _format_pf(value: Any) -> str:
    if value is None:
        return "inf"
    return f"{float(value):.4f}"


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def _runtime_promoted() -> bool:
    return (
        bool(Config.STRATEGY_RUNTIME_ENABLED)
        and list(Config.ENABLED_STRATEGIES) == [portfolio_ab.SLOT_A, portfolio_ab.SLOT_B]
    )


def build_review(summary_path: Path, report_path: Path, json_path: Path) -> dict[str, Any]:
    payload = _read_json(summary_path)
    cells = _flatten_cells(payload)
    trades = _all_trade_rows(cells)
    gates = payload.get("decision_gates") or portfolio_ab._aggregate_gate_read(
        payload.get("matrices", {})
    )
    all_gates_pass = (
        gates["portfolio_dd_gate_pass"]
        and gates["overlap_gate_pass"]
        and gates["router_gate_pass"]
    )

    review = {
        "schema": "strategy_plugin_portfolio_ab_promotion_review.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_summary": str(summary_path),
        "slot_a": payload["slot_a"],
        "slot_b": payload["slot_b"],
        "risk_per_trade": payload["risk_per_trade"],
        "max_total_risk": payload["max_total_risk"],
        "decision_gates": gates,
        "portfolio_totals": _portfolio_totals(cells),
        "window_risk_rank": _window_risk_rows(cells),
        "slot_attribution": _aggregate_by(trades, ("strategy_id",)),
        "slot_symbol_attribution": _aggregate_by(trades, ("strategy_id", "symbol")),
        "symbol_attribution": _aggregate_by(trades, ("symbol",)),
        "regime_attribution": _aggregate_by(trades, ("entry_regime",)),
        "reject_totals": _reject_totals(cells),
        "top_losing_trades": [
            {
                "matrix": row["_matrix"],
                "window": row["_window"],
                "symbol": row.get("symbol"),
                "strategy_id": row.get("strategy_id"),
                "side": row.get("side"),
                "entry_time": row.get("entry_time"),
                "exit_time": row.get("exit_time"),
                "pnl_usdt": round(row["_pnl_usdt_float"], 4),
                "realized_r": round(row["_realized_r_float"], 4),
                "mae_pct": _safe_float(row.get("mae_pct")),
                "mfe_pct": _safe_float(row.get("mfe_pct")),
            }
            for row in sorted(trades, key=lambda item: item["_pnl_usdt_float"])[:10]
        ],
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(review, report_path)
    return review


def _write_report(review: dict[str, Any], report_path: Path) -> None:
    gates = review["decision_gates"]
    totals = review["portfolio_totals"]
    worst_windows = review["window_risk_rank"][:5]
    slot_rows = review["slot_attribution"]
    symbol_rows = review["symbol_attribution"]
    reject_rows = review["reject_totals"]
    all_gates_pass = (
        gates["portfolio_dd_gate_pass"]
        and gates["overlap_gate_pass"]
        and gates["router_gate_pass"]
    )
    runtime_promoted = _runtime_promoted()
    if all_gates_pass and runtime_promoted:
        status = "Status: `RUEI_APPROVED_RUNTIME_PROMOTED`"
        verdict_lines = [
            "- Decision: `FIRST_PROMOTION_CANDIDATE_QUALIFIED_AND_RUEI_APPROVED`",
            "- Ruei approved runtime promotion on 2026-04-29.",
            (
                f"- Promotion landed through `{PROMOTION_COMMIT_1.split()[0]}` "
                f"(catalog enablement) and `{PROMOTION_COMMIT_2.split()[0]}` "
                "(Config runtime defaults)."
            ),
            (
                f"- Recovery backlog scheduling landed through "
                f"`{RECOVERY_BACKLOG_COMMIT.split()[0]}`; no backlog alpha "
                "research starts during post-promotion control."
            ),
            "- BTC trend filter enforcement remains report-only for plugin entries in current StrategyRuntime.",
        ]
        read_tail = [
            "- Risk sensitivity completed separately and kept approved sizing at `RISK_PER_TRADE=0.017`.",
            "- Runtime promotion is complete; post-promotion control verifies default parity and smoke wiring in `reports/portfolio_ab_post_promotion_control.md`.",
        ]
    elif all_gates_pass:
        status = "Status: `PROMOTION_CANDIDATE_REVIEW`"
        verdict_lines = [
            "- Decision: `FIRST_PROMOTION_CANDIDATE_QUALIFIED`",
            "- Runtime promotion is still blocked until Ruei explicitly approves.",
            "- No runtime defaults or catalog promotion flags are changed by this review.",
            "- BTC trend filter enforcement remains report-only for plugin entries in current StrategyRuntime.",
        ]
        read_tail = [
            "- Promotion path should continue with risk sensitivity before any runtime enablement.",
        ]
    else:
        status = "Status: `REVISIT_REQUIRED`"
        verdict_lines = [
            "- Decision: `FAIL_REVISIT_BEFORE_PROMOTION_REVIEW`",
            "- Runtime promotion is blocked.",
            "- No runtime defaults or catalog promotion flags are changed by this review.",
            "- BTC trend filter enforcement remains report-only for plugin entries in current StrategyRuntime.",
        ]
        read_tail = [
            "- Promotion path is blocked until failed gates are resolved.",
        ]

    lines = [
        "# Portfolio A+B Promotion Review",
        "",
        "Date: 2026-04-29",
        status,
        "",
        "## Verdict",
        "",
        *verdict_lines,
        "",
        "## Gate Snapshot",
        "",
        *_table(
            ["gate", "value", "threshold", "result"],
            [
                [
                    "portfolio max_dd_pct",
                    f"{gates['max_portfolio_dd_pct']:.4f}",
                    "8.0000",
                    "PASS" if gates["portfolio_dd_gate_pass"] else "FAIL",
                ],
                [
                    "max same-symbol same-candle A+B emits",
                    gates["max_window_overlap_count"],
                    5,
                    "PASS" if gates["overlap_gate_pass"] else "FAIL",
                ],
                [
                    "Slot A aggregate router block rate",
                    f"{gates['strategy_router_block_rates'][portfolio_ab.SLOT_A]:.4f}",
                    "0.5000",
                    "PASS"
                    if gates["strategy_router_block_rates"][portfolio_ab.SLOT_A] <= 0.5
                    else "FAIL",
                ],
                [
                    "Slot B aggregate router block rate",
                    f"{gates['strategy_router_block_rates'][portfolio_ab.SLOT_B]:.4f}",
                    "0.5000",
                    "PASS"
                    if gates["strategy_router_block_rates"][portfolio_ab.SLOT_B] <= 0.5
                    else "FAIL",
                ],
            ],
        ),
        "",
        "## Matrix Totals",
        "",
        *_table(
            ["matrix", "trades", "net_pnl", "max_dd_pct", "run_errors", "max_overlap"],
            [
                [
                    matrix_name,
                    row["trades"],
                    f"{row['net_pnl']:.4f}",
                    f"{row['max_dd_pct']:.4f}",
                    row["run_errors"],
                    row["max_overlap"],
                ]
                for matrix_name, row in totals.items()
            ],
        ),
        "",
        "## Drawdown Concentration",
        "",
        *_table(
            ["matrix", "window", "trades", "net_pnl", "max_dd_pct", "overlap"],
            [
                [
                    row["matrix"],
                    row["window"],
                    row["trades"],
                    f"{row['net_pnl']:.4f}",
                    f"{row['max_dd_pct']:.4f}",
                    row["same_symbol_same_candle_overlaps"],
                ]
                for row in worst_windows
            ],
        ),
        "",
        "## Slot Attribution",
        "",
        "Validation windows overlap; this is attribution across the validation pack, not a live expectancy estimate.",
        "",
        *_table(
            ["slot", "trades", "win_rate", "net_pnl", "profit_factor", "avg_r", "avg_mae_pct"],
            [
                [
                    "Slot A" if row["strategy_id"] == portfolio_ab.SLOT_A else "Slot B",
                    row["trades"],
                    f"{row['win_rate']:.4f}",
                    f"{row['net_pnl']:.4f}",
                    _format_pf(row["profit_factor"]),
                    f"{row['avg_realized_r']:.4f}",
                    f"{row['avg_mae_pct']:.4f}",
                ]
                for row in slot_rows
            ],
        ),
        "",
        "## Symbol Attribution",
        "",
        *_table(
            ["symbol", "trades", "win_rate", "net_pnl", "profit_factor", "avg_r"],
            [
                [
                    row["symbol"],
                    row["trades"],
                    f"{row['win_rate']:.4f}",
                    f"{row['net_pnl']:.4f}",
                    _format_pf(row["profit_factor"]),
                    f"{row['avg_realized_r']:.4f}",
                ]
                for row in symbol_rows
            ],
        ),
        "",
        "## Reject Totals",
        "",
        *_table(
            [
                "slot",
                "entries",
                "rejects",
                "router_block_rate",
                "position_slot_occupied",
                "strategy_router_blocked",
                "cooldown",
                "central_risk_blocked",
            ],
            [
                [
                    row["slot"],
                    row["entries"],
                    row["rejects"],
                    f"{row['router_block_rate']:.4f}",
                    row["position_slot_occupied"],
                    row["strategy_router_blocked"],
                    row["cooldown"],
                    row["central_risk_blocked"],
                ]
                for row in reject_rows
            ],
        ),
        "",
        "## Top Losing Trades",
        "",
        *_table(
            ["matrix", "window", "symbol", "slot", "entry_time", "pnl_usdt", "realized_r", "mae_pct"],
            [
                [
                    row["matrix"],
                    row["window"],
                    row["symbol"],
                    "Slot A" if row["strategy_id"] == portfolio_ab.SLOT_A else "Slot B",
                    row["entry_time"],
                    f"{row['pnl_usdt']:.4f}",
                    f"{row['realized_r']:.4f}",
                    f"{row['mae_pct']:.4f}",
                ]
                for row in review["top_losing_trades"]
            ],
        ),
        "",
        "## Read",
        "",
        "- Main drawdown concentration is in long stress windows, not in same-candle A/B collisions.",
        "- Slot B has visible `central_risk_blocked` only in the 2021-2022 stress pack, which is expected under Config default `MAX_TOTAL_RISK=0.0642` and should remain monitored.",
        *read_tail,
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Portfolio A+B promotion attribution")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    args = parser.parse_args(argv)
    review = build_review(Path(args.summary), Path(args.report), Path(args.json))
    print(f"[PortfolioABReview] decision_gates={review['decision_gates']}")
    print(f"[PortfolioABReview] report={Path(args.report)}")
    print(f"[PortfolioABReview] json={Path(args.json)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
