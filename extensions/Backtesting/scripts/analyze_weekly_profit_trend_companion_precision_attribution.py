"""Find precision filters for Phase 4A diagnostic trend-companion candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_DIR = (
    REPO_ROOT
    / "extensions"
    / "Backtesting"
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
)
DEFAULT_LANE_JSON = RESULT_DIR / "weekly_profit_frequency_complement_lane_summary.json"
DEFAULT_SUPERTREND_JSON = (
    RESULT_DIR / "weekly_profit_supertrend_trend_companion_probe_no_1d_gate_summary.json"
)
DEFAULT_AROON_JSON = (
    RESULT_DIR / "weekly_profit_aroon_trend_companion_probe_no_1d_gate_summary.json"
)
DEFAULT_JSON = RESULT_DIR / "weekly_profit_trend_companion_precision_attribution_summary.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4a_trend_companion_precision_attribution.md"


@dataclass(frozen=True)
class FilterSpec:
    filter_id: str
    mechanisms: tuple[str, ...]
    symbols: tuple[str, ...]
    ema_spread_min: float | None = None
    ema_spread_max: float | None = None
    distance_atr_max: float | None = None
    atr_pct_min: float | None = None
    rank_policy: str = "none"
    rationale: str = ""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _derive_candidate(candidate: dict[str, Any], full_weeks: set[str]) -> dict[str, Any] | None:
    week = str(candidate.get("week_start") or "")
    if week not in full_weeks:
        return None
    ts = _parse_ts(candidate.get("timestamp"))
    if ts is None:
        return None
    out = dict(candidate)
    entry_price = float(out["entry_price"])
    atr = float(out["atr_4h"])
    if out["mechanism"].startswith("supertrend"):
        distance_atr = (entry_price - float(out["supertrend"])) / atr
    else:
        distance_atr = (entry_price - float(out["prior_swing_high"])) / atr
    out["distance_atr"] = float(distance_atr)
    out["atr_pct"] = float(atr / entry_price) if entry_price else None
    out["hour_utc"] = int(ts.hour)
    out["weekday_utc"] = int(ts.dayofweek)
    out["precision_target"] = bool(
        out.get("baseline_silent_zero_entry_week")
        or out.get("baseline_zero_entry_week")
    )
    return out


def load_candidates(
    *,
    lane_payload: dict[str, Any],
    probe_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    full_weeks = {
        str(row["week_start"])
        for row in lane_payload.get("week_evidence", [])
        if not bool(row.get("is_partial_review_week"))
    }
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for payload in probe_payloads:
        for raw in payload.get("candidates", []):
            candidate = _derive_candidate(raw, full_weeks)
            if candidate is None:
                continue
            key = (
                str(candidate["timestamp"]),
                str(candidate["symbol"]),
                str(candidate["mechanism"]),
            )
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
    return sorted(
        candidates,
        key=lambda row: (row["week_start"], row["timestamp"], row["symbol"], row["mechanism"]),
    )


def _first_per(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: str(item["timestamp"])):
        key = tuple(row[k] for k in keys)
        selected.setdefault(key, row)
    return list(selected.values())


def apply_filter(candidates: list[dict[str, Any]], spec: FilterSpec) -> list[dict[str, Any]]:
    rows = []
    for row in candidates:
        if row["mechanism"] not in spec.mechanisms:
            continue
        if row["symbol"] not in spec.symbols:
            continue
        ema = row.get("ema_spread_1d")
        if ema is None:
            continue
        ema = float(ema)
        if spec.ema_spread_min is not None and ema < spec.ema_spread_min:
            continue
        if spec.ema_spread_max is not None and ema > spec.ema_spread_max:
            continue
        if spec.distance_atr_max is not None and float(row["distance_atr"]) > spec.distance_atr_max:
            continue
        if spec.atr_pct_min is not None and float(row["atr_pct"]) < spec.atr_pct_min:
            continue
        rows.append(row)

    if spec.rank_policy == "first_per_week":
        return _first_per(rows, ("week_start",))
    if spec.rank_policy == "first_per_week_symbol":
        return _first_per(rows, ("week_start", "symbol"))
    if spec.rank_policy == "first_per_week_mechanism_symbol":
        return _first_per(rows, ("week_start", "mechanism", "symbol"))
    return rows


def score_rows(
    rows: list[dict[str, Any]],
    *,
    full_week_count: int,
    baseline_active_week_count: int,
) -> dict[str, Any]:
    positives = [row for row in rows if row["precision_target"]]
    silent_weeks = sorted(
        {
            str(row["week_start"])
            for row in positives
            if row.get("baseline_silent_zero_entry_week")
        }
    )
    active_weeks = sorted(
        {
            str(row["week_start"])
            for row in rows
            if row.get("baseline_active_entry_week")
        }
    )
    overlap_count = sum(
        1 for row in rows if bool(row.get("same_symbol_same_candle_promoted_overlap"))
    )
    candidate_count = len(rows)
    positive_count = len(positives)
    projected_active_week_count = baseline_active_week_count + len(silent_weeks)
    return {
        "candidate_count": candidate_count,
        "silent_or_zero_candidate_count": positive_count,
        "silent_or_zero_candidate_ratio": round(
            positive_count / candidate_count, 4
        )
        if candidate_count
        else 0.0,
        "silent_zero_entry_week_hit_count": len(silent_weeks),
        "silent_zero_entry_weeks_hit": silent_weeks,
        "active_week_candidate_count": sum(
            1 for row in rows if row.get("baseline_active_entry_week")
        ),
        "active_week_candidate_ratio": round(
            sum(1 for row in rows if row.get("baseline_active_entry_week"))
            / candidate_count,
            4,
        )
        if candidate_count
        else 0.0,
        "active_entry_weeks_touched": active_weeks,
        "same_symbol_same_candle_promoted_overlap_count": overlap_count,
        "projected_full_active_entry_week_count": projected_active_week_count,
        "projected_full_active_entry_week_ratio": round(
            projected_active_week_count / full_week_count, 4
        )
        if full_week_count
        else 0.0,
    }


def _filter_to_dict(spec: FilterSpec) -> dict[str, Any]:
    return {
        "filter_id": spec.filter_id,
        "mechanisms": list(spec.mechanisms),
        "symbols": list(spec.symbols),
        "ema_spread_min": spec.ema_spread_min,
        "ema_spread_max": spec.ema_spread_max,
        "distance_atr_max": spec.distance_atr_max,
        "atr_pct_min": spec.atr_pct_min,
        "rank_policy": spec.rank_policy,
        "rationale": spec.rationale,
    }


def build_filter_specs() -> list[FilterSpec]:
    supertrend = "supertrend_flip_4h_trending_up_frequency_companion"
    aroon = "aroon_break_hh_4h_trending_up_frequency_companion"
    return [
        FilterSpec(
            filter_id="btc_recovery_band_trend_breadth",
            mechanisms=(supertrend, aroon),
            symbols=("BTC/USDT",),
            ema_spread_min=-0.08,
            ema_spread_max=-0.01,
            distance_atr_max=3.0,
            rationale=(
                "BTC-only trend recovery band: daily EMA spread is still negative "
                "but no longer panic-deep, and entry is not more than 3 ATR away "
                "from the mechanism anchor."
            ),
        ),
        FilterSpec(
            filter_id="supertrend_deep_recovery_precision",
            mechanisms=(supertrend,),
            symbols=("BTC/USDT", "ETH/USDT"),
            ema_spread_min=-0.12,
            ema_spread_max=-0.06,
            rationale=(
                "Single-mechanism conservative SuperTrend recovery filter with "
                "high precision but lower candidate count."
            ),
        ),
        FilterSpec(
            filter_id="supertrend_deep_recovery_first_week",
            mechanisms=(supertrend,),
            symbols=("BTC/USDT", "ETH/USDT"),
            ema_spread_min=-0.12,
            ema_spread_max=-0.06,
            rank_policy="first_per_week",
            rationale="Same recovery band, capped to the first signal per week.",
        ),
        FilterSpec(
            filter_id="btc_recovery_band_first_week",
            mechanisms=(supertrend, aroon),
            symbols=("BTC/USDT",),
            ema_spread_min=-0.08,
            ema_spread_max=-0.01,
            distance_atr_max=3.0,
            rank_policy="first_per_week",
            rationale="Frequency-balanced BTC recovery band capped to first weekly signal.",
        ),
    ]


def _feature_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_keys = ["ema_spread_1d", "atr_pct", "distance_atr"]
    summary: dict[str, Any] = {"count": len(rows)}
    for key in numeric_keys:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        if values:
            summary[key] = {
                "min": round(min(values), 4),
                "median": round(median(values), 4),
                "max": round(max(values), 4),
            }
    summary["symbols"] = dict(Counter(str(row["symbol"]) for row in rows))
    summary["mechanisms"] = dict(Counter(str(row["mechanism"]) for row in rows))
    return summary


def build_feature_attribution(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    silent = [row for row in candidates if row["precision_target"]]
    active = [row for row in candidates if row.get("baseline_active_entry_week")]
    by_mechanism: dict[str, Any] = {}
    for mechanism in sorted({str(row["mechanism"]) for row in candidates}):
        rows = [row for row in candidates if row["mechanism"] == mechanism]
        by_mechanism[mechanism] = {
            "silent_or_zero": _feature_summary(
                [row for row in rows if row["precision_target"]]
            ),
            "active_spillover": _feature_summary(
                [row for row in rows if row.get("baseline_active_entry_week")]
            ),
        }
    return {
        "silent_or_zero": _feature_summary(silent),
        "active_spillover": _feature_summary(active),
        "by_mechanism": by_mechanism,
    }


def analyze_precision_attribution(
    *,
    lane_payload: dict[str, Any],
    probe_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = load_candidates(lane_payload=lane_payload, probe_payloads=probe_payloads)
    full_weeks = [
        row
        for row in lane_payload.get("week_evidence", [])
        if not bool(row.get("is_partial_review_week"))
    ]
    full_week_count = len(full_weeks)
    baseline_active_week_count = sum(
        1 for row in full_weeks if int(row.get("entry_trades") or 0) > 0
    )

    evaluated = []
    for spec in build_filter_specs():
        selected = apply_filter(candidates, spec)
        metrics = score_rows(
            selected,
            full_week_count=full_week_count,
            baseline_active_week_count=baseline_active_week_count,
        )
        metrics["passes_precision_contract"] = (
            metrics["silent_or_zero_candidate_ratio"] >= 0.70
            and metrics["silent_zero_entry_week_hit_count"] >= 3
            and metrics["same_symbol_same_candle_promoted_overlap_count"] == 0
        )
        evaluated.append(
            {
                "filter": _filter_to_dict(spec),
                "metrics": metrics,
                "selected_candidates": selected,
            }
        )

    passing = [
        item for item in evaluated if item["metrics"]["passes_precision_contract"]
    ]
    passing.sort(
        key=lambda item: (
            -item["metrics"]["silent_zero_entry_week_hit_count"],
            -item["metrics"]["silent_or_zero_candidate_ratio"],
            -item["metrics"]["candidate_count"],
        )
    )
    recommended = passing[0] if passing else None
    return {
        "schema": "strategy_plugin_weekly_profit_trend_companion_precision_attribution.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": (
            "PRECISION_FILTER_FOUND_REQUIRES_PLUGIN_BACKTEST"
            if recommended
            else "NO_PRECISION_FILTER_FOUND"
        ),
        "baseline": {
            "full_week_count": full_week_count,
            "baseline_active_week_count": baseline_active_week_count,
            "baseline_active_week_ratio": round(
                baseline_active_week_count / full_week_count, 4
            )
            if full_week_count
            else 0.0,
        },
        "candidate_pool": {
            "candidate_count": len(candidates),
            "full_week_only": True,
            "source": "diagnostic_no_1d_ema probes with runtime-parity daily EMA features",
        },
        "feature_attribution": build_feature_attribution(candidates),
        "recommended": recommended,
        "evaluated_filters": evaluated,
        "implementation_notes": [
            "This is a pre-plugin precision filter, not runtime promotion.",
            "The filter uses only candle-derived fields available to a plugin: symbol, mechanism trigger, completed 1d EMA spread, and ATR-normalized distance.",
            "Completed 1d EMA spread is computed with the same rolling 1d snapshot semantics used by StrategyRuntime backtests.",
            "It does not use packet_state, baseline week labels, or promoted strategy outcomes as runtime inputs.",
            "Next step is a StrategyPlugin candidate plus A+B+candidate combined weekly packet evaluation.",
        ],
    }


def _fmt_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_report(summary: dict[str, Any]) -> str:
    recommended = summary.get("recommended")
    lines = [
        "# Weekly Profit Phase 4A Trend Companion Precision Attribution",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Verdict: `{summary['verdict']}`",
        "",
        "## Executive Read",
        "",
    ]
    if recommended:
        f = recommended["filter"]
        m = recommended["metrics"]
        lines.extend(
            [
                (
                    f"Recommended filter: `{f['filter_id']}`. It keeps "
                    f"{m['silent_or_zero_candidate_count']} / {m['candidate_count']} "
                    "candidates on baseline silent-or-zero weeks and hits "
                    f"{m['silent_zero_entry_week_hit_count']} silent zero-entry weeks."
                ),
                "",
                (
                    "Projected active full weeks move from "
                    f"{summary['baseline']['baseline_active_week_count']} / "
                    f"{summary['baseline']['full_week_count']} to "
                    f"{m['projected_full_active_entry_week_count']} / "
                    f"{summary['baseline']['full_week_count']} if candidate entries "
                    "survive combined backtest routing and position constraints."
                ),
            ]
        )
    else:
        lines.append("No candidate filter met the precision contract.")
    lines.extend(
        [
            "",
            "## Evaluated Filters",
            "",
            "| filter | candidates | silent/zero ratio | silent weeks hit | active ratio | overlaps | pass |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in summary["evaluated_filters"]:
        f = item["filter"]
        m = item["metrics"]
        lines.append(
            f"| `{f['filter_id']}` | {m['candidate_count']} | "
            f"{_fmt_metric(m['silent_or_zero_candidate_ratio'])} | "
            f"{m['silent_zero_entry_week_hit_count']} | "
            f"{_fmt_metric(m['active_week_candidate_ratio'])} | "
            f"{m['same_symbol_same_candle_promoted_overlap_count']} | "
            f"`{m['passes_precision_contract']}` |"
        )
    if recommended:
        f = recommended["filter"]
        m = recommended["metrics"]
        lines.extend(
            [
                "",
                "## Recommended Filter",
                "",
                "| field | value |",
                "| --- | --- |",
                f"| filter id | `{f['filter_id']}` |",
                f"| mechanisms | `{json.dumps(f['mechanisms'])}` |",
                f"| symbols | `{json.dumps(f['symbols'])}` |",
                f"| ema spread band | `{f['ema_spread_min']} <= ema_spread_1d <= {f['ema_spread_max']}` |",
                f"| distance cap | `distance_atr <= {f['distance_atr_max']}` |",
                f"| rank policy | `{f['rank_policy']}` |",
                f"| rationale | {f['rationale']} |",
                "",
                "## Selected Candidate Weeks",
                "",
                "| bucket | weeks |",
                "| --- | --- |",
                (
                    "| silent zero-entry | "
                    f"`{json.dumps(m['silent_zero_entry_weeks_hit'])}` |"
                ),
                f"| active spillover | `{json.dumps(m['active_entry_weeks_touched'])}` |",
                "",
                "## Selected Candidates",
                "",
                "| timestamp | symbol | mechanism | silent/zero | active | ema_spread_1d | distance_atr |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in recommended["selected_candidates"]:
            lines.append(
                f"| `{row['timestamp']}` | `{row['symbol']}` | "
                f"`{row['mechanism']}` | `{row['precision_target']}` | "
                f"`{bool(row.get('baseline_active_entry_week'))}` | "
                f"{float(row['ema_spread_1d']):.4f} | {float(row['distance_atr']):.3f} |"
            )
    attr = summary["feature_attribution"]
    lines.extend(
        [
            "",
            "## Attribution Read",
            "",
            (
                "The useful candidates cluster in a recovery band where completed 1d "
                "EMA spread is negative, but not panic-deep. This is not a classic "
                "daily trend-continuation entry; it is a 4h bullish recovery trigger "
                "inside a still-negative daily spread."
            ),
            "",
            "| group | count | ema_spread median | distance_atr median |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for label in ["silent_or_zero", "active_spillover"]:
        row = attr[label]
        ema = row.get("ema_spread_1d", {}).get("median", "n/a")
        dist = row.get("distance_atr", {}).get("median", "n/a")
        lines.append(f"| `{label}` | {row['count']} | {ema} | {dist} |")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in summary["implementation_notes"])
    return "\n".join(lines) + "\n"


def write_precision_attribution(
    *,
    lane_path: Path = DEFAULT_LANE_JSON,
    supertrend_path: Path = DEFAULT_SUPERTREND_JSON,
    aroon_path: Path = DEFAULT_AROON_JSON,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    summary = analyze_precision_attribution(
        lane_payload=_load_json(lane_path),
        probe_payloads=[_load_json(supertrend_path), _load_json(aroon_path)],
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze precision filters for trend-companion diagnostic candidates."
    )
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE_JSON)
    parser.add_argument("--supertrend", type=Path, default=DEFAULT_SUPERTREND_JSON)
    parser.add_argument("--aroon", type=Path, default=DEFAULT_AROON_JSON)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    write_precision_attribution(
        lane_path=args.lane,
        supertrend_path=args.supertrend,
        aroon_path=args.aroon,
        json_path=args.json_out,
        report_path=args.report_out,
    )


if __name__ == "__main__":
    main()
