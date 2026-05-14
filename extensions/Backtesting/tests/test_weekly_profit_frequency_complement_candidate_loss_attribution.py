from __future__ import annotations

import json

from extensions.Backtesting.scripts.analyze_weekly_profit_frequency_complement_candidate_loss_attribution import (
    build_loss_attribution_payload,
)
from extensions.Backtesting.scripts.run_portfolio_ab_frequency_complement_candidate import (
    CANDIDATE,
    DEFAULT_WINDOW,
    VARIANT,
)


def test_loss_attribution_flags_unmatched_precision_trades(tmp_path) -> None:
    trades_path = tmp_path / "trades.csv"
    trades_path.write_text(
        "symbol,strategy_id,entry_time,exit_time,pnl_usdt,realized_r,exit_reason,entry_regime,entry_regime_direction,entry_regime_candle_time\n"
        f"BTC/USDT,{CANDIDATE},2026-01-05T04:00:00+00:00,2026-01-06T04:00:00+00:00,-10.0,-1.0,sl_hit,TRENDING,LONG,2026-01-05T00:00:00\n"
        f"BTC/USDT,{CANDIDATE},2026-01-12T04:00:00+00:00,2026-01-13T04:00:00+00:00,-20.0,-1.0,sl_hit,RANGING,LONG,2026-01-12T00:00:00\n",
        encoding="utf-8",
    )
    rejects_path = tmp_path / "signal_rejects.csv"
    rejects_path.write_text(
        "signal_type,reject_reason\n"
        f"{CANDIDATE},position_slot_occupied\n",
        encoding="utf-8",
    )
    source_path = tmp_path / "candidate_summary.json"
    source_path.write_text(
        json.dumps(
            {
                "matrices": {
                    VARIANT: {
                        "custom": {
                            DEFAULT_WINDOW: {
                                "artifacts": {
                                    "trades": str(trades_path),
                                    "signal_rejects": str(rejects_path),
                                }
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    precision_path = tmp_path / "precision.json"
    precision_path.write_text(
        json.dumps(
            {
                "recommended": {
                    "selected_candidates": [
                        {"timestamp": "2026-01-05T00:00:00Z"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    payload = build_loss_attribution_payload(
        source_path=source_path,
        precision_path=precision_path,
    )

    assert payload["verdict"] == "LOSS_ATTRIBUTION_FAIL_WITH_PARITY_DRIFT_OR_BOUNDARY_TRADES"
    assert payload["summary"]["trade_count"] == 2
    assert payload["summary"]["matched_precision_trade_count"] == 1
    assert payload["summary"]["unmatched_precision_trade_count"] == 1
    assert payload["summary"]["pnl_by_entry_regime"]["RANGING"] == -20.0


def test_loss_attribution_flags_confirmed_candidate_edge(tmp_path) -> None:
    trades_path = tmp_path / "trades.csv"
    trades_path.write_text(
        "symbol,strategy_id,entry_time,exit_time,pnl_usdt,realized_r,exit_reason,entry_regime,entry_regime_direction,entry_regime_candle_time\n"
        f"BTC/USDT,{CANDIDATE},2026-01-05T04:00:00+00:00,2026-01-06T04:00:00+00:00,-10.0,-1.0,sl_hit,TRENDING,LONG,2026-01-05T00:00:00\n",
        encoding="utf-8",
    )
    rejects_path = tmp_path / "signal_rejects.csv"
    rejects_path.write_text("signal_type,reject_reason\n", encoding="utf-8")
    source_path = tmp_path / "candidate_summary.json"
    source_path.write_text(
        json.dumps(
            {
                "matrices": {
                    VARIANT: {
                        "custom": {
                            DEFAULT_WINDOW: {
                                "artifacts": {
                                    "trades": str(trades_path),
                                    "signal_rejects": str(rejects_path),
                                }
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    precision_path = tmp_path / "precision.json"
    precision_path.write_text(
        json.dumps(
            {
                "recommended": {
                    "selected_candidates": [
                        {"timestamp": "2026-01-05T00:00:00Z"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    payload = build_loss_attribution_payload(
        source_path=source_path,
        precision_path=precision_path,
    )

    assert payload["verdict"] == "LOSS_ATTRIBUTION_FAIL_CONFIRMED_CANDIDATE_EDGE"
    assert payload["summary"]["matched_precision_trade_count"] == 1
    assert payload["summary"]["unmatched_precision_trade_count"] == 0
