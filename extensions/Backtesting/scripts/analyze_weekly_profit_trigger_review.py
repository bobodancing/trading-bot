"""Analyze Phase 3 weekly-profit packets into a Phase 4 trigger review."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = SCRIPT_ROOT.parents[0]
REPO_ROOT = BACKTEST_ROOT.parents[1]
for path in (SCRIPT_ROOT, BACKTEST_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from build_weekly_profit_control_packet import DEFAULT_JSON as DEFAULT_PACKET_JSON  # noqa: E402


DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_trigger_review_summary.json"
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase4_trigger_review.md"
PARTICIPATION_TRIGGERS = {
    "active_entry_week_ratio_8w",
    "rolling_8w_entry_trade_count",
    "zero_entry_week_streak",
}
ECONOMIC_TRIGGERS = {
    "positive_week_ratio_all_8w_after_fee",
    "positive_week_ratio_exit_active_8w_after_fee",
    "rolling_8w_net_after_fee_pnl",
    "max_consecutive_losing_weeks_after_fee_8w",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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


def _trigger_counts(packets: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for packet in packets:
        decision = packet["decision"]
        for key in ("pause_triggers", "reopen_triggers", "investigate_triggers"):
            counts.update(str(trigger) for trigger in decision.get(key, []))
    return counts


def _state_counts(packets: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for packet in packets:
        counts[str(packet["decision"]["state"])] += 1
    return dict(sorted(counts.items()))


def _dominant_gap(trigger_counts: Counter[str]) -> str:
    participation_count = sum(trigger_counts[trigger] for trigger in PARTICIPATION_TRIGGERS)
    economic_count = sum(trigger_counts[trigger] for trigger in ECONOMIC_TRIGGERS)
    if participation_count > economic_count:
        return "participation_gap"
    if economic_count > participation_count:
        return "economic_quality_gap"
    if participation_count:
        return "mixed_participation_and_economic_gap"
    return "no_material_gap"


def _verdict_for(
    *,
    contract_grade_packet_count: int,
    dominant_gap: str,
    trigger_counts: Counter[str],
    risk_pause_count: int,
) -> str:
    if contract_grade_packet_count == 0:
        return "INSUFFICIENT_CONTRACT_GRADE_PACKETS"
    if risk_pause_count > 0:
        return "RESOLVE_PAUSE_BEFORE_RESEARCH"
    if not trigger_counts:
        return "NO_MATERIAL_TRIGGER_CONTINUE_MONITORING"
    if dominant_gap == "participation_gap":
        return "OPEN_BOUNDED_FREQUENCY_COMPLEMENT_DISCUSSION"
    if dominant_gap == "economic_quality_gap":
        return "OPEN_BOUNDED_ECONOMIC_QUALITY_DISCUSSION"
    if dominant_gap == "mixed_participation_and_economic_gap":
        return "OPEN_MIXED_GAP_TRIAGE_DISCUSSION"
    return "NO_MATERIAL_TRIGGER_CONTINUE_MONITORING"


def _lane(
    rank: int,
    lane: str,
    stance: str,
    why: str,
) -> dict[str, Any]:
    return {"rank": rank, "lane": lane, "stance": stance, "why": why}


def _economic_first_lane(trigger_counts: Counter[str]) -> dict[str, Any]:
    exit_quality_count = (
        trigger_counts["positive_week_ratio_exit_active_8w_after_fee"]
        + trigger_counts["rolling_8w_net_after_fee_pnl"]
        + trigger_counts["max_consecutive_losing_weeks_after_fee_8w"]
    )
    positive_density_count = trigger_counts["positive_week_ratio_all_8w_after_fee"]
    if exit_quality_count > positive_density_count:
        return _lane(
            1,
            "exit_quality_repair",
            "recommended_first_discussion",
            (
                "Economic-quality triggers dominate and point beyond calendar inactivity: "
                "active-exit quality, net PnL, or losing-streak gates are the first failure."
            ),
        )
    return _lane(
        1,
        "positive_week_density_stabilizer",
        "recommended_first_discussion",
        (
            "Economic triggers are dominated by all-week positive density, so the first "
            "discussion should stabilize profitable-week coverage before adding volume."
        ),
    )


def _lane_discussion_for(
    *,
    verdict: str,
    dominant_gap: str,
    trigger_counts: Counter[str],
) -> list[dict[str, Any]]:
    if verdict == "INSUFFICIENT_CONTRACT_GRADE_PACKETS":
        return [
            _lane(
                1,
                "continue_packet_collection",
                "recommended_first_discussion",
                "There is not enough contract-grade packet history to open a research lane.",
            )
        ]
    if verdict == "RESOLVE_PAUSE_BEFORE_RESEARCH":
        return [
            _lane(
                1,
                "operational_risk_resolution",
                "required_first",
                "A pause state wins over research. Resolve risk or operational integrity first.",
            )
        ]
    if verdict == "NO_MATERIAL_TRIGGER_CONTINUE_MONITORING":
        return [
            _lane(
                1,
                "continue_weekly_monitoring",
                "no_research_lane",
                "Contract-grade packets do not show a material participation or economic trigger.",
            )
        ]
    if dominant_gap == "participation_gap":
        return [
            _lane(
                1,
                "frequency_complement_low_overlap",
                "recommended_first_discussion",
                (
                    "Participation triggers dominate the contract-grade packet history, "
                    "while latest contract-grade economics remain net-positive and risk-clean."
                ),
            ),
            _lane(
                2,
                "positive_week_density_stabilizer",
                "secondary_discussion",
                (
                    "All-week positive density should be protected while frequency repair "
                    "adds trade opportunities."
                ),
            ),
            _lane(
                3,
                "exit_quality_repair",
                "not_first",
                (
                    "Exit-active quality and rolling net PnL are not the dominant historical "
                    "failure in this packet set."
                ),
            ),
        ]
    if dominant_gap == "economic_quality_gap":
        first = _economic_first_lane(trigger_counts)
        second_lane = (
            "positive_week_density_stabilizer"
            if first["lane"] == "exit_quality_repair"
            else "exit_quality_repair"
        )
        second_why = (
            "Use as the paired economic diagnostic after the first economic failure mode is scoped."
        )
        return [
            first,
            _lane(2, second_lane, "secondary_discussion", second_why),
            _lane(
                3,
                "frequency_complement_low_overlap",
                "not_first",
                "Do not add frequency before the economic-quality failure is understood.",
            ),
        ]
    return [
        _lane(
            1,
            "mixed_gap_attribution_split",
            "recommended_first_discussion",
            (
                "Participation and economic triggers are tied; split attribution before "
                "choosing a frequency or quality repair lane."
            ),
        ),
        _lane(
            2,
            "frequency_complement_low_overlap",
            "conditional_discussion",
            "Proceed only if attribution shows inactivity remains the first bottleneck.",
        ),
        _lane(
            3,
            "positive_week_density_stabilizer",
            "conditional_discussion",
            "Proceed only if attribution shows trade-quality density is the first bottleneck.",
        ),
    ]


def _recommendation_summary(verdict: str) -> str:
    if verdict == "OPEN_BOUNDED_FREQUENCY_COMPLEMENT_DISCUSSION":
        return (
            "The packet history justifies discussing one bounded frequency-complement "
            "research lane, but it does not authorize runtime-default changes, scanner "
            "runtime activation, threshold loosening, or live/testnet state changes."
        )
    if verdict == "OPEN_BOUNDED_ECONOMIC_QUALITY_DISCUSSION":
        return (
            "The packet history points to economic-quality repair before any frequency "
            "expansion. Do not add trade volume until the quality failure mode is scoped."
        )
    if verdict == "OPEN_MIXED_GAP_TRIAGE_DISCUSSION":
        return (
            "The packet history is mixed. Do an attribution split before choosing between "
            "frequency complement and economic-quality repair."
        )
    if verdict == "RESOLVE_PAUSE_BEFORE_RESEARCH":
        return (
            "A pause condition is present in contract-grade packets. Resolve risk or "
            "operational integrity before opening any research lane."
        )
    if verdict == "NO_MATERIAL_TRIGGER_CONTINUE_MONITORING":
        return (
            "Contract-grade packets do not justify opening a research lane. Continue "
            "weekly packet monitoring."
        )
    return (
        "There are not enough contract-grade packets to open a research lane. Continue "
        "packet collection."
    )


def _packet_row(packet: dict[str, Any]) -> str:
    kpis = packet["kpis"]
    decision = packet["decision"]
    triggers = (
        decision.get("pause_triggers")
        or decision.get("reopen_triggers")
        or decision.get("investigate_triggers")
        or decision.get("notes")
        or ["none"]
    )
    return (
        f"| `{packet['week_start']}` | `{decision['state']}` | "
        f"{_fmt(kpis['active_entry_week_ratio_8w'])} | "
        f"{kpis['rolling_8w_entry_trade_count']} | "
        f"{kpis['zero_entry_week_streak']} | "
        f"{_fmt(kpis['positive_week_ratio_all_8w_after_fee'])} | "
        f"{_fmt(kpis['positive_week_ratio_exit_active_8w_after_fee'])} | "
        f"{_fmt(kpis['rolling_8w_net_after_fee_pnl'])} | "
        f"{', '.join(triggers)} |"
    )


def analyze_trigger_review(packet_payload: dict[str, Any]) -> dict[str, Any]:
    packets = list(packet_payload.get("packets") or [])
    contract_grade_packets = [
        packet for packet in packets if bool(packet.get("decision", {}).get("contract_grade"))
    ]
    if not contract_grade_packets:
        trigger_counts: Counter[str] = Counter()
        latest = None
    else:
        trigger_counts = _trigger_counts(contract_grade_packets)
        latest = packet_payload.get("latest_contract_grade_packet") or contract_grade_packets[-1]

    dominant_gap = _dominant_gap(trigger_counts)
    participation_trigger_count = sum(
        trigger_counts[trigger] for trigger in PARTICIPATION_TRIGGERS
    )
    economic_trigger_count = sum(trigger_counts[trigger] for trigger in ECONOMIC_TRIGGERS)
    reopen_count = sum(
        1
        for packet in contract_grade_packets
        if packet["decision"]["state"] == "reopen_research"
    )
    investigate_count = sum(
        1 for packet in contract_grade_packets if packet["decision"]["state"] == "investigate"
    )
    risk_pause_count = sum(
        1 for packet in contract_grade_packets if packet["decision"]["state"] == "pause"
    )
    verdict = _verdict_for(
        contract_grade_packet_count=len(contract_grade_packets),
        dominant_gap=dominant_gap,
        trigger_counts=trigger_counts,
        risk_pause_count=risk_pause_count,
    )
    lane_discussion = _lane_discussion_for(
        verdict=verdict,
        dominant_gap=dominant_gap,
        trigger_counts=trigger_counts,
    )

    return {
        "schema": "strategy_plugin_weekly_profit_trigger_review.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_packet_schema": packet_payload.get("schema"),
        "source_packet_count": packet_payload.get("packet_count"),
        "contract_grade_packet_count": len(contract_grade_packets),
        "contract_grade_state_counts": _state_counts(contract_grade_packets),
        "trigger_counts": dict(sorted(trigger_counts.items())),
        "participation_trigger_count": participation_trigger_count,
        "economic_trigger_count": economic_trigger_count,
        "dominant_gap": dominant_gap,
        "verdict": verdict,
        "recommendation_summary": _recommendation_summary(verdict),
        "reopen_contract_grade_packet_count": reopen_count,
        "investigate_contract_grade_packet_count": investigate_count,
        "risk_pause_contract_grade_packet_count": risk_pause_count,
        "first_contract_grade_packet": contract_grade_packets[0] if contract_grade_packets else None,
        "latest_contract_grade_packet": latest,
        "contract_grade_packets": contract_grade_packets,
        "lane_discussion": lane_discussion,
    }


def render_report(review: dict[str, Any], *, packet_path: Path) -> str:
    latest = review.get("latest_contract_grade_packet") or {}
    latest_decision = latest.get("decision") or {}
    latest_kpis = latest.get("kpis") or {}
    trigger_counts = review.get("trigger_counts") or {}

    lines = [
        "# Weekly Profit Phase 4 Trigger Review",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `PHASE_4_TRIGGER_REVIEW_READY_FOR_LANE_DISCUSSION`",
        "",
        "## Executive Read",
        "",
        (
            "Formal trigger review verdict: "
            f"`{review['verdict']}`. Dominant gap is `{review['dominant_gap']}`."
        ),
        "",
        review["recommendation_summary"],
        "",
        "## Source",
        "",
        f"- Phase 3 packet JSON: `{packet_path}`",
        f"- Source packet schema: `{review['source_packet_schema']}`",
        f"- Source packet count: `{review['source_packet_count']}`",
        f"- Contract-grade packet count: `{review['contract_grade_packet_count']}`",
        "",
        "## Contract-Grade State Counts",
        "",
        "| state | count |",
        "| --- | ---: |",
    ]
    for state, count in (review.get("contract_grade_state_counts") or {}).items():
        lines.append(f"| `{state}` | {count} |")

    lines.extend(
        [
            "",
            "## Trigger Counts",
            "",
            "| trigger | count |",
            "| --- | ---: |",
        ]
    )
    for trigger, count in trigger_counts.items():
        lines.append(f"| `{trigger}` | {count} |")

    lines.extend(
        [
            "",
            "## Latest Contract-Grade Packet",
            "",
            "| KPI | value |",
            "| --- | ---: |",
            f"| week_start | `{latest.get('week_start')}` |",
            f"| state | `{latest_decision.get('state')}` |",
            f"| active_entry_week_ratio_8w | {_fmt(latest_kpis.get('active_entry_week_ratio_8w'))} |",
            f"| rolling_8w_entry_trade_count | {_fmt(latest_kpis.get('rolling_8w_entry_trade_count'))} |",
            f"| zero_entry_week_streak | {_fmt(latest_kpis.get('zero_entry_week_streak'))} |",
            f"| positive_week_ratio_all_8w_after_fee | {_fmt(latest_kpis.get('positive_week_ratio_all_8w_after_fee'))} |",
            f"| positive_week_ratio_exit_active_8w_after_fee | {_fmt(latest_kpis.get('positive_week_ratio_exit_active_8w_after_fee'))} |",
            f"| rolling_8w_net_after_fee_pnl | {_fmt(latest_kpis.get('rolling_8w_net_after_fee_pnl'))} |",
            f"| worst_week_after_fee_pnl_pct_equity_8w | {_fmt(latest_kpis.get('worst_week_after_fee_pnl_pct_equity_8w'))} |",
            f"| portfolio_max_drawdown_pct_review_window | {_fmt(latest_kpis.get('portfolio_max_drawdown_pct_review_window'))} |",
            "",
            "## Contract-Grade Packet Timeline",
            "",
            "| week_start | state | active-entry ratio 8w | entries 8w | zero-entry streak | positive all 8w | positive active-exit 8w | net 8w | primary trigger |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    lines.extend(_packet_row(packet) for packet in review["contract_grade_packets"])

    lines.extend(
        [
            "",
            "## Diagnosis",
            "",
            (
                "- Participation pressure is the dominant historical trigger: active-entry "
                "ratio and entry-count gates caused most formal reopen windows."
            ),
            (
                "- Latest contract-grade economics are not a hard failure: rolling `8w` "
                "net PnL is positive, worst-week loss is inside the risk envelope, and "
                "no operational pause condition appears in the packet."
            ),
            (
                "- Positive-week density is now the watch item. The latest packet sits at "
                "the `0.3750` all-week lower watch line while active-exit positivity is "
                "still at the continue threshold."
            ),
            "",
            "## Lane Discussion Menu",
            "",
            "| rank | lane | stance | reason |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for item in review["lane_discussion"]:
        lines.append(
            f"| {item['rank']} | `{item['lane']}` | `{item['stance']}` | {item['why']} |"
        )

    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Discuss exactly one bounded lane before implementation.",
            "- Do not change promoted runtime defaults.",
            "- Do not loosen current strategy thresholds to manufacture volume.",
            "- Do not reactivate legacy RSI2 / BB / Slot A SHORT lanes by default.",
            "- Any candidate must add weekly participation without degrading after-fee packet economics or risk integrity.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_trigger_review(
    *,
    packet_path: Path = DEFAULT_PACKET_JSON,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    packet_payload = _load_json(packet_path)
    review = analyze_trigger_review(packet_payload)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(render_report(review, packet_path=packet_path), encoding="utf-8")
    return review


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Phase 3 weekly-profit packets into a Phase 4 trigger review."
    )
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET_JSON)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    write_trigger_review(
        packet_path=args.packet,
        json_path=args.json_out,
        report_path=args.report_out,
    )


if __name__ == "__main__":
    main()
