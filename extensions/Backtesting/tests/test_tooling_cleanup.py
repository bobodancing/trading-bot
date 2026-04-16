import sys
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from backtest_engine import (
    BacktestConfig,
    BacktestResult,
    _assign_entry_regime,
    _record_regime_probe,
    resolve_backtest_window,
)
from report_generator import ReportGenerator
from signal_audit import SignalAuditCollector


def test_resolve_backtest_window_uses_latest_cache_when_omitted(tmp_path):
    (tmp_path / "BTCUSDT_1h_20251007_20260406.parquet").write_text("")
    (tmp_path / "BTCUSDT_1h_20251101_20260301.parquet").write_text("")

    start, end = resolve_backtest_window(["BTC/USDT"], None, None, cache_dir=tmp_path)

    assert start == "2025-10-08"
    assert end == "2026-04-06"


def test_resolve_backtest_window_keeps_explicit_dates(tmp_path):
    start, end = resolve_backtest_window(
        ["BTC/USDT"],
        "2025-11-01",
        "2026-02-28",
        cache_dir=tmp_path,
    )

    assert start == "2025-11-01"
    assert end == "2026-02-28"


def test_resolve_backtest_window_falls_back_to_today_without_cache(tmp_path):
    start, end = resolve_backtest_window(
        ["BTC/USDT"],
        None,
        None,
        cache_dir=tmp_path,
        today=date(2026, 4, 11),
    )

    assert start == "2025-10-13"
    assert end == "2026-04-11"


def test_report_summary_includes_window_regime_composition(tmp_path, capsys):
    audit = SignalAuditCollector()
    for timestamp, regime in [
        ("2026-01-01T00:00:00+00:00", "TRENDING"),
        ("2026-01-01T04:00:00+00:00", "TRENDING"),
        ("2026-01-01T08:00:00+00:00", "RANGING"),
        ("2026-01-01T12:00:00+00:00", "SQUEEZE"),
    ]:
        audit.record_btc_trend(
            timestamp=timestamp,
            source="regime_probe",
            regime=regime,
        )

    idx = pd.date_range("2026-01-01", periods=4, freq="1h", tz="UTC")
    result = BacktestResult(
        trades=[],
        equity_curve=[(ts, 10000.0) for ts in idx],
        config=BacktestConfig(
            symbols=["BTC/USDT"],
            start="2026-01-01",
            end="2026-01-02",
        ),
        signal_audit=audit,
    )

    ReportGenerator().generate(result, tmp_path)

    captured = capsys.readouterr()
    assert "Window regime composition (4H bars)" in captured.out

    with open(tmp_path / "summary.json", encoding="utf-8") as f:
        summary = json.load(f)

    composition = summary["window_regime_composition_4h"]
    assert composition["total_bars"] == 4
    assert composition["TRENDING"] == {"pct": 50.0, "bars": 2}
    assert composition["RANGING"] == {"pct": 25.0, "bars": 1}
    assert composition["SQUEEZE"] == {"pct": 25.0, "bars": 1}


def test_regime_probe_keeps_latest_entry_snapshot():
    contexts = [
        {
            "regime": "TRENDING",
            "direction": "LONG",
            "candle_time": "2026-01-01T00:00:00+00:00",
            "reason": "regime_updated",
        },
        {
            "regime": "RANGING",
            "direction": "SHORT",
            "candle_time": "2026-01-01T04:00:00+00:00",
            "reason": "regime_updated",
        },
    ]

    audit = SignalAuditCollector()
    bot = SimpleNamespace(
        _signal_audit=audit,
        _update_btc_regime_context=lambda: contexts.pop(0),
    )

    _record_regime_probe(bot, "2026-01-01T00:00:00+00:00", grid_enabled=False)
    _record_regime_probe(bot, "2026-01-01T04:00:00+00:00", grid_enabled=False)

    snapshot = bot._backtest_latest_regime_probe_snapshot
    assert snapshot["entry_regime"] == "RANGING"
    assert snapshot["entry_regime_trend"] == "RANGING"
    assert snapshot["entry_regime_candle_time"] == "2026-01-01T04:00:00+00:00"


def test_assign_entry_regime_captures_first_seen_trade_snapshot():
    registry = {}
    active_trades = {
        "BTC/USDT": SimpleNamespace(trade_id="t1"),
    }
    trend_snapshot = {
        "entry_regime": "TRENDING",
        "entry_regime_trend": "LONG",
        "entry_regime_direction": "LONG",
        "entry_regime_reason": "regime_updated",
        "entry_regime_candle_time": "2026-01-01T00:00:00+00:00",
    }
    range_snapshot = {
        "entry_regime": "RANGING",
        "entry_regime_trend": "RANGING",
        "entry_regime_direction": None,
        "entry_regime_reason": "regime_updated",
        "entry_regime_candle_time": "2026-01-01T04:00:00+00:00",
    }

    _assign_entry_regime(active_trades, registry, trend_snapshot)
    _assign_entry_regime(active_trades, registry, range_snapshot)

    assert registry["t1"]["entry_regime"] == "TRENDING"
    assert registry["t1"]["entry_regime_trend"] == "LONG"
