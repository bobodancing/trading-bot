from __future__ import annotations

from datetime import date, timedelta

from extensions.Backtesting.scripts.build_weekly_profit_control_packet import (
    build_weekly_profit_control_payload,
)
from extensions.Backtesting.weekly_profit_control import (
    STATE_CONTINUE,
    STATE_INVESTIGATE,
    STATE_PAUSE,
    STATE_REOPEN_RESEARCH,
    build_weekly_control_packets,
    classify_execution_integrity,
)


def _week_rows(
    *,
    start: str = "2026-01-05",
    entries: list[int],
    exits: list[int],
    pnls: list[float],
) -> list[dict]:
    current = date.fromisoformat(start)
    rows = []
    for entry_count, exit_count, pnl in zip(entries, exits, pnls):
        rows.append(
            {
                "week_start": current.isoformat(),
                "week_end": (current + timedelta(days=6)).isoformat(),
                "entry_trades": entry_count,
                "exit_trades": exit_count,
                "gross_pnl_usdt": pnl,
                "fees_est_usdt": 0.0,
                "net_after_fee_est_usdt": pnl,
            }
        )
        current += timedelta(days=7)
    return rows


def _packets(rows: list[dict], **kwargs):
    return build_weekly_control_packets(
        rows,
        review_start=rows[0]["week_start"],
        review_end=rows[-1]["week_end"],
        review_capital_usdt=10000.0,
        portfolio_max_drawdown_pct_review_window=kwargs.pop("drawdown", 0.0),
        operational_by_week_start=kwargs.pop("operational", None),
    )


def test_execution_integrity_composite_rule_handles_sparse_and_denominator_cases() -> None:
    assert classify_execution_integrity(
        execution_attempt_count_weekly=0,
        execution_failure_count_weekly=0,
    )["status"] == STATE_CONTINUE

    one_failure = classify_execution_integrity(
        execution_attempt_count_weekly=1,
        execution_failure_count_weekly=1,
    )
    assert one_failure["status"] == STATE_INVESTIGATE
    assert one_failure["execution_failure_rate_weekly"] == 100.0

    sparse_repeated = classify_execution_integrity(
        execution_attempt_count_weekly=5,
        execution_failure_count_weekly=2,
    )
    assert sparse_repeated["status"] == STATE_PAUSE

    denominator_watch = classify_execution_integrity(
        execution_attempt_count_weekly=100,
        execution_failure_count_weekly=2,
    )
    assert denominator_watch["status"] == STATE_INVESTIGATE
    assert denominator_watch["execution_failure_rate_weekly"] == 2.0

    denominator_breach = classify_execution_integrity(
        execution_attempt_count_weekly=50,
        execution_failure_count_weekly=2,
    )
    assert denominator_breach["status"] == STATE_PAUSE
    assert denominator_breach["execution_failure_rate_weekly"] == 4.0


def test_participation_gap_reopens_only_after_rolling_8w_is_ready() -> None:
    rows = _week_rows(
        entries=[1, 1, 1, 0, 0, 0, 0, 0],
        exits=[1, 1, 1, 0, 0, 0, 0, 0],
        pnls=[10.0] * 8,
    )

    packets = _packets(rows)

    assert packets[6]["decision"]["state"] == STATE_CONTINUE
    assert packets[6]["decision"]["contract_grade"] is False
    assert packets[7]["decision"]["state"] == STATE_REOPEN_RESEARCH
    assert packets[7]["decision"]["contract_grade"] is True
    assert "active_entry_week_ratio_8w" in packets[7]["decision"]["reopen_triggers"]
    assert "rolling_8w_entry_trade_count" in packets[7]["decision"]["reopen_triggers"]
    assert "zero_entry_week_streak" in packets[7]["decision"]["reopen_triggers"]


