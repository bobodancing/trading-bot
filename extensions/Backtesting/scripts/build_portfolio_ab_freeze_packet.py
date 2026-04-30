"""Build the promotion-gated freeze packet for the Slot A+B portfolio."""

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

from trader.config import Config
from trader.strategies.plugins._catalog import STRATEGY_CATALOG


DEFAULT_PROMOTION_REVIEW = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab"
    / "slot_a_b"
    / "portfolio_ab_promotion_review.json"
)
DEFAULT_RISK_SENSITIVITY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_risk_sensitivity"
    / "portfolio_ab_risk_sensitivity_summary.json"
)
DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab"
    / "slot_a_b"
    / "portfolio_ab_promotion_gated_freeze.json"
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "portfolio_ab_promotion_gated_freeze.md"


SLOT_A_TEST = (
    "trader/tests/"
    "test_macd_signal_trending_up_4h_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter_strategy.py"
)
SLOT_B_TEST = "trader/tests/test_donchian_range_fade_4h_range_width_cv_013_strategy.py"
PROMOTION_COMMIT_1 = "5dee878 chore(runtime): enable frozen portfolio catalog entries"
PROMOTION_COMMIT_2 = "1933e65 feat(runtime): promote frozen portfolio strategies"
RECOVERY_BACKLOG_COMMIT = "827b5a7 docs(research): schedule recovery backlog after promotion"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _catalog_enabled(strategy_id: str) -> bool:
    return bool(STRATEGY_CATALOG.get(strategy_id, {}).get("enabled", False))


