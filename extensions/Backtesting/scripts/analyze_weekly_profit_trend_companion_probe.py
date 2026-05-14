"""Probe Phase 4A trend-companion coverage before plugin implementation."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trader.indicators.registry import IndicatorRegistry

BACKTEST_ROOT = REPO_ROOT / "extensions" / "Backtesting"
CACHE_DIR = BACKTEST_ROOT / "cache"
RESULT_DIR = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
)
DEFAULT_LANE_JSON = RESULT_DIR / "weekly_profit_frequency_complement_lane_summary.json"
DEFAULT_FEASIBILITY_JSON = RESULT_DIR / "promoted_three_leg_weekly_feasibility_summary.json"
DEFAULT_JSON = RESULT_DIR / "weekly_profit_trend_companion_probe_summary.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4a_trend_companion_probe.md"
DEFAULT_AROON_JSON = RESULT_DIR / "weekly_profit_aroon_trend_companion_probe_summary.json"
DEFAULT_AROON_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4a_aroon_trend_companion_probe.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_ts(value: Any) -> pd.Timestamp | None:
    if value in (None, "", "n/a"):
        return None
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _iso(ts: pd.Timestamp | None) -> str | None:
    if ts is None:
        return None
    return ts.isoformat().replace("+00:00", "Z")


def _float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _week_start(ts: pd.Timestamp) -> str:
    start = ts.normalize() - pd.Timedelta(days=int(ts.dayofweek))
    return start.date().isoformat()


def _parse_compact_date(value: str) -> pd.Timestamp:
    return pd.Timestamp(datetime.strptime(value, "%Y%m%d"), tz="UTC")


def _load_market_frame(symbol: str, *, start: str, end: str) -> pd.DataFrame:
    cache_name = f"{symbol.replace('/', '').replace('USDT', 'USDT')}_4h_{start}_{end}.parquet"
    path = CACHE_DIR / cache_name
    if not path.exists():
        raise FileNotFoundError(f"missing 4h cache for {symbol}: {path}")
    frames = []
    symbol_prefix = symbol.replace("/", "")
    target_start = _parse_compact_date(start)
    for candidate in sorted(CACHE_DIR.glob(f"{symbol_prefix}_4h_*.parquet")):
        parts = candidate.stem.split("_")
        if len(parts) < 4:
            continue
        candidate_end = _parse_compact_date(parts[-1])
        if candidate_end < target_start:
            frames.append(pd.read_parquet(candidate))
    frames.append(pd.read_parquet(path))
    frame = pd.concat(frames).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    else:
        frame.index = frame.index.tz_convert("UTC")
    return frame


def _filter_candidates_to_window(
    candidates: list[dict[str, Any]], *, start: str, end: str
) -> list[dict[str, Any]]:
    start_ts = _parse_compact_date(start)
    end_exclusive = _parse_compact_date(end) + pd.Timedelta(days=1)
    filtered = []
    for candidate in candidates:
        ts = _parse_ts(candidate.get("timestamp"))
        if ts is not None and start_ts <= ts < end_exclusive:
            filtered.append(candidate)
    return filtered


def _completed_daily_gate(frame: pd.DataFrame) -> pd.DataFrame:
    daily = frame.resample("1D", label="left", closed="left").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    daily = daily.dropna(subset=["open", "high", "low", "close"])
    daily = IndicatorRegistry.apply(daily, {"ema"})
    gate = daily[["ema_20", "ema_50"]].shift(1)
    return gate


def generate_supertrend_flip_candidates(
    market_frames: dict[str, pd.DataFrame],
    *,
    trend_spread_min: float = 0.005,
    require_trend_gate: bool = True,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for symbol, raw in sorted(market_frames.items()):
        frame = IndicatorRegistry.apply(raw, {"supertrend", "atr"}).sort_index()
        daily_gate = _completed_daily_gate(raw)
        aligned_gate = daily_gate.reindex(frame.index, method="ffill")
        enriched = frame.join(aligned_gate, rsuffix="_1d")
        prev_direction = enriched["supertrend_direction"].shift(1)
        ema_spread = (enriched["ema_20"] - enriched["ema_50"]) / enriched["ema_50"]
        trend_gate = (
            (enriched["ema_20"] > enriched["ema_50"])
            & (ema_spread >= trend_spread_min)
        )
        mask = (
            (prev_direction <= -1)
            & (enriched["supertrend_direction"] == 1)
            & enriched["atr"].notna()
            & (enriched["atr"] > 0)
        )
        if require_trend_gate:
            mask = mask & trend_gate
        for ts, row in enriched.loc[mask].iterrows():
            candidates.append(
                {
                    "timestamp": _iso(pd.Timestamp(ts)),
                    "symbol": symbol,
                    "side": "LONG",
                    "candidate_family": "trend_dominant_silent_week_companion",
                    "mechanism": "supertrend_flip_4h_trending_up_frequency_companion",
                    "entry_timeframe": "4h",
                    "entry_price": float(row["close"]),
                    "atr_4h": float(row["atr"]),
                    "supertrend": float(row["supertrend"]),
                    "trend_gate_mode": (
                        "strict_1d_ema" if require_trend_gate else "diagnostic_no_1d_ema"
                    ),
                    "trend_gate_pass": bool(trend_gate.loc[ts]),
                    "ema_spread_1d": _float_or_none(ema_spread.loc[ts]),
                }
            )
    return candidates


def _aroon(frame: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series]:
    highs = frame["high"].tolist()
    lows = frame["low"].tolist()
    index = frame.index
    aroon_up = pd.Series(index=index, dtype="float64")
    aroon_down = pd.Series(index=index, dtype="float64")
    for i in range(period - 1, len(frame)):
        high_window = highs[i - period + 1 : i + 1]
        low_window = lows[i - period + 1 : i + 1]
        high_pos = max(range(period), key=lambda pos: high_window[pos])
        low_pos = min(range(period), key=lambda pos: low_window[pos])
        bars_since_high = period - 1 - high_pos
        bars_since_low = period - 1 - low_pos
        aroon_up.iloc[i] = ((period - bars_since_high) / period) * 100.0
        aroon_down.iloc[i] = ((period - bars_since_low) / period) * 100.0
    return aroon_up, aroon_down


def generate_aroon_break_candidates(
    market_frames: dict[str, pd.DataFrame],
    *,
    trend_spread_min: float = 0.005,
    aroon_period: int = 14,
    swing_lookback: int = 20,
    require_trend_gate: bool = True,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for symbol, raw in sorted(market_frames.items()):
        frame = IndicatorRegistry.apply(raw, {"atr"}).sort_index()
        aroon_up, aroon_down = _aroon(frame, period=aroon_period)
        daily_gate = _completed_daily_gate(raw)
        aligned_gate = daily_gate.reindex(frame.index, method="ffill")
        enriched = frame.join(aligned_gate, rsuffix="_1d")
        enriched["aroon_up"] = aroon_up
        enriched["aroon_down"] = aroon_down
        prior_swing_high = enriched["high"].shift(1).rolling(swing_lookback).max()
        ema_spread = (enriched["ema_20"] - enriched["ema_50"]) / enriched["ema_50"]
        trend_gate = (
            (enriched["ema_20"] > enriched["ema_50"])
            & (ema_spread >= trend_spread_min)
        )
        mask = (
            (enriched["aroon_up"] > 70.0)
            & (enriched["aroon_down"] < 30.0)
            & (enriched["close"] > prior_swing_high)
            & enriched["atr"].notna()
            & (enriched["atr"] > 0)
        )
        if require_trend_gate:
            mask = mask & trend_gate
        for ts, row in enriched.loc[mask].iterrows():
            candidates.append(
                {
                    "timestamp": _iso(pd.Timestamp(ts)),
                    "symbol": symbol,
                    "side": "LONG",
                    "candidate_family": "trend_dominant_silent_week_companion",
                    "mechanism": "aroon_break_hh_4h_trending_up_frequency_companion",
                    "entry_timeframe": "4h",
                    "entry_price": float(row["close"]),
                    "atr_4h": float(row["atr"]),
                    "aroon_up": float(row["aroon_up"]),
                    "aroon_down": float(row["aroon_down"]),
                    "prior_swing_high": float(prior_swing_high.loc[ts]),
                    "trend_gate_mode": (
                        "strict_1d_ema" if require_trend_gate else "diagnostic_no_1d_ema"
                    ),
                    "trend_gate_pass": bool(trend_gate.loc[ts]),
                    "ema_spread_1d": _float_or_none(ema_spread.loc[ts]),
                }
            )
    return candidates


def _promoted_overlap_keys(
    *,
    lane_rows: list[dict[str, str]],
    trade_rows: list[dict[str, str]],
) -> set[tuple[str, pd.Timestamp]]:
    keys: set[tuple[str, pd.Timestamp]] = set()
    for row in lane_rows:
        ts = _parse_ts(row.get("timestamp"))
        symbol = row.get("symbol")
        if ts is not None and symbol:
            keys.add((symbol, ts))
    for row in trade_rows:
        symbol = row.get("symbol")
        ts = _parse_ts(row.get("entry_regime_candle_time") or row.get("entry_time"))
        if ts is not None and symbol:
            keys.add((symbol, ts.floor("4h")))
    return keys


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(counter.items())}


def evaluate_trend_companion_probe(
    *,
    lane_payload: dict[str, Any],
    feasibility_payload: dict[str, Any],
    candidates: list[dict[str, Any]],
    lane_rows: list[dict[str, str]],
    trade_rows: list[dict[str, str]],
    mechanism: str = "supertrend_flip_4h_trending_up_frequency_companion",
    implementation_eligible: bool = True,
) -> dict[str, Any]:
    week_rows = {
        str(row["week_start"]): row for row in lane_payload.get("week_evidence", [])
    }
    full_weeks = {
        week
        for week, row in week_rows.items()
        if not bool(row.get("is_partial_review_week"))
    }
    silent_zero_weeks = {
        week
        for week, row in week_rows.items()
        if week in full_weeks and row.get("zero_entry_week") and row.get("silent_week")
    }
    zero_weeks = {
        week
        for week, row in week_rows.items()
        if week in full_weeks and row.get("zero_entry_week")
    }
    active_weeks = {
        week
        for week, row in week_rows.items()
        if week in full_weeks and int(row.get("entry_trades") or 0) > 0
    }
    overlap_keys = _promoted_overlap_keys(lane_rows=lane_rows, trade_rows=trade_rows)

    enriched_candidates: list[dict[str, Any]] = []
    regime_counts: Counter[str] = Counter()
    packet_state_counts: Counter[str] = Counter()
    candidate_week_counts: Counter[str] = Counter()
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
        key = (str(candidate.get("symbol")), ts)
        same_candle_overlap = key in overlap_keys
        same_candle_overlap_count += int(same_candle_overlap)
        in_silent = week in silent_zero_weeks
        in_zero = week in zero_weeks
        in_active = week in active_weeks
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
    gates = {
        "silent_week_hit_count_gte_3": len(silent_hit_weeks) >= 3,
        "silent_or_zero_candidate_ratio_gte_0p70": silent_or_zero_ratio >= 0.70,
        "same_symbol_same_candle_overlap_eq_0": same_candle_overlap_count == 0,
        "active_week_candidate_ratio_lte_0p30": active_ratio <= 0.30,
        "market_timestamp_source_ok": True,
    }
    mechanism_prefix = (
        "AROON" if mechanism.startswith("aroon_") else "SUPER_TREND"
    )
    if all(gates.values()) and implementation_eligible:
        verdict = f"{mechanism_prefix}_PROBE_PASS_IMPLEMENT_PLUGIN"
    elif all(gates.values()):
        verdict = f"{mechanism_prefix}_PROBE_DIAGNOSTIC_PASS_REQUIRES_CONTRACT_UPDATE"
    else:
        verdict = f"{mechanism_prefix}_PROBE_FAIL_PIVOT_OR_REVIEW"
    artifacts = feasibility_payload.get("primary_window", {}).get("artifacts", {})
    return {
        "schema": "strategy_plugin_weekly_profit_trend_companion_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "candidate_family": "trend_dominant_silent_week_companion",
        "mechanism": mechanism,
        "trend_gate_mode": (
            "strict_1d_ema" if implementation_eligible else "diagnostic_no_1d_ema"
        ),
        "implementation_eligible": implementation_eligible,
        "source_lane_schema": lane_payload.get("schema"),
        "source_feasibility_schema": feasibility_payload.get("schema"),
        "source_artifacts": artifacts,
        "metrics": {
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
            "silent_zero_entry_weeks_hit": sorted(silent_hit_weeks),
            "zero_entry_weeks_hit": sorted(zero_hit_weeks),
            "active_entry_weeks_hit": sorted(active_hit_weeks),
        },
        "gates": gates,
        "next_action": (
            "Implement the research plugin only if the strict verdict passes. Diagnostic "
            "passes require a contract update and strict review before plugin work."
        ),
        "candidates": enriched_candidates,
    }


def render_report(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    gates = summary["gates"]
    lines = [
        "# Weekly Profit Phase 4A Trend Companion Probe",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Verdict: `{summary['verdict']}`",
        f"Trend gate mode: `{summary['trend_gate_mode']}`",
        "",
        "## Executive Read",
        "",
        (
            f"`{summary['mechanism']}` generated {metrics['candidate_count']} "
            f"synthetic candidates and hit {metrics['silent_zero_entry_week_hit_count']} "
            "silent zero-entry weeks."
        ),
        "",
        "This probe is pre-plugin evidence only. It does not change runtime defaults.",
        "",
        "## Gate Results",
        "",
        "| gate | pass |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{name}` | `{value}` |" for name, value in gates.items())
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| metric | value |",
            "| --- | ---: |",
            f"| candidates | {metrics['candidate_count']} |",
            f"| silent zero-entry weeks hit | {metrics['silent_zero_entry_week_hit_count']} |",
            f"| zero-entry weeks hit | {metrics['zero_entry_week_hit_count']} |",
            f"| active-entry weeks hit | {metrics['active_entry_week_hit_count']} |",
            f"| silent-or-zero candidate ratio | {metrics['silent_or_zero_candidate_ratio']} |",
            f"| active-week candidate ratio | {metrics['active_week_candidate_ratio']} |",
            (
                "| same-symbol same-candle promoted overlaps | "
                f"{metrics['same_symbol_same_candle_promoted_overlap_count']} |"
            ),
            (
                "| candidates by dominant regime | "
                f"`{json.dumps(metrics['candidate_count_by_dominant_regime'], sort_keys=True)}` |"
            ),
            (
                "| candidates by packet state | "
                f"`{json.dumps(metrics['candidate_count_by_packet_state'], sort_keys=True)}` |"
            ),
            "",
            "## Week Hits",
            "",
            "| bucket | weeks |",
            "| --- | --- |",
            (
                "| silent zero-entry | "
                f"`{json.dumps(metrics['silent_zero_entry_weeks_hit'])}` |"
            ),
            f"| zero-entry | `{json.dumps(metrics['zero_entry_weeks_hit'])}` |",
            f"| active-entry | `{json.dumps(metrics['active_entry_weeks_hit'])}` |",
            "",
            "## Next Action",
            "",
            summary["next_action"],
        ]
    )
    return "\n".join(lines) + "\n"


def write_trend_companion_probe(
    *,
    lane_path: Path = DEFAULT_LANE_JSON,
    feasibility_path: Path = DEFAULT_FEASIBILITY_JSON,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
    mechanism: str = "supertrend",
    trend_gate_mode: str = "strict_1d_ema",
) -> dict[str, Any]:
    lane_payload = _load_json(lane_path)
    feasibility_payload = _load_json(feasibility_path)
    artifacts = feasibility_payload["primary_window"]["artifacts"]
    artifact_dir = Path(artifacts["trades"]).parent
    market_frames = {
        "BTC/USDT": _load_market_frame("BTC/USDT", start="20260101", end="20260430"),
        "ETH/USDT": _load_market_frame("ETH/USDT", start="20260101", end="20260430"),
    }
    require_trend_gate = trend_gate_mode == "strict_1d_ema"
    implementation_eligible = require_trend_gate
    if mechanism == "aroon":
        candidates = generate_aroon_break_candidates(
            market_frames, require_trend_gate=require_trend_gate
        )
        mechanism_id = "aroon_break_hh_4h_trending_up_frequency_companion"
    elif mechanism == "supertrend":
        candidates = generate_supertrend_flip_candidates(
            market_frames, require_trend_gate=require_trend_gate
        )
        mechanism_id = "supertrend_flip_4h_trending_up_frequency_companion"
    else:
        raise ValueError(f"unknown mechanism: {mechanism}")
    candidates = _filter_candidates_to_window(
        candidates, start="20260101", end="20260430"
    )
    summary = evaluate_trend_companion_probe(
        lane_payload=lane_payload,
        feasibility_payload=feasibility_payload,
        candidates=candidates,
        lane_rows=_read_csv(artifact_dir / "lane_race_audit.csv"),
        trade_rows=_read_csv(Path(artifacts["trades"])),
        mechanism=mechanism_id,
        implementation_eligible=implementation_eligible,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe trend-companion coverage before plugin implementation."
    )
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE_JSON)
    parser.add_argument("--feasibility", type=Path, default=DEFAULT_FEASIBILITY_JSON)
    parser.add_argument("--mechanism", choices=["supertrend", "aroon"], default="supertrend")
    parser.add_argument(
        "--trend-gate-mode",
        choices=["strict_1d_ema", "diagnostic_no_1d_ema"],
        default="strict_1d_ema",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--report-out", type=Path)
    args = parser.parse_args()
    if args.json_out is not None:
        json_path = args.json_out
    elif args.trend_gate_mode == "diagnostic_no_1d_ema":
        json_path = RESULT_DIR / f"weekly_profit_{args.mechanism}_trend_companion_probe_no_1d_gate_summary.json"
    else:
        json_path = DEFAULT_AROON_JSON if args.mechanism == "aroon" else DEFAULT_JSON
    if args.report_out is not None:
        report_path = args.report_out
    elif args.trend_gate_mode == "diagnostic_no_1d_ema":
        report_path = REPO_ROOT / "reports" / f"weekly_profit_phase4a_{args.mechanism}_trend_companion_probe_no_1d_gate.md"
    else:
        report_path = DEFAULT_AROON_REPORT if args.mechanism == "aroon" else DEFAULT_REPORT
    write_trend_companion_probe(
        lane_path=args.lane,
        feasibility_path=args.feasibility,
        json_path=json_path,
        report_path=report_path,
        mechanism=args.mechanism,
        trend_gate_mode=args.trend_gate_mode,
    )


if __name__ == "__main__":
    main()
