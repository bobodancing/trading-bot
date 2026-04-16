"""
Signal Audit Collector -- captures every signal rejection, regime transition,
and BTC trend resolution during backtest for Patch B diff analysis.

Usage:
    collector = SignalAuditCollector()
    bot._signal_audit = collector   # inject into bot
    # ... run backtest ...
    collector.save(output_dir)
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass
class SignalReject:
    timestamp: str
    symbol: str
    stage: str           # "pre_signal" | "signal_found" | "post_filter"
    reject_reason: str
    signal_type: Optional[str] = None
    signal_side: Optional[str] = None
    signal_tier: Optional[str] = None
    regime: Optional[str] = None
    btc_trend: Optional[str] = None
    detail: Optional[str] = None
    market_reason: Optional[str] = None
    market_strong: Optional[bool] = None
    trend_desc: Optional[str] = None
    mtf_enabled: Optional[bool] = None
    mtf_aligned: Optional[bool] = None
    mtf_reason: Optional[str] = None
    mtf_status: Optional[str] = None
    mtf_close: Optional[float] = None
    mtf_ema_fast: Optional[float] = None
    mtf_ema_slow: Optional[float] = None
    mtf_price_vs_fast_pct: Optional[float] = None
    mtf_fast_vs_slow_pct: Optional[float] = None
    mtf_gate_mode: Optional[str] = None
    tier_min: Optional[str] = None
    tier_min_effective: Optional[str] = None
    tier_score: Optional[float] = None
    tier_multiplier: Optional[float] = None
    volume_grade: Optional[str] = None
    candle_confirmed: Optional[bool] = None
    tier_component_mtf: Optional[int] = None
    tier_component_market: Optional[int] = None
    tier_component_volume: Optional[int] = None
    tier_component_candle: Optional[int] = None
    signal_candle_time: Optional[str] = None
    trend_candle_time: Optional[str] = None
    mtf_candle_time: Optional[str] = None
    arbiter_label: Optional[str] = None
    arbiter_confidence: Optional[float] = None
    arbiter_entry_allowed: Optional[bool] = None
    arbiter_reason: Optional[str] = None
    arbiter_macro_state: Optional[str] = None
    router_allowed: Optional[bool] = None
    router_selected_strategy: Optional[str] = None
    router_reason: Optional[str] = None
    router_policy: Optional[str] = None


@dataclass
class SignalEntry:
    timestamp: str
    symbol: str
    signal_type: str
    signal_side: str
    signal_tier: str
    regime: Optional[str] = None
    btc_trend: Optional[str] = None
    market_reason: Optional[str] = None
    market_strong: Optional[bool] = None
    trend_desc: Optional[str] = None
    mtf_enabled: Optional[bool] = None
    mtf_aligned: Optional[bool] = None
    mtf_reason: Optional[str] = None
    mtf_status: Optional[str] = None
    mtf_close: Optional[float] = None
    mtf_ema_fast: Optional[float] = None
    mtf_ema_slow: Optional[float] = None
    mtf_price_vs_fast_pct: Optional[float] = None
    mtf_fast_vs_slow_pct: Optional[float] = None
    mtf_gate_mode: Optional[str] = None
    tier_min: Optional[str] = None
    tier_min_effective: Optional[str] = None
    tier_score: Optional[float] = None
    tier_multiplier: Optional[float] = None
    volume_grade: Optional[str] = None
    candle_confirmed: Optional[bool] = None
    tier_component_mtf: Optional[int] = None
    tier_component_market: Optional[int] = None
    tier_component_volume: Optional[int] = None
    tier_component_candle: Optional[int] = None
    signal_candle_time: Optional[str] = None
    trend_candle_time: Optional[str] = None
    mtf_candle_time: Optional[str] = None
    arbiter_label: Optional[str] = None
    arbiter_confidence: Optional[float] = None
    arbiter_entry_allowed: Optional[bool] = None
    arbiter_reason: Optional[str] = None
    arbiter_macro_state: Optional[str] = None
    router_allowed: Optional[bool] = None
    router_selected_strategy: Optional[str] = None
    router_reason: Optional[str] = None
    router_policy: Optional[str] = None


@dataclass
class LaneRaceEvent:
    timestamp: str
    symbol: str
    candidate_signal_type: str
    selected_signal_type: Optional[str] = None
    suppressed_by: Optional[str] = None
    won_race_vs: Optional[str] = None
    same_symbol_cooldown_block: Optional[bool] = None
    position_slot_block: Optional[bool] = None
    block_reason: Optional[str] = None
    baseline_match_key: Optional[str] = None
    candidate_signal_side: Optional[str] = None


@dataclass
class RegimeTransition:
    timestamp: str
    old_regime: str
    new_regime: str
    confirm_count: int = 0


@dataclass
class BTCTrendSnapshot:
    timestamp: str
    source: str          # "regime" | "regime_probe" | "1d_fallback" | "none"
    trend: Optional[str] = None
    regime: Optional[str] = None
    direction: Optional[str] = None
    reason: str = ""


class SignalAuditCollector:
    """Collects signal audit data during backtest. No-op when not injected."""

    def __init__(self):
        self.rejects: List[SignalReject] = []
        self.entries: List[SignalEntry] = []
        self.lane_race_events: List[LaneRaceEvent] = []
        self.regime_transitions: List[RegimeTransition] = []
        self.btc_trend_snapshots: List[BTCTrendSnapshot] = []

    # -- Recording methods --

    def record_reject(
        self,
        timestamp,
        symbol: str,
        stage: str,
        reject_reason: str,
        signal_type: Optional[str] = None,
        signal_side: Optional[str] = None,
        signal_tier: Optional[str] = None,
        regime: Optional[str] = None,
        btc_trend: Optional[str] = None,
        detail: Optional[str] = None,
        **extra,
    ):
        payload = {
            "timestamp": str(timestamp),
            "symbol": symbol,
            "stage": stage,
            "reject_reason": reject_reason,
            "signal_type": signal_type,
            "signal_side": signal_side,
            "signal_tier": signal_tier,
            "regime": regime,
            "btc_trend": btc_trend,
            "detail": detail,
            **extra,
        }
        allowed = SignalReject.__dataclass_fields__.keys()
        self.rejects.append(SignalReject(**{key: payload.get(key) for key in allowed}))

    def record_entry(
        self,
        timestamp,
        symbol: str,
        signal_type: str,
        signal_side: str,
        signal_tier: str,
        regime: Optional[str] = None,
        btc_trend: Optional[str] = None,
        **extra,
    ):
        payload = {
            "timestamp": str(timestamp),
            "symbol": symbol,
            "signal_type": signal_type,
            "signal_side": signal_side,
            "signal_tier": signal_tier,
            "regime": regime,
            "btc_trend": btc_trend,
            **extra,
        }
        allowed = SignalEntry.__dataclass_fields__.keys()
        self.entries.append(SignalEntry(**{key: payload.get(key) for key in allowed}))

    def record_lane_race(
        self,
        timestamp,
        symbol: str,
        candidate_signal_type: str,
        selected_signal_type: Optional[str] = None,
        suppressed_by: Optional[str] = None,
        won_race_vs: Optional[str] = None,
        same_symbol_cooldown_block: Optional[bool] = None,
        position_slot_block: Optional[bool] = None,
        block_reason: Optional[str] = None,
        baseline_match_key: Optional[str] = None,
        candidate_signal_side: Optional[str] = None,
    ):
        payload = {
            "timestamp": str(timestamp),
            "symbol": symbol,
            "candidate_signal_type": candidate_signal_type,
            "selected_signal_type": selected_signal_type,
            "suppressed_by": suppressed_by,
            "won_race_vs": won_race_vs,
            "same_symbol_cooldown_block": same_symbol_cooldown_block,
            "position_slot_block": position_slot_block,
            "block_reason": block_reason,
            "baseline_match_key": baseline_match_key,
            "candidate_signal_side": candidate_signal_side,
        }
        allowed = LaneRaceEvent.__dataclass_fields__.keys()
        self.lane_race_events.append(LaneRaceEvent(**{key: payload.get(key) for key in allowed}))

    def record_regime_transition(
        self,
        timestamp,
        old_regime: str,
        new_regime: str,
        confirm_count: int = 0,
    ):
        self.regime_transitions.append(RegimeTransition(
            timestamp=str(timestamp),
            old_regime=old_regime,
            new_regime=new_regime,
            confirm_count=confirm_count,
        ))

    def record_btc_trend(
        self,
        timestamp,
        source: str,
        trend: Optional[str] = None,
        regime: Optional[str] = None,
        direction: Optional[str] = None,
        reason: str = "",
    ):
        self.btc_trend_snapshots.append(BTCTrendSnapshot(
            timestamp=str(timestamp),
            source=source,
            trend=trend,
            regime=regime,
            direction=direction,
            reason=reason,
        ))

    # -- DataFrames --

    def rejects_df(self) -> pd.DataFrame:
        if not self.rejects:
            return pd.DataFrame(columns=list(SignalReject.__dataclass_fields__.keys()))
        return pd.DataFrame([r.__dict__ for r in self.rejects])

    def entries_df(self) -> pd.DataFrame:
        if not self.entries:
            return pd.DataFrame(columns=list(SignalEntry.__dataclass_fields__.keys()))
        return pd.DataFrame([e.__dict__ for e in self.entries])

    def lane_race_df(self) -> pd.DataFrame:
        if not self.lane_race_events:
            return pd.DataFrame(columns=list(LaneRaceEvent.__dataclass_fields__.keys()))
        return pd.DataFrame([e.__dict__ for e in self.lane_race_events])

    def regime_df(self) -> pd.DataFrame:
        if not self.regime_transitions:
            return pd.DataFrame(columns=[
                "timestamp", "old_regime", "new_regime", "confirm_count",
            ])
        return pd.DataFrame([r.__dict__ for r in self.regime_transitions])

    def btc_trend_df(self) -> pd.DataFrame:
        if not self.btc_trend_snapshots:
            return pd.DataFrame(columns=[
                "timestamp", "source", "trend", "regime", "direction", "reason",
            ])
        return pd.DataFrame([s.__dict__ for s in self.btc_trend_snapshots])

    def summary(self) -> dict:
        """Generate a summary dict for quick comparison."""
        rej_df = self.rejects_df()
        ent_df = self.entries_df()
        lane_df = self.lane_race_df()
        reg_df = self.regime_df()
        btc_df = self.btc_trend_df()

        result = {
            "total_rejects": len(self.rejects),
            "total_entries": len(self.entries),
            "lane_race_events": len(self.lane_race_events),
            "regime_transitions": len(self.regime_transitions),
            "btc_trend_snapshots": len(self.btc_trend_snapshots),
        }

        # Reject breakdown by reason
        if not rej_df.empty:
            result["rejects_by_reason"] = rej_df["reject_reason"].value_counts().to_dict()
            result["rejects_by_stage"] = rej_df["stage"].value_counts().to_dict()
            mtf_status = rej_df.get("mtf_status")
            if mtf_status is not None:
                mtf_status = mtf_status.dropna()
                if not mtf_status.empty:
                    result["rejects_by_mtf_status"] = mtf_status.value_counts().to_dict()
            mtf_reason = rej_df.get("mtf_reason")
            if mtf_reason is not None:
                mtf_reason = mtf_reason.dropna()
                if not mtf_reason.empty:
                    result["rejects_by_mtf_reason"] = mtf_reason.value_counts().to_dict()
            mtf_gate_mode = rej_df.get("mtf_gate_mode")
            if mtf_gate_mode is not None:
                mtf_gate_mode = mtf_gate_mode.dropna()
                if not mtf_gate_mode.empty:
                    result["rejects_by_mtf_gate_mode"] = mtf_gate_mode.value_counts().to_dict()
            tier_score = rej_df.get("tier_score")
            if tier_score is not None:
                tier_score = tier_score.dropna()
                if not tier_score.empty:
                    result["rejects_by_tier_score"] = tier_score.astype(str).value_counts().to_dict()
            arbiter_reason = rej_df.get("arbiter_reason")
            if arbiter_reason is not None:
                arbiter_reason = arbiter_reason.dropna()
                if not arbiter_reason.empty:
                    result["rejects_by_arbiter_reason"] = arbiter_reason.value_counts().to_dict()
            router_reason = rej_df.get("router_reason")
            if router_reason is not None:
                router_reason = router_reason.dropna()
                if not router_reason.empty:
                    result["rejects_by_router_reason"] = router_reason.value_counts().to_dict()

        # Entry breakdown by signal type
        if not ent_df.empty:
            result["entries_by_signal_type"] = ent_df["signal_type"].value_counts().to_dict()
            result["entries_by_tier"] = ent_df["signal_tier"].value_counts().to_dict()
            mtf_status = ent_df.get("mtf_status")
            if mtf_status is not None:
                mtf_status = mtf_status.dropna()
                if not mtf_status.empty:
                    result["entries_by_mtf_status"] = mtf_status.value_counts().to_dict()
            mtf_gate_mode = ent_df.get("mtf_gate_mode")
            if mtf_gate_mode is not None:
                mtf_gate_mode = mtf_gate_mode.dropna()
                if not mtf_gate_mode.empty:
                    result["entries_by_mtf_gate_mode"] = mtf_gate_mode.value_counts().to_dict()
            tier_score = ent_df.get("tier_score")
            if tier_score is not None:
                tier_score = tier_score.dropna()
                if not tier_score.empty:
                    result["entries_by_tier_score"] = tier_score.astype(str).value_counts().to_dict()
            arbiter_label = ent_df.get("arbiter_label")
            if arbiter_label is not None:
                arbiter_label = arbiter_label.dropna()
                if not arbiter_label.empty:
                    result["entries_by_arbiter_label"] = arbiter_label.value_counts().to_dict()
            router_selected = ent_df.get("router_selected_strategy")
            if router_selected is not None:
                router_selected = router_selected.dropna()
                if not router_selected.empty:
                    result["entries_by_router_strategy"] = router_selected.value_counts().to_dict()

        if not lane_df.empty:
            result["lane_candidates_by_signal_type"] = (
                lane_df["candidate_signal_type"].value_counts().to_dict()
            )
            selected = lane_df.get("selected_signal_type")
            if selected is not None:
                selected = selected.dropna()
                if not selected.empty:
                    result["lane_selected_by_signal_type"] = selected.value_counts().to_dict()
            suppressed = lane_df.get("suppressed_by")
            if suppressed is not None:
                suppressed = suppressed.dropna()
                if not suppressed.empty:
                    result["lane_suppressed_by"] = suppressed.value_counts().to_dict()

        # Regime stats
        if not reg_df.empty:
            result["regime_transitions_by_type"] = (
                reg_df.apply(lambda r: f"{r['old_regime']}->{r['new_regime']}", axis=1)
                .value_counts().to_dict()
            )

        # BTC trend stats
        if not btc_df.empty:
            result["btc_trend_distribution"] = btc_df["trend"].value_counts(dropna=False).to_dict()
            result["btc_source_distribution"] = btc_df["source"].value_counts().to_dict()

        return result

    # -- I/O --

    def save(self, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.rejects_df().to_csv(output_dir / "signal_rejects.csv", index=False)
        self.entries_df().to_csv(output_dir / "signal_entries.csv", index=False)
        self.lane_race_df().to_csv(output_dir / "lane_race_audit.csv", index=False)
        self.regime_df().to_csv(output_dir / "regime_transitions.csv", index=False)
        self.btc_trend_df().to_csv(output_dir / "btc_trend_log.csv", index=False)

        import json
        with open(output_dir / "signal_audit_summary.json", "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2, ensure_ascii=False, default=str)
