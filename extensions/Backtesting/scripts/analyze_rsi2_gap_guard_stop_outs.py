"""Stop-out attribution for the RSI2 SMA5-gap-guard child candidate."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from extensions.Backtesting.scripts.analyze_rsi2_pullback_trades import (
    FEE_RATE,
    _enrich_trade,
    _fmt,
    _load_entry_frame,
    _load_htf_frame,
    _read_trades,
    _safe_float,
)
from plugin_candidate_review import DEFAULT_WINDOWS
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.rsi2_pullback_1h_sma5_gap_guard import (
    Rsi2Pullback1hSma5GapGuardStrategy,
)
from data_loader import BacktestDataLoader


CANDIDATE_ID = "rsi2_pullback_1h_sma5_gap_guard"
DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results"
REPORT_PATH = REPO_ROOT / "reports" / "rsi2_pullback_1h_sma5_gap_guard_stop_out_attribution.md"
STOP_OUT_CSV = DEFAULT_RESULTS_ROOT / CANDIDATE_ID / "stop_out_attribution.csv"
SUMMARY_CSV = DEFAULT_RESULTS_ROOT / CANDIDATE_ID / "stop_out_attribution_summary.csv"


def _bucket_ratio(value: float) -> str:
    if pd.isna(value):
        return "missing"
    if value < 0.25:
        return "<0.25"
    if value < 0.50:
        return "0.25-0.50"
    if value < 0.75:
        return "0.50-0.75"
    if value < 1.00:
        return "0.75-1.00"
    return ">=1.00"


def _entry_hour_bucket(ts: Any) -> str:
    if pd.isna(ts):
        return "missing"
    hour = pd.Timestamp(ts).hour
    if hour < 6:
        return "00-05"
    if hour < 12:
        return "06-11"
    if hour < 18:
        return "12-17"
    return "18-23"


def _safe_ratio(numerator: float, denominator: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0.0:
        return float("nan")
    return numerator / denominator


def build_enriched_trades(
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    fee_rate: float = FEE_RATE,
) -> pd.DataFrame:
    catalog_entry = get_strategy_catalog([CANDIDATE_ID])[CANDIDATE_ID]
    plugin = Rsi2Pullback1hSma5GapGuardStrategy(params=dict(catalog_entry["params"]))
    loader = BacktestDataLoader()
    rows: list[dict[str, Any]] = []
    symbols = tuple(symbols)

    for window, (start, end) in DEFAULT_WINDOWS.items():
        trades = _read_trades(Path(results_root) / CANDIDATE_ID / window / "trades.csv")
        if trades.empty:
            continue
        frames = {
            symbol: {
                "entry": _load_entry_frame(loader, plugin, symbol, start, end),
                "htf": _load_htf_frame(loader, plugin, symbol, start, end),
            }
            for symbol in symbols
        }
        for _, trade in trades.iterrows():
            symbol = str(trade.get("symbol"))
            if symbol not in frames:
                continue
            enriched = _enrich_trade(
                trade,
                window=window,
                entry_frame=frames[symbol]["entry"],
                htf_frame=frames[symbol]["htf"],
                plugin=plugin,
                fee_rate=fee_rate,
            )
            stop_distance_pct = _safe_float(enriched.get("stop_distance_pct"))
            mae_pct = abs(_safe_float(enriched.get("mae_pct")))
            initial_r = _safe_float(enriched.get("initial_r"))
            atr_1h = _safe_float(enriched.get("atr_1h"))
            entry_price = _safe_float(enriched.get("entry_price"))
            entry_sl = _safe_float(enriched.get("entry_initial_sl"))
            stop_distance_price = entry_price - entry_sl
            stop_distance_atr = _safe_ratio(stop_distance_price, atr_1h)
            mae_to_stop_ratio = _safe_ratio(mae_pct, stop_distance_pct)
            enriched.update(
                {
                    "stop_distance_price": stop_distance_price,
                    "stop_distance_atr": stop_distance_atr,
                    "mae_to_stop_ratio": mae_to_stop_ratio,
                    "mae_to_stop_bucket": _bucket_ratio(mae_to_stop_ratio),
                    "entry_hour_utc": pd.Timestamp(enriched.get("entry_time")).hour,
                    "entry_hour_bucket": _entry_hour_bucket(enriched.get("entry_time")),
                    "initial_r_abs": abs(initial_r) if not pd.isna(initial_r) else float("nan"),
                }
            )
            rows.append(enriched)

    return pd.DataFrame(rows)


def _filter_stop_outs(enriched: pd.DataFrame) -> pd.DataFrame:
    if enriched.empty or "exit_reason" not in enriched.columns:
        return pd.DataFrame()
    return enriched[enriched["exit_reason"] == "sl_hit"].copy()


def _summary_rows(
    stop_outs: pd.DataFrame,
    all_trades: pd.DataFrame,
    group_cols: list[str],
) -> list[dict[str, Any]]:
    if stop_outs.empty:
        return []

    all_counts: dict[str, int] = {}
    if not all_trades.empty:
        for group_key, group in all_trades.groupby(group_cols, dropna=False):
            values = group_key if isinstance(group_key, tuple) else (group_key,)
            label = " / ".join(f"{col}={value}" for col, value in zip(group_cols, values))
            all_counts[label] = int(len(group))

    rows: list[dict[str, Any]] = []
    for group_key, group in stop_outs.groupby(group_cols, dropna=False):
        values = group_key if isinstance(group_key, tuple) else (group_key,)
        label = " / ".join(f"{col}={value}" for col, value in zip(group_cols, values))
        all_count = int(all_counts.get(label, 0))
        stop_count = int(len(group))
        pnl = float(group["pnl_usdt"].sum())
        fees = float(group["fees_est"].sum())
        rows.append(
            {
                "group": label,
                "stop_outs": stop_count,
                "all_trades": all_count,
                "stop_rate": stop_count / all_count if all_count else 0.0,
                "pnl_usdt": pnl,
                "fees_est": fees,
                "net_after_fee_est": pnl - fees,
                "avg_r": float(group["realized_r"].mean()),
                "avg_mae_pct": float(group["mae_pct"].mean()),
                "avg_hold_h": float(group["holding_hours"].mean()),
                "avg_stop_distance_atr": float(group["stop_distance_atr"].mean()),
                "avg_mae_to_stop": float(group["mae_to_stop_ratio"].mean()),
            }
        )
    return sorted(rows, key=lambda row: (row["stop_outs"], -row["net_after_fee_est"]), reverse=True)


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def _summary_table(rows: list[dict[str, Any]], title: str, *, limit: int | None = None) -> list[str]:
    selected = rows if limit is None else rows[:limit]
    lines = [
        f"## {title}",
        "",
        "| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in selected:
        lines.append(
            "| "
            f"{row['group']} | {row['stop_outs']} | {row['all_trades']} | "
            f"{row['stop_rate']:.4f} | {_fmt(row['pnl_usdt'])} | "
            f"{_fmt(row['net_after_fee_est'])} | {_fmt(row['avg_r'])} | "
            f"{_fmt(row['avg_mae_pct'])} | {_fmt(row['avg_hold_h'])} | "
            f"{_fmt(row['avg_mae_to_stop'])} |"
        )
    return lines


def _aggregate_row(df: pd.DataFrame, label: str) -> list[Any]:
    if df.empty:
        return [label, 0, "0.0000", "0.0000", "0.0000", "0.0000", "0.0000"]
    pnl = float(df["pnl_usdt"].sum())
    fees = float(df["fees_est"].sum())
    return [
        label,
        len(df),
        _fmt(pnl),
        _fmt(pnl - fees),
        _fmt(float(df["realized_r"].mean())),
        _fmt(float(df["mae_pct"].mean())),
        _fmt(float(df["holding_hours"].mean())),
    ]


def _top_loser_rows(stop_outs: pd.DataFrame, *, limit: int = 10) -> list[list[Any]]:
    if stop_outs.empty:
        return []
    rows = []
    for _, row in stop_outs.sort_values("pnl_usdt").head(limit).iterrows():
        rows.append(
            [
                row.get("window"),
                row.get("symbol"),
                pd.Timestamp(row.get("entry_time")).isoformat(),
                _fmt(_safe_float(row.get("pnl_usdt"))),
                _fmt(_safe_float(row.get("realized_r"))),
                _fmt(_safe_float(row.get("mae_pct"))),
                _fmt(_safe_float(row.get("sma5_gap_atr"))),
                row.get("sma200_dist_bucket"),
                row.get("htf_sma200_dist_bucket"),
                row.get("holding_bucket"),
            ]
        )
    return rows


def _guardability_rows(enriched: pd.DataFrame) -> list[dict[str, Any]]:
    checks = [
        (
            "BTC only",
            enriched["symbol"] == "BTC/USDT",
        ),
        (
            "TRENDING_UP BTC",
            (enriched["window"] == "TRENDING_UP") & (enriched["symbol"] == "BTC/USDT"),
        ),
        (
            "SMA5 gap >= 1.00 ATR",
            enriched["sma5_gap_atr_bucket"] == ">=1.00",
        ),
        (
            "entry hour 12-17 UTC",
            enriched["entry_hour_bucket"] == "12-17",
        ),
        (
            "entry regime RANGING",
            enriched["entry_regime"] == "RANGING",
        ),
        (
            "4h SMA200 distance >=10%",
            enriched["htf_sma200_dist_bucket"] == ">=10%",
        ),
    ]
    rows = []
    for label, mask in checks:
        subset = enriched[mask].copy()
        if subset.empty:
            continue
        stops = subset[subset["exit_reason"] == "sl_hit"]
        non_stops = subset[subset["exit_reason"] != "sl_hit"]
        all_pnl = float(subset["pnl_usdt"].sum())
        all_fees = float(subset["fees_est"].sum())
        stop_pnl = float(stops["pnl_usdt"].sum()) if not stops.empty else 0.0
        non_stop_pnl = float(non_stops["pnl_usdt"].sum()) if not non_stops.empty else 0.0
        rows.append(
            {
                "candidate_guard": label,
                "trades": int(len(subset)),
                "stop_outs": int(len(stops)),
                "stop_rate": len(stops) / len(subset),
                "pnl_usdt": all_pnl,
                "net_after_fee_est": all_pnl - all_fees,
                "stop_pnl": stop_pnl,
                "non_stop_pnl": non_stop_pnl,
            }
        )
    return rows


def _guardability_table(rows: list[dict[str, Any]]) -> list[str]:
    return _table(
        [
            "candidate_guard",
            "trades",
            "stop_outs",
            "stop_rate",
            "pnl_usdt",
            "net_after_fee_est",
            "stop_pnl",
            "non_stop_pnl",
        ],
        [
            [
                row["candidate_guard"],
                row["trades"],
                row["stop_outs"],
                f"{row['stop_rate']:.4f}",
                _fmt(row["pnl_usdt"]),
                _fmt(row["net_after_fee_est"]),
                _fmt(row["stop_pnl"]),
                _fmt(row["non_stop_pnl"]),
            ]
            for row in rows
        ],
    )


def _decision_read(
    stop_outs: pd.DataFrame,
    segment_rows: dict[str, list[dict[str, Any]]],
    guardability_rows: list[dict[str, Any]],
) -> list[str]:
    if stop_outs.empty:
        return [
            "- No residual `sl_hit` trades were found; no churn-reduction child is justified from stop-outs.",
        ]

    top_segments = []
    for name, rows in segment_rows.items():
        if not rows:
            continue
        row = rows[0]
        share = row["stop_outs"] / len(stop_outs)
        top_segments.append((share, name, row))
    top_segments.sort(reverse=True, key=lambda item: item[0])
    strongest_share, strongest_name, strongest_row = top_segments[0]

    lines = [
        f"- Residual stop-outs total `{len(stop_outs)}` across the default review matrix.",
        (
            f"- Strongest single segmentation is `{strongest_name}`: "
            f"{strongest_row['group']} has {strongest_row['stop_outs']} stop-outs "
            f"({strongest_share:.1%} of stop-outs)."
        ),
    ]
    net_negative_guards = [
        row
        for row in guardability_rows
        if row["candidate_guard"] != "TRENDING_UP BTC"
        and row["net_after_fee_est"] < -250.0
        and row["non_stop_pnl"] < abs(row["stop_pnl"])
    ]
    if net_negative_guards:
        candidate = sorted(net_negative_guards, key=lambda row: row["net_after_fee_est"])[0]
        lines.append(
            (
                "- A possible Phase 4.2 hypothesis exists, but it must be treated as "
                f"defensive: `{candidate['candidate_guard']}` is net-negative after "
                "fees in this attribution."
            )
        )
    else:
        lines.append(
            "- The visible concentrations are broad participation buckets with material non-stop PnL, so they do not justify a clean second guard."
        )
        lines.append(
            "- `TRENDING_UP BTC` is net-negative after fees, but it is a research-window label, not a live plugin-local guard."
        )
        lines.append(
            "- Phase 4.2 should park RSI2 for now unless Ruei explicitly wants a defensive low-participation variant."
        )
    lines.extend(
        [
            "- Do not loosen RSI, SMA5-gap, or trend thresholds from this read.",
            "- This report is diagnostic only and does not modify runtime defaults, catalog flags, scanner behavior, or production/testnet state.",
        ]
    )
    return lines


def write_report(
    enriched: pd.DataFrame,
    *,
    report_path: Path,
    stop_out_csv: Path,
    summary_csv: Path,
    fee_rate: float,
) -> None:
    stop_outs = _filter_stop_outs(enriched)
    segment_rows = {
        "window": _summary_rows(stop_outs, enriched, ["window"]),
        "window_symbol": _summary_rows(stop_outs, enriched, ["window", "symbol"]),
        "symbol": _summary_rows(stop_outs, enriched, ["symbol"]),
        "entry_regime": _summary_rows(stop_outs, enriched, ["entry_regime"]),
        "sma5_gap_atr_bucket": _summary_rows(stop_outs, enriched, ["sma5_gap_atr_bucket"]),
        "sma200_dist_bucket": _summary_rows(stop_outs, enriched, ["sma200_dist_bucket"]),
        "htf_sma200_dist_bucket": _summary_rows(stop_outs, enriched, ["htf_sma200_dist_bucket"]),
        "atr_pct_bucket": _summary_rows(stop_outs, enriched, ["atr_pct_bucket"]),
        "holding_bucket": _summary_rows(stop_outs, enriched, ["holding_bucket"]),
        "rsi2_bucket": _summary_rows(stop_outs, enriched, ["rsi2_bucket"]),
        "entry_hour_bucket": _summary_rows(stop_outs, enriched, ["entry_hour_bucket"]),
    }
    guard_rows = _guardability_rows(enriched)

    _write_csv(stop_outs.to_dict("records"), stop_out_csv)
    flat_summary_rows = []
    for segment, rows in segment_rows.items():
        for row in rows:
            flat_summary_rows.append({"segment": segment, **row})
    _write_csv(flat_summary_rows, summary_csv)

    non_stop = enriched[enriched["exit_reason"] != "sl_hit"].copy()
    lines = [
        "# rsi2_pullback_1h_sma5_gap_guard Stop-Out Attribution",
        "",
        "Date: 2026-04-30",
        "Status: `PHASE_4_1_DIAGNOSTIC_ONLY`",
        "",
        "## Scope",
        "",
        f"- Candidate: `{CANDIDATE_ID}`",
        "- Purpose: attribute residual `sl_hit` trades before any Phase 4.2 child spec.",
        "- Windows: standard `DEFAULT_WINDOWS` from `extensions/Backtesting/plugin_candidate_review.py`.",
        "- Symbols: `BTC/USDT`, `ETH/USDT`.",
        f"- Fee estimate: `{fee_rate}` per side on entry and exit notional.",
        f"- Stop-out CSV: `{stop_out_csv}`",
        f"- Segment summary CSV: `{summary_csv}`",
        "",
        "## Aggregate",
        "",
        *_table(
            ["scope", "trades", "pnl_usdt", "net_after_fee_est", "avg_r", "avg_mae_pct", "avg_hold_h"],
            [
                _aggregate_row(enriched, "all_trades"),
                _aggregate_row(stop_outs, "sl_hit"),
                _aggregate_row(non_stop, "non_sl_hit"),
            ],
        ),
        "",
        *_summary_table(segment_rows["window"], "Window Stop-Outs"),
        "",
        *_summary_table(segment_rows["window_symbol"], "Window And Symbol Stop-Outs"),
        "",
        *_summary_table(segment_rows["symbol"], "Symbol Stop-Outs"),
        "",
        *_summary_table(segment_rows["entry_regime"], "Entry-Regime Stop-Outs"),
        "",
        *_summary_table(segment_rows["sma5_gap_atr_bucket"], "SMA5 Gap ATR Stop-Outs"),
        "",
        *_summary_table(segment_rows["sma200_dist_bucket"], "1h SMA200 Distance Stop-Outs"),
        "",
        *_summary_table(segment_rows["htf_sma200_dist_bucket"], "4h SMA200 Distance Stop-Outs"),
        "",
        *_summary_table(segment_rows["atr_pct_bucket"], "ATR Percent Stop-Outs"),
        "",
        *_summary_table(segment_rows["holding_bucket"], "Holding-Time Stop-Outs"),
        "",
        *_summary_table(segment_rows["rsi2_bucket"], "RSI2 Stop-Outs"),
        "",
        *_summary_table(segment_rows["entry_hour_bucket"], "Entry-Hour Stop-Outs"),
        "",
        "## Guardability Check",
        "",
        "These broad cuts are not recommendations; they test whether the obvious concentrations are actually net-bad after winner retention.",
        "",
        *_guardability_table(guard_rows),
        "",
        "## Top Stop-Outs",
        "",
        *_table(
            [
                "window",
                "symbol",
                "entry_time",
                "pnl_usdt",
                "realized_r",
                "mae_pct",
                "sma5_gap_atr",
                "sma200_bucket",
                "htf_sma200_bucket",
                "holding_bucket",
            ],
            _top_loser_rows(stop_outs),
        ),
        "",
        "## Decision Read",
        "",
        *_decision_read(stop_outs, segment_rows, guard_rows),
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    fee_rate: float = FEE_RATE,
    report_path: Path = REPORT_PATH,
    stop_out_csv: Path = STOP_OUT_CSV,
    summary_csv: Path = SUMMARY_CSV,
) -> tuple[Path, Path, Path]:
    enriched = build_enriched_trades(results_root=results_root, fee_rate=fee_rate)
    write_report(
        enriched,
        report_path=report_path,
        stop_out_csv=stop_out_csv,
        summary_csv=summary_csv,
        fee_rate=fee_rate,
    )
    return report_path, stop_out_csv, summary_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze stop-outs for rsi2_pullback_1h_sma5_gap_guard"
    )
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--fee-rate", type=float, default=FEE_RATE)
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--stop-out-csv", default=str(STOP_OUT_CSV))
    parser.add_argument("--summary-csv", default=str(SUMMARY_CSV))
    args = parser.parse_args(argv)

    report_path, stop_out_csv, summary_csv = run(
        results_root=Path(args.results_root),
        fee_rate=args.fee_rate,
        report_path=Path(args.report),
        stop_out_csv=Path(args.stop_out_csv),
        summary_csv=Path(args.summary_csv),
    )
    print(f"[Rsi2GapGuardStopOuts] report={report_path}")
    print(f"[Rsi2GapGuardStopOuts] stop_out_csv={stop_out_csv}")
    print(f"[Rsi2GapGuardStopOuts] summary_csv={summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
