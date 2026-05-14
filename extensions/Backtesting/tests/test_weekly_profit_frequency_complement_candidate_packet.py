from __future__ import annotations

import json
from datetime import date, timedelta

from extensions.Backtesting.scripts.analyze_weekly_profit_frequency_complement_candidate_packet import (
    build_candidate_packet_payload,
)
from extensions.Backtesting.scripts.run_portfolio_ab_frequency_complement_candidate import (
    CANDIDATE,
    DEFAULT_WINDOW,
    VARIANT,
)


def _trade_line(day: date, strategy_id: str, pnl: float) -> str:
    return (
        f"BTC/USDT,{strategy_id},{day.isoformat()}T00:00:00+00:00,"
        f"{day.isoformat()}T04:00:00+00:00,{pnl},100.0,101.0,1.0"
    )


def test_candidate_packet_compares_against_phase3_baseline(tmp_path) -> None:
    trades_path = tmp_path / "trades.csv"
    lines = [
        "symbol,strategy_id,entry_time,exit_time,pnl_usdt,entry_price,exit_price,total_size",
    ]
    current = date.fromisoformat("2026-01-05")
    for idx in range(8):
        day = current + timedelta(days=idx * 7)
        lines.append(_trade_line(day, CANDIDATE, 10.0))
    trades_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    source_path = tmp_path / "candidate_summary.json"
    source = {
        "generated_at": "2026-05-13T00:00:00+00:00",
        "matrices": {
            VARIANT: {
                "custom": {
                    DEFAULT_WINDOW: {
                        "window": {"start": "2026-01-05", "end": "2026-03-01"},
                        "artifacts": {"trades": str(trades_path)},
                        "portfolio": {"trades": 8, "net_pnl": 80.0, "max_dd_pct": 0.0},
                    }
                }
            }
        },
    }
    source_path.write_text(json.dumps(source), encoding="utf-8")

    baseline_path = tmp_path / "baseline_packets.json"
    baseline_path.write_text(
        json.dumps(
            {
                "latest_contract_grade_packet": {
                    "week_start": "2026-02-23",
                    "decision": {"state": "reopen_research"},
                    "kpis": {
                        "active_entry_week_ratio_8w": 0.375,
                        "rolling_8w_entry_trade_count": 3,
                        "positive_week_ratio_all_8w_after_fee": 0.25,
                        "rolling_8w_net_after_fee_pnl": 15.0,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    payload = build_candidate_packet_payload(
        source_path=source_path,
        baseline_packet_path=baseline_path,
        fee_rate=0.0,
        review_capital_usdt=10000.0,
    )

    assert payload["schema"] == "strategy_plugin_weekly_profit_frequency_complement_candidate_packets.v1"
    assert payload["weekly_summary"]["entry_trades"] == 8
    assert payload["latest_contract_grade_packet"]["decision"]["state"] == "continue"
    assert payload["baseline_comparison"]["contract_grade_comparable"] is True
    assert payload["baseline_comparison"]["active_entry_week_ratio_8w_delta"] == 0.625
    assert payload["baseline_comparison"]["rolling_8w_entry_trade_count_delta"] == 5
