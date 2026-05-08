import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from trader.config import Config
from trader.runtime_observability import RuntimeFunnelRecorder
from trader.strategies import MarketSnapshot, StrategyPlugin
from trader.strategy_runtime import StrategyRuntime


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _frame(rows=8):
    idx = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + rows), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


class _NoCandidatePlugin(StrategyPlugin):
    id = "no_candidate"
    version = "1.0.0"
    tags = {"test"}
    required_timeframes = {"1h": 8}
    required_indicators = set()
    allowed_symbols = {"BTC/USDT"}

    def generate_candidates(self, context):
        return []


class _FakeBot:
    def __init__(self, recorder):
        self.active_trades = {}
        self.runtime_observer = recorder
        self.signal_scanner = SimpleNamespace(check_cooldowns=lambda _symbol: True)


def test_runtime_funnel_recorder_writes_jsonl_and_latest_summary(tmp_path):
    recorder = RuntimeFunnelRecorder(
        jsonl_path=tmp_path / "strategy_runtime_funnel.jsonl",
        latest_path=tmp_path / "strategy_runtime_latest.json",
    )

    recorder.record_event("plugin_candidates", plugin_id="slot_b_short", candidate_count=0)
    recorder.record_event("strategy_reject", strategy_id="slot_b_short", reason="cooldown")
    recorder.record_event("strategy_entry_ready", strategy_id="slot_b_short")

    events = _read_jsonl(tmp_path / "strategy_runtime_funnel.jsonl")
    latest = json.loads((tmp_path / "strategy_runtime_latest.json").read_text(encoding="utf-8"))

    assert [event["event"] for event in events] == [
        "plugin_candidates",
        "strategy_reject",
        "strategy_entry_ready",
    ]
    assert latest["event_counts"]["plugin_candidates"] == 1
    assert latest["plugin_zero_candidate_counts"]["slot_b_short"] == 1
    assert latest["reject_counts"]["cooldown"] == 1
    assert latest["entry_counts"]["slot_b_short"] == 1


def test_strategy_runtime_records_zero_candidate_scan_cycle(tmp_path, monkeypatch):
    recorder = RuntimeFunnelRecorder(
        jsonl_path=tmp_path / "strategy_runtime_funnel.jsonl",
        latest_path=tmp_path / "strategy_runtime_latest.json",
    )
    bot = _FakeBot(recorder)
    runtime = StrategyRuntime(bot)
    plugin = _NoCandidatePlugin()
    snapshot = MarketSnapshot(
        frames={"BTC/USDT": {"1h": _frame()}},
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    monkeypatch.setattr(Config, "STRATEGY_RUNTIME_ENABLED", True)
    monkeypatch.setattr(Config, "USE_SCANNER_SYMBOLS", False)
    monkeypatch.setattr(Config, "SCANNER_UNIVERSE_ENABLED", False)
    monkeypatch.setattr(Config, "SYMBOLS", ["BTC/USDT"])
    monkeypatch.setattr(Config, "REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr(Config, "REGIME_ROUTER_ENABLED", False)
    monkeypatch.setattr(runtime, "refresh_registry", lambda: None)
    monkeypatch.setattr(runtime, "enabled_plugins", lambda: [plugin])
    monkeypatch.setattr(runtime.snapshot_builder, "build", lambda _symbols, _plugins: snapshot)

    runtime.scan_for_entries()

    events = _read_jsonl(tmp_path / "strategy_runtime_funnel.jsonl")
    plugin_event = next(event for event in events if event["event"] == "plugin_candidates")
    snapshot_event = next(event for event in events if event["event"] == "snapshot_built")
    latest = json.loads((tmp_path / "strategy_runtime_latest.json").read_text(encoding="utf-8"))

    assert plugin_event["plugin_id"] == "no_candidate"
    assert plugin_event["candidate_count"] == 0
    assert snapshot_event["frames"]["BTC/USDT"]["1h"]["rows"] == 8
    assert latest["last_cycle"]["status"] == "completed"
    assert latest["last_cycle"]["candidates"] == 0
    assert latest["plugin_zero_candidate_counts"]["no_candidate"] == 1
