from __future__ import annotations

from extensions.Backtesting.scripts.analyze_weekly_profit_trend_companion_precision_attribution import (
    analyze_precision_attribution,
    apply_filter,
    build_filter_specs,
    render_report,
)


SUPERTREND = "supertrend_flip_4h_trending_up_frequency_companion"
AROON = "aroon_break_hh_4h_trending_up_frequency_companion"


def _week(week_start: str, *, entries: int = 0) -> dict:
    return {
        "week_start": week_start,
        "is_partial_review_week": False,
        "entry_trades": entries,
    }


def _candidate(
    week_start: str,
    timestamp: str,
    *,
    mechanism: str = SUPERTREND,
    symbol: str = "BTC/USDT",
    silent: bool = True,
    active: bool = False,
    ema: float = -0.04,
    distance: float = 1.0,
) -> dict:
    base = {
        "week_start": week_start,
        "timestamp": timestamp,
        "symbol": symbol,
        "mechanism": mechanism,
        "entry_price": 100.0,
        "atr_4h": 10.0,
        "ema_spread_1d": ema,
        "baseline_silent_zero_entry_week": silent,
        "baseline_zero_entry_week": silent,
        "baseline_active_entry_week": active,
        "same_symbol_same_candle_promoted_overlap": False,
    }
    if mechanism == SUPERTREND:
        base["supertrend"] = 100.0 - distance * 10.0
    else:
        base["prior_swing_high"] = 100.0 - distance * 10.0
    return base


def _lane_payload() -> dict:
    return {
        "week_evidence": [
            _week("2026-01-05"),
            _week("2026-01-12"),
            _week("2026-01-19"),
            _week("2026-01-26", entries=1),
        ]
    }


def test_precision_attribution_recommends_filter_that_meets_contract() -> None:
    probe_payloads = [
        {
            "candidates": [
                _candidate("2026-01-05", "2026-01-05T00:00:00Z", mechanism=AROON),
                _candidate("2026-01-12", "2026-01-12T00:00:00Z", mechanism=SUPERTREND),
                _candidate("2026-01-19", "2026-01-19T00:00:00Z", mechanism=AROON),
                _candidate(
                    "2026-01-26",
                    "2026-01-26T00:00:00Z",
                    mechanism=AROON,
                    silent=False,
                    active=True,
                ),
            ]
        }
    ]

    summary = analyze_precision_attribution(
        lane_payload=_lane_payload(),
        probe_payloads=probe_payloads,
    )

    assert summary["verdict"] == "PRECISION_FILTER_FOUND_REQUIRES_PLUGIN_BACKTEST"
    recommended = summary["recommended"]
    assert recommended["filter"]["filter_id"] == "btc_recovery_band_trend_breadth"
    assert recommended["metrics"]["silent_or_zero_candidate_ratio"] == 0.75
    assert recommended["metrics"]["silent_zero_entry_week_hit_count"] == 3
    assert recommended["metrics"]["passes_precision_contract"] is True


def test_precision_filter_ignores_partial_weeks_and_uses_candle_features() -> None:
    spec = build_filter_specs()[0]
    rows = [
        _candidate("2025-12-29", "2026-01-02T00:00:00Z", mechanism=AROON),
        _candidate("2026-01-05", "2026-01-05T00:00:00Z", mechanism=AROON),
        _candidate("2026-01-12", "2026-01-12T00:00:00Z", mechanism=SUPERTREND),
        _candidate("2026-01-19", "2026-01-19T00:00:00Z", mechanism=AROON),
    ]
    summary = analyze_precision_attribution(
        lane_payload=_lane_payload(),
        probe_payloads=[{"candidates": rows}],
    )

    selected = apply_filter(summary["recommended"]["selected_candidates"], spec)

    assert all(row["week_start"] != "2025-12-29" for row in selected)
    assert "packet_state" not in summary["recommended"]["filter"]
    assert "dominant_regime" not in summary["recommended"]["filter"]


def test_precision_report_renders_recommended_conditions() -> None:
    summary = analyze_precision_attribution(
        lane_payload=_lane_payload(),
        probe_payloads=[
            {
                "candidates": [
                    _candidate("2026-01-05", "2026-01-05T00:00:00Z", mechanism=AROON),
                    _candidate("2026-01-12", "2026-01-12T00:00:00Z", mechanism=SUPERTREND),
                    _candidate("2026-01-19", "2026-01-19T00:00:00Z", mechanism=AROON),
                ]
            }
        ],
    )

    report = render_report(summary)

    assert "btc_recovery_band_trend_breadth" in report
    assert "-0.08 <= ema_spread_1d <= -0.01" in report
    assert "distance_atr <= 3.0" in report
