from __future__ import annotations

from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion_repair_holdout import (
    _robustness_summary,
    _window_row,
)


def test_robustness_summary_requires_all_windows_to_pass() -> None:
    rows = [
        {
            "window_key": "default/TRENDING_UP",
            "gate_pass": True,
            "candidate_slot_after_fee_pnl_usdt": 10.0,
            "active_entry_week_ratio_8w_delta": 0.125,
            "positive_week_ratio_exit_active_8w_after_fee_delta": 0.0,
            "rolling_8w_net_after_fee_pnl_delta": 5.0,
            "portfolio_max_drawdown_pct_review_window_delta": 0.25,
        },
        {
            "window_key": "default/RANGING",
            "gate_pass": False,
            "candidate_slot_after_fee_pnl_usdt": -1.0,
            "active_entry_week_ratio_8w_delta": 0.0,
            "positive_week_ratio_exit_active_8w_after_fee_delta": -0.1,
            "rolling_8w_net_after_fee_pnl_delta": -2.0,
            "portfolio_max_drawdown_pct_review_window_delta": 0.1,
        },
    ]

    summary = _robustness_summary(rows)

    assert summary["hard_gate_pass_windows"] == 1
    assert summary["negative_candidate_windows"] == ["default/RANGING"]
    assert summary["all_windows_pass"] is False
    assert summary["promotion_read"] == "needs_more_research"


def test_window_row_surfaces_failed_gate_names() -> None:
    row = _window_row(
        window_key="default/MIXED",
        window_spec={
            "matrix": "default",
            "window": "MIXED",
            "start": "2025-02-01",
            "end": "2025-08-31",
        },
        baseline_cell={"portfolio": {"max_dd_pct": 1.0, "run_errors": 0}},
        repair_cell={"portfolio": {"max_dd_pct": 1.5, "run_errors": 0}},
        baseline_payload={
            "weekly_summary": {
                "entry_trades": 1,
                "active_entry_weeks": 1,
                "net_after_fee_est_usdt": 10.0,
            }
        },
        repair_payload={
            "weekly_summary": {
                "entry_trades": 2,
                "active_entry_weeks": 2,
                "net_after_fee_est_usdt": 15.0,
            },
            "baseline_comparison": {
                "active_entry_week_ratio_8w_delta": 0.1,
                "positive_week_ratio_all_8w_after_fee_delta": 0.0,
                "positive_week_ratio_exit_active_8w_after_fee_delta": -0.1,
                "rolling_8w_net_after_fee_pnl_delta": 5.0,
                "portfolio_max_drawdown_pct_review_window_delta": 0.5,
                "baseline_state": "investigate",
                "candidate_state": "investigate",
            },
        },
        gate_read={
            "candidate_slot_trades": 1,
            "candidate_slot_after_fee_pnl_usdt": 5.0,
            "all_hard_gates_pass": False,
            "gates": {
                "positive_exit_active_8w_ratio_not_down": False,
                "run_errors_clean": True,
            },
        },
    )

    assert row["window_key"] == "default/MIXED"
    assert row["failed_gates"] == "positive_exit_active_8w_ratio_not_down"
    assert row["gate_pass"] is False
