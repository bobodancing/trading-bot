"""Build the Phase 4A frequency-complement lane spec from weekly packets."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = SCRIPT_ROOT.parents[0]
REPO_ROOT = BACKTEST_ROOT.parents[1]
for path in (SCRIPT_ROOT, BACKTEST_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from build_weekly_profit_control_packet import DEFAULT_JSON as DEFAULT_PACKET_JSON  # noqa: E402
from analyze_promoted_three_leg_weekly_feasibility import (  # noqa: E402
    DEFAULT_JSON as DEFAULT_FEASIBILITY_JSON,
)


DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_frequency_complement_lane_summary.json"
)
DEFAULT_SPEC = REPO_ROOT / "plans" / "weekly_profit_phase4a_frequency_complement_lane_spec.md"
PARTICIPATION_TRIGGERS = {
    "active_entry_week_ratio_8w",
    "rolling_8w_entry_trade_count",
    "zero_entry_week_streak",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _fmt(value: Any, *, places: int = 4) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{places}f}"
    if value is None:
        return "null"
    return str(value)


def _parse_ts(raw: Any) -> datetime | None:
    if not raw or str(raw) == "n/a":
        return None
    value = str(raw).replace("Z", "+00:00")
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        try:
            ts = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _week_start_for_ts(raw: Any) -> str | None:
    ts = _parse_ts(raw)
    if ts is None:
        return None
    week_start = ts.date() - timedelta(days=ts.date().weekday())
    return week_start.isoformat()


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: int(counter[key]) for key in sorted(counter)}


def _counter_to_pct(counter: Counter[str]) -> dict[str, float]:
    total = sum(counter.values())
    if not total:
        return {}
    return {key: round(counter[key] / total, 4) for key in sorted(counter)}


def _dominant(counter: Counter[str]) -> str:
    if not counter:
        return "UNKNOWN"
    return counter.most_common(1)[0][0]


def _packet_triggers(packet: dict[str, Any] | None) -> list[str]:
    if not packet:
        return []
    decision = packet.get("decision") or {}
    triggers: list[str] = []
    for key in ("pause_triggers", "reopen_triggers", "investigate_triggers", "notes"):
        triggers.extend(str(item) for item in decision.get(key, []))
    return triggers


def _participation_triggered(packet: dict[str, Any] | None) -> bool:
    return any(trigger in PARTICIPATION_TRIGGERS for trigger in _packet_triggers(packet))


def _regime_by_week(regime_rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    by_week: dict[str, Counter[str]] = defaultdict(Counter)
    for row in regime_rows:
        week_start = _week_start_for_ts(row.get("timestamp"))
        if week_start is None:
            continue
        by_week[week_start][str(row.get("regime") or "UNKNOWN")] += 1
    return by_week


def _lane_race_by_week(lane_rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    by_week: dict[str, Counter[str]] = defaultdict(Counter)
    for row in lane_rows:
        week_start = _week_start_for_ts(row.get("timestamp"))
        if week_start is None:
            continue
        by_week[week_start][str(row.get("candidate_signal_type") or "unknown")] += 1
    return by_week


def _week_evidence_rows(
    *,
    packet_payload: dict[str, Any],
    feasibility_payload: dict[str, Any],
    regime_rows: list[dict[str, str]],
    lane_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    primary = feasibility_payload["primary_window"]
    packet_by_week = {packet["week_start"]: packet for packet in packet_payload["packets"]}
    regime_counts = _regime_by_week(regime_rows)
    lane_counts = _lane_race_by_week(lane_rows)
    rows: list[dict[str, Any]] = []

    for week in primary["weeks"]:
        week_start = str(week["week_start"])
        packet = packet_by_week.get(week_start)
        decision = (packet or {}).get("decision") or {}
        regimes = regime_counts.get(week_start, Counter())
        lane_races = lane_counts.get(week_start, Counter())
        entry_trades = _safe_int(week.get("entry_trades"))
        is_partial = bool((packet or {}).get("is_partial_review_week"))
        rows.append(
            {
                "week_start": week_start,
                "week_end": str(week["week_end"]),
                "is_partial_review_week": is_partial,
                "contract_grade": bool(decision.get("contract_grade")),
                "packet_state": str(decision.get("state") or "none"),
                "packet_triggers": _packet_triggers(packet),
                "participation_triggered": _participation_triggered(packet),
                "entry_trades": entry_trades,
                "exit_trades": _safe_int(week.get("exit_trades")),
                "zero_entry_week": entry_trades == 0,
                "lane_race_event_count": int(sum(lane_races.values())),
                "lane_race_candidate_counts": _counter_to_dict(lane_races),
                "silent_week": entry_trades == 0 and sum(lane_races.values()) == 0,
                "gross_pnl_usdt": round(_safe_float(week.get("gross_pnl_usdt")), 4),
                "fees_est_usdt": round(_safe_float(week.get("fees_est_usdt")), 4),
                "net_after_fee_est_usdt": round(
                    _safe_float(week.get("net_after_fee_est_usdt")), 4
                ),
                "slot_net_after_fee_est_usdt": dict(
                    week.get("slot_net_after_fee_est_usdt") or {}
                ),
                "symbol_net_after_fee_est_usdt": dict(
                    week.get("symbol_net_after_fee_est_usdt") or {}
                ),
                "regime_bar_counts": _counter_to_dict(regimes),
                "regime_bar_ratio": _counter_to_pct(regimes),
                "dominant_regime": _dominant(regimes),
            }
        )
    return rows


def _aggregate_counter(rows: list[dict[str, Any]], field: str) -> Counter[str]:
    total: Counter[str] = Counter()
    for row in rows:
        total.update({key: int(value) for key, value in row.get(field, {}).items()})
    return total


def analyze_frequency_complement_lane(
    *,
    packet_payload: dict[str, Any],
    feasibility_payload: dict[str, Any],
    regime_rows: list[dict[str, str]],
    lane_rows: list[dict[str, str]],
) -> dict[str, Any]:
    week_rows = _week_evidence_rows(
        packet_payload=packet_payload,
        feasibility_payload=feasibility_payload,
        regime_rows=regime_rows,
        lane_rows=lane_rows,
    )
    full_weeks = [row for row in week_rows if not row["is_partial_review_week"]]
    active_full_weeks = [row for row in full_weeks if row["entry_trades"] > 0]
    zero_full_weeks = [row for row in full_weeks if row["zero_entry_week"]]
    silent_full_weeks = [row for row in zero_full_weeks if row["silent_week"]]
    participation_packet_weeks = [
        row for row in week_rows if row["contract_grade"] and row["participation_triggered"]
    ]
    lane_race_active_weeks = [row for row in full_weeks if row["lane_race_event_count"] > 0]

    zero_regime_counts = _aggregate_counter(silent_full_weeks, "regime_bar_counts")
    active_lane_counts = _aggregate_counter(active_full_weeks, "lane_race_candidate_counts")
    active_slot_counts: Counter[str] = Counter()
    for row in active_full_weeks:
        for slot, value in row["slot_net_after_fee_est_usdt"].items():
            if _safe_float(value) != 0.0:
                active_slot_counts[str(slot)] += 1

    active_ratio_full = round(len(active_full_weeks) / len(full_weeks), 4) if full_weeks else 0.0
    silent_ratio_full = (
        round(len(silent_full_weeks) / len(full_weeks), 4) if full_weeks else 0.0
    )
    zero_regime_dominants = Counter(row["dominant_regime"] for row in silent_full_weeks)

    return {
        "schema": "strategy_plugin_weekly_profit_frequency_complement_lane.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_packet_schema": packet_payload.get("schema"),
        "source_feasibility_schema": feasibility_payload.get("schema"),
        "verdict": "FREQUENCY_COMPLEMENT_LANE_SELECTED",
        "baseline": {
            "week_count_all": len(week_rows),
            "week_count_full": len(full_weeks),
            "active_entry_week_count_full": len(active_full_weeks),
            "active_entry_week_ratio_full": active_ratio_full,
            "zero_entry_week_count_full": len(zero_full_weeks),
            "silent_zero_entry_week_count_full": len(silent_full_weeks),
            "silent_zero_entry_week_ratio_full": silent_ratio_full,
            "participation_trigger_packet_count": len(participation_packet_weeks),
            "lane_race_active_week_count_full": len(lane_race_active_weeks),
        },
        "gap_evidence": {
            "silent_zero_entry_weeks": silent_full_weeks,
            "participation_trigger_packet_weeks": participation_packet_weeks,
            "silent_zero_entry_regime_bar_counts": _counter_to_dict(zero_regime_counts),
            "silent_zero_entry_regime_bar_ratio": _counter_to_pct(zero_regime_counts),
            "silent_zero_entry_dominant_regime_counts": _counter_to_dict(
                zero_regime_dominants
            ),
            "promoted_lane_race_candidate_counts_active_weeks": _counter_to_dict(
                active_lane_counts
            ),
            "promoted_slot_active_week_counts": _counter_to_dict(active_slot_counts),
        },
        "lane_spec": {
            "lane_id": "frequency_complement_low_overlap",
            "objective": (
                "Add participation in full zero-entry weeks where promoted legs emitted no "
                "lane-race activity, while preserving the existing after-fee and risk profile."
            ),
            "primary_target": (
                "Silent full zero-entry weeks, not partial boundary weeks and not weeks "
                "where promoted Slot A / Slot B candidates already fired."
            ),
            "first_search_bias": (
                "Trend-dominant or mixed silent weeks first, because silent zero-entry "
                "regime bars are more TRENDING than RANGING in the current evidence."
            ),
            "selected_discussion_option": "trend_dominant_silent_week_companion",
            "selected_option_reason": (
                "Ruei selected option 1 after the Phase 4A lane discussion. It targets "
                "the largest silent-week regime bucket before any range or mixed-transition "
                "research expansion."
            ),
            "candidate_contract_path": (
                "plans/weekly_profit_phase4a_trend_dominant_silent_week_companion_spec.md"
            ),
            "hard_exclusions": [
                "Do not change promoted runtime defaults.",
                "Do not loosen thresholds in existing promoted strategies.",
                "Do not activate scanner runtime consumption.",
                "Do not reopen legacy RSI2 / BB / Slot A SHORT lanes by default.",
                "Do not bypass StrategyPlugin, central RiskPlan, arbiter, router, or execution handoff.",
            ],
            "acceptance_gates": [
                "Convert at least 3 full silent zero-entry weeks into active-entry weeks in the primary window.",
                "Reduce contract-grade reopen_research packets from 7 / 9 to 3 / 9 or fewer.",
                "Keep latest contract-grade packet state at investigate or better, ideally continue.",
                "Keep combined primary-window net after-fee estimate at or above the promoted baseline.",
                "Keep rolling 8w net after-fee PnL positive in every contract-grade packet.",
                "Keep worst-week loss above the -7% independent pause line and portfolio drawdown at or below 8%.",
                "Keep at least 70% of new candidate entries on baseline silent or zero-entry weeks.",
                "Do not create same-symbol same-candle overlap with promoted entries.",
            ],
            "discussion_options": [
                {
                    "rank": 1,
                    "option": "trend_dominant_silent_week_companion",
                    "why": (
                        "Most silent zero-entry regime bars are TRENDING, yet promoted Slot A "
                        "did not participate in many of those full weeks."
                    ),
                },
                {
                    "rank": 2,
                    "option": "range_silent_week_companion",
                    "why": (
                        "Several silent weeks are RANGING-dominant, but existing Donchian "
                        "fade legs did not fire; this is secondary because positive-week "
                        "density is already a watch item."
                    ),
                },
                {
                    "rank": 3,
                    "option": "mixed_transition_attribution_probe",
                    "why": (
                        "Mixed weeks may reveal transition gaps, but they need attribution "
                        "before becoming a strategy candidate."
                    ),
                },
            ],
        },
        "week_evidence": week_rows,
    }


def _week_table_row(row: dict[str, Any]) -> str:
    return (
        f"| `{row['week_start']}` | {row['entry_trades']} | "
        f"{row['lane_race_event_count']} | `{row['dominant_regime']}` | "
        f"`{json.dumps(row['regime_bar_counts'], sort_keys=True)}` | "
        f"`{row['packet_state']}` | "
        f"{', '.join(row['packet_triggers'] or ['none'])} |"
    )


def render_spec(summary: dict[str, Any]) -> str:
    baseline = summary["baseline"]
    gap = summary["gap_evidence"]
    spec = summary["lane_spec"]

    lines = [
        "# Weekly Profit Phase 4A Frequency Complement Lane Spec",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `PHASE_4A_LANE_SELECTED`",
        "",
        "## Executive Read",
        "",
        (
            "Selected lane: "
            f"`{spec['lane_id']}` with discussion option "
            f"`{spec['selected_discussion_option']}`. The target is still not a "
            "runtime promotion; it is a bounded research lane aimed at full silent "
            "zero-entry weeks."
        ),
        "",
        (
            "The strongest evidence is that full zero-entry weeks also have zero "
            "promoted lane-race activity. This points to candidate silence, not just "
            "post-signal blocking, so the first research question is what independent "
            "signal family can cover those weeks without overlapping existing legs."
        ),
        "",
        "## Baseline Gap Metrics",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| full weeks | {baseline['week_count_full']} |",
        f"| full active-entry weeks | {baseline['active_entry_week_count_full']} |",
        f"| full active-entry ratio | {_fmt(baseline['active_entry_week_ratio_full'])} |",
        f"| full zero-entry weeks | {baseline['zero_entry_week_count_full']} |",
        f"| full silent zero-entry weeks | {baseline['silent_zero_entry_week_count_full']} |",
        f"| full silent zero-entry ratio | {_fmt(baseline['silent_zero_entry_week_ratio_full'])} |",
        f"| contract-grade participation-trigger packets | {baseline['participation_trigger_packet_count']} |",
        f"| full weeks with promoted lane-race activity | {baseline['lane_race_active_week_count_full']} |",
        "",
        "## Silent Zero-Entry Regime Mix",
        "",
        "| item | value |",
        "| --- | ---: |",
        (
            f"| regime bar counts | "
            f"`{json.dumps(gap['silent_zero_entry_regime_bar_counts'], sort_keys=True)}` |"
        ),
        (
            f"| regime bar ratio | "
            f"`{json.dumps(gap['silent_zero_entry_regime_bar_ratio'], sort_keys=True)}` |"
        ),
        (
            f"| dominant-regime week counts | "
            f"`{json.dumps(gap['silent_zero_entry_dominant_regime_counts'], sort_keys=True)}` |"
        ),
        "",
        "## Silent Full Zero-Entry Weeks",
        "",
        "| week_start | entries | lane-race events | dominant regime | regime bars | packet state | packet triggers |",
        "| --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    lines.extend(_week_table_row(row) for row in gap["silent_zero_entry_weeks"])

    lines.extend(
        [
            "",
            "## Existing Promoted Activity",
            "",
            "| item | value |",
            "| --- | ---: |",
            (
                f"| promoted lane-race candidate counts on active weeks | "
                f"`{json.dumps(gap['promoted_lane_race_candidate_counts_active_weeks'], sort_keys=True)}` |"
            ),
            (
                f"| promoted slot active-week counts | "
                f"`{json.dumps(gap['promoted_slot_active_week_counts'], sort_keys=True)}` |"
            ),
            "",
            "## Lane Spec",
            "",
            "| field | value |",
            "| --- | --- |",
            f"| lane id | `{spec['lane_id']}` |",
            f"| objective | {spec['objective']} |",
            f"| primary target | {spec['primary_target']} |",
            f"| first search bias | {spec['first_search_bias']} |",
            f"| selected discussion option | `{spec['selected_discussion_option']}` |",
            f"| selected option reason | {spec['selected_option_reason']} |",
            f"| candidate contract | `{spec['candidate_contract_path']}` |",
            "",
            "## Acceptance Gates",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in spec["acceptance_gates"])
    lines.extend(["", "## Hard Exclusions", ""])
    lines.extend(f"- {item}" for item in spec["hard_exclusions"])
    lines.extend(
        [
            "",
            "## Discussion Options",
            "",
            "| rank | option | reason |",
            "| ---: | --- | --- |",
        ]
    )
    for item in spec["discussion_options"]:
        lines.append(f"| {item['rank']} | `{item['option']}` | {item['why']} |")

    lines.extend(
        [
            "",
            "## Decision Record",
            "",
            "`trend_dominant_silent_week_companion` is selected. Implementation must start from the candidate contract path above and must not change runtime defaults.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_frequency_complement_lane_spec(
    *,
    packet_path: Path = DEFAULT_PACKET_JSON,
    feasibility_path: Path = DEFAULT_FEASIBILITY_JSON,
    json_path: Path = DEFAULT_JSON,
    spec_path: Path = DEFAULT_SPEC,
) -> dict[str, Any]:
    packet_payload = _load_json(packet_path)
    feasibility_payload = _load_json(feasibility_path)
    artifact_dir = Path(feasibility_payload["primary_window"]["artifacts"]["trades"]).parent
    summary = analyze_frequency_complement_lane(
        packet_payload=packet_payload,
        feasibility_payload=feasibility_payload,
        regime_rows=_read_csv(artifact_dir / "btc_trend_log.csv"),
        lane_rows=_read_csv(artifact_dir / "lane_race_audit.csv"),
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    spec_path.write_text(render_spec(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a Phase 4A frequency-complement lane spec from weekly packets."
    )
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET_JSON)
    parser.add_argument("--feasibility", type=Path, default=DEFAULT_FEASIBILITY_JSON)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--spec-out", type=Path, default=DEFAULT_SPEC)
    args = parser.parse_args()
    write_frequency_complement_lane_spec(
        packet_path=args.packet,
        feasibility_path=args.feasibility,
        json_path=args.json_out,
        spec_path=args.spec_out,
    )


if __name__ == "__main__":
    main()
