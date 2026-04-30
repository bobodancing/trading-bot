"""Trade attribution for the rsi2_pullback_1h candidate."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_loader import BacktestDataLoader
from plugin_candidate_review import DEFAULT_WINDOWS
from trader.indicators.registry import IndicatorRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.rsi2_pullback_1h import Rsi2Pullback1hStrategy


CANDIDATE_ID = "rsi2_pullback_1h"
DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results"
REPORT_PATH = REPO_ROOT / "reports" / "rsi2_pullback_1h_trade_attribution.md"
FEE_RATE = 0.0004
SUMMARY_FIELDS = (
    "group",
    "trades",
    "win_rate",
    "gross_positive",
    "gross_loss",
    "pnl_usdt",
    "fees_est",
    "fee_drag_ratio",
    "net_after_fee_est",
    "avg_pnl_usdt",
    "avg_net_after_fee_est",
    "avg_realized_r",
    "avg_holding_hours",
)


def _latest_position_before(frame: pd.DataFrame, ts: pd.Timestamp) -> int | None:
    if frame is None or frame.empty:
        return None
    pos = frame.index.searchsorted(ts, side="left") - 1
    if pos < 0:
        return None
    return int(pos)


def _safe_float(value) -> float:
    try:
        if value is None or pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _ratio_pct(numerator: float, denominator: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return float("nan")
    return (numerator / denominator - 1.0) * 100.0


def _diff_pct(numerator: float, denominator: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return float("nan")
    return (numerator - denominator) / denominator * 100.0


def _diff_atr(numerator: float, denominator: float, atr: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or pd.isna(atr) or atr == 0:
        return float("nan")
    return (numerator - denominator) / atr


def _bucket(value: float, edges: list[float], labels: list[str]) -> str:
    if pd.isna(value):
        return "missing"
    for edge, label in zip(edges, labels):
        if value < edge:
            return label
    return labels[-1]


def _holding_bucket(value: float) -> str:
    if pd.isna(value):
        return "missing"
    if value <= 2:
        return "<=2h"
    if value <= 5:
        return "3-5h"
    if value <= 10:
        return "6-10h"
    return ">10h"


def _read_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    trades = pd.read_csv(path)
    if trades.empty:
        return trades
    for col in ("entry_time", "exit_time"):
        if col in trades.columns:
            trades[col] = pd.to_datetime(trades[col], utc=True, errors="coerce")
    return trades


def _load_entry_frame(
    loader: BacktestDataLoader,
    plugin: Rsi2Pullback1hStrategy,
    symbol: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    timeframe = str(plugin.params.get("timeframe", "1h"))
    frame = loader.get_data(symbol, timeframe, start, end)
    frame = IndicatorRegistry.apply(frame, set(plugin.required_indicators))
    return plugin._with_entry_indicators(
        frame,
        rsi_period=int(plugin.params.get("rsi_period", 2)),
        sma_trend_len=int(plugin.params.get("sma_trend_len", 200)),
        sma_exit_len=int(plugin.params.get("sma_exit_len", 5)),
    )


def _load_htf_frame(
    loader: BacktestDataLoader,
    plugin: Rsi2Pullback1hStrategy,
    symbol: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    timeframe = str(plugin.params.get("htf_timeframe", "4h"))
    frame = loader.get_data(symbol, timeframe, start, end)
    frame = IndicatorRegistry.apply(frame, set(plugin.required_indicators))
    return plugin._with_htf_indicators(
        frame,
        htf_sma_trend_len=int(plugin.params.get("htf_sma_trend_len", 200)),
    )


def _enrich_trade(
    row: pd.Series,
    *,
    window: str,
    entry_frame: pd.DataFrame,
    htf_frame: pd.DataFrame,
    plugin: Rsi2Pullback1hStrategy,
    fee_rate: float,
) -> dict:
    entry_ts = pd.Timestamp(row["entry_time"])
    entry_pos = _latest_position_before(entry_frame, entry_ts)
    htf_pos = _latest_position_before(htf_frame, entry_ts)
    entry_candle = entry_frame.iloc[entry_pos] if entry_pos is not None else pd.Series(dtype=float)
    htf_candle = htf_frame.iloc[htf_pos] if htf_pos is not None else pd.Series(dtype=float)

    sma_trend_len = int(plugin.params.get("sma_trend_len", 200))
    sma_exit_len = int(plugin.params.get("sma_exit_len", 5))
    htf_sma_trend_len = int(plugin.params.get("htf_sma_trend_len", 200))
    sma_200_col = plugin._sma_col(sma_trend_len)
    sma_5_col = plugin._sma_col(sma_exit_len)
    htf_sma_200_col = plugin._sma_col(htf_sma_trend_len)

    entry_price = _safe_float(row.get("entry_price"))
    exit_price = _safe_float(row.get("exit_price"))
    total_size = _safe_float(row.get("total_size"))
    pnl_usdt = _safe_float(row.get("pnl_usdt"))
    fees_est = (entry_price * total_size + exit_price * total_size) * fee_rate

    close_1h = _safe_float(entry_candle.get("close"))
    atr_1h = _safe_float(entry_candle.get("atr"))
    sma_5 = _safe_float(entry_candle.get(sma_5_col))
    sma_200_1h = _safe_float(entry_candle.get(sma_200_col))
    close_4h = _safe_float(htf_candle.get("close"))
    sma_200_4h = _safe_float(htf_candle.get(htf_sma_200_col))
    stop_distance_pct = _diff_pct(entry_price, _safe_float(row.get("entry_initial_sl")))

    enriched = {
        **row.to_dict(),
        "window": window,
        "outcome": "winner" if pnl_usdt > 0 else "loser",
        "fees_est": fees_est,
        "net_after_fee_est": pnl_usdt - fees_est,
        "entry_candle_time": "" if entry_pos is None else entry_frame.index[entry_pos].isoformat(),
        "htf_candle_time": "" if htf_pos is None else htf_frame.index[htf_pos].isoformat(),
        "entry_close_1h": close_1h,
        "rsi_2": _safe_float(entry_candle.get("rsi_2")),
        "sma_5_1h": sma_5,
        "sma_200_1h": sma_200_1h,
        "atr_1h": atr_1h,
        "close_4h": close_4h,
        "sma_200_4h": sma_200_4h,
        "price_vs_sma200_pct": _ratio_pct(close_1h, sma_200_1h),
        "htf_price_vs_sma200_pct": _ratio_pct(close_4h, sma_200_4h),
        "sma5_gap_pct": _ratio_pct(sma_5, close_1h),
        "sma5_gap_atr": _diff_atr(sma_5, close_1h, atr_1h),
        "entry_extension_atr": _diff_atr(close_1h, sma_200_1h, atr_1h),
        "atr_pct": _ratio_pct(close_1h + atr_1h, close_1h),
        "stop_distance_pct": stop_distance_pct,
        "rsi2_bucket": _bucket(
            _safe_float(entry_candle.get("rsi_2")),
            [2.0, 5.0, 8.0, 10.0],
            ["<2", "2-5", "5-8", "8-10"],
        ),
        "sma200_dist_bucket": _bucket(
            _ratio_pct(close_1h, sma_200_1h),
            [2.0, 5.0, 10.0, 999999.0],
            ["0-2%", "2-5%", "5-10%", ">=10%"],
        ),
        "htf_sma200_dist_bucket": _bucket(
            _ratio_pct(close_4h, sma_200_4h),
            [2.0, 5.0, 10.0, 999999.0],
            ["0-2%", "2-5%", "5-10%", ">=10%"],
        ),
        "sma5_gap_atr_bucket": _bucket(
            _diff_atr(sma_5, close_1h, atr_1h),
            [0.25, 0.50, 1.00, 999999.0],
            ["<0.25", "0.25-0.50", "0.50-1.00", ">=1.00"],
        ),
        "atr_pct_bucket": _bucket(
            _ratio_pct(close_1h + atr_1h, close_1h),
            [0.5, 1.0, 1.5, 999999.0],
            ["<0.5%", "0.5-1.0%", "1.0-1.5%", ">=1.5%"],
        ),
        "stop_distance_pct_bucket": _bucket(
            stop_distance_pct,
            [1.0, 2.0, 3.0, 999999.0],
            ["<1%", "1-2%", "2-3%", ">=3%"],
        ),
        "holding_bucket": _holding_bucket(_safe_float(row.get("holding_hours"))),
    }
    return enriched


def build_enriched_trades(
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    fee_rate: float = FEE_RATE,
) -> pd.DataFrame:
    catalog_entry = get_strategy_catalog([CANDIDATE_ID])[CANDIDATE_ID]
    plugin = Rsi2Pullback1hStrategy(params=dict(catalog_entry["params"]))
    loader = BacktestDataLoader()
    rows: list[dict] = []
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
            rows.append(
                _enrich_trade(
                    trade,
                    window=window,
                    entry_frame=frames[symbol]["entry"],
                    htf_frame=frames[symbol]["htf"],
                    plugin=plugin,
                    fee_rate=fee_rate,
                )
            )

    return pd.DataFrame(rows)


def _summary_rows(df: pd.DataFrame, group_cols: list[str]) -> list[dict]:
    if df.empty:
        return []
    rows = []
    grouped = df.groupby(group_cols, dropna=False)
    for group_key, group in grouped:
        gross_positive = float(group.loc[group["pnl_usdt"] > 0, "pnl_usdt"].sum())
        gross_loss = float(group.loc[group["pnl_usdt"] < 0, "pnl_usdt"].sum())
        pnl = float(group["pnl_usdt"].sum())
        fees = float(group["fees_est"].sum())
        trades = int(len(group))
        values = group_key if isinstance(group_key, tuple) else (group_key,)
        label = " / ".join(
            f"{col}={value}" for col, value in zip(group_cols, values)
        )
        rows.append(
            {
                "group": label,
                "trades": trades,
                "win_rate": float((group["pnl_usdt"] > 0).mean()) if trades else 0.0,
                "gross_positive": gross_positive,
                "gross_loss": gross_loss,
                "pnl_usdt": pnl,
                "fees_est": fees,
                "fee_drag_ratio": fees / gross_positive if gross_positive > 0 else float("nan"),
                "net_after_fee_est": pnl - fees,
                "avg_pnl_usdt": pnl / trades if trades else 0.0,
                "avg_net_after_fee_est": (pnl - fees) / trades if trades else 0.0,
                "avg_realized_r": float(group["realized_r"].mean()) if "realized_r" in group else float("nan"),
                "avg_holding_hours": float(group["holding_hours"].mean()) if "holding_hours" in group else float("nan"),
            }
        )
    return sorted(rows, key=lambda item: item["net_after_fee_est"])


def _write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(SUMMARY_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: float) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def _summary_table(rows: list[dict], title: str, *, limit: int | None = None) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    selected = rows if limit is None else rows[:limit]
    for row in selected:
        lines.append(
            "| "
            f"{row['group']} | {row['trades']} | "
            f"{_fmt(row['win_rate'])} | {_fmt(row['pnl_usdt'])} | "
            f"{_fmt(row['fees_est'])} | {_fmt(row['fee_drag_ratio'])} | "
            f"{_fmt(row['net_after_fee_est'])} | {_fmt(row['avg_realized_r'])} | "
            f"{_fmt(row['avg_holding_hours'])} |"
        )
    return lines


def _best_worst_segments(
    rows: list[dict],
    *,
    min_trades: int,
    take: int = 5,
) -> tuple[list[dict], list[dict]]:
    scoped = [row for row in rows if int(row["trades"]) >= min_trades]
    worst = sorted(scoped, key=lambda row: row["net_after_fee_est"])[:take]
    best = sorted(scoped, key=lambda row: row["net_after_fee_est"], reverse=True)[:take]
    return best, worst


def _segment_lines(rows: list[dict], *, min_trades: int) -> list[str]:
    best, worst = _best_worst_segments(rows, min_trades=min_trades)
    lines = [
        "## Best/Worst Segments",
        "",
        f"Minimum trades per segment: `{min_trades}`.",
        "",
        "### Best",
        "",
        "| group | trades | pnl_usdt | fees_est | net_after_fee_est | fee_drag_ratio |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in best:
        lines.append(
            "| "
            f"{row['group']} | {row['trades']} | {_fmt(row['pnl_usdt'])} | "
            f"{_fmt(row['fees_est'])} | {_fmt(row['net_after_fee_est'])} | "
            f"{_fmt(row['fee_drag_ratio'])} |"
        )
    lines.extend(
        [
            "",
            "### Worst",
            "",
            "| group | trades | pnl_usdt | fees_est | net_after_fee_est | fee_drag_ratio |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in worst:
        lines.append(
            "| "
            f"{row['group']} | {row['trades']} | {_fmt(row['pnl_usdt'])} | "
            f"{_fmt(row['fees_est'])} | {_fmt(row['net_after_fee_est'])} | "
            f"{_fmt(row['fee_drag_ratio'])} |"
        )
    return lines


def write_report(
    enriched: pd.DataFrame,
    *,
    report_path: Path,
    enriched_csv_path: Path,
    summary_csv_path: Path,
    fee_rate: float,
    min_segment_trades: int,
) -> None:
    window_rows = _summary_rows(enriched, ["window"])
    exit_rows = _summary_rows(enriched, ["window", "exit_reason"])
    rsi_rows = _summary_rows(enriched, ["window", "rsi2_bucket"])
    sma200_rows = _summary_rows(enriched, ["window", "sma200_dist_bucket"])
    htf_sma200_rows = _summary_rows(enriched, ["window", "htf_sma200_dist_bucket"])
    sma5_rows = _summary_rows(enriched, ["window", "sma5_gap_atr_bucket"])
    atr_rows = _summary_rows(enriched, ["window", "atr_pct_bucket"])
    holding_rows = _summary_rows(enriched, ["window", "holding_bucket"])
    all_segment_rows = (
        exit_rows
        + rsi_rows
        + sma200_rows
        + htf_sma200_rows
        + sma5_rows
        + atr_rows
        + holding_rows
    )

    _write_csv(all_segment_rows, summary_csv_path)
    enriched_csv_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(enriched_csv_path, index=False)

    total_rows = _summary_rows(enriched.assign(scope="TOTAL"), ["scope"])
    lines = [
        "# rsi2_pullback_1h Trade Attribution",
        "",
        "Date: 2026-04-25  ",
        "Status: `DIAGNOSTIC_ONLY`",
        "",
        "## Scope",
        "",
        "- Candidate: `rsi2_pullback_1h`",
        "- Windows: standard `DEFAULT_WINDOWS` from `extensions/Backtesting/plugin_candidate_review.py`",
        "- Symbols: `BTC/USDT`, `ETH/USDT`",
        "- Method: join each trade to the previous closed 1h and 4h candle before `entry_time`, then rebuild plugin-local `rsi_2`, `sma_5`, `sma_200`, and ATR context.",
        f"- Fee estimate: `{fee_rate}` per side on entry and exit notional.",
        f"- Enriched trades CSV: `{enriched_csv_path}`",
        f"- Segment summary CSV: `{summary_csv_path}`",
        "",
        *_summary_table(total_rows, "Aggregate"),
        "",
        *_summary_table(window_rows, "Window Summary"),
        "",
        *_summary_table(exit_rows, "Exit Reason Attribution"),
        "",
        *_summary_table(sma5_rows, "SMA5 Gap ATR Buckets"),
        "",
        *_summary_table(sma200_rows, "1h SMA200 Distance Buckets"),
        "",
        *_summary_table(htf_sma200_rows, "4h SMA200 Distance Buckets"),
        "",
        *_summary_table(rsi_rows, "RSI2 Buckets"),
        "",
        *_summary_table(holding_rows, "Holding-Time Buckets"),
        "",
        *_summary_table(atr_rows, "ATR Percent Buckets"),
        "",
        *_segment_lines(all_segment_rows, min_trades=min_segment_trades),
        "",
        "## Read",
        "",
        "- This is diagnostic evidence only; it does not modify runtime defaults or promote the candidate.",
        "- Use this report to pick one child-spec guard at a time; do not loosen entry thresholds from this output.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    fee_rate: float = FEE_RATE,
    min_segment_trades: int = 10,
) -> tuple[Path, Path, Path]:
    enriched = build_enriched_trades(results_root=results_root, fee_rate=fee_rate)
    enriched_csv_path = Path(results_root) / CANDIDATE_ID / "trade_attribution.csv"
    summary_csv_path = Path(results_root) / CANDIDATE_ID / "trade_attribution_summary.csv"
    write_report(
        enriched,
        report_path=REPORT_PATH,
        enriched_csv_path=enriched_csv_path,
        summary_csv_path=summary_csv_path,
        fee_rate=fee_rate,
        min_segment_trades=min_segment_trades,
    )
    return enriched_csv_path, summary_csv_path, REPORT_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze rsi2_pullback_1h trade attribution")
    parser.add_argument(
        "--results-root",
        default=str(DEFAULT_RESULTS_ROOT),
        help="Backtest artifact root directory",
    )
    parser.add_argument("--fee-rate", type=float, default=FEE_RATE)
    parser.add_argument("--min-segment-trades", type=int, default=10)
    args = parser.parse_args(argv)

    enriched_csv, summary_csv, report_path = run(
        results_root=Path(args.results_root),
        fee_rate=args.fee_rate,
        min_segment_trades=args.min_segment_trades,
    )
    print(f"[TradeAttribution] enriched_csv={enriched_csv}")
    print(f"[TradeAttribution] summary_csv={summary_csv}")
    print(f"[TradeAttribution] report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
