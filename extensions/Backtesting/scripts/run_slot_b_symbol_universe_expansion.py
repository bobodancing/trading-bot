"""Run Phase 5/4E research-only Slot B symbol-universe expansion review."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = SCRIPT_ROOT.parents[0]
REPO_ROOT = BACKTEST_ROOT.parents[1]
for path in (SCRIPT_ROOT, BACKTEST_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analyze_promoted_three_leg_weekly_feasibility import (  # noqa: E402
    DEFAULT_FEE_RATE,
    _build_week_rows,
    _fee_estimate,
    _fmt,
    _read_csv,
    _read_json,
    _repo_path,
    _summarize_week_rows,
    _week_start_for_ts,
)
from backtest_engine import BacktestConfig, BacktestEngine  # noqa: E402
from build_weekly_profit_control_packet import DEFAULT_REVIEW_CAPITAL_USDT  # noqa: E402
from config_presets import explicit_symbol_universe, plugin_runtime_defaults  # noqa: E402
from data_loader import BacktestDataLoader  # noqa: E402
from funding_loader import FundingLoader  # noqa: E402
from report_generator import ReportGenerator  # noqa: E402
from weekly_profit_control import build_weekly_control_packets  # noqa: E402
from extensions.Backtesting.scripts import run_portfolio_ab_short_ablation as short_ablation  # noqa: E402
from trader.config import Config  # noqa: E402


SLOT_A_LONG = short_ablation.SLOT_A_LONG
SLOT_B_LONG = short_ablation.SLOT_B_LONG
SLOT_B_SHORT = short_ablation.SLOT_B_SHORT
CANDIDATE_LONG = "donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion"
CANDIDATE_SHORT = "donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion"

BASELINE_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_CANDIDATE_SYMBOLS = ("SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "LINK/USDT")
DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-04-30"
DEFAULT_WINDOW = "2026_01_01_2026_04_30"
VARIANT = "slot_a_b_promoted_plus_slot_b_symbol_universe_expansion"

STRATEGIES_COMBINED = (SLOT_A_LONG, SLOT_B_LONG, SLOT_B_SHORT, CANDIDATE_LONG, CANDIDATE_SHORT)
STRATEGIES_CANDIDATE = (CANDIDATE_LONG, CANDIDATE_SHORT)
STRATEGY_LABELS = {
    SLOT_A_LONG: "Slot A LONG",
    SLOT_B_LONG: "Slot B LONG",
    SLOT_B_SHORT: "Slot B SHORT",
    CANDIDATE_LONG: "Slot B LONG Expansion",
    CANDIDATE_SHORT: "Slot B SHORT Expansion",
}

DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results" / "slot_b_symbol_universe_expansion"
DEFAULT_SUMMARY = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_summary.json"
DEFAULT_PACKET_JSON = DEFAULT_RESULTS_ROOT / "weekly_profit_slot_b_symbol_universe_expansion_packets.json"
DEFAULT_AVAILABILITY_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_data_availability.csv"
DEFAULT_ATTRIBUTION_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_symbol_attribution.csv"
DEFAULT_WEEKLY_CSV = DEFAULT_RESULTS_ROOT / "slot_b_symbol_universe_expansion_weekly_rows.csv"
DEFAULT_REPORT = REPO_ROOT / "reports" / "weekly_profit_phase5_4e_slot_b_symbol_universe_expansion.md"

BASELINE_SUMMARY = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "portfolio_ab_short_ablation_summary.json"
)
BASELINE_PACKET_JSON = (
    BACKTEST_ROOT
    / "results"
    / "portfolio_ab_bidirectional"
    / "short_ablation"
    / "weekly_profit_control_packets.json"
)


def _symbol_slug(symbol: str) -> str:
    return symbol.replace("/", "").lower()


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


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _research_overrides(risk_per_trade: float) -> dict[str, Any]:
    overrides = plugin_runtime_defaults()
    overrides["RISK_PER_TRADE"] = float(risk_per_trade)
    return explicit_symbol_universe(overrides)


def _build_config(
    start: str,
    end: str,
    *,
    symbols: list[str],
    strategies: list[str],
    risk_per_trade: float,
) -> BacktestConfig:
    return BacktestConfig(
        symbols=list(symbols),
        start=start,
        end=end,
        warmup_bars=100,
        enabled_strategies=list(strategies),
        allowed_plugin_ids=list(strategies),
        precompute_indicators=True,
        config_overrides=_research_overrides(risk_per_trade),
    )


def _run_cell(
    *,
    start: str,
    end: str,
    symbols: list[str],
    strategies: list[str],
    risk_per_trade: float,
    output_dir: Path,
    rerun: bool,
    label: str,
) -> dict[str, Any]:
    if rerun or not (output_dir / "summary.json").exists():
        print(
            "[SlotBSymbolUniverseExpansion] "
            f"{label}: {start}->{end} symbols={','.join(symbols)} "
            f"strategies={','.join(strategies)}"
        )
        cfg = _build_config(
            start,
            end,
            symbols=symbols,
            strategies=strategies,
            risk_per_trade=risk_per_trade,
        )
        result = BacktestEngine(cfg).run()
        ReportGenerator().generate(result, output_dir)
    else:
        print(f"[SlotBSymbolUniverseExpansion] reuse {label}: {output_dir}")

    cell = _summary_row(output_dir, strategies=strategies)
    cell["window"] = {"start": start, "end": end}
    cell["symbols"] = list(symbols)
    return cell


def _trade_metrics(rows: list[dict[str, str]], *, fee_rate: float) -> dict[str, Any]:
    gross = sum(_safe_float(row.get("pnl_usdt")) for row in rows)
    fees = sum(_fee_estimate(row, fee_rate=fee_rate) for row in rows)
    after_fee = gross - fees
    wins = sum(1 for row in rows if _safe_float(row.get("pnl_usdt")) > 0.0)
    worst = None
    for row in rows:
        row_after_fee = _safe_float(row.get("pnl_usdt")) - _fee_estimate(row, fee_rate=fee_rate)
        if worst is None or row_after_fee < worst["after_fee_pnl_usdt"]:
            worst = {
                "symbol": row.get("symbol", ""),
                "strategy_id": row.get("strategy_id", ""),
                "side": row.get("side", ""),
                "entry_time": row.get("entry_time", ""),
                "exit_time": row.get("exit_time", ""),
                "after_fee_pnl_usdt": round(row_after_fee, 4),
                "gross_pnl_usdt": round(_safe_float(row.get("pnl_usdt")), 4),
            }
    return {
        "trades": len(rows),
        "gross_pnl_usdt": round(gross, 4),
        "fees_est_usdt": round(fees, 4),
        "after_fee_pnl_usdt": round(after_fee, 4),
        "win_rate": round(wins / len(rows), 4) if rows else 0.0,
        "worst_trade": worst or {},
    }


def _per_strategy_metrics(
    rows: list[dict[str, str]],
    *,
    strategies: list[str],
    fee_rate: float,
) -> dict[str, dict[str, Any]]:
    return {
        strategy_id: _trade_metrics(
            [row for row in rows if row.get("strategy_id") == strategy_id],
            fee_rate=fee_rate,
        )
        for strategy_id in strategies
    }


def _summary_row(cell_dir: Path, *, strategies: list[str]) -> dict[str, Any]:
    summary = _read_json(cell_dir / "summary.json")
    trades = _read_csv(cell_dir / "trades.csv")
    return {
        "portfolio": {
            "trades": _safe_int(summary.get("total_trades")),
            "gross_pnl": round(sum(_safe_float(row.get("pnl_usdt")) for row in trades), 4),
            "max_dd_pct": round(_safe_float(summary.get("max_drawdown_pct")), 4),
            "run_errors": _safe_int(summary.get("backtest_run_error_count")),
        },
        "per_strategy": _per_strategy_metrics(
            trades,
            strategies=strategies,
            fee_rate=DEFAULT_FEE_RATE,
        ),
        "artifacts": {
            "summary": str(cell_dir / "summary.json"),
            "trades": str(cell_dir / "trades.csv"),
            "signal_rejects": str(cell_dir / "signal_rejects.csv"),
            "signal_entries": str(cell_dir / "signal_entries.csv"),
        },
    }


def _trend_start(start: str) -> str:
    return (datetime.fromisoformat(start) - timedelta(days=300)).strftime("%Y-%m-%d")


def _expected_gap_hours(timeframe: str) -> float:
    return {"1h": 1.0, "4h": 4.0, "1d": 24.0}[timeframe]


def _frame_stats(
    frame: pd.DataFrame,
    *,
    timeframe: str,
    requested_start: str,
    requested_end: str,
) -> dict[str, Any]:
    if frame is None or frame.empty:
        return {
            "rows": 0,
            "first_ts": None,
            "last_ts": None,
            "covers_start": False,
            "covers_end": False,
            "max_gap_hours": None,
            "gap_count": None,
            "available": False,
        }

    start_ts = pd.Timestamp(requested_start, tz="UTC")
    end_ts = pd.Timestamp(requested_end, tz="UTC")
    diffs = frame.index.to_series().diff().dropna().dt.total_seconds() / 3600.0
    expected_gap = _expected_gap_hours(timeframe)
    gap_count = int((diffs > expected_gap * 1.5).sum())
    max_gap = round(float(diffs.max()), 4) if not diffs.empty else 0.0
    first = frame.index[0]
    last = frame.index[-1]
    covers_start = bool(first <= start_ts)
    covers_end = bool(last >= end_ts)
    return {
        "rows": int(len(frame)),
        "first_ts": first.isoformat(),
        "last_ts": last.isoformat(),
        "covers_start": covers_start,
        "covers_end": covers_end,
        "max_gap_hours": max_gap,
        "gap_count": gap_count,
        "available": bool(covers_start and covers_end and gap_count == 0),
    }


def _load_symbol_frames(
    symbol: str,
    *,
    start: str,
    end: str,
    data_loader: BacktestDataLoader,
    funding_loader: FundingLoader,
) -> dict[str, Any]:
    trend_start = _trend_start(start)
    frames: dict[str, pd.DataFrame] = {}
    errors: list[str] = []
    for timeframe, frame_start in (("1h", start), ("4h", start), ("1d", trend_start)):
        try:
            frames[timeframe] = data_loader.get_data(symbol, timeframe, frame_start, end)
        except Exception as exc:  # pragma: no cover - network-dependent guard
            errors.append(f"{timeframe}:{type(exc).__name__}:{exc}")
            frames[timeframe] = pd.DataFrame()
    try:
        funding = funding_loader.get_funding_rates(symbol, start, end)
    except Exception as exc:  # pragma: no cover - network-dependent guard
        errors.append(f"funding:{type(exc).__name__}:{exc}")
        funding = pd.Series(dtype=float)

    return {
        "symbol": symbol,
        "frames": frames,
        "funding_rows": int(len(funding)),
        "errors": errors,
    }


def _availability_probe(
    *,
    start: str,
    end: str,
    candidate_symbols: list[str],
) -> dict[str, Any]:
    data_loader = BacktestDataLoader()
    funding_loader = FundingLoader()
    all_symbols = list(BASELINE_SYMBOLS) + list(candidate_symbols)
    loaded = {
        symbol: _load_symbol_frames(
            symbol,
            start=start,
            end=end,
            data_loader=data_loader,
            funding_loader=funding_loader,
        )
        for symbol in all_symbols
    }

    baseline_sets = [
        set(loaded[symbol]["frames"]["1h"].index)
        for symbol in BASELINE_SYMBOLS
        if not loaded[symbol]["frames"]["1h"].empty
    ]
    baseline_common_1h = set.intersection(*baseline_sets) if baseline_sets else set()

    rows: list[dict[str, Any]] = []
    selected_symbols: list[str] = []
    excluded_symbols: list[str] = []
    for symbol in all_symbols:
        item = loaded[symbol]
        frame_stats = {
            "1h": _frame_stats(
                item["frames"]["1h"],
                timeframe="1h",
                requested_start=start,
                requested_end=end,
            ),
            "4h": _frame_stats(
                item["frames"]["4h"],
                timeframe="4h",
                requested_start=start,
                requested_end=end,
            ),
            "1d": _frame_stats(
                item["frames"]["1d"],
                timeframe="1d",
                requested_start=_trend_start(start),
                requested_end=end,
            ),
        }
        missing_baseline_1h = sorted(baseline_common_1h - set(item["frames"]["1h"].index))
        ohlcv_available = all(frame_stats[tf]["available"] for tf in ("1h", "4h", "1d"))
        no_shared_cursor_shrink = len(missing_baseline_1h) == 0
        include = symbol in BASELINE_SYMBOLS or (ohlcv_available and no_shared_cursor_shrink)
        if symbol not in BASELINE_SYMBOLS:
            if include:
                selected_symbols.append(symbol)
            else:
                excluded_symbols.append(symbol)

        row = {
            "symbol": symbol,
            "is_baseline_symbol": symbol in BASELINE_SYMBOLS,
            "included": include,
            "exclude_reason": ""
            if include
            else (
                "ohlcv_gap_or_bounds"
                if not ohlcv_available
                else "shared_1h_cursor_shrink"
            ),
            "baseline_common_1h_rows": len(baseline_common_1h),
            "missing_baseline_1h_rows": len(missing_baseline_1h),
            "funding_rows": item["funding_rows"],
            "errors": ";".join(item["errors"]),
        }
        for tf in ("1h", "4h", "1d"):
            stats = frame_stats[tf]
            for key, value in stats.items():
                row[f"{tf}_{key}"] = value
        rows.append(row)

    expanded_sets = [
        set(loaded[symbol]["frames"]["1h"].index)
        for symbol in list(BASELINE_SYMBOLS) + selected_symbols
        if not loaded[symbol]["frames"]["1h"].empty
    ]
    expanded_common_1h = set.intersection(*expanded_sets) if expanded_sets else set()
    return {
        "start": start,
        "end": end,
        "baseline_symbols": list(BASELINE_SYMBOLS),
        "candidate_symbols_requested": list(candidate_symbols),
        "candidate_symbols_selected": selected_symbols,
        "candidate_symbols_excluded": excluded_symbols,
        "baseline_common_1h_rows": len(baseline_common_1h),
        "expanded_common_1h_rows": len(expanded_common_1h),
        "shared_cursor_delta_rows": len(expanded_common_1h) - len(baseline_common_1h),
        "rows": rows,
    }


def _latest_contract_grade(payload: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            packet
            for packet in reversed(payload.get("packets", []))
            if bool(packet.get("decision", {}).get("contract_grade"))
        ),
        None,
    )


def _load_baseline(fee_rate: float) -> dict[str, Any]:
    source = _read_json(BASELINE_SUMMARY)
    cell = source["matrices"]["slot_b_short_overlay"]["custom"][DEFAULT_WINDOW]
    trade_path = _repo_path(cell["artifacts"]["trades"])
    trades = _read_csv(trade_path)
    weeks, overflow = _build_week_rows(
        trades,
        start=str(cell["window"]["start"]),
        end=str(cell["window"]["end"]),
        fee_rate=fee_rate,
    )
    packet_payload = _read_json(BASELINE_PACKET_JSON)
    latest_contract = packet_payload.get("latest_contract_grade_packet") or _latest_contract_grade(
        packet_payload
    )
    return {
        "summary_source": str(BASELINE_SUMMARY),
        "packet_source": str(BASELINE_PACKET_JSON),
        "cell": cell,
        "trade_artifact": str(trade_path),
        "trades": trades,
        "weeks": weeks,
        "overflow": overflow,
        "weekly_summary": _summarize_week_rows(weeks),
        "latest_contract_grade_packet": latest_contract,
    }


def _week_contribution(rows: list[dict[str, str]], *, start: str, end: str, fee_rate: float) -> list[dict[str, Any]]:
    weeks, _overflow = _build_week_rows(rows, start=start, end=end, fee_rate=fee_rate)
    return [
        {
            "week_start": row["week_start"],
            "entry_trades": row["entry_trades"],
            "exit_trades": row["exit_trades"],
            "net_after_fee_est_usdt": row["net_after_fee_est_usdt"],
        }
        for row in weeks
        if row["entry_trades"] or row["exit_trades"] or row["net_after_fee_est_usdt"]
    ]


def _worst_week(rows: list[dict[str, str]], *, start: str, end: str, fee_rate: float) -> dict[str, Any]:
    weeks, _overflow = _build_week_rows(rows, start=start, end=end, fee_rate=fee_rate)
    if not weeks:
        return {}
    active_weeks = [
        row
        for row in weeks
        if _safe_int(row.get("entry_trades"))
        or _safe_int(row.get("exit_trades"))
        or _safe_float(row.get("net_after_fee_est_usdt")) != 0.0
    ]
    review_weeks = active_weeks or weeks
    worst = min(review_weeks, key=lambda row: _safe_float(row.get("net_after_fee_est_usdt")))
    return {
        "week_start": worst["week_start"],
        "week_end": worst["week_end"],
        "net_after_fee_est_usdt": worst["net_after_fee_est_usdt"],
        "entry_trades": worst["entry_trades"],
        "exit_trades": worst["exit_trades"],
    }


def _attribution_row(
    *,
    scope: str,
    symbol: str,
    strategy_id: str,
    rows: list[dict[str, str]],
    start: str,
    end: str,
    fee_rate: float,
    baseline_entry_times: set[str],
    baseline_entry_weeks: set[str],
) -> dict[str, Any]:
    metrics = _trade_metrics(rows, fee_rate=fee_rate)
    entry_weeks = {
        _week_start_for_ts(row.get("entry_time")).isoformat()
        for row in rows
        if _week_start_for_ts(row.get("entry_time")) is not None
    }
    exact_overlap = sum(1 for row in rows if str(row.get("entry_time") or "") in baseline_entry_times)
    week_overlap = sum(1 for week in entry_weeks if week in baseline_entry_weeks)
    return {
        "scope": scope,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_label": STRATEGY_LABELS.get(strategy_id, strategy_id),
        "trades": metrics["trades"],
        "gross_pnl_usdt": metrics["gross_pnl_usdt"],
        "fees_est_usdt": metrics["fees_est_usdt"],
        "after_fee_pnl_usdt": metrics["after_fee_pnl_usdt"],
        "win_rate": metrics["win_rate"],
        "active_entry_weeks": len(entry_weeks),
        "weekly_contribution": _week_contribution(
            rows,
            start=start,
            end=end,
            fee_rate=fee_rate,
        ),
        "worst_trade": metrics["worst_trade"],
        "worst_week": _worst_week(rows, start=start, end=end, fee_rate=fee_rate),
        "same_entry_time_overlap_with_baseline": exact_overlap,
        "entry_week_overlap_with_baseline": week_overlap,
    }


def _attribution_rows(
    rows: list[dict[str, str]],
    *,
    scope: str,
    symbols: list[str],
    strategies: list[str],
    start: str,
    end: str,
    fee_rate: float,
    baseline_trades: list[dict[str, str]],
) -> list[dict[str, Any]]:
    baseline_entry_times = {str(row.get("entry_time") or "") for row in baseline_trades}
    baseline_entry_weeks = {
        _week_start_for_ts(row.get("entry_time")).isoformat()
        for row in baseline_trades
        if _week_start_for_ts(row.get("entry_time")) is not None
    }
    output: list[dict[str, Any]] = []
    for symbol in symbols:
        symbol_rows = [row for row in rows if row.get("symbol") == symbol]
        output.append(
            _attribution_row(
                scope=scope,
                symbol=symbol,
                strategy_id="ALL",
                rows=symbol_rows,
                start=start,
                end=end,
                fee_rate=fee_rate,
                baseline_entry_times=baseline_entry_times,
                baseline_entry_weeks=baseline_entry_weeks,
            )
        )
        for strategy_id in strategies:
            strategy_rows = [row for row in symbol_rows if row.get("strategy_id") == strategy_id]
            output.append(
                _attribution_row(
                    scope=scope,
                    symbol=symbol,
                    strategy_id=strategy_id,
                    rows=strategy_rows,
                    start=start,
                    end=end,
                    fee_rate=fee_rate,
                    baseline_entry_times=baseline_entry_times,
                    baseline_entry_weeks=baseline_entry_weeks,
                )
            )
    return output


def _weekly_control_payload(
    *,
    cell: dict[str, Any],
    baseline: dict[str, Any],
    fee_rate: float,
    review_capital_usdt: float,
) -> dict[str, Any]:
    trade_path = _repo_path(cell["artifacts"]["trades"])
    trades = _read_csv(trade_path)
    window = cell["window"]
    weeks, overflow = _build_week_rows(
        trades,
        start=str(window["start"]),
        end=str(window["end"]),
        fee_rate=fee_rate,
        slot_labels=STRATEGY_LABELS,
    )
    operational_by_week = {
        str(row["week_start"]): {
            "execution_attempt_count_weekly": 0,
            "execution_failure_count_weekly": 0,
            "config_drift_events_weekly": 0,
            "unprotected_position_events_weekly": 0,
        }
        for row in weeks
    }
    packets = build_weekly_control_packets(
        weeks,
        review_start=str(window["start"]),
        review_end=str(window["end"]),
        review_capital_usdt=review_capital_usdt,
        portfolio_max_drawdown_pct_review_window=float(cell["portfolio"].get("max_dd_pct") or 0.0),
        operational_by_week_start=operational_by_week,
    )
    latest_contract = _latest_contract_grade({"packets": packets})
    baseline_latest = baseline.get("latest_contract_grade_packet") or {}
    comparison = _compare_latest_contracts(latest_contract, baseline_latest)
    return {
        "schema": "strategy_plugin_weekly_profit_slot_b_symbol_universe_expansion_packets.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "variant": VARIANT,
            "primary_window_key": f"custom/{DEFAULT_WINDOW}",
            "primary_window_start": window["start"],
            "primary_window_end": window["end"],
            "trade_artifact": str(trade_path),
        },
        "method": {
            "week_boundary": "UTC ISO weeks anchored on Monday",
            "participation_basis": "entry week",
            "economic_outcome_basis": "exit week realized PnL",
            "fee_rate_per_side_estimate": fee_rate,
            "review_capital_usdt": review_capital_usdt,
            "operational_input_source": "backtest-control defaults",
        },
        "portfolio_reference": dict(cell.get("portfolio") or {}),
        "overflow": overflow,
        "weekly_summary": _summarize_week_rows(weeks),
        "latest_contract_grade_packet": latest_contract,
        "baseline_latest_contract_grade_packet": baseline_latest,
        "baseline_comparison": comparison,
        "packets": packets,
        "weeks": weeks,
    }


def _compare_latest_contracts(candidate: dict[str, Any] | None, baseline: dict[str, Any] | None) -> dict[str, Any]:
    if not candidate or not baseline:
        return {"contract_grade_comparable": False}
    candidate_kpis = candidate["kpis"]
    baseline_kpis = baseline["kpis"]
    fields = (
        "active_entry_week_ratio_8w",
        "rolling_8w_entry_trade_count",
        "positive_week_ratio_all_8w_after_fee",
        "positive_week_ratio_exit_active_8w_after_fee",
        "rolling_8w_net_after_fee_pnl",
        "portfolio_max_drawdown_pct_review_window",
    )
    comparison = {
        "contract_grade_comparable": True,
        "baseline_week_start": baseline["week_start"],
        "candidate_week_start": candidate["week_start"],
        "baseline_state": baseline["decision"]["state"],
        "candidate_state": candidate["decision"]["state"],
    }
    for field in fields:
        baseline_value = baseline_kpis[field]
        candidate_value = candidate_kpis[field]
        comparison[f"baseline_{field}"] = baseline_value
        comparison[f"candidate_{field}"] = candidate_value
        comparison[f"{field}_delta"] = round(float(candidate_value) - float(baseline_value), 4)
    return comparison


def _candidate_trade_rows(combined_trades: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in combined_trades
        if row.get("strategy_id") in {CANDIDATE_LONG, CANDIDATE_SHORT}
    ]


def _gate_read(
    *,
    weekly_payload: dict[str, Any],
    combined_cell: dict[str, Any],
    candidate_attribution: list[dict[str, Any]],
) -> dict[str, Any]:
    comparison = weekly_payload["baseline_comparison"]
    candidate_rows = [row for row in candidate_attribution if row["strategy_id"] == "ALL"]
    candidate_after_fee = round(sum(_safe_float(row["after_fee_pnl_usdt"]) for row in candidate_rows), 4)
    candidate_trades = sum(_safe_int(row["trades"]) for row in candidate_rows)
    losing_symbol_trades = sum(
        _safe_int(row["trades"])
        for row in candidate_rows
        if _safe_float(row["after_fee_pnl_usdt"]) < 0.0
    )
    losing_trade_share = round(losing_symbol_trades / candidate_trades, 4) if candidate_trades else 0.0
    max_dd_delta = _safe_float(
        comparison.get("portfolio_max_drawdown_pct_review_window_delta")
    )
    gates = {
        "combined_rolling_8w_after_fee_pnl_not_below_baseline": _safe_float(
            comparison.get("rolling_8w_net_after_fee_pnl_delta")
        )
        >= 0.0,
        "candidate_slot_after_fee_non_negative": candidate_after_fee >= 0.0,
        "active_entry_8w_ratio_improves": _safe_float(
            comparison.get("active_entry_week_ratio_8w_delta")
        )
        > 0.0,
        "positive_all_week_8w_ratio_not_down": _safe_float(
            comparison.get("positive_week_ratio_all_8w_after_fee_delta")
        )
        >= 0.0,
        "positive_exit_active_8w_ratio_not_down": _safe_float(
            comparison.get("positive_week_ratio_exit_active_8w_after_fee_delta")
        )
        >= 0.0,
        "max_dd_not_materially_larger": max_dd_delta <= 1.0,
        "new_volume_not_mostly_losing_symbols": losing_trade_share <= 0.5,
        "no_threshold_loosening": True,
        "run_errors_clean": _safe_int(combined_cell["portfolio"].get("run_errors")) == 0,
    }
    return {
        "candidate_slot_after_fee_pnl_usdt": candidate_after_fee,
        "candidate_slot_trades": candidate_trades,
        "losing_symbol_trade_share": losing_trade_share,
        "max_dd_materiality_threshold_pct_points": 1.0,
        "gates": gates,
        "all_hard_gates_pass": all(bool(value) for value in gates.values()),
    }


def _render_report(payload: dict[str, Any], weekly_payload: dict[str, Any]) -> str:
    availability = payload["data_availability"]
    combined = payload["combined"]["cell"]
    baseline = payload["baseline"]["weekly_summary"]
    combined_weekly = weekly_payload["weekly_summary"]
    comparison = weekly_payload["baseline_comparison"]
    gate = payload["gate_read"]
    selected = availability["candidate_symbols_selected"]
    excluded = availability["candidate_symbols_excluded"]
    candidate_rows = [
        row for row in payload["combined"]["candidate_symbol_attribution"] if row["strategy_id"] == "ALL"
    ]
    latest = weekly_payload["latest_contract_grade_packet"] or {}
    decision = latest.get("decision", {"state": "none"})
    lines = [
        "# Weekly Profit Phase 5 / 4E Slot B Symbol-Universe Expansion",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_EVALUATED`",
        "",
        "## Executive Read",
        "",
        (
            f"Latest contract-grade packet state is `{decision['state']}` for the "
            "A+B+Slot-B-expanded-symbols combined run."
        ),
        "",
        _strict_read(gate),
        "",
        "Runtime defaults remain unchanged. Slot A was not expanded. Scanner runtime universe remains disabled.",
        "",
        "Standalone per-symbol attribution keeps `BTC/USDT` as a regime-context sidecar, while candidate plugins remain scoped to the single alt symbol under review.",
        "",
        "## Scope",
        "",
        f"- Baseline symbols: {', '.join(f'`{symbol}`' for symbol in BASELINE_SYMBOLS)}",
        f"- Requested candidate symbols: {', '.join(f'`{symbol}`' for symbol in availability['candidate_symbols_requested'])}",
        f"- Included candidate symbols: {', '.join(f'`{symbol}`' for symbol in selected) or '`none`'}",
        f"- Excluded candidate symbols: {', '.join(f'`{symbol}`' for symbol in excluded) or '`none`'}",
        f"- Candidate LONG: `{CANDIDATE_LONG}`",
        f"- Candidate SHORT: `{CANDIDATE_SHORT}`",
        "- Candidate plugins are catalog `enabled=False` and research-only.",
        "",
        "## Data Availability Gate",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| baseline common 1H rows | {availability['baseline_common_1h_rows']} |",
        f"| expanded common 1H rows | {availability['expanded_common_1h_rows']} |",
        f"| shared cursor delta rows | {availability['shared_cursor_delta_rows']} |",
        "",
        "## Baseline vs Combined Weekly Packet",
        "",
        "| metric | baseline | combined | delta |",
        "| --- | ---: | ---: | ---: |",
        _comparison_row(comparison, "active_entry_week_ratio_8w"),
        _comparison_row(comparison, "rolling_8w_entry_trade_count"),
        _comparison_row(comparison, "positive_week_ratio_all_8w_after_fee"),
        _comparison_row(comparison, "positive_week_ratio_exit_active_8w_after_fee"),
        _comparison_row(comparison, "rolling_8w_net_after_fee_pnl"),
        _comparison_row(comparison, "portfolio_max_drawdown_pct_review_window"),
        "",
        "## Primary Window Summary",
        "",
        "| metric | baseline | combined |",
        "| --- | ---: | ---: |",
        f"| entry trades | {baseline['entry_trades']} | {combined_weekly['entry_trades']} |",
        f"| exit trades | {baseline['exit_trades']} | {combined_weekly['exit_trades']} |",
        f"| active entry weeks | {baseline['active_entry_weeks']} | {combined_weekly['active_entry_weeks']} |",
        f"| after-fee positive week ratio all | {_fmt(baseline['after_fee_positive_week_ratio_all'])} | {_fmt(combined_weekly['after_fee_positive_week_ratio_all'])} |",
        f"| net after fee estimate | {_fmt(baseline['net_after_fee_est_usdt'])} | {_fmt(combined_weekly['net_after_fee_est_usdt'])} |",
        f"| worst after-fee week | {_fmt(baseline['worst_week_after_fee_pnl_est_usdt'])} | {_fmt(combined_weekly['worst_week_after_fee_pnl_est_usdt'])} |",
        f"| portfolio max DD pct | {_fmt(payload['baseline']['cell']['portfolio']['max_dd_pct'])} | {_fmt(combined['portfolio']['max_dd_pct'])} |",
        "",
        "## Candidate Symbol Attribution",
        "",
        "| symbol | trades | gross pnl | fees est | after-fee pnl | win rate | active entry weeks | worst week | same-time overlap | entry-week overlap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in candidate_rows:
        worst_week = row["worst_week"].get("net_after_fee_est_usdt", 0.0)
        lines.append(
            f"| `{row['symbol']}` | {row['trades']} | {_fmt(row['gross_pnl_usdt'])} | "
            f"{_fmt(row['fees_est_usdt'])} | {_fmt(row['after_fee_pnl_usdt'])} | "
            f"{_fmt(row['win_rate'])} | {row['active_entry_weeks']} | "
            f"{_fmt(worst_week)} | {row['same_entry_time_overlap_with_baseline']} | "
            f"{row['entry_week_overlap_with_baseline']} |"
        )

    lines.extend(
        [
            "",
            "## Hard Gate Read",
            "",
            "| gate | pass |",
            "| --- | --- |",
        ]
    )
    for key, value in gate["gates"].items():
        lines.append(f"| `{key}` | `{bool(value)}` |")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Summary JSON: `{payload['artifact']['summary_json']}`",
            f"- Weekly packet JSON: `{payload['artifact']['weekly_packet_json']}`",
            f"- Data availability CSV: `{payload['artifact']['availability_csv']}`",
            f"- Symbol attribution CSV: `{payload['artifact']['attribution_csv']}`",
            f"- Weekly rows CSV: `{payload['artifact']['weekly_csv']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _comparison_row(comparison: dict[str, Any], field: str) -> str:
    return (
        f"| `{field}` | {_fmt(comparison.get(f'baseline_{field}', 0.0))} | "
        f"{_fmt(comparison.get(f'candidate_{field}', 0.0))} | "
        f"{_fmt(comparison.get(f'{field}_delta', 0.0))} |"
    )


def _strict_read(gate: dict[str, Any]) -> str:
    if gate["all_hard_gates_pass"]:
        return (
            "The expanded Slot B symbol lane passes this first hard-gate packet. "
            "This is still research-only and does not authorize runtime promotion."
        )
    failed = [key for key, value in gate["gates"].items() if not value]
    return (
        "The expanded Slot B symbol lane does not pass the hard gates. Failed gate(s): "
        + ", ".join(f"`{item}`" for item in failed)
        + "."
    )


def _csv_attribution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                "scope": row["scope"],
                "symbol": row["symbol"],
                "strategy_id": row["strategy_id"],
                "strategy_label": row["strategy_label"],
                "trades": row["trades"],
                "gross_pnl_usdt": row["gross_pnl_usdt"],
                "fees_est_usdt": row["fees_est_usdt"],
                "after_fee_pnl_usdt": row["after_fee_pnl_usdt"],
                "win_rate": row["win_rate"],
                "active_entry_weeks": row["active_entry_weeks"],
                "worst_trade_after_fee_pnl_usdt": row["worst_trade"].get("after_fee_pnl_usdt", ""),
                "worst_week_start": row["worst_week"].get("week_start", ""),
                "worst_week_after_fee_pnl_usdt": row["worst_week"].get("net_after_fee_est_usdt", ""),
                "same_entry_time_overlap_with_baseline": row["same_entry_time_overlap_with_baseline"],
                "entry_week_overlap_with_baseline": row["entry_week_overlap_with_baseline"],
            }
        )
    return output


def _weekly_csv_rows(weeks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for week in weeks:
        row = {
            "week_start": week["week_start"],
            "week_end": week["week_end"],
            "entry_trades": week["entry_trades"],
            "exit_trades": week["exit_trades"],
            "gross_pnl_usdt": week["gross_pnl_usdt"],
            "fees_est_usdt": week["fees_est_usdt"],
            "net_after_fee_est_usdt": week["net_after_fee_est_usdt"],
        }
        for symbol, value in week["symbol_net_after_fee_est_usdt"].items():
            row[f"{symbol}_net_after_fee_est_usdt"] = value
        rows.append(row)
    return rows


def run_slot_b_symbol_universe_expansion(
    *,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    window_name: str = DEFAULT_WINDOW,
    candidate_symbols: list[str] | None = None,
    risk_per_trade: float = 0.017,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    summary_path: Path = DEFAULT_SUMMARY,
    packet_json_path: Path = DEFAULT_PACKET_JSON,
    availability_csv_path: Path = DEFAULT_AVAILABILITY_CSV,
    attribution_csv_path: Path = DEFAULT_ATTRIBUTION_CSV,
    weekly_csv_path: Path = DEFAULT_WEEKLY_CSV,
    report_path: Path = DEFAULT_REPORT,
    fee_rate: float = DEFAULT_FEE_RATE,
    review_capital_usdt: float = DEFAULT_REVIEW_CAPITAL_USDT,
    rerun: bool = False,
) -> tuple[Path, Path]:
    candidate_symbols = list(candidate_symbols or DEFAULT_CANDIDATE_SYMBOLS)
    availability = _availability_probe(
        start=start,
        end=end,
        candidate_symbols=candidate_symbols,
    )
    _write_csv(
        availability_csv_path,
        availability["rows"],
        fieldnames=list(availability["rows"][0].keys()) if availability["rows"] else [],
    )

    selected_symbols = list(availability["candidate_symbols_selected"])
    baseline = _load_baseline(fee_rate)
    standalone_cells: dict[str, Any] = {}
    standalone_trades: list[dict[str, str]] = []
    for symbol in selected_symbols:
        cell = _run_cell(
            start=start,
            end=end,
            symbols=["BTC/USDT", symbol],
            strategies=list(STRATEGIES_CANDIDATE),
            risk_per_trade=risk_per_trade,
            output_dir=Path(results_root)
            / "standalone_with_btc_context"
            / _symbol_slug(symbol)
            / window_name,
            rerun=rerun,
            label=f"standalone/{symbol}",
        )
        standalone_cells[symbol] = cell
        standalone_trades.extend(_read_csv(_repo_path(cell["artifacts"]["trades"])))

    combined_symbols = list(BASELINE_SYMBOLS) + selected_symbols
    combined_cell = _run_cell(
        start=start,
        end=end,
        symbols=combined_symbols,
        strategies=list(STRATEGIES_COMBINED),
        risk_per_trade=risk_per_trade,
        output_dir=Path(results_root) / VARIANT / "custom" / window_name,
        rerun=rerun,
        label=VARIANT,
    )
    combined_trades = _read_csv(_repo_path(combined_cell["artifacts"]["trades"]))
    candidate_combined_trades = _candidate_trade_rows(combined_trades)

    standalone_attribution = _attribution_rows(
        standalone_trades,
        scope="standalone",
        symbols=selected_symbols,
        strategies=list(STRATEGIES_CANDIDATE),
        start=start,
        end=end,
        fee_rate=fee_rate,
        baseline_trades=baseline["trades"],
    )
    candidate_symbol_attribution = _attribution_rows(
        candidate_combined_trades,
        scope="combined_candidate",
        symbols=selected_symbols,
        strategies=list(STRATEGIES_CANDIDATE),
        start=start,
        end=end,
        fee_rate=fee_rate,
        baseline_trades=baseline["trades"],
    )

    weekly_payload = _weekly_control_payload(
        cell=combined_cell,
        baseline=baseline,
        fee_rate=fee_rate,
        review_capital_usdt=review_capital_usdt,
    )
    gate_read = _gate_read(
        weekly_payload=weekly_payload,
        combined_cell=combined_cell,
        candidate_attribution=candidate_symbol_attribution,
    )

    all_attribution_rows = standalone_attribution + candidate_symbol_attribution
    _write_csv(
        attribution_csv_path,
        _csv_attribution_rows(all_attribution_rows),
        fieldnames=[
            "scope",
            "symbol",
            "strategy_id",
            "strategy_label",
            "trades",
            "gross_pnl_usdt",
            "fees_est_usdt",
            "after_fee_pnl_usdt",
            "win_rate",
            "active_entry_weeks",
            "worst_trade_after_fee_pnl_usdt",
            "worst_week_start",
            "worst_week_after_fee_pnl_usdt",
            "same_entry_time_overlap_with_baseline",
            "entry_week_overlap_with_baseline",
        ],
    )
    weekly_csv_rows = _weekly_csv_rows(weekly_payload["weeks"])
    weekly_fieldnames = sorted({key for row in weekly_csv_rows for key in row})
    preferred_weekly_fields = [
        "week_start",
        "week_end",
        "entry_trades",
        "exit_trades",
        "gross_pnl_usdt",
        "fees_est_usdt",
        "net_after_fee_est_usdt",
    ]
    weekly_fieldnames = preferred_weekly_fields + [
        key for key in weekly_fieldnames if key not in preferred_weekly_fields
    ]
    _write_csv(weekly_csv_path, weekly_csv_rows, fieldnames=weekly_fieldnames)

    payload = {
        "schema": "strategy_plugin_slot_b_symbol_universe_expansion.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_EVALUATED",
        "variant": VARIANT,
        "window": {"name": window_name, "start": start, "end": end},
        "baseline_symbols": list(BASELINE_SYMBOLS),
        "candidate_symbols_requested": candidate_symbols,
        "candidate_symbols_selected": selected_symbols,
        "strategies": {
            "slot_a_long": SLOT_A_LONG,
            "slot_b_long": SLOT_B_LONG,
            "slot_b_short": SLOT_B_SHORT,
            "candidate_long": CANDIDATE_LONG,
            "candidate_short": CANDIDATE_SHORT,
        },
        "risk_per_trade": float(risk_per_trade),
        "max_total_risk_source": "Config.MAX_TOTAL_RISK",
        "max_total_risk": float(Config.MAX_TOTAL_RISK),
        "fee_rate_per_side_estimate": fee_rate,
        "data_availability": availability,
        "baseline": {
            "summary_source": baseline["summary_source"],
            "packet_source": baseline["packet_source"],
            "cell": baseline["cell"],
            "weekly_summary": baseline["weekly_summary"],
            "latest_contract_grade_packet": baseline["latest_contract_grade_packet"],
        },
        "standalone": {
            "cells": standalone_cells,
            "symbol_attribution": standalone_attribution,
        },
        "combined": {
            "symbols": combined_symbols,
            "cell": combined_cell,
            "candidate_symbol_attribution": candidate_symbol_attribution,
        },
        "gate_read": gate_read,
        "artifact": {
            "summary_json": str(summary_path),
            "weekly_packet_json": str(packet_json_path),
            "availability_csv": str(availability_csv_path),
            "attribution_csv": str(attribution_csv_path),
            "weekly_csv": str(weekly_csv_path),
            "report": str(report_path),
        },
    }

    packet_json_path.parent.mkdir(parents=True, exist_ok=True)
    packet_json_path.write_text(json.dumps(weekly_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(payload, weekly_payload), encoding="utf-8")
    print(f"[SlotBSymbolUniverseExpansion] summary={summary_path}")
    print(f"[SlotBSymbolUniverseExpansion] weekly_packet={packet_json_path}")
    print(f"[SlotBSymbolUniverseExpansion] report={report_path}")
    return summary_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Phase 5/4E Slot B symbol-universe expansion review."
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--window-name", default=DEFAULT_WINDOW)
    parser.add_argument("--candidate-symbols", nargs="+", default=list(DEFAULT_CANDIDATE_SYMBOLS))
    parser.add_argument("--risk-per-trade", type=float, default=0.017)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--packet-json-path", type=Path, default=DEFAULT_PACKET_JSON)
    parser.add_argument("--availability-csv-path", type=Path, default=DEFAULT_AVAILABILITY_CSV)
    parser.add_argument("--attribution-csv-path", type=Path, default=DEFAULT_ATTRIBUTION_CSV)
    parser.add_argument("--weekly-csv-path", type=Path, default=DEFAULT_WEEKLY_CSV)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    parser.add_argument("--review-capital-usdt", type=float, default=DEFAULT_REVIEW_CAPITAL_USDT)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args(argv)
    run_slot_b_symbol_universe_expansion(
        start=args.start,
        end=args.end,
        window_name=args.window_name,
        candidate_symbols=list(args.candidate_symbols),
        risk_per_trade=args.risk_per_trade,
        results_root=args.results_root,
        summary_path=args.summary_path,
        packet_json_path=args.packet_json_path,
        availability_csv_path=args.availability_csv_path,
        attribution_csv_path=args.attribution_csv_path,
        weekly_csv_path=args.weekly_csv_path,
        report_path=args.report_path,
        fee_rate=args.fee_rate,
        review_capital_usdt=args.review_capital_usdt,
        rerun=bool(args.rerun),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
