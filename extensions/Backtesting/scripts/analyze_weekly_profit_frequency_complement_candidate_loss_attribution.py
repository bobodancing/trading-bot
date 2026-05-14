"""Attribute losses for the Phase 4 frequency-complement research candidate."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from extensions.Backtesting.scripts.run_portfolio_ab_frequency_complement_candidate import (  # noqa: E402
    CANDIDATE,
    DEFAULT_SUMMARY as DEFAULT_CANDIDATE_SUMMARY,
    DEFAULT_WINDOW,
    VARIANT,
)


RESULT_DIR = REPO_ROOT / "extensions" / "Backtesting" / "results"
DEFAULT_PRECISION_JSON = (
    RESULT_DIR
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_trend_companion_precision_attribution_summary.json"
)
DEFAULT_JSON = (
    RESULT_DIR
    / "portfolio_ab_frequency_complement_candidate"
    / "weekly_profit_frequency_complement_candidate_loss_attribution.json"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "reports"
    / "weekly_profit_phase4c_frequency_complement_candidate_loss_attribution.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


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


def _iso_z(value: Any) -> str | None:
    ts = _parse_ts(value)
    if ts is None:
        return None
    return ts.isoformat().replace("+00:00", "Z")


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(counter[key]) for key in sorted(counter)}


def _sum_by(rows: list[dict[str, Any]], field: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[str(row.get(field) or "UNKNOWN")] += _safe_float(row.get("pnl_usdt"))
    return {key: round(value, 4) for key, value in sorted(totals.items())}


def _candidate_artifacts(source: dict[str, Any]) -> tuple[Path, Path]:
    cell = source["matrices"][VARIANT]["custom"][DEFAULT_WINDOW]
    artifacts = cell["artifacts"]
    return Path(artifacts["trades"]), Path(artifacts["signal_rejects"])


def _precision_selected_keys(precision: dict[str, Any]) -> set[str]:
    recommended = precision.get("recommended") or {}
    return {
        str(row["timestamp"])
        for row in recommended.get("selected_candidates", [])
    }


def _trade_candidate_key(row: dict[str, str]) -> str | None:
    return _iso_z(row.get("entry_regime_candle_time") or row.get("entry_time"))


def build_loss_attribution_payload(
    *,
    source_path: Path = DEFAULT_CANDIDATE_SUMMARY,
    precision_path: Path = DEFAULT_PRECISION_JSON,
) -> dict[str, Any]:
    source = _read_json(source_path)
    precision = _read_json(precision_path)
    trade_path, reject_path = _candidate_artifacts(source)
    trades = [
        row for row in _read_csv(trade_path) if row.get("strategy_id") == CANDIDATE
    ]
    rejects = [
        row for row in _read_csv(reject_path) if row.get("signal_type") == CANDIDATE
    ]
    selected_keys = _precision_selected_keys(precision)

    enriched: list[dict[str, Any]] = []
    for row in trades:
        key = _trade_candidate_key(row)
        pnl = _safe_float(row.get("pnl_usdt"))
        realized_r = _safe_float(row.get("realized_r"))
        enriched.append(
            {
                "candidate_key": key,
                "entry_time": row.get("entry_time"),
                "exit_time": row.get("exit_time"),
                "entry_price": _safe_float(row.get("entry_price")),
                "exit_price": _safe_float(row.get("exit_price")),
                "pnl_usdt": round(pnl, 4),
                "realized_r": round(realized_r, 4),
                "exit_reason": row.get("exit_reason") or "unknown",
                "entry_regime": row.get("entry_regime") or "UNKNOWN",
                "entry_regime_direction": row.get("entry_regime_direction") or "UNKNOWN",
                "matched_precision_candidate": key in selected_keys if key else False,
            }
        )

    pnl_total = round(sum(_safe_float(row["pnl_usdt"]) for row in enriched), 4)
    losses = [row for row in enriched if _safe_float(row["pnl_usdt"]) < 0.0]
    wins = [row for row in enriched if _safe_float(row["pnl_usdt"]) > 0.0]
    unmatched = [row for row in enriched if not row["matched_precision_candidate"]]
    reject_counts = Counter(row.get("reject_reason") or "UNKNOWN" for row in rejects)

    if pnl_total < 0.0 and unmatched:
        verdict = "LOSS_ATTRIBUTION_FAIL_WITH_PARITY_DRIFT_OR_BOUNDARY_TRADES"
    elif pnl_total < 0.0:
        verdict = "LOSS_ATTRIBUTION_FAIL_CONFIRMED_CANDIDATE_EDGE"
    else:
        verdict = "LOSS_ATTRIBUTION_PASS_REVIEW_NEXT_FILTER"

    return {
        "schema": "strategy_plugin_weekly_profit_frequency_complement_candidate_loss_attribution.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "source": {
            "candidate_summary": str(source_path),
            "precision_attribution": str(precision_path),
            "trades": str(trade_path),
            "signal_rejects": str(reject_path),
        },
        "candidate": CANDIDATE,
        "summary": {
            "trade_count": len(enriched),
            "win_count": len(wins),
            "loss_count": len(losses),
            "net_pnl_usdt": pnl_total,
            "matched_precision_trade_count": sum(
                1 for row in enriched if row["matched_precision_candidate"]
            ),
            "unmatched_precision_trade_count": len(unmatched),
            "exit_reason_counts": _counter_dict(
                Counter(row["exit_reason"] for row in enriched)
            ),
            "entry_regime_counts": _counter_dict(
                Counter(row["entry_regime"] for row in enriched)
            ),
            "entry_regime_direction_counts": _counter_dict(
                Counter(row["entry_regime_direction"] for row in enriched)
            ),
            "pnl_by_exit_reason": _sum_by(enriched, "exit_reason"),
            "pnl_by_entry_regime": _sum_by(enriched, "entry_regime"),
            "pnl_by_entry_regime_direction": _sum_by(
                enriched,
                "entry_regime_direction",
            ),
            "reject_counts": _counter_dict(reject_counts),
        },
        "trades": enriched,
    }


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    unmatched = int(summary["unmatched_precision_trade_count"])
    if unmatched:
        precision_read = (
            f"Precision match count is `{summary['matched_precision_trade_count']}` "
            f"matched and `{unmatched}` unmatched. Unmatched trades are treated as parity "
            "or boundary-risk evidence, not promotion evidence."
        )
        next_actions = [
            "- Do not promote this candidate.",
            "- Repair remaining parity or boundary-risk mismatch before testing another loss-side filter.",
            "- If unmatched precision trades persist after parity repair, freeze the lane and move to the next frequency complement family.",
        ]
    else:
        precision_read = (
            f"Precision match count is `{summary['matched_precision_trade_count']}` "
            "matched and `0` unmatched. Phase 4C parity drift is removed; the remaining "
            "loss is confirmed candidate-edge evidence."
        )
        next_actions = [
            "- Do not promote this candidate.",
            "- Freeze this BTC recovery-band lane unless a new candle-feature-only loss filter can be proven on matched trades without destroying cadence.",
            "- Move the next frequency-complement research pass to a different family if no such filter is available.",
        ]
    lines = [
        "# Weekly Profit Phase 4C Frequency Complement Candidate Loss Attribution",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Verdict: `{payload['verdict']}`",
        "",
        "## Executive Read",
        "",
        (
            f"`{payload['candidate']}` closed {summary['trade_count']} trades with "
            f"net PnL `{summary['net_pnl_usdt']}` USDT. The lane still fails the "
            "weekly-profit objective unless this loss source is repaired."
        ),
        "",
        precision_read,
        "",
        "## Loss Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| trades | {summary['trade_count']} |",
        f"| wins | {summary['win_count']} |",
        f"| losses | {summary['loss_count']} |",
        f"| net pnl | {summary['net_pnl_usdt']:.4f} |",
        f"| matched precision trades | {summary['matched_precision_trade_count']} |",
        f"| unmatched precision trades | {summary['unmatched_precision_trade_count']} |",
        "",
        "## Buckets",
        "",
        "| bucket | counts | pnl |",
        "| --- | --- | --- |",
        (
            "| exit reason | "
            f"`{json.dumps(summary['exit_reason_counts'], sort_keys=True)}` | "
            f"`{json.dumps(summary['pnl_by_exit_reason'], sort_keys=True)}` |"
        ),
        (
            "| entry regime | "
            f"`{json.dumps(summary['entry_regime_counts'], sort_keys=True)}` | "
            f"`{json.dumps(summary['pnl_by_entry_regime'], sort_keys=True)}` |"
        ),
        (
            "| entry regime direction | "
            f"`{json.dumps(summary['entry_regime_direction_counts'], sort_keys=True)}` | "
            f"`{json.dumps(summary['pnl_by_entry_regime_direction'], sort_keys=True)}` |"
        ),
        "",
        "## Candidate Trades",
        "",
        "| key | entry | exit | pnl | realized_r | exit_reason | regime | direction | precision_match |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |",
    ]
    for row in payload["trades"]:
        lines.append(
            f"| `{row['candidate_key']}` | `{row['entry_time']}` | `{row['exit_time']}` | "
            f"{row['pnl_usdt']:.4f} | {row['realized_r']:.4f} | "
            f"`{row['exit_reason']}` | `{row['entry_regime']}` | "
            f"`{row['entry_regime_direction']}` | `{row['matched_precision_candidate']}` |"
        )
    lines.extend(
        [
            "",
            "## Next Action",
            "",
            *next_actions,
        ]
    )
    return "\n".join(lines) + "\n"


def write_loss_attribution(
    *,
    source_path: Path = DEFAULT_CANDIDATE_SUMMARY,
    precision_path: Path = DEFAULT_PRECISION_JSON,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    payload = build_loss_attribution_payload(
        source_path=source_path,
        precision_path=precision_path,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attribute losses for the Phase 4 frequency-complement candidate."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_CANDIDATE_SUMMARY)
    parser.add_argument("--precision", type=Path, default=DEFAULT_PRECISION_JSON)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    write_loss_attribution(
        source_path=args.source,
        precision_path=args.precision,
        json_path=args.json_out,
        report_path=args.report_out,
    )


if __name__ == "__main__":
    main()
