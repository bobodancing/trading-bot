from __future__ import annotations

import json

from extensions.Backtesting.scripts.analyze_weekly_profit_range_break_retest_repair_filter import (
    build_repair_filter_payload,
)
from extensions.Backtesting.scripts.run_portfolio_ab_range_break_retest_candidate import (
    CANDIDATE,
    DEFAULT_WINDOW,
    VARIANT,
)


def _candidate(
    timestamp: str,
    week_start: str,
    *,
    bbw: float,
    retest_distance: float,
    pnl_bucket: str,
) -> dict:
    return {
        "timestamp": timestamp,
        "symbol": "BTC/USDT" if pnl_bucket in {"win", "large_loss"} else "ETH/USDT",
        "side": "LONG",
        "week_start": week_start,
        "baseline_silent_zero_entry_week": True,
        "baseline_zero_entry_week": True,
        "baseline_active_entry_week": False,
        "break_strength_atr": 0.5,
        "breakout_close_quality": 0.8,
        "retest_distance_atr": retest_distance,
        "retest_lag_bars": 1,
        "width_cv": 0.05,
        "range_width_pct": 0.08,
        "bbw_pctrank": bbw,
        "adx": 18.0,
        "adx_slope_5": 1.0,
        "ema_spread_20_50": 0.01,
    }


def _trade_line(
    timestamp: str,
    pnl: float,
    *,
    symbol: str = "BTC/USDT",
    exit_reason: str = "exit",
) -> str:
    candle_time = timestamp.replace("Z", "")
    return (
        f"{symbol},{CANDIDATE},0.1,100.0,101.0,{pnl},0.1,{exit_reason},"
        f"{candle_time},{candle_time}+00:00,{candle_time}+00:00"
    )


def test_range_break_retest_repair_filter_finds_two_condition_candidate(tmp_path) -> None:
    probe_path = tmp_path / "probe.json"
    probe_path.write_text(
        json.dumps(
            {
                "recommended": {
                    "selected_candidates": [
                        _candidate("2026-01-06T00:00:00Z", "2026-01-05", bbw=2.0, retest_distance=0.1, pnl_bucket="win"),
                        _candidate("2026-01-13T00:00:00Z", "2026-01-12", bbw=38.0, retest_distance=0.2, pnl_bucket="large_loss"),
                        _candidate("2026-01-20T00:00:00Z", "2026-01-19", bbw=18.0, retest_distance=0.3, pnl_bucket="unknown"),
                        _candidate("2026-01-27T00:00:00Z", "2026-01-26", bbw=20.0, retest_distance=-0.1, pnl_bucket="small_loss"),
                        _candidate("2026-02-03T00:00:00Z", "2026-02-02", bbw=30.0, retest_distance=0.1, pnl_bucket="win"),
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    trades_path = tmp_path / "trades.csv"
    trades_path.write_text(
        "\n".join(
            [
                "symbol,strategy_id,total_size,entry_price,exit_price,pnl_usdt,realized_r,exit_reason,entry_regime_candle_time,entry_time,exit_time",
                _trade_line("2026-01-06T00:00:00Z", 5.0),
                _trade_line("2026-01-13T00:00:00Z", -100.0, exit_reason="sl_hit"),
                _trade_line("2026-01-27T00:00:00Z", -10.0, symbol="ETH/USDT"),
                _trade_line("2026-02-03T00:00:00Z", 3.0),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    source_path = tmp_path / "source.json"
    source_path.write_text(
        json.dumps(
            {
                "matrices": {
                    VARIANT: {
                        "custom": {
                            DEFAULT_WINDOW: {
                                "artifacts": {
                                    "trades": str(trades_path),
                                    "signal_rejects": str(tmp_path / "rejects.csv"),
                                }
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    payload = build_repair_filter_payload(
        probe_path=probe_path,
        source_path=source_path,
        fee_rate=0.0,
    )

    assert payload["verdict"] == "REPAIR_FILTER_FOUND_BACKTEST_REQUIRED"
    assert payload["recommended"]["params"] == {
        "bbw_pctrank_max": 30.0,
        "min_retest_distance_atr": 0.0,
    }
    assert payload["recommended"]["candidate_count"] == 3
    assert payload["recommended"]["silent_zero_entry_week_hit_count"] == 3
    assert payload["recommended"]["known_gross_pnl_usdt"] == 8.0