def test_pause_precedence_wins_over_reopen_research_triggers() -> None:
    rows = _week_rows(
        entries=[1, 1, 1, 0, 0, 0, 0, 0],
        exits=[1, 1, 1, 0, 0, 0, 0, 0],
        pnls=[10.0, 10.0, -800.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    )

    latest = _packets(rows)[-1]

    assert latest["decision"]["state"] == STATE_PAUSE
    assert latest["decision"]["reopen_triggers"] == []
    assert "worst_week_after_fee_pnl_pct_equity_8w" in latest["decision"]["pause_triggers"]


def test_negative_8w_pnl_reopens_when_economic_sample_floor_is_met() -> None:
    rows = _week_rows(
        entries=[1, 1, 1, 1, 1, 1, 1, 1],
        exits=[1, 1, 1, 1, 1, 1, 1, 1],
        pnls=[10.0, -11.0, 10.0, -11.0, 10.0, -11.0, 10.0, -11.0],
    )

    latest = _packets(rows)[-1]

    assert latest["kpis"]["meets_economic_sample_floor"] is True
    assert latest["decision"]["state"] == STATE_REOPEN_RESEARCH
    assert latest["decision"]["reopen_triggers"] == ["rolling_8w_net_after_fee_pnl"]


def test_positive_all_week_ratio_reopens_when_participation_is_adequate() -> None:
    rows = _week_rows(
        entries=[1, 1, 1, 1, 1, 1, 1, 1],
        exits=[1, 1, 1, 1, 1, 1, 1, 1],
        pnls=[10.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
    )

    latest = _packets(rows)[-1]

    assert latest["decision"]["state"] == STATE_REOPEN_RESEARCH
    assert "positive_week_ratio_all_8w_after_fee" in latest["decision"]["reopen_triggers"]


def test_execution_warning_blocks_reopen_until_operations_are_clean() -> None:
    rows = _week_rows(
        entries=[1, 1, 1, 0, 0, 0, 0, 0],
        exits=[1, 1, 1, 0, 0, 0, 0, 0],
        pnls=[10.0] * 8,
    )
    operational = {
        rows[-1]["week_start"]: {
            "execution_attempt_count_weekly": 1,
            "execution_failure_count_weekly": 1,
        }
    }

    latest = _packets(rows, operational=operational)[-1]

    assert latest["decision"]["state"] == STATE_INVESTIGATE
    assert latest["decision"]["reopen_triggers"] == []
    assert latest["decision"]["investigate_triggers"] == ["execution_integrity_weekly"]


def test_partial_review_week_blocks_contract_grade_reopen_but_not_pause() -> None:
    rows = _week_rows(
        entries=[1, 1, 1, 0, 0, 0, 0, 0],
        exits=[1, 1, 1, 0, 0, 0, 0, 0],
        pnls=[10.0] * 8,
    )

    partial_latest = build_weekly_control_packets(
        rows,
        review_start=rows[0]["week_start"],
        review_end=(date.fromisoformat(rows[-1]["week_end"]) - timedelta(days=2)).isoformat(),
        review_capital_usdt=10000.0,
        portfolio_max_drawdown_pct_review_window=0.0,
    )[-1]

    assert partial_latest["decision"]["state"] == STATE_CONTINUE
    assert partial_latest["decision"]["contract_grade"] is False
    assert "rolling_8w_contains_partial_review_week_observe_only" in partial_latest["decision"]["notes"]

    partial_pause_rows = _week_rows(
        entries=[1, 1, 1, 0, 0, 0, 0, 0],
        exits=[1, 1, 1, 0, 0, 0, 0, 0],
        pnls=[10.0, 10.0, -800.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    )
    partial_pause = build_weekly_control_packets(
        partial_pause_rows,
        review_start=partial_pause_rows[0]["week_start"],
        review_end=(
            date.fromisoformat(partial_pause_rows[-1]["week_end"]) - timedelta(days=2)
        ).isoformat(),
        review_capital_usdt=10000.0,
        portfolio_max_drawdown_pct_review_window=0.0,
    )[-1]

    assert partial_pause["decision"]["state"] == STATE_PAUSE
    assert partial_pause["decision"]["contract_grade"] is True


def test_script_payload_emits_machine_readable_latest_packet(tmp_path) -> None:
    trades_path = tmp_path / "trades.csv"
    lines = [
        "symbol,strategy_id,entry_time,exit_time,pnl_usdt,entry_price,exit_price,total_size",
    ]
    current = date.fromisoformat("2026-01-05")
    for idx in range(9):
        day = current + timedelta(days=idx * 7)
        lines.append(
            "BTC/USDT,donchian_range_fade_4h_range_width_cv_013,"
            f"{day.isoformat()}T00:00:00+00:00,{day.isoformat()}T04:00:00+00:00,"
            "10.0,100.0,101.0,1.0"
        )
    trades_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    source_path = tmp_path / "summary.json"
    source_path.write_text(
        """
{
  "generated_at": "2026-05-12T00:00:00+00:00",
  "matrices": {
    "slot_b_short_overlay": {
      "custom": {
        "2026_01_01_2026_04_30": {
          "window": {"start": "2026-01-05", "end": "2026-03-05"},
          "artifacts": {
            "trades": "__TRADES__",
            "summary": "__SUMMARY__"
          },
          "portfolio": {"trades": 9, "net_pnl": 90.0, "max_dd_pct": 0.0}
        }
      }
    }
  }
}
""".replace("__TRADES__", str(trades_path).replace("\\", "\\\\"))
        .replace("__SUMMARY__", str(tmp_path / "cell_summary.json").replace("\\", "\\\\")),
        encoding="utf-8",
    )

    payload = build_weekly_profit_control_payload(
        source_path=source_path,
        fee_rate=0.0,
        review_capital_usdt=10000.0,
    )

    latest = payload["latest_packet"]
    assert payload["schema"] == "strategy_plugin_weekly_profit_control_packets.v1"
    assert latest["schema"] == "strategy_plugin_weekly_profit_control_packet.v1"
    assert payload["latest_contract_grade_packet"]["week_start"] == "2026-02-23"
    assert latest["kpis"]["rolling_8w_complete"] is True
    assert latest["kpis"]["rolling_8w_has_partial_review_week"] is True
    assert latest["decision"]["state"] == STATE_CONTINUE
    assert latest["decision"]["contract_grade"] is False
