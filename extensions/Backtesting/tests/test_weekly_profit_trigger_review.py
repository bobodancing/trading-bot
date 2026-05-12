from __future__ import annotations

from extensions.Backtesting.scripts.analyze_weekly_profit_trigger_review import (
    analyze_trigger_review,
    render_report,
)


def _packet(
    week_start: str,
    *,
    state: str,
    contract_grade: bool = True,
    pause: list[str] | None = None,
    reopen: list[str] | None = None,
    investigate: list[str] | None = None,
) -> dict:
    return {
        "week_start": week_start,
        "decision": {
            "state": state,
            "contract_grade": contract_grade,
            "pause_triggers": pause or [],
            "reopen_triggers": reopen or [],
            "investigate_triggers": investigate or [],
            "notes": [],
        },
        "kpis": {
            "active_entry_week_ratio_8w": 0.5,
            "rolling_8w_entry_trade_count": 6,
            "zero_entry_week_streak": 0,
            "positive_week_ratio_all_8w_after_fee": 0.375,
            "positive_week_ratio_exit_active_8w_after_fee": 0.6,
            "rolling_8w_net_after_fee_pnl": 42.0,
            "worst_week_after_fee_pnl_pct_equity_8w": -1.0,
            "portfolio_max_drawdown_pct_review_window": 2.0,
        },
    }


def test_trigger_review_prefers_frequency_complement_when_participation_dominates() -> None:
    payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packet_count": 3,
        "latest_contract_grade_packet": _packet(
            "2026-03-09",
            state="investigate",
            investigate=["positive_week_ratio_all_8w_after_fee"],
        ),
        "packets": [
            _packet(
                "2026-02-23",
                state="reopen_research",
                reopen=["active_entry_week_ratio_8w", "rolling_8w_entry_trade_count"],
            ),
            _packet(
                "2026-03-02",
                state="reopen_research",
                reopen=["active_entry_week_ratio_8w"],
            ),
            _packet(
                "2026-03-09",
                state="investigate",
                investigate=["positive_week_ratio_all_8w_after_fee"],
            ),
        ],
    }

    review = analyze_trigger_review(payload)

    assert review["verdict"] == "OPEN_BOUNDED_FREQUENCY_COMPLEMENT_DISCUSSION"
    assert review["dominant_gap"] == "participation_gap"
    assert review["participation_trigger_count"] == 3
    assert review["economic_trigger_count"] == 1
    assert review["lane_discussion"][0]["lane"] == "frequency_complement_low_overlap"


def test_trigger_review_continues_monitoring_when_no_material_gap_exists() -> None:
    payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packet_count": 2,
        "latest_contract_grade_packet": _packet("2026-03-02", state="continue"),
        "packets": [
            _packet("2026-02-23", state="continue"),
            _packet("2026-03-02", state="continue"),
        ],
    }

    review = analyze_trigger_review(payload)

    assert review["verdict"] == "NO_MATERIAL_TRIGGER_CONTINUE_MONITORING"
    assert review["dominant_gap"] == "no_material_gap"
    assert review["lane_discussion"][0]["lane"] == "continue_weekly_monitoring"
    assert review["lane_discussion"][0]["stance"] == "no_research_lane"


def test_trigger_review_prefers_economic_quality_when_economic_triggers_dominate() -> None:
    payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packet_count": 3,
        "latest_contract_grade_packet": _packet(
            "2026-03-09",
            state="reopen_research",
            reopen=["rolling_8w_net_after_fee_pnl"],
        ),
        "packets": [
            _packet(
                "2026-02-23",
                state="reopen_research",
                reopen=["rolling_8w_net_after_fee_pnl"],
            ),
            _packet(
                "2026-03-02",
                state="reopen_research",
                reopen=["positive_week_ratio_exit_active_8w_after_fee"],
            ),
            _packet(
                "2026-03-09",
                state="investigate",
                investigate=["active_entry_week_ratio_8w"],
            ),
        ],
    }

    review = analyze_trigger_review(payload)

    assert review["verdict"] == "OPEN_BOUNDED_ECONOMIC_QUALITY_DISCUSSION"
    assert review["dominant_gap"] == "economic_quality_gap"
    assert review["economic_trigger_count"] == 2
    assert review["participation_trigger_count"] == 1
    assert review["lane_discussion"][0]["lane"] == "exit_quality_repair"
    assert review["lane_discussion"][2]["lane"] == "frequency_complement_low_overlap"
    assert review["lane_discussion"][2]["stance"] == "not_first"


def test_trigger_review_resolves_pause_before_research() -> None:
    payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packet_count": 2,
        "latest_contract_grade_packet": _packet(
            "2026-03-02",
            state="pause",
            pause=["portfolio_max_drawdown_pct_review_window"],
        ),
        "packets": [
            _packet(
                "2026-02-23",
                state="reopen_research",
                reopen=["active_entry_week_ratio_8w"],
            ),
            _packet(
                "2026-03-02",
                state="pause",
                pause=["portfolio_max_drawdown_pct_review_window"],
            ),
        ],
    }

    review = analyze_trigger_review(payload)

    assert review["verdict"] == "RESOLVE_PAUSE_BEFORE_RESEARCH"
    assert review["risk_pause_contract_grade_packet_count"] == 1
    assert review["lane_discussion"][0]["lane"] == "operational_risk_resolution"
    assert review["lane_discussion"][0]["stance"] == "required_first"


def test_trigger_review_handles_missing_contract_grade_packets() -> None:
    payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packet_count": 1,
        "packets": [
            _packet(
                "2026-01-05",
                state="continue",
                contract_grade=False,
            )
        ],
    }

    review = analyze_trigger_review(payload)

    assert review["verdict"] == "INSUFFICIENT_CONTRACT_GRADE_PACKETS"
    assert review["dominant_gap"] == "no_material_gap"
    assert review["contract_grade_packet_count"] == 0


def test_trigger_review_report_renders_lane_menu() -> None:
    payload = {
        "schema": "strategy_plugin_weekly_profit_control_packets.v1",
        "packet_count": 1,
        "latest_contract_grade_packet": _packet(
            "2026-02-23",
            state="reopen_research",
            reopen=["active_entry_week_ratio_8w"],
        ),
        "packets": [
            _packet(
                "2026-02-23",
                state="reopen_research",
                reopen=["active_entry_week_ratio_8w"],
            )
        ],
    }
    review = analyze_trigger_review(payload)

    report = render_report(review, packet_path="packet.json")

    assert "Weekly Profit Phase 4 Trigger Review" in report
    assert "`frequency_complement_low_overlap`" in report
    assert "Do not change promoted runtime defaults" in report
