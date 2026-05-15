from __future__ import annotations

from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion import (
    CANDIDATE_LONG,
    CANDIDATE_SHORT,
    SLOT_A_LONG,
)
from extensions.Backtesting.scripts.run_slot_b_symbol_universe_expansion_repair import (
    _filter_trade_rows,
    _rank_repair_variants,
    _repair_admission_variants,
)


def test_repair_admission_variant_drops_link_short_and_ada_long() -> None:
    variant = next(
        row
        for row in _repair_admission_variants(["ADA/USDT", "LINK/USDT", "SOL/USDT"])
        if row["variant"] == "drop_link_short_ada_long"
    )

    assert CANDIDATE_LONG not in variant["admission"]["ADA/USDT"]
    assert CANDIDATE_SHORT in variant["admission"]["ADA/USDT"]
    assert CANDIDATE_LONG in variant["admission"]["LINK/USDT"]
    assert CANDIDATE_SHORT not in variant["admission"]["LINK/USDT"]
    assert variant["admission"]["SOL/USDT"] == {CANDIDATE_LONG, CANDIDATE_SHORT}


def test_filter_trade_rows_keeps_promoted_and_admitted_candidates_only() -> None:
    rows = [
        {"symbol": "BTC/USDT", "strategy_id": SLOT_A_LONG},
        {"symbol": "ADA/USDT", "strategy_id": CANDIDATE_LONG},
        {"symbol": "ADA/USDT", "strategy_id": CANDIDATE_SHORT},
        {"symbol": "LINK/USDT", "strategy_id": CANDIDATE_LONG},
        {"symbol": "LINK/USDT", "strategy_id": CANDIDATE_SHORT},
    ]
    admission = {
        "ADA/USDT": {CANDIDATE_SHORT},
        "LINK/USDT": {CANDIDATE_LONG},
    }

    filtered = _filter_trade_rows(
        rows,
        admission,
        promoted_strategies={SLOT_A_LONG},
        candidate_strategies={CANDIDATE_LONG, CANDIDATE_SHORT},
    )

    assert filtered == [
        {"symbol": "BTC/USDT", "strategy_id": SLOT_A_LONG},
        {"symbol": "ADA/USDT", "strategy_id": CANDIDATE_SHORT},
        {"symbol": "LINK/USDT", "strategy_id": CANDIDATE_LONG},
    ]


def test_rank_repair_variants_prefers_expectancy_after_hard_gate_quality() -> None:
    def row(name: str, after_fee: float, rolling_delta: float) -> dict:
        return {
            "variant": name,
            "candidate_slot_after_fee_pnl_usdt": after_fee,
            "baseline_comparison": {
                "active_entry_week_ratio_8w_delta": 0.125,
                "positive_week_ratio_exit_active_8w_after_fee_delta": 0.0667,
                "rolling_8w_net_after_fee_pnl_delta": rolling_delta,
            },
            "gate_read": {"all_hard_gates_pass": True},
        }

    ranked = _rank_repair_variants(
        [
            row("higher_rolling_lower_expectancy", 100.0, 500.0),
            row("lower_rolling_higher_expectancy", 200.0, 400.0),
        ]
    )

    assert ranked[0]["variant"] == "lower_rolling_higher_expectancy"
