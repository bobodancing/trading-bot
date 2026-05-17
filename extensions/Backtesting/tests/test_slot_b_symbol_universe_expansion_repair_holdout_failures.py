from __future__ import annotations

from extensions.Backtesting.scripts.analyze_slot_b_symbol_universe_expansion_repair_holdout_failures import (
    _drawdown_proxy,
    _symbol_side_rows,
    _window_verdict,
)


LONG_ID = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion_repair"
SHORT_ID = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion_repair"


def _trade(
    *,
    symbol: str,
    strategy_id: str,
    pnl: float,
    entry: str,
    exit_: str,
    total_size: float = 1.0,
    entry_price: float = 100.0,
    exit_price: float = 100.0,
) -> dict[str, str]:
    return {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "pnl_usdt": str(pnl),
        "entry_time": entry,
        "exit_time": exit_,
        "total_size": str(total_size),
        "entry_price": str(entry_price),
        "exit_price": str(exit_price),
    }


def test_symbol_side_rows_marks_negative_side_after_fees() -> None:
    rows = [
        _trade(
            symbol="SOL/USDT",
            strategy_id=LONG_ID,
            pnl=10.0,
            entry="2025-01-01T00:00:00+00:00",
            exit_="2025-01-01T04:00:00+00:00",
        ),
        _trade(
            symbol="SOL/USDT",
            strategy_id=SHORT_ID,
            pnl=-5.0,
            entry="2025-01-02T00:00:00+00:00",
            exit_="2025-01-02T04:00:00+00:00",
        ),
    ]

    output = _symbol_side_rows(
        window_key="default/MIXED",
        candidate_trades=rows,
        candidate_ids={LONG_ID, SHORT_ID},
        fee_rate=0.0,
    )
    short = next(row for row in output if row["symbol"] == "SOL/USDT" and row["side"] == "SHORT")
    total = next(row for row in output if row["symbol"] == "ALL" and row["side"] == "ALL")

    assert short["after_fee_pnl_usdt"] == -5.0
    assert short["losing_symbol_side"] is True
    assert total["trades"] == 2
    assert total["after_fee_pnl_usdt"] == 5.0


def test_drawdown_proxy_attributes_worst_segment_to_candidate() -> None:
    rows = [
        _trade(
            symbol="BTC/USDT",
            strategy_id="promoted",
            pnl=100.0,
            entry="2025-01-01T00:00:00+00:00",
            exit_="2025-01-01T04:00:00+00:00",
        ),
        _trade(
            symbol="LINK/USDT",
            strategy_id=LONG_ID,
            pnl=-200.0,
            entry="2025-01-02T00:00:00+00:00",
            exit_="2025-01-02T04:00:00+00:00",
        ),
        _trade(
            symbol="ETH/USDT",
            strategy_id="promoted",
            pnl=-50.0,
            entry="2025-01-03T00:00:00+00:00",
            exit_="2025-01-03T04:00:00+00:00",
        ),
    ]

    output = _drawdown_proxy(
        window_key="default/MIXED",
        repair_trades=rows,
        candidate_ids={LONG_ID, SHORT_ID},
        fee_rate=0.0,
        review_capital_usdt=10000.0,
    )

    assert output["segment_candidate_trades"] == 1
    assert output["segment_candidate_net_after_fee_usdt"] == -200.0
    assert output["worst_candidate_symbol"] == "LINK/USDT"
    assert output["worst_candidate_side"] == "LONG"


def test_window_verdict_prioritizes_negative_expectancy() -> None:
    verdict = _window_verdict(
        window_row={
            "window_key": "supplemental/range_low_vol",
            "failed_gates": "candidate_slot_after_fee_non_negative,max_dd_not_materially_larger",
        },
        symbol_side_rows=[
            {
                "symbol": "ALL",
                "side": "ALL",
                "after_fee_pnl_usdt": -10.0,
                "trades": 3,
            },
            {
                "symbol": "SOL/USDT",
                "side": "LONG",
                "losing_symbol_side": True,
            },
        ],
        weekly_rows=[
            {
                "week_start": "2025-09-01T00:00:00+00:00",
                "candidate_week_negative": True,
                "candidate_turns_week_negative": True,
            }
        ],
        drawdown_row={
            "max_realized_trade_dd_pct": 2.0,
            "segment_candidate_net_after_fee_usdt": -10.0,
            "worst_candidate_symbol": "SOL/USDT",
            "worst_candidate_side": "LONG",
        },
    )

    assert verdict["verdict"] == "PARK_WINDOW_NEGATIVE_EXPECTANCY"
    assert verdict["losing_symbol_sides"] == ["SOL/USDT:LONG"]
