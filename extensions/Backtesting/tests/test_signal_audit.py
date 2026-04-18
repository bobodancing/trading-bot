import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from signal_audit import SignalAuditCollector


def test_signal_audit_save_preserves_diagnostic_columns(tmp_path):
    collector = SignalAuditCollector()
    collector.record_reject(
        timestamp="2026-01-01T00:00:00+00:00",
        symbol="BTC/USDT",
        stage="post_filter",
        reject_reason="tier_filter",
        signal_type="fixture_long",
        signal_side="LONG",
        signal_tier="C",
        detail="tier=C min=A score=0",
        mtf_status="misaligned",
        mtf_aligned=False,
        mtf_reason="mtf_fail",
        mtf_gate_mode="hard_blocked",
        tier_score=0,
        tier_min="A",
        tier_min_effective="A",
        tier_component_mtf=0,
        signal_candle_time="2026-01-01T00:00:00+00:00",
        trend_candle_time="2025-12-31T20:00:00+00:00",
        mtf_candle_time="2025-12-31T20:00:00+00:00",
    )
    collector.record_entry(
        timestamp="2026-01-01T04:00:00+00:00",
        symbol="BTC/USDT",
        signal_type="fixture_long",
        signal_side="LONG",
        signal_tier="A",
        mtf_status="aligned",
        mtf_aligned=True,
        mtf_reason="mtf_ok",
        mtf_gate_mode="hard_aligned",
        tier_score=7,
        tier_component_mtf=2,
        tier_component_market=2,
        tier_component_volume=2,
        tier_component_candle=1,
        signal_candle_time="2026-01-01T04:00:00+00:00",
    )

    collector.save(tmp_path)

    rejects = pd.read_csv(tmp_path / "signal_rejects.csv")
    entries = pd.read_csv(tmp_path / "signal_entries.csv")

    assert "mtf_status" in rejects.columns
    assert "tier_score" in rejects.columns
    assert "signal_candle_time" in rejects.columns
    assert rejects.iloc[0]["mtf_status"] == "misaligned"
    assert rejects.iloc[0]["tier_score"] == 0

    assert "mtf_status" in entries.columns
    assert "tier_component_candle" in entries.columns
    assert entries.iloc[0]["mtf_status"] == "aligned"
    assert entries.iloc[0]["tier_score"] == 7
    assert "mtf_gate_mode" in entries.columns
    assert entries.iloc[0]["mtf_gate_mode"] == "hard_aligned"


def test_signal_audit_summary_includes_tier_and_mtf_breakdowns():
    collector = SignalAuditCollector()
    collector.record_reject(
        timestamp="2026-01-01T00:00:00+00:00",
        symbol="BTC/USDT",
        stage="post_filter",
        reject_reason="tier_filter",
        mtf_status="misaligned",
        mtf_reason="mtf_fail",
        mtf_gate_mode="ema_soft_structure",
        tier_score=0,
    )
    collector.record_entry(
        timestamp="2026-01-01T04:00:00+00:00",
        symbol="BTC/USDT",
        signal_type="fixture_long",
        signal_side="LONG",
        signal_tier="A",
        mtf_status="aligned",
        mtf_gate_mode="hard_aligned",
        tier_score=7,
    )

    summary = collector.summary()

    assert summary["rejects_by_mtf_status"] == {"misaligned": 1}
    assert summary["rejects_by_mtf_reason"] == {"mtf_fail": 1}
    assert summary["rejects_by_mtf_gate_mode"] == {"ema_soft_structure": 1}
    assert summary["rejects_by_tier_score"] == {"0": 1}
    assert summary["entries_by_mtf_status"] == {"aligned": 1}
    assert summary["entries_by_mtf_gate_mode"] == {"hard_aligned": 1}
    assert summary["entries_by_tier_score"] == {"7": 1}


def test_signal_audit_saves_lane_race_audit(tmp_path):
    collector = SignalAuditCollector()
    collector.record_lane_race(
        timestamp="2026-01-01T00:00:00+00:00",
        symbol="ETH/USDT",
        candidate_signal_type="fixture_long",
        selected_signal_type="fixture_exit",
        suppressed_by="priority",
        won_race_vs=None,
        same_symbol_cooldown_block=False,
        position_slot_block=False,
        block_reason="priority:fixture_exit",
        baseline_match_key="ETH/USDT|2026-01-01T00:00:00+00:00",
        candidate_signal_side="LONG",
    )

    collector.save(tmp_path)

    lane_df = pd.read_csv(tmp_path / "lane_race_audit.csv")
    assert lane_df.iloc[0]["candidate_signal_type"] == "fixture_long"
    assert lane_df.iloc[0]["selected_signal_type"] == "fixture_exit"
    assert lane_df.iloc[0]["suppressed_by"] == "priority"

    summary = collector.summary()
    assert summary["lane_race_events"] == 1
    assert summary["lane_candidates_by_signal_type"] == {"fixture_long": 1}
    assert summary["lane_suppressed_by"] == {"priority": 1}
