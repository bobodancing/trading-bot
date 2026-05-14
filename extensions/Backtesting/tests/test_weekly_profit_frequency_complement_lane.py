from __future__ import annotations

from extensions.Backtesting.scripts.analyze_weekly_profit_frequency_complement_lane import (
    analyze_frequency_complement_lane,
    render_spec,
)


def _packet(week_start: str, *, partial: bool = False) -> dict:
    return {
        "week_start": week_start,
        "week_end": "2026-01-11",
        "is_partial_review_week": partial,
        "decision": {
            "state": "reopen_research",
            "contract_grade": not partial,
            "pause_triggers": [],
            "reopen_triggers": ["active_entry_week_ratio_8w"],
            "investigate_triggers": [],
            "notes": [],
        },
    }


def _week(week_start: str, *, entries: int = 0) -> dict:
    return {
        "week_start": week_start,
        "week_end": "2026-01-11",
        "entry_trades": entries,
        "exit_trades": 0,
        "gross_pnl_usdt": 0.0,
        "fees_est_usdt": 0.0,
        "net_after_fee_est_usdt": 0.0,
        "slot_net_after_fee_est_usdt": {},
        "symbol_net_after_fee_est_usdt": {},
    }


def _payloads():
    packet_payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packets": [
            _packet("2026-01-05", partial=True),
            _packet("2026-01-12"),
            _packet("2026-01-19"),
            _packet("2026-01-26"),
        ],
    }
    feasibility_payload = {
        "schema": "strategy_plugin_promoted_three_leg_weekly_feasibility.v1",
        "primary_window": {
            "artifacts": {"trades": "ignored/trades.csv"},
            "weeks": [
                _week("2026-01-05", entries=0),
                _week("2026-01-12", entries=0),
                _week("2026-01-19", entries=0),
                _week("2026-01-26", entries=1),
            ],
        },
    }
    regime_rows = [
        {"timestamp": "2026-01-05T00:00:00+00:00", "regime": "TRENDING"},
        {"timestamp": "2026-01-12T00:00:00+00:00", "regime": "TRENDING"},
        {"timestamp": "2026-01-19T00:00:00+00:00", "regime": "RANGING"},
        {"timestamp": "2026-01-26T00:00:00+00:00", "regime": "TRENDING"},
    ]
    lane_rows = [
        {
            "timestamp": "2026-01-19T00:00:00+00:00",
            "candidate_signal_type": "existing_promoted_candidate",
        },
        {
            "timestamp": "2026-01-26T00:00:00+00:00",
            "candidate_signal_type": "existing_promoted_candidate",
        },
    ]
    return packet_payload, feasibility_payload, regime_rows, lane_rows


def test_frequency_lane_targets_only_full_silent_zero_entry_weeks() -> None:
    packet_payload, feasibility_payload, regime_rows, lane_rows = _payloads()

    summary = analyze_frequency_complement_lane(
        packet_payload=packet_payload,
        feasibility_payload=feasibility_payload,
        regime_rows=regime_rows,
        lane_rows=lane_rows,
    )

    assert summary["baseline"]["week_count_full"] == 3
    assert summary["baseline"]["zero_entry_week_count_full"] == 2
    assert summary["baseline"]["silent_zero_entry_week_count_full"] == 1
    silent_weeks = summary["gap_evidence"]["silent_zero_entry_weeks"]
    assert [row["week_start"] for row in silent_weeks] == ["2026-01-12"]
    assert silent_weeks[0]["dominant_regime"] == "TRENDING"


def test_frequency_lane_spec_keeps_guardrails_and_acceptance_gates() -> None:
    packet_payload, feasibility_payload, regime_rows, lane_rows = _payloads()
    summary = analyze_frequency_complement_lane(
        packet_payload=packet_payload,
        feasibility_payload=feasibility_payload,
        regime_rows=regime_rows,
        lane_rows=lane_rows,
    )

    spec = summary["lane_spec"]

    assert summary["verdict"] == "FREQUENCY_COMPLEMENT_LANE_SELECTED"
    assert spec["lane_id"] == "frequency_complement_low_overlap"
    assert spec["selected_discussion_option"] == "trend_dominant_silent_week_companion"
    assert spec["candidate_contract_path"].endswith(
        "weekly_profit_phase4a_trend_dominant_silent_week_companion_spec.md"
    )
    assert any("Do not loosen thresholds" in item for item in spec["hard_exclusions"])
    assert any("Convert at least 3" in item for item in spec["acceptance_gates"])
    assert spec["discussion_options"][0]["option"] == "trend_dominant_silent_week_companion"


def test_frequency_lane_report_renders_selected_decision() -> None:
    packet_payload, feasibility_payload, regime_rows, lane_rows = _payloads()
    summary = analyze_frequency_complement_lane(
        packet_payload=packet_payload,
        feasibility_payload=feasibility_payload,
        regime_rows=regime_rows,
        lane_rows=lane_rows,
    )

    report = render_spec(summary)

    assert "Weekly Profit Phase 4A Frequency Complement Lane Spec" in report
    assert "frequency_complement_low_overlap" in report
    assert "PHASE_4A_LANE_SELECTED" in report
    assert "Decision Record" in report
    assert "trend_dominant_silent_week_companion" in report
