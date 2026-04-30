"""Count entry-gate attribution for the bb_fade_squeeze_1h candidate."""

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
from trader.strategies.plugins.bb_fade_squeeze_1h import BbFadeSqueeze1hStrategy


CANDIDATE_ID = "bb_fade_squeeze_1h"
DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_RESULTS_ROOT = BACKTEST_ROOT / "results"
REPORT_PATH = REPO_ROOT / "reports" / "bb_fade_squeeze_1h_gate_attribution.md"
CSV_COLUMNS = (
    "window",
    "symbol",
    "total_cursors",
    "valid_bars",
    "missing_data",
    "rsi_pass",
    "lower_touch_pass",
    "bbw_squeeze_pass",
    "htf_adx_pass",
    "cum_rsi",
    "cum_rsi_lower",
    "cum_rsi_lower_bbw",
    "all_gates",
    "post_cooldown_signals",
    "cooldown_blocked",
    "first_fail_rsi",
    "first_fail_lower_touch",
    "first_fail_bbw_squeeze",
    "first_fail_htf_adx",
    "near_miss_rsi",
    "near_miss_lower_touch",
    "near_miss_bbw_squeeze",
    "near_miss_htf_adx",
)
GATE_ORDER = (
    ("rsi", "rsi_pass"),
    ("lower_touch", "lower_touch_pass"),
    ("bbw_squeeze", "bbw_squeeze_pass"),
    ("htf_adx", "htf_adx_pass"),
)
ENTRY_REQUIRED_COLUMNS = (
    "close",
    "rsi_14",
    "bb_lower",
    "bb_mid",
    "bb_upper",
    "bbw",
    "bbw_pctrank",
    "atr",
)


def _empty_row(window: str, symbol: str) -> dict[str, int | str]:
    row: dict[str, int | str] = {"window": window, "symbol": symbol}
    for key in CSV_COLUMNS:
        row.setdefault(key, 0)
    return row


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00%"
    return f"{(float(numerator) / float(denominator)) * 100.0:.2f}%"


def _fmt_count_pct(numerator: int, denominator: int) -> str:
    return f"{numerator} ({_pct(numerator, denominator)})"


def _latest_position_before(frame: pd.DataFrame, ts: pd.Timestamp) -> int | None:
    if frame is None or frame.empty:
        return None
    pos = frame.index.searchsorted(ts, side="left") - 1
    if pos < 0:
        return None
    return int(pos)


