"""Probe Phase 4D-A range-break retest coverage before plugin work."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = SCRIPT_ROOT.parents[0]
REPO_ROOT = BACKTEST_ROOT.parents[1]
for path in (SCRIPT_ROOT, BACKTEST_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analyze_weekly_profit_trend_companion_probe import (  # noqa: E402
    DEFAULT_FEASIBILITY_JSON,
    DEFAULT_LANE_JSON,
    _counter_to_dict,
    _filter_candidates_to_window,
    _iso,
    _load_json,
    _load_market_frame,
    _parse_ts,
    _promoted_overlap_keys,
    _read_csv,
    _week_start,
)
from trader.indicators.registry import IndicatorRegistry  # noqa: E402


RESULT_DIR = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
)
DEFAULT_JSON = RESULT_DIR / "weekly_profit_range_break_retest_probe_summary.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4d_range_break_retest_probe.md"
DEFAULT_START = "20260101"
DEFAULT_END = "20260430"

DEFAULT_PRESETS: list[dict[str, Any]] = [
    {
        "variant_id": "range_break_retest_conservative_30",
        "mechanism": "donchian30_break_retest_hold_4h_continuation",
        "donchian_len": 30,
        "range_window": 15,
        "bbw_pctrank_window": 50,
        "width_cv_max": 0.18,
        "bbw_pctrank_max": 45.0,
        "break_atr_min": 0.05,
        "max_retest_bars": 3,
        "retest_band_atr": 0.35,
        "min_adx": 12.0,
        "min_adx_slope_5": -2.0,
        "breakout_close_quality_min": 0.55,
        "trend_aligned": False,
    },
    {
        "variant_id": "range_break_hold_conservative_30",
        "mechanism": "donchian30_break_hold_4h_continuation",
        "donchian_len": 30,
        "range_window": 15,
        "bbw_pctrank_window": 50,
        "width_cv_max": 0.18,
        "bbw_pctrank_max": 45.0,
        "break_atr_min": 0.05,
        "max_retest_bars": 3,
        "retest_band_atr": 0.20,
        "min_adx": 12.0,
        "min_adx_slope_5": -2.0,
        "breakout_close_quality_min": 0.55,
        "trend_aligned": False,
        "hold_only": True,
    },
    {
        "variant_id": "range_break_retest_conservative_20",
        "mechanism": "donchian20_break_retest_hold_4h_continuation",
        "donchian_len": 20,
        "range_window": 15,
        "bbw_pctrank_window": 50,
        "width_cv_max": 0.18,
        "bbw_pctrank_max": 45.0,
        "break_atr_min": 0.05,
        "max_retest_bars": 3,
        "retest_band_atr": 0.35,
        "min_adx": 12.0,
        "min_adx_slope_5": -2.0,
        "breakout_close_quality_min": 0.55,
        "trend_aligned": False,
    },
    {
        "variant_id": "range_break_retest_broad_30",
        "mechanism": "donchian30_break_retest_hold_4h_broad_diagnostic",
        "donchian_len": 30,
        "range_window": 15,
        "bbw_pctrank_window": 50,
        "width_cv_max": 0.35,
        "bbw_pctrank_max": 80.0,
        "break_atr_min": 0.0,
        "max_retest_bars": 6,
        "retest_band_atr": 0.50,
        "min_adx": 8.0,
        "min_adx_slope_5": -8.0,
        "breakout_close_quality_min": 0.45,
        "trend_aligned": False,
    },
]


def _float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _with_range_features(
    frame: pd.DataFrame,
    *,
    donchian_len: int,
    range_window: int,
    bbw_pctrank_window: int,
) -> pd.DataFrame:
    enriched = IndicatorRegistry.apply(frame, {"atr", "adx", "bbw", "ema"}).sort_index()
    enriched["range_high"] = enriched["high"].shift(1).rolling(donchian_len).max()
    enriched["range_low"] = enriched["low"].shift(1).rolling(donchian_len).min()
    enriched["range_width"] = enriched["range_high"] - enriched["range_low"]
    enriched["range_mid"] = (enriched["range_high"] + enriched["range_low"]) / 2.0
    width_mean = enriched["range_width"].rolling(range_window).mean()
    width_std = enriched["range_width"].rolling(range_window).std(ddof=0)
    enriched["width_cv"] = width_std / width_mean
    enriched["range_width_pct"] = enriched["range_width"] / enriched["close"]
    enriched["bbw_pctrank"] = (
        enriched["bbw"].rolling(bbw_pctrank_window).rank(pct=True) * 100.0
    )
    enriched["adx_slope_5"] = enriched["adx"] - enriched["adx"].shift(5)
    enriched["ema_spread_20_50"] = (
        enriched["ema_20"] - enriched["ema_50"]
    ) / enriched["ema_50"]
    return enriched


def _breakout_close_quality(row: pd.Series, side: str) -> float | None:
    candle_range = float(row["high"] - row["low"])
    if candle_range <= 0.0:
        return None
    if side == "LONG":
        return float((row["close"] - row["low"]) / candle_range)
    return float((row["high"] - row["close"]) / candle_range)


def _passes_breakout(row: pd.Series, *, side: str, preset: dict[str, Any]) -> bool:
    required = [
        "atr",
        "range_high",
        "range_low",
        "width_cv",
        "bbw_pctrank",
        "adx",
        "adx_slope_5",
        "ema_spread_20_50",
    ]
    if row[required].isna().any() or float(row["atr"]) <= 0.0:
        return False
    if float(row["width_cv"]) > float(preset["width_cv_max"]):
        return False
    if float(row["bbw_pctrank"]) > float(preset["bbw_pctrank_max"]):
        return False
    if float(row["adx"]) < float(preset["min_adx"]):
        return False
    if float(row["adx_slope_5"]) < float(preset["min_adx_slope_5"]):
        return False
    quality = _breakout_close_quality(row, side)
    if quality is None or quality < float(preset["breakout_close_quality_min"]):
        return False
    break_atr = float(preset["break_atr_min"]) * float(row["atr"])
    if side == "LONG":
        if bool(preset.get("trend_aligned")) and float(row["ema_spread_20_50"]) < 0.0:
            return False
        return float(row["close"]) > float(row["range_high"]) + break_atr
    if bool(preset.get("trend_aligned")) and float(row["ema_spread_20_50"]) > 0.0:
        return False
    return float(row["close"]) < float(row["range_low"]) - break_atr


def _passes_retest(
    row: pd.Series,
    *,
    side: str,
    boundary: float,
    preset: dict[str, Any],
) -> tuple[bool, float | None]:
    if pd.isna(row["atr"]) or float(row["atr"]) <= 0.0:
        return False, None
    atr = float(row["atr"])
    band = float(preset["retest_band_atr"]) * atr
    if side == "LONG":
        distance_atr = float((row["low"] - boundary) / atr)
        touched = True if bool(preset.get("hold_only")) else float(row["low"]) <= boundary + band
        held = float(row["close"]) >= boundary
    else:
        distance_atr = float((boundary - row["high"]) / atr)
        touched = True if bool(preset.get("hold_only")) else float(row["high"]) >= boundary - band
        held = float(row["close"]) <= boundary
    return bool(touched and held), distance_atr


def generate_range_break_retest_candidates(
    market_frames: dict[str, pd.DataFrame],
    *,
    preset: dict[str, Any],
    feature_cache: dict[tuple[str, int, int, int], pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for symbol, raw in sorted(market_frames.items()):
        feature_key = (
            symbol,
            int(preset["donchian_len"]),
            int(preset["range_window"]),
            int(preset["bbw_pctrank_window"]),
        )
        if feature_cache is not None and feature_key in feature_cache:
            frame = feature_cache[feature_key]
        else:
            frame = _with_range_features(
                raw,
                donchian_len=int(preset["donchian_len"]),
                range_window=int(preset["range_window"]),
                bbw_pctrank_window=int(preset["bbw_pctrank_window"]),
            )
            if feature_cache is not None:
                feature_cache[feature_key] = frame
        index = list(frame.index)
        max_retest_bars = int(preset["max_retest_bars"])
        for breakout_i in range(0, max(0, len(frame) - max_retest_bars)):
            breakout = frame.iloc[breakout_i]
            for side in ("LONG", "SHORT"):
                if not _passes_breakout(breakout, side=side, preset=preset):
                    continue
                boundary = float(
                    breakout["range_high"] if side == "LONG" else breakout["range_low"]
                )
                for lag in range(1, max_retest_bars + 1):
                    retest = frame.iloc[breakout_i + lag]
                    passed, distance_atr = _passes_retest(
                        retest,
                        side=side,
                        boundary=boundary,
                        preset=preset,
                    )
                    if not passed:
                        continue
                    breakout_ts = pd.Timestamp(index[breakout_i])
                    retest_ts = pd.Timestamp(index[breakout_i + lag])
                    break_strength = (
                        float((breakout["close"] - boundary) / breakout["atr"])
                        if side == "LONG"
                        else float((boundary - breakout["close"]) / breakout["atr"])
                    )
                    candidates.append(
                        {
                            "timestamp": _iso(retest_ts),
                            "symbol": symbol,
                            "side": side,
                            "candidate_family": "range_break_retest_frequency_complement",
                            "mechanism": str(preset["mechanism"]),
                            "variant_id": str(preset["variant_id"]),
                            "entry_timeframe": "4h",
                            "entry_price": float(retest["close"]),
                            "breakout_timestamp": _iso(breakout_ts),
                            "breakout_close": float(breakout["close"]),
                            "range_boundary": boundary,
                            "retest_lag_bars": int(lag),
                            "retest_distance_atr": _float_or_none(distance_atr),
                            "break_strength_atr": round(break_strength, 4),
                            "breakout_close_quality": round(
                                float(_breakout_close_quality(breakout, side) or 0.0), 4
                            ),
                            "donchian_len": int(preset["donchian_len"]),
                            "range_window": int(preset["range_window"]),
                            "width_cv": round(float(breakout["width_cv"]), 6),
                            "range_width_pct": round(float(breakout["range_width_pct"]), 6),
                            "bbw_pctrank": round(float(breakout["bbw_pctrank"]), 4),
                            "adx": round(float(breakout["adx"]), 4),
                            "adx_slope_5": round(float(breakout["adx_slope_5"]), 4),
                            "ema_spread_20_50": round(
                                float(breakout["ema_spread_20_50"]), 6
                            ),
                            "preset": {
                                key: value
                                for key, value in preset.items()
                                if key not in {"variant_id", "mechanism"}
                            },
                        }
                    )
                    break
    return candidates


def _week_sets(lane_payload: dict[str, Any]) -> dict[str, set[str]]:
    week_rows = {
        str(row["week_start"]): row for row in lane_payload.get("week_evidence", [])
    }
    full_weeks = {
        week
        for week, row in week_rows.items()
        if not bool(row.get("is_partial_review_week"))
    }
    return {
        "silent_zero": {
            week
            for week, row in week_rows.items()
            if week in full_weeks and row.get("zero_entry_week") and row.get("silent_week")
        },
        "zero": {
            week
            for week, row in week_rows.items()
            if week in full_weeks and row.get("zero_entry_week")
        },
        "active": {
            week
            for week, row in week_rows.items()
            if week in full_weeks and int(row.get("entry_trades") or 0) > 0
        },
        "full": full_weeks,
    }


def _enrich_candidates(
    *,
    lane_payload: dict[str, Any],
    candidates: list[dict[str, Any]],
    overlap_keys: set[tuple[str, pd.Timestamp]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    week_rows = {
        str(row["week_start"]): row for row in lane_payload.get("week_evidence", [])
    }
    weeks = _week_sets(lane_payload)
    enriched_candidates: list[dict[str, Any]] = []
    regime_counts: Counter[str] = Counter()
    packet_state_counts: Counter[str] = Counter()
    candidate_week_counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    symbol_counts: Counter[str] = Counter()
    silent_hit_weeks: set[str] = set()
    zero_hit_weeks: set[str] = set()
    active_hit_weeks: set[str] = set()
    same_candle_overlap_count = 0
    silent_or_zero_candidate_count = 0
    active_candidate_count = 0

    for candidate in candidates:
        ts = _parse_ts(candidate.get("timestamp"))
        if ts is None:
            continue
        week = _week_start(ts)
        row = week_rows.get(week, {})
        symbol = str(candidate.get("symbol") or "")
        same_candle_overlap = (symbol, ts) in overlap_keys
        same_candle_overlap_count += int(same_candle_overlap)
        in_silent = week in weeks["silent_zero"]
        in_zero = week in weeks["zero"]
        in_active = week in weeks["active"]
        silent_or_zero_candidate_count += int(in_silent or in_zero)
        active_candidate_count += int(in_active)
        if in_silent:
            silent_hit_weeks.add(week)
        if in_zero:
            zero_hit_weeks.add(week)
        if in_active:
            active_hit_weeks.add(week)
        regime = str(row.get("dominant_regime") or "UNKNOWN")
        packet_state = str(row.get("packet_state") or "UNKNOWN")
        regime_counts[regime] += 1
        packet_state_counts[packet_state] += 1
        candidate_week_counts[week] += 1
        side_counts[str(candidate.get("side") or "UNKNOWN")] += 1
        symbol_counts[symbol or "UNKNOWN"] += 1
        enriched = dict(candidate)
        enriched.update(
            {
                "week_start": week,
                "baseline_silent_zero_entry_week": in_silent,
                "baseline_zero_entry_week": in_zero,
                "baseline_active_entry_week": in_active,
                "dominant_regime": regime,
                "packet_state": packet_state,
                "same_symbol_same_candle_promoted_overlap": same_candle_overlap,
            }
        )
        enriched_candidates.append(enriched)

    total = len(enriched_candidates)
    silent_or_zero_ratio = silent_or_zero_candidate_count / total if total else 0.0
    active_ratio = active_candidate_count / total if total else 0.0
    metrics = {
        "candidate_count": total,
        "silent_zero_entry_week_hit_count": len(silent_hit_weeks),
        "zero_entry_week_hit_count": len(zero_hit_weeks),
        "active_entry_week_hit_count": len(active_hit_weeks),
        "silent_or_zero_candidate_count": silent_or_zero_candidate_count,
        "silent_or_zero_candidate_ratio": round(silent_or_zero_ratio, 4),
        "active_week_candidate_count": active_candidate_count,
        "active_week_candidate_ratio": round(active_ratio, 4),
        "same_symbol_same_candle_promoted_overlap_count": same_candle_overlap_count,
        "candidate_count_by_dominant_regime": _counter_to_dict(regime_counts),
        "candidate_count_by_packet_state": _counter_to_dict(packet_state_counts),
        "candidate_count_by_week": _counter_to_dict(candidate_week_counts),
        "candidate_count_by_side": _counter_to_dict(side_counts),
        "candidate_count_by_symbol": _counter_to_dict(symbol_counts),
        "silent_zero_entry_weeks_hit": sorted(silent_hit_weeks),
        "zero_entry_weeks_hit": sorted(zero_hit_weeks),
        "active_entry_weeks_hit": sorted(active_hit_weeks),
    }
    return enriched_candidates, metrics


def _gates(metrics: dict[str, Any]) -> dict[str, bool]:
    total = int(metrics["candidate_count"])
    return {
        "candidate_count_between_3_and_20": 3 <= total <= 20,
        "silent_week_hit_count_gte_3": int(metrics["silent_zero_entry_week_hit_count"]) >= 3,
        "silent_or_zero_candidate_ratio_gte_0p70": (
            float(metrics["silent_or_zero_candidate_ratio"]) >= 0.70
        ),
        "same_symbol_same_candle_overlap_eq_0": (
            int(metrics["same_symbol_same_candle_promoted_overlap_count"]) == 0
        ),
        "active_week_candidate_ratio_lte_0p30": (
            float(metrics["active_week_candidate_ratio"]) <= 0.30
        ),
        "market_timestamp_source_ok": True,
    }


def _variant_rank(summary: dict[str, Any]) -> tuple[Any, ...]:
    gates_pass = all(summary["gates"].values())
    metrics = summary["metrics"]
    return (
        int(gates_pass),
        int(metrics["silent_zero_entry_week_hit_count"]),
        float(metrics["silent_or_zero_candidate_ratio"]),
        -float(metrics["active_week_candidate_ratio"]),
        -int(metrics["same_symbol_same_candle_promoted_overlap_count"]),
        -int(metrics["candidate_count"]),
    )


def evaluate_range_break_retest_probe(
    *,
    lane_payload: dict[str, Any],
    feasibility_payload: dict[str, Any],
    variant_candidates: dict[str, list[dict[str, Any]]],
    presets: list[dict[str, Any]],
    lane_rows: list[dict[str, str]],
    trade_rows: list[dict[str, str]],
) -> dict[str, Any]:
    overlap_keys = _promoted_overlap_keys(lane_rows=lane_rows, trade_rows=trade_rows)
    summaries: list[dict[str, Any]] = []
    for preset in presets:
        variant_id = str(preset["variant_id"])
        enriched_candidates, metrics = _enrich_candidates(
            lane_payload=lane_payload,
            candidates=variant_candidates.get(variant_id, []),
            overlap_keys=overlap_keys,
        )
        gates = _gates(metrics)
        summaries.append(
            {
                "variant_id": variant_id,
                "mechanism": str(preset["mechanism"]),
                "preset": dict(preset),
                "gates": gates,
                "metrics": metrics,
                "candidates": enriched_candidates,
            }
        )

    selected = max(summaries, key=_variant_rank) if summaries else None
    selected_passes = bool(selected and all(selected["gates"].values()))
    verdict = (
        "RANGE_BREAK_RETEST_PROBE_PASS_RESEARCH_PLUGIN_CANDIDATE"
        if selected_passes
        else "RANGE_BREAK_RETEST_PROBE_FAIL_PIVOT_OR_REVIEW"
    )
    artifacts = feasibility_payload.get("primary_window", {}).get("artifacts", {})
    return {
        "schema": "strategy_plugin_weekly_profit_range_break_retest_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "candidate_family": "range_break_retest_frequency_complement",
        "source_lane_schema": lane_payload.get("schema"),
        "source_feasibility_schema": feasibility_payload.get("schema"),
        "source_artifacts": artifacts,
        "method": {
            "entry_timeframe": "4h",
            "range_source": "prior Donchian high/low excluding breakout candle",
            "compression_features": ["donchian_width_cv", "bollinger_bandwidth_pctrank"],
            "expansion_features": ["break_strength_atr", "breakout_close_quality", "adx"],
            "retest_confirmation": (
                "candidate timestamp is the first post-breakout candle within max_retest_bars "
                "that touches or holds the broken boundary and closes outside it"
            ),
            "runtime_inputs": "candle-derived fields only; baseline week labels are diagnostic labels only",
        },
        "variant_count": len(summaries),
        "selected_variant": selected["variant_id"] if selected else None,
        "selected_metrics": selected["metrics"] if selected else {},
        "selected_gates": selected["gates"] if selected else {},
        "recommended": {
            "implement_research_plugin": selected_passes,
            "variant_id": selected["variant_id"] if selected else None,
            "mechanism": selected["mechanism"] if selected else None,
            "selected_candidates": selected["candidates"] if selected else [],
        },
        "variant_summaries": summaries,
        "next_action": (
            "Implement a research-only StrategyPlugin candidate and run A+B+candidate "
            "combined weekly packet evaluation."
            if selected_passes
            else "Do not implement this family yet; pivot to another frequency-complement family."
        ),
    }


def render_report(payload: dict[str, Any]) -> str:
    selected = payload["recommended"]
    metrics = payload["selected_metrics"]
    gates = payload["selected_gates"]
    lines = [
        "# Weekly Profit Phase 4D Range-Break Retest Probe",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Verdict: `{payload['verdict']}`",
        "",
        "## Executive Read",
        "",
    ]
    if selected.get("implement_research_plugin"):
        lines.extend(
            [
                (
                    f"Selected variant `{selected['variant_id']}` hit "
                    f"{metrics['silent_zero_entry_week_hit_count']} silent zero-entry weeks "
                    f"with silent-or-zero ratio `{metrics['silent_or_zero_candidate_ratio']}`."
                ),
                "",
                (
                    "This is a research-plugin candidate, not a runtime promotion. "
                    "The next proof point is A+B+candidate combined weekly packet evaluation."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "No range-break retest variant passed the strict diagnostic gates.",
                "",
                "Do not build a plugin from this family without a new evidence pass.",
            ]
        )
    lines.extend(
        [
            "",
            "## Gate Results",
            "",
            "| gate | pass |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| `{name}` | `{value}` |" for name, value in gates.items())
    lines.extend(
        [
            "",
            "## Selected Metrics",
            "",
            "| metric | value |",
            "| --- | ---: |",
            f"| candidates | {metrics.get('candidate_count', 0)} |",
            f"| silent zero-entry weeks hit | {metrics.get('silent_zero_entry_week_hit_count', 0)} |",
            f"| zero-entry weeks hit | {metrics.get('zero_entry_week_hit_count', 0)} |",
            f"| active-entry weeks hit | {metrics.get('active_entry_week_hit_count', 0)} |",
            f"| silent-or-zero candidate ratio | {metrics.get('silent_or_zero_candidate_ratio', 0)} |",
            f"| active-week candidate ratio | {metrics.get('active_week_candidate_ratio', 0)} |",
            (
                "| same-symbol same-candle promoted overlaps | "
                f"{metrics.get('same_symbol_same_candle_promoted_overlap_count', 0)} |"
            ),
            (
                "| candidates by side | "
                f"`{json.dumps(metrics.get('candidate_count_by_side', {}), sort_keys=True)}` |"
            ),
            (
                "| candidates by symbol | "
                f"`{json.dumps(metrics.get('candidate_count_by_symbol', {}), sort_keys=True)}` |"
            ),
            "",
            "## Variant Comparison",
            "",
            "| variant | candidates | silent weeks | silent/zero ratio | active ratio | overlaps | pass |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for summary in payload["variant_summaries"]:
        summary_metrics = summary["metrics"]
        lines.append(
            f"| `{summary['variant_id']}` | "
            f"{summary_metrics['candidate_count']} | "
            f"{summary_metrics['silent_zero_entry_week_hit_count']} | "
            f"{summary_metrics['silent_or_zero_candidate_ratio']} | "
            f"{summary_metrics['active_week_candidate_ratio']} | "
            f"{summary_metrics['same_symbol_same_candle_promoted_overlap_count']} | "
            f"`{all(summary['gates'].values())}` |"
        )
    lines.extend(
        [
            "",
            "## Week Hits",
            "",
            "| bucket | weeks |",
            "| --- | --- |",
            (
                "| silent zero-entry | "
                f"`{json.dumps(metrics.get('silent_zero_entry_weeks_hit', []))}` |"
            ),
            f"| zero-entry | `{json.dumps(metrics.get('zero_entry_weeks_hit', []))}` |",
            f"| active-entry | `{json.dumps(metrics.get('active_entry_weeks_hit', []))}` |",
            "",
            "## Selected Candidates",
            "",
            "| timestamp | symbol | side | breakout | lag | width_cv | bbw_pct | adx | break_atr | silent/zero | active |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for candidate in selected.get("selected_candidates", []):
        lines.append(
            f"| `{candidate['timestamp']}` | `{candidate['symbol']}` | "
            f"`{candidate['side']}` | `{candidate['breakout_timestamp']}` | "
            f"{candidate['retest_lag_bars']} | {candidate['width_cv']:.4f} | "
            f"{candidate['bbw_pctrank']:.1f} | {candidate['adx']:.2f} | "
            f"{candidate['break_strength_atr']:.4f} | "
            f"`{candidate['baseline_silent_zero_entry_week'] or candidate['baseline_zero_entry_week']}` | "
            f"`{candidate['baseline_active_entry_week']}` |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This is pre-plugin diagnostic evidence only.",
            "- Runtime defaults, promoted strategies, scanner settings, credentials, and risk caps remain unchanged.",
            "- Baseline week labels are used only for offline attribution; the proposed plugin inputs are candle-derived.",
            "",
            "## Next Action",
            "",
            payload["next_action"],
        ]
    )
    return "\n".join(lines) + "\n"


def write_range_break_retest_probe(
    *,
    lane_path: Path = DEFAULT_LANE_JSON,
    feasibility_path: Path = DEFAULT_FEASIBILITY_JSON,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
    presets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    lane_payload = _load_json(lane_path)
    feasibility_payload = _load_json(feasibility_path)
    artifacts = feasibility_payload["primary_window"]["artifacts"]
    artifact_dir = Path(artifacts["trades"]).parent
    market_frames = {
        "BTC/USDT": _load_market_frame("BTC/USDT", start=DEFAULT_START, end=DEFAULT_END),
        "ETH/USDT": _load_market_frame("ETH/USDT", start=DEFAULT_START, end=DEFAULT_END),
    }
    active_presets = list(presets or DEFAULT_PRESETS)
    variant_candidates: dict[str, list[dict[str, Any]]] = {}
    feature_cache: dict[tuple[str, int, int, int], pd.DataFrame] = {}
    for preset in active_presets:
        candidates = generate_range_break_retest_candidates(
            market_frames,
            preset=preset,
            feature_cache=feature_cache,
        )
        variant_candidates[str(preset["variant_id"])] = _filter_candidates_to_window(
            candidates,
            start=DEFAULT_START,
            end=DEFAULT_END,
        )
    payload = evaluate_range_break_retest_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        variant_candidates=variant_candidates,
        presets=active_presets,
        lane_rows=_read_csv(artifact_dir / "lane_race_audit.csv"),
        trade_rows=_read_csv(Path(artifacts["trades"])),
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe range-break retest coverage before plugin implementation."
    )
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE_JSON)
    parser.add_argument("--feasibility", type=Path, default=DEFAULT_FEASIBILITY_JSON)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    payload = write_range_break_retest_probe(
        lane_path=args.lane,
        feasibility_path=args.feasibility,
        json_path=args.json_out,
        report_path=args.report_out,
    )
    print(
        json.dumps(
            {
                "verdict": payload["verdict"],
                "selected_variant": payload["selected_variant"],
                "selected_metrics": payload["selected_metrics"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