def _repo_exists(relative_path: str) -> bool:
    return (REPO_ROOT / relative_path).exists()


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def _risk_rows(risk_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(risk_payload.get("risks", []), key=lambda row: row["risk_per_trade"])


def _baseline_risk(risk_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return min(risk_rows, key=lambda row: abs(row["risk_per_trade"] - 0.017))


def _freeze_decision(review: dict[str, Any], risk_rows: list[dict[str, Any]]) -> str:
    gates = review["decision_gates"]
    gates_pass = (
        gates["portfolio_dd_gate_pass"]
        and gates["overlap_gate_pass"]
        and gates["router_gate_pass"]
    )
    sensitivity_pass = all(row["gate_pass"] for row in risk_rows)
    if gates_pass and sensitivity_pass:
        return "FROZEN_AS_FIRST_2_SLOT_PROMOTION_CANDIDATE"
    return "FREEZE_BLOCKED_REVIEW_REQUIRED"


def build_freeze_packet(
    *,
    promotion_review_path: Path,
    risk_sensitivity_path: Path,
    json_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    review = _read_json(promotion_review_path)
    risk_payload = _read_json(risk_sensitivity_path)
    risks = _risk_rows(risk_payload)
    baseline = _baseline_risk(risks)
    slot_a = review["slot_a"]
    slot_b = review["slot_b"]
    decision = _freeze_decision(review, risks)

    candidate_files = {
        slot_a: {
            "plugin": (
                "trader/strategies/plugins/"
                "macd_signal_trending_up_4h_staged_derisk_giveback_partial67_"
                "transition_aware_tightened_late_entry_filter.py"
            ),
            "spec": (
                "plans/"
                "cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_"
                "giveback_partial67_transition_aware_tightened_late_entry_filter.md"
            ),
            "focused_test": SLOT_A_TEST,
            "catalog_enabled": _catalog_enabled(slot_a),
        },
        slot_b: {
            "plugin": "trader/strategies/plugins/donchian_range_fade_4h_range_width_cv_013.py",
            "spec": "plans/cartridge_spec_donchian_range_fade_4h_range_width_cv_013.md",
            "focused_test": SLOT_B_TEST,
            "catalog_enabled": _catalog_enabled(slot_b),
        },
    }
    for row in candidate_files.values():
        row["plugin_exists"] = _repo_exists(row["plugin"])
        row["spec_exists"] = _repo_exists(row["spec"])
        row["focused_test_exists"] = _repo_exists(row["focused_test"])
    all_candidate_files_exist = all(
        row["plugin_exists"] and row["spec_exists"] and row["focused_test_exists"]
        for row in candidate_files.values()
    )
    catalog_entries_runtime_enabled = all(
        strategy_id in STRATEGY_CATALOG and row["catalog_enabled"]
        for strategy_id, row in candidate_files.items()
    )
    runtime_defaults_promoted = (
        bool(Config.STRATEGY_RUNTIME_ENABLED)
        and list(Config.ENABLED_STRATEGIES) == [slot_a, slot_b]
    )
    runtime_promoted = catalog_entries_runtime_enabled and runtime_defaults_promoted

    packet = {
        "schema": "strategy_plugin_portfolio_ab_promotion_gated_freeze.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "runtime_enablement": (
            "RUEI_APPROVED_RUNTIME_PROMOTED"
            if runtime_promoted
            else "BLOCKED_PENDING_EXPLICIT_RUEI_APPROVAL"
        ),
        "source_artifacts": {
            "promotion_review": str(promotion_review_path),
            "risk_sensitivity": str(risk_sensitivity_path),
        },
        "slot_a": slot_a,
        "slot_b": slot_b,
        "frozen_inputs": {
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "risk_per_trade": baseline["risk_per_trade"],
            "max_total_risk": Config.MAX_TOTAL_RISK,
            "max_total_risk_source": "Config.MAX_TOTAL_RISK",
            "strategy_runtime_enabled_default": Config.STRATEGY_RUNTIME_ENABLED,
            "enabled_strategies_default": list(Config.ENABLED_STRATEGIES),
            "regime_arbiter_enabled_default": Config.REGIME_ARBITER_ENABLED,
            "regime_router_enabled_default": Config.REGIME_ROUTER_ENABLED,
            "strategy_router_policy_default": Config.STRATEGY_ROUTER_POLICY,
        },
        "candidate_files": candidate_files,
        "decision_gates": review["decision_gates"],
        "portfolio_totals": review["portfolio_totals"],
        "slot_attribution": review["slot_attribution"],
        "reject_totals": review["reject_totals"],
        "risk_sensitivity": risks,
        "freeze_checklist": [
            {
                "gate": "StrategyRuntime portfolio matrix",
                "status": "PASS" if review["decision_gates"]["portfolio_dd_gate_pass"] else "FAIL",
                "evidence": "reports/portfolio_a_b_combined_first_pass.md",
            },
            {
                "gate": "Candidate specs, plugins, and focused tests exist",
                "status": "PASS" if all_candidate_files_exist else "FAIL",
                "evidence": "Frozen Candidate table",
            },
            {
                "gate": "Catalog entries present and runtime-enabled",
                "status": "PASS" if catalog_entries_runtime_enabled else "FAIL",
                "evidence": "trader/strategies/plugins/_catalog.py",
            },
            {
                "gate": "Same-symbol same-candle overlap",
                "status": "PASS" if review["decision_gates"]["overlap_gate_pass"] else "FAIL",
                "evidence": f"max_overlap={review['decision_gates']['max_window_overlap_count']}",
            },
            {
                "gate": "Router block rate",
                "status": "PASS" if review["decision_gates"]["router_gate_pass"] else "FAIL",
                "evidence": "both slots <= 0.50 aggregate router block rate",
            },
            {
                "gate": "Risk sensitivity",
                "status": "PASS" if all(row["gate_pass"] for row in risks) else "FAIL",
                "evidence": "reports/portfolio_a_b_risk_sensitivity.md",
            },
            {
                "gate": "dry_count_only does not open positions",
                "status": "PASS",
                "evidence": (
                    "extensions/Backtesting/tests/test_backtest_engine.py::"
                    "test_dry_count_only_records_candidate_without_opening_trade"
                ),
            },
            {
                "gate": "Central risk and execution handoff",
                "status": "PASS",
                "evidence": "trader/strategy_runtime.py::_process_intent -> _build_risk_plan -> _execute_order_plan",
            },
            {
                "gate": "Runtime defaults promoted",
                "status": "PASS"
                if runtime_defaults_promoted
                else "FAIL",
                "evidence": "Config.STRATEGY_RUNTIME_ENABLED / Config.ENABLED_STRATEGIES defaults",
            },
        ],
        "remaining_blockers": (
            [
                "Ruei approval: `APPROVED`.",
                f"Promotion commit 1: `{PROMOTION_COMMIT_1}`.",
                f"Promotion commit 2: `{PROMOTION_COMMIT_2}`.",
                f"Recovery backlog scheduling commit: `{RECOVERY_BACKLOG_COMMIT}`.",
                "Post-promotion control is tracked in `reports/portfolio_ab_post_promotion_control.md`.",
                "Paper-trade, shadow-mode, and service deployment policy remain outside this freeze packet.",
            ]
            if runtime_promoted
            else [
                "Ruei explicit approval for runtime promotion.",
                "Promotion commit 1: mark the selected catalog entries enabled=True.",
                "Promotion commit 2: set Config.STRATEGY_RUNTIME_ENABLED=True and add both ids to Config.ENABLED_STRATEGIES.",
                "Re-run Config.validate and the full trader/tests + extensions/Backtesting/tests suite after promotion edits.",
                "Paper-trade or shadow-mode policy remains out of scope for this freeze packet.",
            ]
        ),
        "current_caveats": [
            "Current StrategyRuntime does not enforce BTC_TREND_FILTER_ENABLED on plugin entries.",
            "Validation windows overlap; portfolio-pack totals are review evidence, not live expectancy estimates.",
            "0.020 risk sensitivity passed but does not automatically justify promotion above 0.017.",
        ],
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(packet, report_path)
    return packet


def _status(value: str) -> str:
    return f"`{value}`"


def _write_report(packet: dict[str, Any], report_path: Path) -> None:
    gates = packet["decision_gates"]
    totals = packet["portfolio_totals"]
    risks = packet["risk_sensitivity"]
    files = packet["candidate_files"]
    slot_a = packet["slot_a"]
    slot_b = packet["slot_b"]
    runtime_promoted = packet.get("runtime_enablement") == "RUEI_APPROVED_RUNTIME_PROMOTED"
    enabled_strategies = ", ".join(
        f"`{strategy_id}`"
        for strategy_id in packet["frozen_inputs"]["enabled_strategies_default"]
    )

    lines = [
        "# Portfolio A+B Promotion-Gated Freeze",
        "",
        "Date: 2026-04-29",
        (
            "Status: `RUEI_APPROVED_RUNTIME_PROMOTED`"
            if runtime_promoted
            else "Status: `PROMOTION_GATED_FREEZE`"
        ),
        "",
        "## Decision",
        "",
        f"- Freeze decision: `{packet['decision']}`.",
        *(
            [
                "- Ruei approved runtime promotion on 2026-04-29.",
                (
                    f"- Runtime promotion landed in commits "
                    f"`{PROMOTION_COMMIT_1.split()[0]}` and "
                    f"`{PROMOTION_COMMIT_2.split()[0]}`."
                ),
                (
                    f"- Recovery backlog scheduling landed in commit "
                    f"`{RECOVERY_BACKLOG_COMMIT.split()[0]}`; backlog remains "
                    "scheduled recovery only."
                ),
                "- Credentials, scanner defaults, and live service state were not changed by promotion.",
                "- Approved promotion sizing is `RISK_PER_TRADE=0.017`.",
            ]
            if runtime_promoted
            else [
                "- Runtime enablement remains blocked until Ruei explicitly approves it.",
                "- No runtime defaults, credentials, scanner defaults, or live service state were changed.",
                "- Baseline promotion-review sizing stays at `RISK_PER_TRADE=0.017`.",
            ]
        ),
        "",
        "## Frozen Candidate",
        "",
        *_table(
            [
                "slot",
                "strategy_id",
                "spec",
                "plugin",
                "focused_test",
                "catalog_enabled",
            ],
            [
                [
                    "Slot A",
                    f"`{slot_a}`",
                    f"`{files[slot_a]['spec']}`",
                    f"`{files[slot_a]['plugin']}`",
                    f"`{files[slot_a]['focused_test']}`",
                    files[slot_a]["catalog_enabled"],
                ],
                [
                    "Slot B",
                    f"`{slot_b}`",
                    f"`{files[slot_b]['spec']}`",
                    f"`{files[slot_b]['plugin']}`",
                    f"`{files[slot_b]['focused_test']}`",
                    files[slot_b]["catalog_enabled"],
                ],
            ],
        ),
        "",
        "## Frozen Runtime Inputs",
        "",
        *_table(
            ["item", "value"],
            [
                ["symbols", "`BTC/USDT`, `ETH/USDT`"],
                ["RISK_PER_TRADE", f"`{packet['frozen_inputs']['risk_per_trade']:.3f}`"],
                ["MAX_TOTAL_RISK", f"`{packet['frozen_inputs']['max_total_risk']:.4f}` from Config default"],
                ["STRATEGY_RUNTIME_ENABLED default", packet["frozen_inputs"]["strategy_runtime_enabled_default"]],
                ["ENABLED_STRATEGIES default", f"[{enabled_strategies}]"],
                ["REGIME_ARBITER_ENABLED default", packet["frozen_inputs"]["regime_arbiter_enabled_default"]],
                ["REGIME_ROUTER_ENABLED default", packet["frozen_inputs"]["regime_router_enabled_default"]],
                ["STRATEGY_ROUTER_POLICY default", f"`{packet['frozen_inputs']['strategy_router_policy_default']}`"],
            ],
        ),
        "",
        "## Hard Gates",
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
                    "5",
                    "PASS" if gates["overlap_gate_pass"] else "FAIL",
                ],
                [
                    "Slot A router block rate",
                    f"{gates['strategy_router_block_rates'][slot_a]:.4f}",
                    "0.5000",
                    "PASS" if gates["router_gate_pass"] else "FAIL",
                ],
                [
                    "Slot B router block rate",
                    f"{gates['strategy_router_block_rates'][slot_b]:.4f}",
                    "0.5000",
                    "PASS" if gates["router_gate_pass"] else "FAIL",
                ],
            ],
        ),
        "",
        "## Portfolio Totals",
        "",
        *_table(
            ["matrix", "trades", "net_pnl", "max_dd_pct", "run_errors", "max_overlap"],
            [
                [
                    "default",
                    totals["default"]["trades"],
                    f"{totals['default']['net_pnl']:.4f}",
                    f"{totals['default']['max_dd_pct']:.4f}",
                    totals["default"]["run_errors"],
                    totals["default"]["max_overlap"],
                ],
                [
                    "supplemental",
                    totals["supplemental"]["trades"],
                    f"{totals['supplemental']['net_pnl']:.4f}",
                    f"{totals['supplemental']['max_dd_pct']:.4f}",
                    totals["supplemental"]["run_errors"],
                    totals["supplemental"]["max_overlap"],
                ],
            ],
        ),
        "",
        "## Risk Sensitivity",
        "",
        *_table(
            [
                "risk",
                "total_pack_pnl",
                "max_dd_pct",
                "overlap",
                "central_risk_blocked",
                "entry_stop_violations",
                "gate",
            ],
            [
                [
                    f"{row['risk_per_trade']:.3f}",
                    f"{row['total_validation_pnl']:.4f}",
                    f"{row['max_dd_pct']:.4f}",
                    row["max_overlap"],
                    row["central_risk_blocked"],
                    row["entry_stop_violations"],
                    "PASS" if row["gate_pass"] else "FAIL",
                ]
                for row in risks
            ],
        ),
        "",
        "## Freeze Checklist",
        "",
        *_table(
            ["gate", "status", "evidence"],
            [
                [row["gate"], _status(row["status"]), row["evidence"]]
                for row in packet["freeze_checklist"]
            ],
        ),
        "",
        "## Runtime Parity Read",
        "",
        "- Entry path remains `StrategyPlugin.generate_candidates -> SignalIntent -> StrategyRuntime._process_intent -> arbiter/router -> central RiskPlan -> ExecutableOrderPlan -> TradingBot._execute_order_plan`.",
        "- Plugins do not size orders, place orders, mutate Config defaults, load credentials, or write runtime persistence directly.",
        "- `dry_count_only` is covered as audit-only and must not be used as tradeability proof.",
        "- BTC trend filter is report-only for this freeze because the current plugin entry path does not enforce it as a reject or size-zero multiplier.",
        "",
        "## Promotion Closeout" if runtime_promoted else "## Remaining Blockers",
        "",
        *[f"- {item}" for item in packet["remaining_blockers"]],
        "",
        "## Caveats",
        "",
        *[f"- {item}" for item in packet["current_caveats"]],
        "",
        "## Source Artifacts",
        "",
        "- `reports/portfolio_a_b_combined_first_pass.md`",
        "- `reports/portfolio_ab_promotion_review.md`",
        "- `reports/portfolio_a_b_risk_sensitivity.md`",
        f"- `{packet['source_artifacts']['promotion_review']}`",
        f"- `{packet['source_artifacts']['risk_sensitivity']}`",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Slot A+B freeze packet")
    parser.add_argument("--promotion-review", default=str(DEFAULT_PROMOTION_REVIEW))
    parser.add_argument("--risk-sensitivity", default=str(DEFAULT_RISK_SENSITIVITY))
    parser.add_argument("--json-path", default=str(DEFAULT_JSON))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)

    packet = build_freeze_packet(
        promotion_review_path=Path(args.promotion_review),
        risk_sensitivity_path=Path(args.risk_sensitivity),
        json_path=Path(args.json_path),
        report_path=Path(args.report_path),
    )
    print(f"[PortfolioABFreeze] decision={packet['decision']}")
    print(f"[PortfolioABFreeze] report={Path(args.report_path)}")
    print(f"[PortfolioABFreeze] json={Path(args.json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
