from __future__ import annotations

from extensions.Backtesting.scripts.analyze_weekly_profit_range_break_retest_probe import (
    evaluate_range_break_retest_probe,
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


def _candidate(timestamp: str, *, symbol: str = "BTC/USDT", side: str = "LONG") -> dict:
    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "side": side,
        "candidate_family": "range_break_retest_frequency_complement",
        "mechanism": "donchian30_break_retest_hold_4h_continuation",
        "variant_id": "range_break_retest_conservative_30",
        "entry_timeframe": "4h",
        "entry_price": 100.0,
        "breakout_timestamp": timestamp,
        "retest_lag_bars": 1,
        "width_cv": 0.1,
        "bbw_pctrank": 20.0,
        "adx": 20.0,
        "break_strength_atr": 0.5,
    }


def _payloads() -> tuple[dict, dict, list[dict]]:
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
    presets = [
        {
            "variant_id": "range_break_retest_conservative_30",
            "mechanism": "donchian30_break_retest_hold_4h_continuation",
        },
        {
            "variant_id": "range_break_retest_broad_30",
            "mechanism": "donchian30_break_retest_hold_4h_broad_diagnostic",
        },
    ]
    return lane_payload, feasibility_payload, presets


def test_range_break_retest_probe_selects_passing_variant() -> None:
    lane_payload, feasibility_payload, presets = _payloads()

    payload = evaluate_range_break_retest_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        variant_candidates={
            "range_break_retest_conservative_30": [
                _candidate("2026-01-06T00:00:00Z"),
                _candidate("2026-01-13T00:00:00Z", symbol="ETH/USDT"),
                _candidate("2026-01-20T00:00:00Z", side="SHORT"),
                _candidate("2026-01-27T00:00:00Z", symbol="ETH/USDT"),
            ],
            "range_break_retest_broad_30": [
                _candidate("2026-01-27T00:00:00Z"),
            ],
        },
        presets=presets,
        lane_rows=[],
        trade_rows=[],
    )

    assert payload["verdict"] == "RANGE_BREAK_RETEST_PROBE_PASS_RESEARCH_PLUGIN_CANDIDATE"
    assert payload["selected_variant"] == "range_break_retest_conservative_30"
    assert payload["selected_metrics"]["silent_zero_entry_week_hit_count"] == 3
    assert payload["selected_metrics"]["silent_or_zero_candidate_ratio"] == 0.75
    assert payload["selected_metrics"]["active_week_candidate_ratio"] == 0.25
    assert payload["recommended"]["implement_research_plugin"] is True


def test_range_break_retest_probe_fails_on_overlap_or_sparse_hits() -> None:
    lane_payload, feasibility_payload, presets = _payloads()

    payload = evaluate_range_break_retest_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        variant_candidates={
            "range_break_retest_conservative_30": [
                _candidate("2026-01-06T00:00:00Z"),
                _candidate("2026-01-27T00:00:00Z"),
            ],
            "range_break_retest_broad_30": [],
        },
        presets=presets,
        lane_rows=[{"timestamp": "2026-01-06T00:00:00Z", "symbol": "BTC/USDT"}],
        trade_rows=[],
    )

    assert payload["verdict"] == "RANGE_BREAK_RETEST_PROBE_FAIL_PIVOT_OR_REVIEW"
    assert payload["selected_gates"]["silent_week_hit_count_gte_3"] is False
    assert payload["selected_gates"]["same_symbol_same_candle_overlap_eq_0"] is False


def test_range_break_retest_report_renders_guardrails() -> None:
    lane_payload, feasibility_payload, presets = _payloads()
    payload = evaluate_range_break_retest_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        variant_candidates={"range_break_retest_conservative_30": []},
        presets=presets,
        lane_rows=[],
        trade_rows=[],
    )

    report = render_report(payload)

    assert "Weekly Profit Phase 4D Range-Break Retest Probe" in report
    assert "Runtime defaults" in report
    assert "pre-plugin diagnostic evidence" in report
