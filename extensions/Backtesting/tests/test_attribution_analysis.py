import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from attribution_analysis import analyze_baselines


def _write_json(path: Path, payload: dict) -> None:
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def _make_dir(base: Path, name: str) -> Path:
    d = base / name
    d.mkdir()
    _write_json(d / "summary.json", {})
    _write_json(d / "signal_audit_summary.json", {})
    return d


def test_analyze_baselines_classifies_trend_delay(tmp_path):
    before_dir = _make_dir(tmp_path, "before")
    after_dir = _make_dir(tmp_path, "after")

    _write_csv(before_dir / "signal_entries.csv", [
        {"timestamp": "2026-01-01T00:00:00+00:00", "symbol": "BTC/USDT", "signal_type": "EMA_PULLBACK"},
    ])
    _write_csv(after_dir / "signal_entries.csv", [
        {"timestamp": "2026-01-01T04:00:00+00:00", "symbol": "BTC/USDT", "signal_type": "EMA_PULLBACK"},
    ])
    _write_csv(after_dir / "signal_rejects.csv", [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "BTC/USDT",
            "stage": "post_filter",
            "reject_reason": "trend_filter",
            "signal_type": "EMA_PULLBACK",
        },
    ])
    _write_csv(before_dir / "trades.csv", [
        {
            "entry_time": "2026-01-01T00:00:00+00:00",
            "exit_time": "2026-01-01T08:00:00+00:00",
            "symbol": "BTC/USDT",
            "signal_type": "EMA_PULLBACK",
            "pnl_usdt": 10.0,
        },
    ])
    _write_csv(after_dir / "trades.csv", [
        {
            "entry_time": "2026-01-01T04:00:00+00:00",
            "exit_time": "2026-01-01T10:00:00+00:00",
            "symbol": "BTC/USDT",
            "signal_type": "EMA_PULLBACK",
            "pnl_usdt": 4.0,
        },
    ])

    result = analyze_baselines(before_dir, after_dir, window_hours=24)
    rows = result["rows"]

    assert len(rows) == 1
    assert rows.iloc[0]["attribution"] == "trend_delay"
    assert rows.iloc[0]["delta_hours"] == 4.0
    assert result["summary"]["matched_trade_pnl_shift"]["delta_total"] == -6.0


def test_analyze_baselines_classifies_signal_disappeared(tmp_path):
    before_dir = _make_dir(tmp_path, "before")
    after_dir = _make_dir(tmp_path, "after")

    _write_csv(before_dir / "signal_entries.csv", [
        {"timestamp": "2026-01-01T00:00:00+00:00", "symbol": "ETH/USDT", "signal_type": "2B"},
    ])
    _write_csv(after_dir / "signal_entries.csv", [])
    _write_csv(after_dir / "signal_rejects.csv", [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "ETH/USDT",
            "stage": "signal_found",
            "reject_reason": "no_signal_detected",
        },
    ])
    _write_csv(before_dir / "trades.csv", [])
    _write_csv(after_dir / "trades.csv", [])

    result = analyze_baselines(before_dir, after_dir, window_hours=24)
    rows = result["rows"]

    assert len(rows) == 1
    assert rows.iloc[0]["attribution"] == "signal_disappeared"


def test_analyze_baselines_classifies_same_time_retype(tmp_path):
    before_dir = _make_dir(tmp_path, "before")
    after_dir = _make_dir(tmp_path, "after")

    _write_csv(before_dir / "signal_entries.csv", [
        {"timestamp": "2026-01-01T00:00:00+00:00", "symbol": "SOL/USDT", "signal_type": "VOLUME_BREAKOUT"},
    ])
    _write_csv(after_dir / "signal_entries.csv", [
        {"timestamp": "2026-01-01T00:00:00+00:00", "symbol": "SOL/USDT", "signal_type": "EMA_PULLBACK"},
    ])
    _write_csv(after_dir / "signal_rejects.csv", [])
    _write_csv(before_dir / "trades.csv", [])
    _write_csv(after_dir / "trades.csv", [])

    result = analyze_baselines(before_dir, after_dir, window_hours=24)
    rows = result["rows"]

    assert len(rows) == 1
    assert rows.iloc[0]["attribution"] == "retyped_to_ema_pullback"


def test_analyze_baselines_preserves_tier_mtf_diagnostics(tmp_path):
    before_dir = _make_dir(tmp_path, "before_diag")
    after_dir = _make_dir(tmp_path, "after_diag")

    _write_csv(before_dir / "signal_entries.csv", [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "BTC/USDT",
            "signal_type": "EMA_PULLBACK",
            "signal_tier": "A",
            "tier_score": 7,
            "mtf_status": "aligned",
            "mtf_reason": "mtf_ok",
        },
    ])
    _write_csv(after_dir / "signal_entries.csv", [
        {
            "timestamp": "2026-01-01T04:00:00+00:00",
            "symbol": "BTC/USDT",
            "signal_type": "EMA_PULLBACK",
            "signal_tier": "B",
            "tier_score": 5,
            "mtf_status": "aligned",
            "mtf_reason": "mtf_ok",
        },
    ])
    _write_csv(after_dir / "signal_rejects.csv", [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "BTC/USDT",
            "stage": "post_filter",
            "reject_reason": "tier_filter",
            "signal_type": "EMA_PULLBACK",
            "tier_score": 0,
            "tier_min": "A",
            "mtf_status": "misaligned",
            "mtf_reason": "mtf_fail",
        },
    ])
    _write_csv(before_dir / "trades.csv", [])
    _write_csv(after_dir / "trades.csv", [])

    result = analyze_baselines(before_dir, after_dir, window_hours=24)
    row = result["rows"].iloc[0]

    assert row["before_signal_tier"] == "A"
    assert row["after_signal_tier"] == "B"
    assert row["before_tier_score"] == 7
    assert row["after_tier_score"] == 5
    assert row["after_same_time_tier_score"] == 0
    assert row["after_same_time_tier_min"] == "A"
    assert row["before_mtf_status"] == "aligned"
    assert row["after_same_time_mtf_status"] == "misaligned"
    assert row["after_same_time_mtf_reason"] == "mtf_fail"
