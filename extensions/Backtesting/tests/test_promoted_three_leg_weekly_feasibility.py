from __future__ import annotations

from extensions.Backtesting.scripts.analyze_promoted_three_leg_weekly_feasibility import (
    _analysis_payload,
    _build_week_rows,
    _decision_profile,
    _fee_estimate,
    _summarize_week_rows,
)


def test_fee_estimate_uses_entry_and_exit_notional() -> None:
    row = {
        "entry_price": "100.0",
        "exit_price": "110.0",
        "total_size": "2.0",
    }

    assert _fee_estimate(row, fee_rate=0.001) == 0.42


def test_weekly_summary_separates_entry_participation_from_exit_outcome() -> None:
    trades = [
        {
            "symbol": "BTC/USDT",
            "strategy_id": "donchian_range_fade_4h_range_width_cv_013",
            "entry_time": "2026-01-06T01:00:00+00:00",
            "exit_time": "2026-01-06T05:00:00+00:00",
            "pnl_usdt": "10.0",
            "entry_price": "100.0",
            "exit_price": "101.0",
            "total_size": "1.0",
        },
        {
            "symbol": "ETH/USDT",
            "strategy_id": "donchian_range_fade_4h_range_width_cv_013_short",
            "entry_time": "2026-01-13T01:00:00+00:00",
            "exit_time": "2026-01-20T05:00:00+00:00",
            "pnl_usdt": "-5.0",
            "entry_price": "50.0",
            "exit_price": "49.0",
            "total_size": "2.0",
        },
    ]

    weeks, overflow = _build_week_rows(
        trades,
        start="2026-01-05",
        end="2026-01-25",
        fee_rate=0.0,
    )
    summary = _summarize_week_rows(weeks)

    assert overflow == {"entry_outside_window": 0, "exit_outside_window": 0}
    assert summary["weeks"] == 3
    assert summary["entry_trades"] == 2
    assert summary["exit_trades"] == 2
    assert summary["active_entry_weeks"] == 2
    assert summary["active_exit_weeks"] == 2
    assert summary["zero_entry_week_count"] == 1
    assert summary["zero_exit_week_count"] == 1
    assert summary["after_fee_positive_week_ratio_all"] == 0.3333
    assert summary["after_fee_positive_week_ratio_exit_active"] == 0.5
    assert summary["net_after_fee_est_usdt"] == 5.0
    assert summary["worst_week_after_fee_pnl_est_usdt"] == -5.0
    assert summary["weekly_entry_trade_count_distribution"] == {"0": 1, "1": 2}
    assert summary["weekly_exit_trade_count_distribution"] == {"0": 1, "1": 2}


def test_decision_profile_is_data_driven() -> None:
    primary = {
        "summary": {
            "active_entry_week_ratio": 0.75,
            "after_fee_positive_week_ratio_all": 0.25,
            "net_after_fee_est_usdt": 20.0,
        }
    }

    decision = _decision_profile(primary)

    assert decision["label"] == "Weekly outcome stability gap dominates."
    assert "positive-week density" in decision["read"]


def test_analysis_payload_preserves_explicit_source_path(tmp_path) -> None:
    trades_path = tmp_path / "trades.csv"
    trades_path.write_text(
        "symbol,strategy_id,entry_time,exit_time,pnl_usdt,entry_price,exit_price,total_size\n"
        "BTC/USDT,donchian_range_fade_4h_range_width_cv_013,"
        "2026-01-06T00:00:00+00:00,2026-01-06T04:00:00+00:00,"
        "10.0,100.0,101.0,1.0\n",
        encoding="utf-8",
    )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text("{}", encoding="utf-8")
    source_path = tmp_path / "custom_source.json"
    source = {
        "matrices": {
            "slot_b_short_overlay": {
                "custom": {
                    "2026_01_01_2026_04_30": {
                        "window": {"start": "2026-01-01", "end": "2026-04-30"},
                        "artifacts": {
                            "trades": str(trades_path),
                            "summary": str(summary_path),
                        },
                        "portfolio": {"trades": 1, "net_pnl": 10.0},
                    }
                }
            }
        }
    }

    payload = _analysis_payload(source, source_path=source_path, fee_rate=0.0)

    assert payload["source_summary"] == str(source_path)
    assert payload["primary_window"]["summary"]["exit_trades"] == 1
    assert payload["decision_screen"]["status"] == "exploratory_only_not_a_phase_2_kpi_contract"
