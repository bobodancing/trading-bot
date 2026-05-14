"""Find repair filters for the Phase 4D range-break retest candidate."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = SCRIPT_ROOT.parents[0]
REPO_ROOT = BACKTEST_ROOT.parents[1]
for path in (SCRIPT_ROOT, BACKTEST_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analyze_promoted_three_leg_weekly_feasibility import DEFAULT_FEE_RATE, _fmt  # noqa: E402
from extensions.Backtesting.scripts.run_portfolio_ab_range_break_retest_candidate import (  # noqa: E402
    CANDIDATE,
    DEFAULT_SUMMARY as DEFAULT_CANDIDATE_SUMMARY,
    DEFAULT_WINDOW,
    VARIANT,
)


DEFAULT_PROBE_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_range_break_retest_probe_summary.json"
)
DEFAULT_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_range_break_retest_candidate"
    / "weekly_profit_range_break_retest_repair_filter.json"
)
DEFAULT_REPORT = (
    REPO_ROOT / "reports" / "weekly_profit_phase4d_range_break_retest_repair_filter.md"
)

MIN_SILENT_WEEKS = 3
MIN_SILENT_OR_ZERO_RATIO = 0.70
MAX_ACTIVE_RATIO = 0.30


Predicate = tuple[str, dict[str, Any], Callable[[dict[str, Any]], bool]]


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


def _candidate_artifacts(source: dict[str, Any]) -> tuple[Path, Path]:
    cell = source["matrices"][VARIANT]["custom"][DEFAULT_WINDOW]
    artifacts = cell["artifacts"]
    return Path(artifacts["trades"]), Path(artifacts["signal_rejects"])


def _trade_candidate_key(row: dict[str, str]) -> str | None:
    return _iso_z(row.get("entry_regime_candle_time") or row.get("entry_time"))


def _trade_lookup_key(row: dict[str, str]) -> tuple[str, str] | None:
    key = _trade_candidate_key(row)
    symbol = str(row.get("symbol") or "")
    if key is None or not symbol:
        return None
    return symbol, key


def _candidate_lookup_key(row: dict[str, Any]) -> tuple[str, str] | None:
    key = _iso_z(row.get("timestamp"))
    symbol = str(row.get("symbol") or "")
    if key is None or not symbol:
        return None
    return symbol, key


def _fee_estimate(row: dict[str, str], fee_rate: float) -> float:
    size = _safe_float(row.get("total_size"))
    entry = _safe_float(row.get("entry_price"))
    exit_price = _safe_float(row.get("exit_price"))
    if size <= 0.0:
        return 0.0
    return fee_rate * size * (entry + exit_price)


def _selected_rows(
    *,
    probe: dict[str, Any],
    source: dict[str, Any],
    fee_rate: float,
) -> list[dict[str, Any]]:
    trade_path, _reject_path = _candidate_artifacts(source)
    trades = [
        row for row in _read_csv(trade_path) if row.get("strategy_id") == CANDIDATE
    ]
    trade_by_key = {
        key: row for row in trades for key in [_trade_lookup_key(row)] if key is not None
    }

    rows: list[dict[str, Any]] = []
    for candidate in (probe.get("recommended") or {}).get("selected_candidates", []):
        key = _iso_z(candidate.get("timestamp"))
        trade = trade_by_key.get(_candidate_lookup_key(candidate))
        pnl = _safe_float((trade or {}).get("pnl_usdt"))
        fee = _fee_estimate(trade or {}, fee_rate)
        row = dict(candidate)
        row.update(
            {
                "candidate_key": key,
                "accepted_trade": trade is not None,
                "pnl_usdt": round(pnl, 4) if trade is not None else None,
                "fee_est_usdt": round(fee, 4) if trade is not None else None,
                "after_fee_pnl_est_usdt": round(pnl - fee, 4) if trade is not None else None,
                "realized_r": (
                    round(_safe_float(trade.get("realized_r")), 4)
                    if trade is not None
                    else None
                ),
                "exit_reason": (trade or {}).get("exit_reason") or "not_accepted",
                "entry_time": (trade or {}).get("entry_time"),
                "exit_time": (trade or {}).get("exit_time"),
            }
        )
        rows.append(row)
    return rows


def _numeric_predicate(
    label: str,
    params: dict[str, Any],
    field: str,
    op: str,
    threshold: float,
) -> Predicate:
    def keep(row: dict[str, Any]) -> bool:
        value = row.get(field)
        if value is None:
            return False
        numeric = float(value)
        if op == "<=":
            return numeric <= threshold
        if op == ">=":
            return numeric >= threshold
        raise ValueError(f"unsupported predicate op: {op}")

    return label, params, keep


def _candidate_predicates(rows: list[dict[str, Any]]) -> list[Predicate]:
    predicates: list[Predicate] = []
    observed = {
        field: sorted(
            {
                round(float(row[field]), 6)
                for row in rows
                if row.get(field) is not None
            }
        )
        for field in (
            "bbw_pctrank",
            "range_width_pct",
            "retest_distance_atr",
            "break_strength_atr",
            "breakout_close_quality",
            "adx",
            "adx_slope_5",
            "width_cv",
        )
    }
    for value in observed["bbw_pctrank"]:
        predicates.append(
            _numeric_predicate(
                f"bbw_pctrank <= {value:g}",
                {"bbw_pctrank_max": value},
                "bbw_pctrank",
                "<=",
                value,
            )
        )
    for value in observed["range_width_pct"]:
        predicates.append(
            _numeric_predicate(
                f"range_width_pct <= {value:g}",
                {"range_width_pct_max": value},
                "range_width_pct",
                "<=",
                value,
            )
        )
    for value in sorted(set(observed["retest_distance_atr"] + [0.0])):
        predicates.append(
            _numeric_predicate(
                f"retest_distance_atr >= {value:g}",
                {"min_retest_distance_atr": value},
                "retest_distance_atr",
                ">=",
                value,
            )
        )
    for value in observed["break_strength_atr"]:
        predicates.append(
            _numeric_predicate(
                f"break_strength_atr >= {value:g}",
                {"break_atr_min": value},
                "break_strength_atr",
                ">=",
                value,
            )
        )
    for value in observed["breakout_close_quality"]:
        predicates.append(
            _numeric_predicate(
                f"breakout_close_quality >= {value:g}",
                {"breakout_close_quality_min": value},
                "breakout_close_quality",
                ">=",
                value,
            )
        )
    for value in observed["adx"]:
        predicates.append(
            _numeric_predicate(
                f"adx >= {value:g}",
                {"min_adx": value},
                "adx",
                ">=",
                value,
            )
        )
    for value in observed["adx_slope_5"]:
        predicates.append(
            _numeric_predicate(
                f"adx_slope_5 >= {value:g}",
                {"min_adx_slope_5": value},
                "adx_slope_5",
                ">=",
                value,
            )
        )
    for value in observed["width_cv"]:
        predicates.append(
            _numeric_predicate(
                f"width_cv <= {value:g}",
                {"width_cv_max": value},
                "width_cv",
                "<=",
                value,
            )
        )
    return predicates


def _merge_params(parts: list[dict[str, Any]]) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    for params in parts:
        for key, value in params.items():
            if key in merged and merged[key] != value:
                return None
            merged[key] = value
    return merged


def _filter_specs(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], list[Callable[[dict[str, Any]], bool]]]]:
    predicates = _candidate_predicates(rows)
    specs: list[tuple[str, dict[str, Any], list[Callable[[dict[str, Any]], bool]]]] = []
    for label, params, fn in predicates:
        specs.append((label, dict(params), [fn]))
    for idx, left in enumerate(predicates):
        for right in predicates[idx + 1 :]:
            label = f"{left[0]} AND {right[0]}"
            params = _merge_params([left[1], right[1]])
            if params is None:
                continue
            specs.append((label, params, [left[2], right[2]]))
    return specs


def _evaluate_filter(
    rows: list[dict[str, Any]],
    *,
    label: str,
    params: dict[str, Any],
    predicates: list[Callable[[dict[str, Any]], bool]],
) -> dict[str, Any]:
    kept = [row for row in rows if all(predicate(row) for predicate in predicates)]
    accepted = [row for row in kept if bool(row.get("accepted_trade"))]
    losing = [row for row in accepted if _safe_float(row.get("pnl_usdt")) < 0.0]
    silent_weeks = {
        str(row.get("week_start"))
        for row in kept
        if bool(row.get("baseline_silent_zero_entry_week"))
    }
    silent_or_zero_count = sum(
        1
        for row in kept
        if bool(row.get("baseline_silent_zero_entry_week"))
        or bool(row.get("baseline_zero_entry_week"))
    )
    active_count = sum(1 for row in kept if bool(row.get("baseline_active_entry_week")))
    candidate_count = len(kept)
    silent_ratio = silent_or_zero_count / candidate_count if candidate_count else 0.0
    active_ratio = active_count / candidate_count if candidate_count else 0.0
    known_gross = sum(_safe_float(row.get("pnl_usdt")) for row in accepted)
    known_after_fee = sum(_safe_float(row.get("after_fee_pnl_est_usdt")) for row in accepted)
    gates = {
        "candidate_count_gte_3": candidate_count >= 3,
        "silent_week_hit_count_gte_3": len(silent_weeks) >= MIN_SILENT_WEEKS,
        "silent_or_zero_candidate_ratio_gte_0p70": silent_ratio >= MIN_SILENT_OR_ZERO_RATIO,
        "active_week_candidate_ratio_lte_0p30": active_ratio <= MAX_ACTIVE_RATIO,
        "known_gross_pnl_nonnegative": known_gross >= 0.0,
    }
    return {
        "filter": label,
        "params": params,
        "gates": gates,
        "candidate_count": candidate_count,
        "accepted_trade_count": len(accepted),
        "known_loss_count": len(losing),
        "known_gross_pnl_usdt": round(known_gross, 4),
        "known_after_fee_pnl_est_usdt": round(known_after_fee, 4),
        "silent_zero_entry_week_hit_count": len(silent_weeks),
        "silent_or_zero_candidate_ratio": round(silent_ratio, 4),
        "active_week_candidate_ratio": round(active_ratio, 4),
        "silent_zero_entry_weeks_hit": sorted(silent_weeks),
        "kept_candidate_keys": [str(row.get("candidate_key")) for row in kept],
        "accepted_trade_keys": [
            str(row.get("candidate_key")) for row in accepted if row.get("candidate_key")
        ],
        "exit_reason_counts": dict(
            sorted(Counter(str(row.get("exit_reason")) for row in accepted).items())
        ),
    }


def _rank_filter(row: dict[str, Any]) -> tuple[Any, ...]:
    gates = row["gates"]
    cadence_pass = all(
        bool(gates[key])
        for key in (
            "candidate_count_gte_3",
            "silent_week_hit_count_gte_3",
            "silent_or_zero_candidate_ratio_gte_0p70",
            "active_week_candidate_ratio_lte_0p30",
        )
    )
    return (
        int(cadence_pass),
        int(gates["known_gross_pnl_nonnegative"]),
        float(row["known_gross_pnl_usdt"]),
        -int(row["known_loss_count"]),
        int(row["silent_zero_entry_week_hit_count"]),
        float(row["silent_or_zero_candidate_ratio"]),
        -len(row["params"]),
    )


def build_repair_filter_payload(
    *,
    probe_path: Path = DEFAULT_PROBE_JSON,
    source_path: Path = DEFAULT_CANDIDATE_SUMMARY,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> dict[str, Any]:
    probe = _read_json(probe_path)
    source = _read_json(source_path)
    rows = _selected_rows(probe=probe, source=source, fee_rate=fee_rate)
    current = _evaluate_filter(
        rows,
        label="current candidate",
        params={},
        predicates=[lambda _row: True],
    )
    evaluations = [
        _evaluate_filter(rows, label=label, params=params, predicates=predicates)
        for label, params, predicates in _filter_specs(rows)
    ]
    feasible = [
        row
        for row in evaluations
        if all(
            row["gates"][key]
            for key in (
                "candidate_count_gte_3",
                "silent_week_hit_count_gte_3",
                "silent_or_zero_candidate_ratio_gte_0p70",
                "active_week_candidate_ratio_lte_0p30",
            )
        )
    ]
    recommended = max(feasible, key=_rank_filter) if feasible else None
    verdict = (
        "REPAIR_FILTER_FOUND_BACKTEST_REQUIRED"
        if recommended and recommended["gates"]["known_gross_pnl_nonnegative"]
        else "REPAIR_FILTER_CADENCE_ONLY_OR_NOT_FOUND"
    )
    top = sorted(evaluations, key=_rank_filter, reverse=True)[:12]
    return {
        "schema": "strategy_plugin_weekly_profit_range_break_retest_repair_filter.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "candidate": CANDIDATE,
        "source": {
            "probe": str(probe_path),
            "candidate_summary": str(source_path),
            "variant": VARIANT,
            "window": DEFAULT_WINDOW,
        },
        "guardrails": {
            "runtime_defaults_unchanged": True,
            "catalog_candidate_enabled": False,
            "filter_inputs": "StrategyPlugin candle-derived metadata only",
        },
        "current": current,
        "recommended": recommended,
        "top_filters": top,
        "selected_candidates": rows,
    }


def render_report(payload: dict[str, Any]) -> str:
    current = payload["current"]
    recommended = payload["recommended"]
    lines = [
        "# Weekly Profit Phase 4D Range-Break Retest Repair Filter",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        f"Verdict: `{payload['verdict']}`",
        "",
        "## Executive Read",
        "",
        (
            f"Current candidate keeps {current['candidate_count']} diagnostic candidates, "
            f"hits {current['silent_zero_entry_week_hit_count']} silent zero-entry weeks, "
            f"and has known gross PnL `{_fmt(current['known_gross_pnl_usdt'])}` USDT."
        ),
        "",
    ]
    if recommended:
        lines.extend(
            [
                (
                    f"Recommended repair filter: `{recommended['filter']}`. It keeps "
                    f"{recommended['candidate_count']} candidates, hits "
                    f"{recommended['silent_zero_entry_week_hit_count']} silent zero-entry weeks, "
                    f"and has known gross PnL `{_fmt(recommended['known_gross_pnl_usdt'])}` USDT "
                    "before rerouting effects."
                ),
                "",
                (
                    "This is not promotion evidence. It is only a backtest-only repair "
                    "candidate; the next proof point is A+B+repaired-candidate packet evaluation."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "No repair filter preserved the cadence gates.",
                "",
                "Freeze this family unless a new mechanism is proposed.",
            ]
        )
    lines.extend(
        [
            "",
            "## Recommended Params",
            "",
            f"`{json.dumps((recommended or {}).get('params', {}), sort_keys=True)}`",
            "",
            "## Current Vs Recommended",
            "",
            "| metric | current | recommended |",
            "| --- | ---: | ---: |",
            f"| candidates | {current['candidate_count']} | {(recommended or {}).get('candidate_count', 0)} |",
            (
                f"| accepted trades | {current['accepted_trade_count']} | "
                f"{(recommended or {}).get('accepted_trade_count', 0)} |"
            ),
            (
                f"| known gross pnl | {_fmt(current['known_gross_pnl_usdt'])} | "
                f"{_fmt((recommended or {}).get('known_gross_pnl_usdt', 0.0))} |"
            ),
            (
                f"| known after-fee pnl est | {_fmt(current['known_after_fee_pnl_est_usdt'])} | "
                f"{_fmt((recommended or {}).get('known_after_fee_pnl_est_usdt', 0.0))} |"
            ),
            (
                f"| silent zero-entry weeks hit | {current['silent_zero_entry_week_hit_count']} | "
                f"{(recommended or {}).get('silent_zero_entry_week_hit_count', 0)} |"
            ),
            (
                f"| silent-or-zero ratio | {_fmt(current['silent_or_zero_candidate_ratio'])} | "
                f"{_fmt((recommended or {}).get('silent_or_zero_candidate_ratio', 0.0))} |"
            ),
            (
                f"| active-week ratio | {_fmt(current['active_week_candidate_ratio'])} | "
                f"{_fmt((recommended or {}).get('active_week_candidate_ratio', 0.0))} |"
            ),
            "",
            "## Top Filters",
            "",
            "| filter | candidates | silent weeks | silent/zero ratio | active ratio | known gross | known after-fee | pass cadence |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["top_filters"]:
        pass_cadence = all(
            row["gates"][key]
            for key in (
                "candidate_count_gte_3",
                "silent_week_hit_count_gte_3",
                "silent_or_zero_candidate_ratio_gte_0p70",
                "active_week_candidate_ratio_lte_0p30",
            )
        )
        lines.append(
            f"| `{row['filter']}` | {row['candidate_count']} | "
            f"{row['silent_zero_entry_week_hit_count']} | "
            f"{_fmt(row['silent_or_zero_candidate_ratio'])} | "
            f"{_fmt(row['active_week_candidate_ratio'])} | "
            f"{_fmt(row['known_gross_pnl_usdt'])} | "
            f"{_fmt(row['known_after_fee_pnl_est_usdt'])} | "
            f"`{pass_cadence}` |"
        )
    lines.extend(
        [
            "",
            "## Selected Candidates",
            "",
            "| key | symbol | side | week | accepted | pnl | fee est | exit | bbw_pct | retest_dist | silent/zero | active |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["selected_candidates"]:
        lines.append(
            f"| `{row['candidate_key']}` | `{row['symbol']}` | `{row['side']}` | "
            f"`{row['week_start']}` | `{row['accepted_trade']}` | "
            f"{_fmt(row.get('pnl_usdt') or 0.0)} | "
            f"{_fmt(row.get('fee_est_usdt') or 0.0)} | "
            f"`{row['exit_reason']}` | {float(row['bbw_pctrank']):.1f} | "
            f"{float(row['retest_distance_atr']):.4f} | "
            f"`{row['baseline_silent_zero_entry_week'] or row['baseline_zero_entry_week']}` | "
            f"`{row['baseline_active_entry_week']}` |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Runtime defaults remain unchanged.",
            "- The candidate remains catalog-disabled.",
            "- Filter inputs are candle-derived StrategyPlugin metadata; baseline week labels are attribution only.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_repair_filter(
    *,
    probe_path: Path = DEFAULT_PROBE_JSON,
    source_path: Path = DEFAULT_CANDIDATE_SUMMARY,
    json_path: Path = DEFAULT_JSON,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> dict[str, Any]:
    payload = build_repair_filter_payload(
        probe_path=probe_path,
        source_path=source_path,
        fee_rate=fee_rate,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find repair filters for the Phase 4D range-break retest candidate."
    )
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE_JSON)
    parser.add_argument("--source", type=Path, default=DEFAULT_CANDIDATE_SUMMARY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    args = parser.parse_args()
    payload = write_repair_filter(
        probe_path=args.probe,
        source_path=args.source,
        json_path=args.json_out,
        report_path=args.report_out,
        fee_rate=args.fee_rate,
    )
    print(
        json.dumps(
            {
                "verdict": payload["verdict"],
                "recommended": payload["recommended"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