def _with_indicators(
    loader: BacktestDataLoader,
    plugin: BbFadeSqueeze1hStrategy,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    frame = loader.get_data(symbol, timeframe, start, end)
    if frame is None or frame.empty:
        return pd.DataFrame()
    return IndicatorRegistry.apply(frame, plugin.required_indicators)


def _load_window_frames(
    loader: BacktestDataLoader,
    plugin: BbFadeSqueeze1hStrategy,
    symbols: Iterable[str],
    start: str,
    end: str,
) -> dict[str, dict[str, pd.DataFrame]]:
    frames: dict[str, dict[str, pd.DataFrame]] = {}
    bbw_window = int(plugin.params.get("bbw_pctrank_window", 100))
    for symbol in symbols:
        entry = _with_indicators(loader, plugin, symbol, plugin.params["timeframe"], start, end)
        entry = plugin._with_bbw_pctrank(entry, bbw_window)
        htf = _with_indicators(loader, plugin, symbol, plugin.params["htf_timeframe"], start, end)
        frames[symbol] = {"entry": entry, "htf": htf}
    return frames


def _common_entry_timestamps(
    frames: dict[str, dict[str, pd.DataFrame]],
    symbols: Iterable[str],
) -> list[pd.Timestamp]:
    timestamp_sets = []
    for symbol in symbols:
        frame = frames.get(symbol, {}).get("entry", pd.DataFrame())
        if frame.empty:
            return []
        timestamp_sets.append(set(frame.index))
    if not timestamp_sets:
        return []
    return sorted(set.intersection(*timestamp_sets))


def _is_valid_entry_row(row: pd.Series, htf_row: pd.Series) -> bool:
    if row[list(ENTRY_REQUIRED_COLUMNS)].isna().any():
        return False
    return "adx" in htf_row.index and pd.notna(htf_row["adx"])


def _count_symbol_window(
    *,
    window: str,
    symbol: str,
    all_ts: list[pd.Timestamp],
    entry_frame: pd.DataFrame,
    htf_frame: pd.DataFrame,
    plugin: BbFadeSqueeze1hStrategy,
    warmup_bars: int,
) -> dict[str, int | str]:
    row = _empty_row(window, symbol)
    rsi_entry = float(plugin.params.get("rsi_entry", 30.0))
    bbw_pctrank_max = float(plugin.params.get("bbw_pctrank_max", 20.0))
    htf_adx_max = float(plugin.params.get("htf_adx_max", 20.0))
    cooldown_bars = int(plugin.params.get("cooldown_bars", 5))
    last_signal_pos: int | None = None

    for cursor_idx, ts in enumerate(all_ts):
        if cursor_idx < warmup_bars:
            continue
        row["total_cursors"] = int(row["total_cursors"]) + 1
        entry_pos = _latest_position_before(entry_frame, ts)
        htf_pos = _latest_position_before(htf_frame, ts)
        if entry_pos is None or htf_pos is None:
            row["missing_data"] = int(row["missing_data"]) + 1
            continue

        latest = entry_frame.iloc[entry_pos]
        htf_latest = htf_frame.iloc[htf_pos]
        if not _is_valid_entry_row(latest, htf_latest):
            row["missing_data"] = int(row["missing_data"]) + 1
            continue

        row["valid_bars"] = int(row["valid_bars"]) + 1
        gates = {
            "rsi": float(latest["rsi_14"]) < rsi_entry,
            "lower_touch": float(latest["close"]) <= float(latest["bb_lower"]),
            "bbw_squeeze": float(latest["bbw_pctrank"]) < bbw_pctrank_max,
            "htf_adx": float(htf_latest["adx"]) < htf_adx_max,
        }

        for gate_name, column in GATE_ORDER:
            if gates[gate_name]:
                row[column] = int(row[column]) + 1

        if gates["rsi"]:
            row["cum_rsi"] = int(row["cum_rsi"]) + 1
        if gates["rsi"] and gates["lower_touch"]:
            row["cum_rsi_lower"] = int(row["cum_rsi_lower"]) + 1
        if gates["rsi"] and gates["lower_touch"] and gates["bbw_squeeze"]:
            row["cum_rsi_lower_bbw"] = int(row["cum_rsi_lower_bbw"]) + 1
        all_gates = all(gates.values())
        if all_gates:
            row["all_gates"] = int(row["all_gates"]) + 1
            if (
                last_signal_pos is not None
                and cooldown_bars > 0
                and (entry_pos - last_signal_pos) < cooldown_bars
            ):
                row["cooldown_blocked"] = int(row["cooldown_blocked"]) + 1
            else:
                row["post_cooldown_signals"] = int(row["post_cooldown_signals"]) + 1
                last_signal_pos = entry_pos

        for gate_name, _column in GATE_ORDER:
            if not gates[gate_name]:
                row[f"first_fail_{gate_name}"] = int(row[f"first_fail_{gate_name}"]) + 1
                break

        failed = [gate_name for gate_name, _column in GATE_ORDER if not gates[gate_name]]
        if len(failed) == 1:
            row[f"near_miss_{failed[0]}"] = int(row[f"near_miss_{failed[0]}"]) + 1

    return row


def _aggregate_rows(window: str, rows: list[dict[str, int | str]]) -> dict[str, int | str]:
    aggregate = _empty_row(window, "ALL")
    for row in rows:
        if row["window"] != window or row["symbol"] == "ALL":
            continue
        for key in CSV_COLUMNS:
            if key in {"window", "symbol"}:
                continue
            aggregate[key] = int(aggregate[key]) + int(row[key])
    return aggregate


def _total_row(rows: list[dict[str, int | str]]) -> dict[str, int | str]:
    total = _empty_row("TOTAL", "ALL")
    for row in rows:
        if row["symbol"] != "ALL" or row["window"] == "TOTAL":
            continue
        for key in CSV_COLUMNS:
            if key in {"window", "symbol"}:
                continue
            total[key] = int(total[key]) + int(row[key])
    return total


def count_gate_attribution(
    *,
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    warmup_bars: int = 100,
) -> list[dict[str, int | str]]:
    catalog_entry = get_strategy_catalog([CANDIDATE_ID])[CANDIDATE_ID]
    plugin = BbFadeSqueeze1hStrategy(params=dict(catalog_entry["params"]))
    loader = BacktestDataLoader()
    symbols = tuple(symbols)
    rows: list[dict[str, int | str]] = []

    for window, (start, end) in DEFAULT_WINDOWS.items():
        frames = _load_window_frames(loader, plugin, symbols, start, end)
        all_ts = _common_entry_timestamps(frames, symbols)
        window_rows = []
        for symbol in symbols:
            row = _count_symbol_window(
                window=window,
                symbol=symbol,
                all_ts=all_ts,
                entry_frame=frames[symbol]["entry"],
                htf_frame=frames[symbol]["htf"],
                plugin=plugin,
                warmup_bars=warmup_bars,
            )
            window_rows.append(row)
        rows.extend(window_rows)
        rows.append(_aggregate_rows(window, window_rows))

    rows.append(_total_row(rows))
    return rows


def write_csv(rows: list[dict[str, int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def _row_by_window(rows: list[dict[str, int | str]], window: str) -> dict[str, int | str]:
    for row in rows:
        if row["window"] == window and row["symbol"] == "ALL":
            return row
    return _empty_row(window, "ALL")


def _single_gate_table(rows: list[dict[str, int | str]]) -> list[str]:
    lines = [
        "| window | valid bars | RSI < 30 | close <= BB lower | BBW pctrank < 20 | 4h ADX < 20 | all gates | post-cooldown |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for window in [*DEFAULT_WINDOWS.keys(), "TOTAL"]:
        row = _row_by_window(rows, window)
        valid = int(row["valid_bars"])
        lines.append(
            "| "
            f"{window} | {valid} | "
            f"{_fmt_count_pct(int(row['rsi_pass']), valid)} | "
            f"{_fmt_count_pct(int(row['lower_touch_pass']), valid)} | "
            f"{_fmt_count_pct(int(row['bbw_squeeze_pass']), valid)} | "
            f"{_fmt_count_pct(int(row['htf_adx_pass']), valid)} | "
            f"{_fmt_count_pct(int(row['all_gates']), valid)} | "
            f"{int(row['post_cooldown_signals'])} |"
        )
    return lines


def _cumulative_table(rows: list[dict[str, int | str]]) -> list[str]:
    lines = [
        "| window | valid bars | after RSI | + lower touch | + BBW squeeze | + 4h ADX |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for window in [*DEFAULT_WINDOWS.keys(), "TOTAL"]:
        row = _row_by_window(rows, window)
        valid = int(row["valid_bars"])
        lines.append(
            "| "
            f"{window} | {valid} | "
            f"{_fmt_count_pct(int(row['cum_rsi']), valid)} | "
            f"{_fmt_count_pct(int(row['cum_rsi_lower']), valid)} | "
            f"{_fmt_count_pct(int(row['cum_rsi_lower_bbw']), valid)} | "
            f"{_fmt_count_pct(int(row['all_gates']), valid)} |"
        )
    return lines


def _near_miss_table(rows: list[dict[str, int | str]]) -> list[str]:
    lines = [
        "| window | fail only RSI | fail only lower touch | fail only BBW squeeze | fail only 4h ADX |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for window in [*DEFAULT_WINDOWS.keys(), "TOTAL"]:
        row = _row_by_window(rows, window)
        lines.append(
            "| "
            f"{window} | "
            f"{int(row['near_miss_rsi'])} | "
            f"{int(row['near_miss_lower_touch'])} | "
            f"{int(row['near_miss_bbw_squeeze'])} | "
            f"{int(row['near_miss_htf_adx'])} |"
        )
    return lines


def _first_fail_table(rows: list[dict[str, int | str]]) -> list[str]:
    lines = [
        "| window | first fail RSI | first fail lower touch | first fail BBW squeeze | first fail 4h ADX | pass all |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for window in [*DEFAULT_WINDOWS.keys(), "TOTAL"]:
        row = _row_by_window(rows, window)
        lines.append(
            "| "
            f"{window} | "
            f"{int(row['first_fail_rsi'])} | "
            f"{int(row['first_fail_lower_touch'])} | "
            f"{int(row['first_fail_bbw_squeeze'])} | "
            f"{int(row['first_fail_htf_adx'])} | "
            f"{int(row['all_gates'])} |"
        )
    return lines


def write_report(rows: list[dict[str, int | str]], report_path: Path, csv_path: Path) -> None:
    total = _row_by_window(rows, "TOTAL")
    lines = [
        "# bb_fade_squeeze_1h Gate Attribution",
        "",
        "Date: 2026-04-25  ",
        "Status: `DIAGNOSTIC_ONLY`",
        "",
        "## Scope",
        "",
        "- Candidate: `bb_fade_squeeze_1h`",
        "- Windows: standard `DEFAULT_WINDOWS` from `extensions/Backtesting/plugin_candidate_review.py`",
        "- Symbols: `BTC/USDT`, `ETH/USDT`",
        "- Method: closed-bar shifted 1h cursor after the same 100-bar warmup used by candidate review.",
        f"- CSV: `{csv_path}`",
        "",
        "## Single Gate Pass Rates",
        "",
        *_single_gate_table(rows),
        "",
        "## Cumulative Survival",
        "",
        *_cumulative_table(rows),
        "",
        "## Near Misses",
        "",
        "A near miss fails exactly one of the four gates while passing the other three.",
        "",
        *_near_miss_table(rows),
        "",
        "## First Failing Gate",
        "",
        "First-fail attribution uses entry order: RSI -> lower-band touch -> BBW squeeze -> 4h ADX.",
        "",
        *_first_fail_table(rows),
        "",
        "## Read",
        "",
        f"- Total valid evaluated bars: `{int(total['valid_bars'])}`.",
        f"- Fully qualified all-gate bars: `{int(total['all_gates'])}`.",
        f"- Post-cooldown candidate signals: `{int(total['post_cooldown_signals'])}`.",
        "- This is diagnostic evidence only; it does not modify runtime defaults or promote the candidate.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(results_root: Path = DEFAULT_RESULTS_ROOT) -> tuple[Path, Path, list[dict[str, int | str]]]:
    rows = count_gate_attribution()
    csv_path = Path(results_root) / CANDIDATE_ID / "gate_attribution.csv"
    write_csv(rows, csv_path)
    write_report(rows, REPORT_PATH, csv_path)
    return csv_path, REPORT_PATH, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count bb_fade_squeeze_1h gate attribution")
    parser.add_argument(
        "--results-root",
        default=str(DEFAULT_RESULTS_ROOT),
        help="Backtest artifact root directory",
    )
    args = parser.parse_args(argv)

    csv_path, report_path, _rows = run(Path(args.results_root))
    print(f"[GateAttribution] csv={csv_path}")
    print(f"[GateAttribution] report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
