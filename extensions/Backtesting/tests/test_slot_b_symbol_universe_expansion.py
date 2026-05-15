from __future__ import annotations

import pytest

from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion import (
    CANDIDATE_LONG,
    _attribution_rows,
    _gate_read,
)


def test_gate_read_fails_when_exit_active_positive_ratio_declines() -> None:
    weekly_payload = {
        "baseline_comparison": {
            "rolling_8w_net_after_fee_pnl_delta": 10.0,
            "active_entry_week_ratio_8w_delta": 0.25,
            "positive_week_ratio_all_8w_after_fee_delta": 0.125,
            "positive_week_ratio_exit_active_8w_after_fee_delta": -0.01,
            "portfolio_max_drawdown_pct_review_window_delta": 0.25,
        }
    }
    combined_cell = {"portfolio": {"run_errors": 0}}
    candidate_attribution = [
        {
            "strategy_id": "ALL",
            "symbol": "SOL/USDT",
            "trades": 3,
            "after_fee_pnl_usdt": 25.0,
        }
    ]

    gate = _gate_read(
        weekly_payload=weekly_payload,
        combined_cell=combined_cell,
        candidate_attribution=candidate_attribution,
    )

    assert gate["gates"]["positive_exit_active_8w_ratio_not_down"] is False
    assert gate["all_hard_gates_pass"] is False


def test_symbol_attribution_includes_fees_and_baseline_overlap() -> None:
    candidate_trades = [
        {
            "symbol": "SOL/USDT",
            "strategy_id": CANDIDATE_LONG,
            "side": "LONG",
            "entry_time": "2026-01-06T00:00:00+00:00",
            "exit_time": "2026-01-06T04:00:00+00:00",
            "pnl_usdt": "10.0",
            "entry_price": "100.0",
            "exit_price": "110.0",
            "total_size": "1.0",
        }
    ]
    baseline_trades = [
        {
            "entry_time": "2026-01-06T00:00:00+00:00",
        }
    ]

    rows = _attribution_rows(
        candidate_trades,
        scope="standalone",
        symbols=["SOL/USDT"],
        strategies=[CANDIDATE_LONG],
        start="2026-01-05",
        end="2026-01-11",
        fee_rate=0.0004,
        baseline_trades=baseline_trades,
    )
    total = next(row for row in rows if row["strategy_id"] == "ALL")

    assert total["trades"] == 1
    assert total["gross_pnl_usdt"] == pytest.approx(10.0)
    assert total["fees_est_usdt"] == pytest.approx(0.084)
    assert total["after_fee_pnl_usdt"] == pytest.approx(9.916)
    assert total["same_entry_time_overlap_with_baseline"] == 1
    assert total["entry_week_overlap_with_baseline"] == 1
