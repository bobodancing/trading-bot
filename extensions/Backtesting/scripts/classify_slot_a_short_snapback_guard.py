"""Dry-classify Slot A SHORT trades through V1/V2 snapback guards."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_loader import BacktestDataLoader
from trader.indicators.registry import IndicatorRegistry
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_snapback_followthrough_guard import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy,
)
from trader.strategies.plugins.macd_signal_trending_down_4h_staged_derisk_giveback_partial67_snapback_guard import (
    MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy,
)


SLOT_A_SHORT = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
WINDOW_NAME = "classic_rollercoaster_2021_2022"
WINDOW_START = "2021-01-01"
WINDOW_END = "2022-12-31"
SYMBOL = "BTC/USDT"

SOURCE_TRADES_PATH = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "slot_a_short_overlay"
    / "supplemental"
    / WINDOW_NAME
    / "trades.csv"
)
RESULTS_ROOT = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "slot_a_short_snapback_classifier"
)
SUMMARY_PATH = RESULTS_ROOT / "slot_a_short_snapback_classifier_summary.json"
CLASSIFIED_TRADES_PATH = RESULTS_ROOT / "slot_a_short_snapback_classifier_trades.csv"
REPORT_PATH = REPO_ROOT / "reports" / "slot_a_short_snapback_classifier.md"


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _profit_factor(pnls: list[float]) -> float | None:
    gross_profit = sum(max(value, 0.0) for value in pnls)
    gross_loss = abs(sum(min(value, 0.0) for value in pnls))
    if gross_loss <= 0.0:
        return None
    return round(gross_profit / gross_loss, 4)


def _mean(records: list[dict[str, Any]], key: str) -> float:
    if not records:
        return 0.0
    return round(sum(_safe_float(row.get(key)) for row in records) / len(records), 4)


def _metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [_safe_float(row.get("pnl_usdt")) for row in records]
    wins = [value for value in pnls if value > 0.0]
    losses = [value for value in pnls if value < 0.0]
    trades = len(records)
    sl_hits = [row for row in records if row.get("exit_reason") == "sl_hit"]
    zero_hour_sl_hits = [
        row
        for row in sl_hits
        if _safe_float(row.get("holding_hours")) <= 0.0
    ]
    return {
        "trades": trades,
        "net_pnl": round(sum(pnls), 4),
        "win_rate": round(len(wins) / trades, 4) if trades else 0.0,
        "profit_factor": _profit_factor(pnls),
        "avg_realized_r": _mean(records, "realized_r"),
        "avg_mfe_pct": _mean(records, "mfe_pct"),
        "avg_mae_pct": _mean(records, "mae_pct"),
        "avg_holding_hours": _mean(records, "holding_hours"),
        "sl_hit_trades": len(sl_hits),
        "zero_hour_sl_hit_trades": len(zero_hour_sl_hits),
        "avg_downside_move_atr": _mean(records, "snapback_guard_downside_move_atr"),
        "avg_entry_extension_atr": _mean(records, "snapback_guard_entry_extension_atr"),
        "avg_close_through_atr": _mean(records, "followthrough_close_through_atr"),
        "avg_close_location": _mean(records, "followthrough_close_location"),
        "followthrough_raw_confirmed_trades": sum(
            1 for row in records if _safe_bool(row.get("followthrough_raw_confirmed"))
        ),
        "followthrough_confirmed_trades": sum(
            1 for row in records if _safe_bool(row.get("followthrough_confirmed"))
        ),
        "followthrough_exhaustion_trades": sum(
            1 for row in records if _safe_bool(row.get("followthrough_exhaustion_active"))
        ),
    }


def _group_metrics(
    records: list[dict[str, Any]],
    key: str,
    *,
    expected: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    grouped = {name: [] for name in expected or []}
    for row in records:
        group = str(row.get(key) or "unknown")
        grouped.setdefault(group, []).append(row)
    return {name: _metrics(rows) for name, rows in sorted(grouped.items())}


def _load_indicator_frame() -> pd.DataFrame:
    loader = BacktestDataLoader()
    frame = loader.get_data(SYMBOL, "4h", WINDOW_START, WINDOW_END)
    prepared = IndicatorRegistry.apply(
        frame.copy().reset_index(),
        {"macd", "atr", "ema"},
    )
    prepared["timestamp"] = pd.to_datetime(prepared["timestamp"], utc=True)
    prepared = prepared.set_index("timestamp")
    return prepared


def _visible_frame(frame: pd.DataFrame, entry_time: str) -> pd.DataFrame:
    timestamp = pd.Timestamp(entry_time)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return frame[frame.index < timestamp]


def _classify_trade(
    row: dict[str, str],
    *,
    indicator_frame: pd.DataFrame,
    v1: MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy,
    v2: MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy,
) -> dict[str, Any]:
    visible = _visible_frame(indicator_frame, str(row.get("entry_time") or ""))
    v1_metrics = v1._snapback_guard_metrics(
        visible,
        lookback_bars=int(v1.params["snapback_guard_lookback_bars"]),
        downside_move_atr_min=float(v1.params["snapback_downside_move_atr_min"]),
        entry_extension_atr_min=float(v1.params["snapback_entry_extension_atr_min"]),
    )
    v2_metrics = v2._followthrough_guard_metrics(
        visible,
        lookback_bars=int(v2.params["snapback_guard_lookback_bars"]),
        downside_move_atr_min=float(v2.params["snapback_downside_move_atr_min"]),
        entry_extension_atr_min=float(v2.params["snapback_entry_extension_atr_min"]),
        close_through_atr_min=float(v2.params["followthrough_close_through_atr_min"]),
        close_through_atr_max=float(v2.params["followthrough_close_through_atr_max"]),
        close_location_max=float(v2.params["followthrough_close_location_max"]),
        downside_move_atr_max=float(v2.params["followthrough_downside_move_atr_max"]),
        entry_extension_atr_max=float(v2.params["followthrough_entry_extension_atr_max"]),
        hist_expansion_min=float(v2.params["followthrough_hist_expansion_min"]),
        votes_min=int(v2.params["followthrough_votes_min"]),
    )

    v1_missing = v1_metrics is None
    v2_missing = v2_metrics is None
    v1_blocks = bool(v1_metrics and v1_metrics["snapback_guard_active"])
    v2_blocks = bool(v2_metrics and v2_metrics["snapback_guard_active"])
    v1_decision = "missing" if v1_missing else "block" if v1_blocks else "keep"
    v2_decision = "missing" if v2_missing else "block" if v2_blocks else "keep"

    enriched: dict[str, Any] = {
        "entry_time": row.get("entry_time"),
        "exit_time": row.get("exit_time"),
        "pnl_usdt": _safe_float(row.get("pnl_usdt")),
        "realized_r": _safe_float(row.get("realized_r")),
        "mfe_pct": _safe_float(row.get("mfe_pct")),
        "mae_pct": _safe_float(row.get("mae_pct")),
        "holding_hours": _safe_float(row.get("holding_hours")),
        "exit_reason": row.get("exit_reason"),
        "v1_decision": v1_decision,
        "v2_decision": v2_decision,
        "v1_v2_bucket": f"v1_{v1_decision}_v2_{v2_decision}",
        "metrics_missing": v1_missing or v2_missing,
    }
    for metrics in (v1_metrics, v2_metrics):
        if metrics:
            enriched.update(metrics)
    return enriched


def _fmt_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _metrics_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {metrics['trades']} | {metrics['net_pnl']:.4f} | "
        f"{metrics['win_rate']:.4f} | {_fmt_optional(metrics['profit_factor'])} | "
        f"{metrics['avg_realized_r']:.4f} | {metrics['avg_mfe_pct']:.4f} | "
        f"{metrics['avg_mae_pct']:.4f} | {metrics['avg_holding_hours']:.1f} | "
        f"{metrics['sl_hit_trades']} | {metrics['zero_hour_sl_hit_trades']} | "
        f"{metrics['avg_downside_move_atr']:.4f} | "
        f"{metrics['avg_entry_extension_atr']:.4f} | "
        f"{metrics['avg_close_through_atr']:.4f} | "
        f"{metrics['followthrough_exhaustion_trades']} |"
    )


def _top_trade_rows(records: list[dict[str, Any]], *, limit: int = 12) -> list[str]:
    rows = []
    selected = sorted(records, key=lambda row: _safe_float(row.get("pnl_usdt")))
    for row in selected[:limit]:
        rows.append(
            f"| `{row['entry_time']}` | {row['pnl_usdt']:.4f} | "
            f"{row['realized_r']:.4f} | {row['mfe_pct']:.4f} | "
            f"{row['mae_pct']:.4f} | {row['holding_hours']:.1f} | "
            f"`{row['exit_reason']}` | `{row['v1_decision']}` | "
            f"`{row['v2_decision']}` | `{row.get('followthrough_exhaustion_reason', 'none')}` |"
        )
    return rows


def _write_classified_csv(records: list[dict[str, Any]]) -> Path:
    fields = [
        "entry_time",
        "exit_time",
        "pnl_usdt",
        "realized_r",
        "mfe_pct",
        "mae_pct",
        "holding_hours",
        "exit_reason",
        "v1_decision",
        "v2_decision",
        "v1_v2_bucket",
        "snapback_late_breakdown_active",
        "snapback_guard_downside_move_atr",
        "snapback_guard_entry_extension_atr",
        "followthrough_raw_confirmed",
        "followthrough_confirmed",
        "followthrough_votes",
        "followthrough_exhaustion_active",
        "followthrough_exhaustion_reason",
        "followthrough_close_through_atr",
        "followthrough_close_location",
    ]
    CLASSIFIED_TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CLASSIFIED_TRADES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({field: row.get(field) for field in fields})
    return CLASSIFIED_TRADES_PATH


def _write_report(payload: dict[str, Any]) -> Path:
    comparison = payload["comparison_buckets"]
    v1 = payload["v1_buckets"]
    v2 = payload["v2_buckets"]
    v2_extra_records = [
        row
        for row in payload["classified_trades"]
        if row["v1_v2_bucket"] == "v1_block_v2_keep"
    ]
    v2_extra = comparison.get("v1_block_v2_keep", _metrics([]))
    v2_has_value = (
        v2_extra["trades"] > 0
        and v2_extra["net_pnl"] > 0.0
        and v2_extra["profit_factor"] is not None
        and v2_extra["profit_factor"] > 1.0
    )
    verdict = (
        "V2_HAS_LIMITED_DIFFERENTIATED_VALUE"
        if v2_has_value
        else "V2_NOT_DIFFERENTIATED_FROM_V1"
    )
    payload["verdict"] = verdict

    lines = [
        "# Slot A SHORT Snapback Guard Dry Classifier",
        "",
        f"Date: {payload['date']}",
        "Status: `RESEARCH_ONLY_DRY_CLASSIFIER`",
        "",
        "## Scope",
        "",
        "- Goal: answer whether V2 preserves any useful bearish continuation that V1's blunt late-breakdown guard would cut.",
        "- This pass does not run a backtest and does not change runtime defaults.",
        f"- Source trades: `{payload['source_trades_path']}`",
        f"- Classified trades CSV: `{payload['classified_trades_path']}`",
        f"- Summary artifact: `{payload['summary_path']}`",
        "",
        "## Verdict",
        "",
        f"Verdict: `{verdict}`.",
        "",
        "V2 has value only if `v1_block_v2_keep` is positive and not dominated by stop-outs. That bucket represents trades V1 would remove but V2 would preserve as non-exhausted bearish continuation.",
        "",
        "## Baseline And Guard Buckets",
        "",
        "| bucket | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | avg_downside_move_atr | avg_entry_extension_atr | avg_close_through_atr | exhaustion_trades |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        _metrics_row("baseline all Slot A SHORT", payload["baseline_metrics"]),
        _metrics_row("V1 keep", v1["keep"]),
        _metrics_row("V1 block", v1["block"]),
        _metrics_row("V2 keep", v2["keep"]),
        _metrics_row("V2 block", v2["block"]),
        "",
        "## V2 Vs V1 Differentiation",
        "",
        "| bucket | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | avg_downside_move_atr | avg_entry_extension_atr | avg_close_through_atr | exhaustion_trades |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for bucket in (
        "v1_keep_v2_keep",
        "v1_block_v2_block",
        "v1_block_v2_keep",
        "v1_keep_v2_block",
        "v1_missing_v2_missing",
    ):
        if bucket in comparison:
            lines.append(_metrics_row(f"`{bucket}`", comparison[bucket]))

    lines.extend(
        [
            "",
            "## V2-Kept V1-Blocked Trades",
            "",
            "| entry_time | pnl_usdt | realized_r | mfe_pct | mae_pct | hold_h | exit_reason | V1 | V2 | exhaustion_reason |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
            *_top_trade_rows(v2_extra_records),
            "",
            "## Read",
            "",
        ]
    )
    if v2_has_value:
        lines.extend(
            [
                "- V2 is differentiated from V1 on the classic Slot A SHORT trade set: it preserves a positive `v1_block_v2_keep` bucket.",
                "- The value is still limited: the bucket is small and includes at least one loser, so this is evidence for a repair direction, not a promotion signal.",
                "- The next step is a full `classic_rollercoaster_2021_2022` V2 backtest to check portfolio interaction, duplicate-entry behavior, cooldowns, and order-path effects.",
            ]
        )
    else:
        lines.extend(
            [
                "- V2 is not differentiated enough from V1 on the classic Slot A SHORT trade set.",
                "- Recommended action is to freeze this repair lane, not to spend more runs on a V3 or full classic backtest.",
                "- Reopen only if the portfolio later needs a separate trend-continuation SHORT thesis; do not restart from a Slot A LONG mirror.",
            ]
        )
    lines.append("- This remains research-only; no runtime activation is implied.")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT_PATH


def classify_slot_a_short_snapback_guard() -> tuple[Path, Path]:
    rows = [
        row
        for row in _read_csv(SOURCE_TRADES_PATH)
        if row.get("strategy_id") == SLOT_A_SHORT
    ]
    indicator_frame = _load_indicator_frame()
    v1 = MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackGuardStrategy()
    v2 = (
        MacdSignalTrendingDown4hStagedDeriskGivebackPartial67SnapbackFollowthroughGuardStrategy()
    )
    classified = [
        _classify_trade(row, indicator_frame=indicator_frame, v1=v1, v2=v2)
        for row in rows
    ]

    classified_path = _write_classified_csv(classified)
    payload: dict[str, Any] = {
        "schema": "strategy_plugin_slot_a_short_snapback_dry_classifier.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": "2026-05-07",
        "status": "RESEARCH_ONLY_DRY_CLASSIFIER",
        "source_trades_path": str(SOURCE_TRADES_PATH),
        "classified_trades_path": str(classified_path),
        "summary_path": str(SUMMARY_PATH),
        "report_path": str(REPORT_PATH),
        "window": {
            "name": WINDOW_NAME,
            "start": WINDOW_START,
            "end": WINDOW_END,
        },
        "strategy_id": SLOT_A_SHORT,
        "v1_params": dict(v1.params),
        "v2_params": dict(v2.params),
        "baseline_metrics": _metrics(classified),
        "v1_buckets": _group_metrics(
            classified,
            "v1_decision",
            expected=["keep", "block", "missing"],
        ),
        "v2_buckets": _group_metrics(
            classified,
            "v2_decision",
            expected=["keep", "block", "missing"],
        ),
        "comparison_buckets": _group_metrics(
            classified,
            "v1_v2_bucket",
            expected=[
                "v1_keep_v2_keep",
                "v1_block_v2_block",
                "v1_block_v2_keep",
                "v1_keep_v2_block",
                "v1_missing_v2_missing",
            ],
        ),
        "classified_trades": classified,
    }
    report = _write_report(payload)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[SlotAShortSnapbackClassifier] summary={SUMMARY_PATH}")
    print(f"[SlotAShortSnapbackClassifier] trades={classified_path}")
    print(f"[SlotAShortSnapbackClassifier] report={report}")
    return SUMMARY_PATH, report


def main() -> int:
    classify_slot_a_short_snapback_guard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
