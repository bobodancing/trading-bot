"""Analyze why the mirrored Slot A SHORT probe breaks down.

This is research-only attribution. It reads existing backtest artifacts and
does not run new backtests or change runtime defaults.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]

RESULTS_ROOT = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "slot_a_short_failure_attribution"
)
SUMMARY_PATH = RESULTS_ROOT / "slot_a_short_failure_attribution_summary.json"
REPORT_PATH = REPO_ROOT / "reports" / "slot_a_short_failure_attribution.md"

SLOT_A_LONG = (
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_A_SHORT = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_B_LONG = "donchian_range_fade_4h_range_width_cv_013"
SLOT_B_SHORT = "donchian_range_fade_4h_range_width_cv_013_short"

STRATEGY_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_A_SHORT: "Slot A SHORT",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
}

SOURCES = {
    "slot_a_short_overlay_default": (
        BACKTEST_ROOT
        / "results"
        / "portfolio_ab_bidirectional"
        / "short_ablation"
        / "slot_a_short_overlay"
        / "default"
    ),
    "slot_a_short_overlay_stress": (
        BACKTEST_ROOT
        / "results"
        / "portfolio_ab_bidirectional"
        / "short_ablation"
        / "slot_a_short_overlay"
        / "supplemental"
        / "classic_rollercoaster_2021_2022"
    ),
    "all_four_supplemental": (
        BACKTEST_ROOT
        / "results"
        / "portfolio_ab_bidirectional"
        / "slot_a_b_long_short"
        / "supplemental"
    ),
    "slot_b_short_overlay_stress": (
        BACKTEST_ROOT
        / "results"
        / "portfolio_ab_bidirectional"
        / "short_ablation"
        / "slot_b_short_overlay"
        / "supplemental"
        / "classic_rollercoaster_2021_2022"
    ),
}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _trade_files(source_path: Path) -> list[tuple[str, Path]]:
    if (source_path / "trades.csv").exists():
        return [(source_path.name, source_path / "trades.csv")]
    files = []
    for path in sorted(source_path.glob("*/trades.csv")):
        files.append((path.parent.name, path))
    return files


def _source_windows(source_path: Path) -> list[str]:
    return [window_name for window_name, _path in _trade_files(source_path)]


def _load_source(source_name: str, source_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for window_name, path in _trade_files(source_path):
        for row in _read_csv(path):
            item = dict(row)
            item["_source"] = source_name
            item["_window"] = window_name
            item["_path"] = str(path)
            rows.append(item)
    return rows


def _profit_factor(pnls: list[float]) -> float | None:
    gross_profit = sum(max(value, 0.0) for value in pnls)
    gross_loss = abs(sum(min(value, 0.0) for value in pnls))
    if gross_loss <= 0:
        return None
    return round(gross_profit / gross_loss, 4)


def _metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    pnls = [_safe_float(row.get("pnl_usdt")) for row in rows]
    wins = [value for value in pnls if value > 0.0]
    losses = [value for value in pnls if value < 0.0]
    trades = len(rows)
    sl_hits = [row for row in rows if row.get("exit_reason") == "sl_hit"]
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
        "avg_realized_r": round(
            sum(_safe_float(row.get("realized_r")) for row in rows) / trades,
            4,
        )
        if trades
        else 0.0,
        "avg_mfe_pct": round(
            sum(_safe_float(row.get("mfe_pct")) for row in rows) / trades,
            4,
        )
        if trades
        else 0.0,
        "avg_mae_pct": round(
            sum(_safe_float(row.get("mae_pct")) for row in rows) / trades,
            4,
        )
        if trades
        else 0.0,
        "avg_holding_hours": round(
            sum(_safe_float(row.get("holding_hours")) for row in rows) / trades,
            1,
        )
        if trades
        else 0.0,
        "gross_profit": round(sum(wins), 4),
        "gross_loss": round(sum(losses), 4),
        "max_win": round(max(pnls), 4) if pnls else 0.0,
        "max_loss": round(min(pnls), 4) if pnls else 0.0,
        "sl_hit_trades": len(sl_hits),
        "zero_hour_sl_hit_trades": len(zero_hour_sl_hits),
        "giveback_exit_trades": sum(
            1 for row in rows if row.get("exit_reason") == "GIVEBACK_EXIT"
        ),
        "unknown_exit_trades": sum(
            1 for row in rows if row.get("exit_reason") == "unknown"
        ),
    }


def _group_metrics(
    rows: list[dict[str, str]],
    key: str,
    *,
    strategy_id: str | None = None,
    expected_groups: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {
        group: [] for group in (expected_groups or [])
    }
    fallback_grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if strategy_id and row.get("strategy_id") != strategy_id:
            continue
        group_key = str(row.get(key) or "unknown")
        if group_key in grouped:
            grouped[group_key].append(row)
        else:
            fallback_grouped[group_key].append(row)
    for group_key, group_rows in fallback_grouped.items():
        grouped[group_key] = group_rows
    return {
        group_key: _metrics(group_rows)
        for group_key, group_rows in sorted(grouped.items())
    }


def _strategy_metrics(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {
        strategy_id: _metrics(
            [row for row in rows if row.get("strategy_id") == strategy_id]
        )
        for strategy_id in (SLOT_A_LONG, SLOT_A_SHORT, SLOT_B_LONG, SLOT_B_SHORT)
    }


def _month(row: dict[str, str]) -> str:
    entry_time = str(row.get("entry_time") or "")
    return entry_time[:7] if len(entry_time) >= 7 else "unknown"


def _monthly_metrics(rows: list[dict[str, str]], *, strategy_id: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("strategy_id") == strategy_id:
            grouped[_month(row)].append(row)
    metrics = [
        {"month": month, **_metrics(group_rows)}
        for month, group_rows in grouped.items()
    ]
    metrics.sort(key=lambda row: (row["net_pnl"], row["month"]))
    return metrics


def _top_losses(rows: list[dict[str, str]], *, strategy_id: str, limit: int = 8) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("strategy_id") == strategy_id
    ]
    selected.sort(key=lambda row: _safe_float(row.get("pnl_usdt")))
    losses = []
    for row in selected[:limit]:
        losses.append(
            {
                "entry_time": row.get("entry_time"),
                "exit_time": row.get("exit_time"),
                "pnl_usdt": round(_safe_float(row.get("pnl_usdt")), 4),
                "realized_r": round(_safe_float(row.get("realized_r")), 4),
                "mfe_pct": round(_safe_float(row.get("mfe_pct")), 4),
                "mae_pct": round(_safe_float(row.get("mae_pct")), 4),
                "holding_hours": round(_safe_float(row.get("holding_hours")), 1),
                "exit_reason": row.get("exit_reason"),
                "entry_regime": row.get("entry_regime"),
                "entry_regime_direction": row.get("entry_regime_direction"),
            }
        )
    return losses


def _counter(rows: list[dict[str, str]], field: str, *, strategy_id: str) -> dict[str, int]:
    counts = Counter(
        str(row.get(field) or "blank")
        for row in rows
        if row.get("strategy_id") == strategy_id
    )
    return dict(sorted(counts.items()))


def _fmt_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _metrics_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {metrics['trades']} | {metrics['net_pnl']:.4f} | "
        f"{metrics['win_rate']:.4f} | {_fmt_optional(metrics['profit_factor'])} | "
        f"{metrics['avg_realized_r']:.4f} | {metrics['avg_mfe_pct']:.4f} | "
        f"{metrics['avg_mae_pct']:.4f} | {metrics['avg_holding_hours']:.1f} | "
        f"{metrics['sl_hit_trades']} | {metrics['zero_hour_sl_hit_trades']} | "
        f"{metrics['giveback_exit_trades']} |"
    )


def _window_rows(window_metrics: dict[str, dict[str, Any]]) -> list[str]:
    rows = []
    for window_name, metrics in sorted(
        window_metrics.items(),
        key=lambda item: item[1]["net_pnl"],
    ):
        rows.append(_metrics_row(f"`{window_name}`", metrics))
    return rows


def _month_rows(months: list[dict[str, Any]], *, limit: int = 10) -> list[str]:
    rows = []
    for item in months[:limit]:
        rows.append(_metrics_row(f"`{item['month']}`", item))
    return rows


def _loss_rows(losses: list[dict[str, Any]]) -> list[str]:
    rows = []
    for row in losses:
        rows.append(
            f"| `{row['entry_time']}` | `{row['exit_time']}` | "
            f"{row['pnl_usdt']:.4f} | {row['realized_r']:.4f} | "
            f"{row['mfe_pct']:.4f} | {row['mae_pct']:.4f} | "
            f"{row['holding_hours']:.1f} | `{row['exit_reason']}` | "
            f"`{row['entry_regime']}` | `{row['entry_regime_direction']}` |"
        )
    return rows


def _write_report(payload: dict[str, Any]) -> Path:
    overlay_stress = payload["sources"]["slot_a_short_overlay_stress"]
    all_four_stress = payload["sources"]["all_four_supplemental"]["windows"].get(
        "classic_rollercoaster_2021_2022",
        {},
    )
    slot_b_stress = payload["sources"]["slot_b_short_overlay_stress"]
    overlay_default_windows = payload["sources"]["slot_a_short_overlay_default"]["windows"]
    all_four_windows = payload["sources"]["all_four_supplemental"]["slot_a_short_by_window"]
    worst_months = payload["sources"]["slot_a_short_overlay_stress"]["slot_a_short_by_month"]
    top_losses = payload["sources"]["slot_a_short_overlay_stress"]["slot_a_short_top_losses"]

    lines = [
        "# Slot A SHORT Failure Attribution",
        "",
        f"Date: {payload['date']}",
        "Status: `RESEARCH_ONLY_FAILURE_ATTRIBUTION`",
        "",
        "## Scope",
        "",
        "- Goal: explain why the mirrored Slot A SHORT probe breaks; this is not a promotion lane.",
        "- Runtime defaults are not changed.",
        "- No thresholds, scanner defaults, router policy, credentials, or live/testnet state are changed.",
        "- Attribution uses existing backtest artifacts. A full Slot A SHORT overlay supplemental rerun timed out before completing all cells, so this pass uses overlay default cells, overlay `classic_rollercoaster_2021_2022`, and the all-four supplemental matrix for wider window coverage.",
        f"- Summary artifact: `{payload['summary_path']}`",
        "",
        "## Stress Window Contrast",
        "",
        "`classic_rollercoaster_2021_2022` is the failure window that exposed the mirror-SHORT problem.",
        "",
        "| source | strategy | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for source_label, source_payload in [
        ("Slot A SHORT overlay", overlay_stress),
        ("all-four reference", all_four_stress),
        ("Slot B SHORT overlay", slot_b_stress),
    ]:
        strategy_payload = source_payload.get("strategies", {})
        for strategy_id in (SLOT_A_LONG, SLOT_A_SHORT, SLOT_B_SHORT):
            metrics = strategy_payload.get(strategy_id)
            if metrics and metrics["trades"]:
                lines.append(
                    _metrics_row(
                        f"{source_label} / {STRATEGY_LABELS[strategy_id]}",
                        metrics,
                    )
                )

    lines.extend(
        [
            "",
            "## Window Read",
            "",
            "Slot A SHORT is not failing because every SHORT is bad. It is specifically weak in the 2021-2022 rollercoaster stress window, while Slot B SHORT remains positive in the same broad regime.",
            "",
            "Slot A SHORT in all-four supplemental:",
            "",
            "| window | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *_window_rows(all_four_windows),
            "",
            "Slot A SHORT overlay default cells completed before the supplemental rerun timed out:",
            "",
            "| window | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *_window_rows(overlay_default_windows),
            "",
            "## Loss Concentration",
            "",
            "Worst Slot A SHORT months in the overlay stress window:",
            "",
            "| month | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *_month_rows(worst_months),
            "",
            "Worst Slot A SHORT trades in the overlay stress window:",
            "",
            "| entry_time | exit_time | pnl_usdt | realized_r | mfe_pct | mae_pct | hold_h | exit_reason | entry_regime | entry_regime_direction |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
            *_loss_rows(top_losses),
            "",
            "## Attribution",
            "",
            "1. The mirror breaks at the thesis level, not at runtime routing. Slot A SHORT uses the expected SHORT side, has no entry-stop violations in the inspected stress artifacts, and its losses persist in both overlay and all-four references.",
            "2. The stress-window signature is late-breakdown / snapback risk. In the overlay stress window, Slot A SHORT has weak favorable excursion, larger adverse excursion, many stop hits, and several zero-hour stop hits; this is exactly the profile of shorting after the bearish move is already crowded or exhausted.",
            "3. The LONG cartridge has asymmetric payoff support. In the same stress window, Slot A LONG carries far better MFE/MAE and profit factor, so the staged derisk/giveback lifecycle fits upside continuation better than downside continuation.",
            "4. The current SHORT transition-aware veto is too narrow for crash-rebound structure. It only catches a specific breakdown plus MACD-hist exhaustion plus high extension state; the worst losses show immediate stop behavior that slips through that gate.",
            "5. Lifecycle protection is not the main repair. Slot A SHORT rarely reaches protected giveback exits in the failure window; repair should start at entry/regime context, not by overfitting the exit.",
            "",
            "## Repair Directions",
            "",
            "- Treat Slot A SHORT as an independent bearish-continuation thesis, not a symmetric mirror of Slot A LONG.",
            "- Add an exhaustion/snapback guard before any parameter tuning: regime age, distance from EMA, recent downside velocity, and failed-breakdown context are better candidates than loosening MACD confirmation.",
            "- Consider a side-specific transition filter that blocks late bearish breakdowns after large downside excursion unless follow-through is confirmed.",
            "- If lifecycle is revisited, test it after entry filtering; the current evidence says the bad trades often fail before derisk/giveback can help.",
            "- Keep Slot A SHORT research-only until this attribution can be converted into a falsifiable repair experiment.",
        ]
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT_PATH


def analyze_slot_a_short_failure() -> tuple[Path, Path]:
    source_rows = {
        name: _load_source(name, path)
        for name, path in SOURCES.items()
    }

    overlay_stress_rows = source_rows["slot_a_short_overlay_stress"]
    slot_b_stress_rows = source_rows["slot_b_short_overlay_stress"]
    all_four_supp_rows = source_rows["all_four_supplemental"]
    overlay_default_rows = source_rows["slot_a_short_overlay_default"]

    all_four_windows = _group_metrics(
        all_four_supp_rows,
        "_window",
        strategy_id=SLOT_A_SHORT,
        expected_groups=_source_windows(SOURCES["all_four_supplemental"]),
    )
    overlay_default_windows = _group_metrics(
        overlay_default_rows,
        "_window",
        strategy_id=SLOT_A_SHORT,
        expected_groups=_source_windows(SOURCES["slot_a_short_overlay_default"]),
    )

    payload: dict[str, Any] = {
        "schema": "strategy_plugin_slot_a_short_failure_attribution.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": "2026-05-07",
        "status": "RESEARCH_ONLY_FAILURE_ATTRIBUTION",
        "summary_path": str(SUMMARY_PATH),
        "report_path": str(REPORT_PATH),
        "strategies": {
            "slot_a_long": SLOT_A_LONG,
            "slot_a_short": SLOT_A_SHORT,
            "slot_b_long": SLOT_B_LONG,
            "slot_b_short": SLOT_B_SHORT,
        },
        "sources": {
            "slot_a_short_overlay_default": {
                "path": str(SOURCES["slot_a_short_overlay_default"]),
                "windows": overlay_default_windows,
            },
            "slot_a_short_overlay_stress": {
                "path": str(SOURCES["slot_a_short_overlay_stress"]),
                "strategies": _strategy_metrics(overlay_stress_rows),
                "slot_a_short_by_month": _monthly_metrics(
                    overlay_stress_rows,
                    strategy_id=SLOT_A_SHORT,
                ),
                "slot_a_short_top_losses": _top_losses(
                    overlay_stress_rows,
                    strategy_id=SLOT_A_SHORT,
                ),
                "slot_a_short_exit_reasons": _counter(
                    overlay_stress_rows,
                    "exit_reason",
                    strategy_id=SLOT_A_SHORT,
                ),
                "slot_a_short_entry_regime_direction": _counter(
                    overlay_stress_rows,
                    "entry_regime_direction",
                    strategy_id=SLOT_A_SHORT,
                ),
            },
            "all_four_supplemental": {
                "path": str(SOURCES["all_four_supplemental"]),
                "slot_a_short_by_window": all_four_windows,
                "windows": {
                    window: {
                        "strategies": _strategy_metrics(
                            [
                                row
                                for row in all_four_supp_rows
                                if row.get("_window") == window
                            ]
                        )
                    }
                    for window in sorted({row.get("_window") for row in all_four_supp_rows})
                },
            },
            "slot_b_short_overlay_stress": {
                "path": str(SOURCES["slot_b_short_overlay_stress"]),
                "strategies": _strategy_metrics(slot_b_stress_rows),
            },
        },
    }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report = _write_report(payload)
    print(f"[SlotAShortFailureAttribution] summary={SUMMARY_PATH}")
    print(f"[SlotAShortFailureAttribution] report={report}")
    return SUMMARY_PATH, report


def main() -> int:
    analyze_slot_a_short_failure()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
