from __future__ import annotations

from extensions.Backtesting.scripts.analyze_weekly_profit_trend_companion_probe import (
    evaluate_trend_companion_probe,
    render_report,
)


def _week(
    week_start: str,
    *,
    entries: int = 0,
    silent: bool = True,
    regime: str = "TRENDING",
    state: str = "reopen_research",
) -> dict:
    return {
        "week_start": week_start,
        "week_end": "2026-01-11",
        "is_partial_review_week": False,
        "contract_grade": True,
        "packet_state": state,
        "packet_triggers": ["active_entry_week_ratio_8w"],
        "entry_trades": entries,
        "zero_entry_week": entries == 0,
        "silent_week": silent,
        "dominant_regime": regime,
    }


def _candidate(timestamp: str, *, symbol: str = "BTC/USDT") -> dict:
    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "side": "LONG",
        "candidate_family": "trend_dominant_silent_week_companion",
        "mechanism": "supertrend_flip_4h_trending_up_frequency_companion",
    }


def _payloads() -> tuple[dict, dict]:
    lane_payload = {
        "schema": "strategy_plugin_weekly_profit_frequency_complement_lane.v1",
        "week_evidence": [
            _week("2026-01-05"),
            _week("2026-01-12"),
            _week("2026-01-19", regime="RANGING"),
            _week("2026-01-26", entries=1, silent=False, state="continue"),
        ],
    }
    feasibility_payload = {
        "schema": "strategy_plugin_promoted_three_leg_weekly_feasibility.v1",
        "primary_window": {"artifacts": {"trades": "ignored/trades.csv"}},
    }
    return lane_payload, feasibility_payload


def test_trend_companion_probe_passes_only_when_silent_coverage_is_real() -> None:
    lane_payload, feasibility_payload = _payloads()
    summary = evaluate_trend_companion_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        candidates=[
            _candidate("2026-01-06T00:00:00Z"),
            _candidate("2026-01-13T00:00:00Z", symbol="ETH/USDT"),
            _candidate("2026-01-20T00:00:00Z"),
            _candidate("2026-01-27T00:00:00Z", symbol="ETH/USDT"),
        ],
        lane_rows=[],
        trade_rows=[],
        mechanism="aroon_break_hh_4h_trending_up_frequency_companion",
    )

    assert summary["verdict"] == "AROON_PROBE_PASS_IMPLEMENT_PLUGIN"
    assert summary["mechanism"] == "aroon_break_hh_4h_trending_up_frequency_companion"
    assert summary["metrics"]["silent_zero_entry_week_hit_count"] == 3
    assert summary["metrics"]["silent_or_zero_candidate_ratio"] == 0.75
    assert summary["metrics"]["active_week_candidate_ratio"] == 0.25
    assert summary["metrics"]["candidate_count_by_dominant_regime"] == {
        "RANGING": 1,
        "TRENDING": 3,
    }


def test_trend_companion_probe_fails_on_sparse_hits_or_promoted_overlap() -> None:
    lane_payload, feasibility_payload = _payloads()
    summary = evaluate_trend_companion_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        candidates=[
            _candidate("2026-01-06T00:00:00Z"),
            _candidate("2026-01-27T00:00:00Z"),
        ],
        lane_rows=[
            {
                "timestamp": "2026-01-06T00:00:00Z",
                "symbol": "BTC/USDT",
            }
        ],
        trade_rows=[],
    )

    assert summary["verdict"] == "SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW"
    assert summary["gates"]["silent_week_hit_count_gte_3"] is False
    assert summary["gates"]["same_symbol_same_candle_overlap_eq_0"] is False


def test_trend_companion_probe_report_renders_verdict_and_next_action() -> None:
    lane_payload, feasibility_payload = _payloads()
    summary = evaluate_trend_companion_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        candidates=[],
        lane_rows=[],
        trade_rows=[],
    )

    report = render_report(summary)

    assert "Weekly Profit Phase 4A Trend Companion Probe" in report
    assert "SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW" in report
    assert "Diagnostic passes require a contract update" in report


def test_trend_companion_probe_diagnostic_pass_is_not_plugin_greenlight() -> None:
    lane_payload, feasibility_payload = _payloads()
    summary = evaluate_trend_companion_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        candidates=[
            _candidate("2026-01-06T00:00:00Z"),
            _candidate("2026-01-13T00:00:00Z", symbol="ETH/USDT"),
            _candidate("2026-01-20T00:00:00Z"),
            _candidate("2026-01-27T00:00:00Z", symbol="ETH/USDT"),
        ],
        lane_rows=[],
        trade_rows=[],
        mechanism="aroon_break_hh_4h_trending_up_frequency_companion",
        implementation_eligible=False,
    )

    assert summary["verdict"] == "AROON_PROBE_DIAGNOSTIC_PASS_REQUIRES_CONTRACT_UPDATE"
    assert summary["trend_gate_mode"] == "diagnostic_no_1d_ema"
    assert summary["implementation_eligible"] is False
