"""Measure ADX regime distribution for 15m BTC/ETH across review windows."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKTEST_ROOT.parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_loader import BacktestDataLoader
from plugin_candidate_review import DEFAULT_WINDOWS
from trader.indicators.technical import _adx


SYMBOLS = ("BTC/USDT", "ETH/USDT")
TIMEFRAME = "15m"
ADX_LENGTH = 14
REPORT_PATH = REPO_ROOT / "reports" / "regime_distribution_baseline.md"


def _extract_adx_series(df: pd.DataFrame) -> pd.Series:
    adx_data = _adx(df["high"], df["low"], df["close"], length=ADX_LENGTH)
    if isinstance(adx_data, pd.DataFrame):
        for column in adx_data.columns:
            if str(column).upper().startswith(f"ADX_{ADX_LENGTH}".upper()):
                return adx_data[column]
        raise ValueError(f"could not find ADX_{ADX_LENGTH} column in _adx output")
    if isinstance(adx_data, pd.Series):
        return adx_data
    raise TypeError("_adx returned unsupported result type")


def _percent(count: int, total: int) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(count / total) * 100.0:.2f}%"


def _quantile(series: pd.Series, q: float) -> float:
    return float(series.quantile(q))


def _measure_cell(loader: BacktestDataLoader, symbol: str, window_name: str, start: str, end: str) -> dict:
    df = loader.get_data(symbol, TIMEFRAME, start, end)
    adx = _extract_adx_series(df).dropna()

    total_bars = int(len(df))
    valid_bars = int(len(adx))

    lt20 = int((adx < 20).sum())
    ge20_lt25 = int(((adx >= 20) & (adx < 25)).sum())
    ge25_lt30 = int(((adx >= 25) & (adx < 30)).sum())
    ge30 = int((adx >= 30).sum())
    lt25 = int((adx < 25).sum())
    ge25 = int((adx >= 25).sum())

    return {
        "symbol": symbol,
        "window": window_name,
        "start": start,
        "end": end,
        "total_bars": total_bars,
        "valid_bars": valid_bars,
        "adx_lt_20": lt20,
        "adx_20_to_25": ge20_lt25,
        "adx_25_to_30": ge25_lt30,
        "adx_ge_30": ge30,
        "adx_lt_25": lt25,
        "adx_ge_25": ge25,
        "p25": _quantile(adx, 0.25),
        "p50": _quantile(adx, 0.50),
        "p75": _quantile(adx, 0.75),
        "p90": _quantile(adx, 0.90),
    }


def _window_summary(rows: list[dict], window_name: str) -> tuple[int, int, float]:
    selected = [row for row in rows if row["window"] == window_name]
    valid_bars = sum(int(row["valid_bars"]) for row in selected)
    lt25 = sum(int(row["adx_lt_25"]) for row in selected)
    pct = (lt25 / valid_bars * 100.0) if valid_bars else 0.0
    return valid_bars, lt25, pct


def _detail_table(row: dict) -> list[str]:
    valid_bars = int(row["valid_bars"])
    return [
        "| metric | value |",
        "| --- | --- |",
        f"| total_bars | {row['total_bars']} |",
        f"| valid_bars | {valid_bars} |",
        f"| adx < 20 | {row['adx_lt_20']} ({_percent(row['adx_lt_20'], valid_bars)}) |",
        f"| 20 <= adx < 25 | {row['adx_20_to_25']} ({_percent(row['adx_20_to_25'], valid_bars)}) |",
        f"| 25 <= adx < 30 | {row['adx_25_to_30']} ({_percent(row['adx_25_to_30'], valid_bars)}) |",
        f"| adx >= 30 | {row['adx_ge_30']} ({_percent(row['adx_ge_30'], valid_bars)}) |",
        f"| adx < 25 (RANGING band) | {row['adx_lt_25']} ({_percent(row['adx_lt_25'], valid_bars)}) |",
        f"| adx >= 25 (TRENDING band) | {row['adx_ge_25']} ({_percent(row['adx_ge_25'], valid_bars)}) |",
        f"| p25 / p50 / p75 / p90 | {row['p25']:.4f} / {row['p50']:.4f} / {row['p75']:.4f} / {row['p90']:.4f} |",
    ]


def write_report(rows: list[dict]) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lines = [
        "# Regime Distribution Baseline",
        "",
        f"- generated_at: `{generated_at}`",
        "- data source: `Binance ccxt`",
        f"- timeframe: `{TIMEFRAME}`",
        f"- windows: {', '.join(f'`{name}` ({start} -> {end})' for name, (start, end) in DEFAULT_WINDOWS.items())}",
        "",
    ]

    for row in rows:
        lines.extend([
            f"### {row['symbol']} - {row['window']}",
            "",
            *_detail_table(row),
            "",
        ])

    lines.extend([
        "## Combined Summary",
        "",
        "| window | valid_bars | adx < 25 count | adx < 25 pct |",
        "| --- | ---: | ---: | ---: |",
    ])
    for window_name in DEFAULT_WINDOWS:
        valid_bars, lt25, pct = _window_summary(rows, window_name)
        lines.append(f"| {window_name} | {valid_bars} | {lt25} | {pct:.2f}% |")

    lookup = {(row["symbol"], row["window"]): row for row in rows}
    lines.extend([
        "",
        "## Plain-Language Readout",
        "",
        (
            "BTC/USDT uses `adx < 25` on 15m for "
            f"TRENDING_UP {(_window_summary([lookup[('BTC/USDT', 'TRENDING_UP')]], 'TRENDING_UP')[2]):.2f}%, "
            f"RANGING {(_window_summary([lookup[('BTC/USDT', 'RANGING')]], 'RANGING')[2]):.2f}%, "
            f"and MIXED {(_window_summary([lookup[('BTC/USDT', 'MIXED')]], 'MIXED')[2]):.2f}% of valid bars."
        ),
        (
            "ETH/USDT uses `adx < 25` on 15m for "
            f"TRENDING_UP {(_window_summary([lookup[('ETH/USDT', 'TRENDING_UP')]], 'TRENDING_UP')[2]):.2f}%, "
            f"RANGING {(_window_summary([lookup[('ETH/USDT', 'RANGING')]], 'RANGING')[2]):.2f}%, "
            f"and MIXED {(_window_summary([lookup[('ETH/USDT', 'MIXED')]], 'MIXED')[2]):.2f}% of valid bars."
        ),
    ])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT_PATH


def main() -> int:
    loader = BacktestDataLoader()
    rows: list[dict] = []
    for symbol in SYMBOLS:
        for window_name, (start, end) in DEFAULT_WINDOWS.items():
            print(f"[RegimeDistribution] {symbol} {TIMEFRAME} {window_name}: {start} -> {end}")
            rows.append(_measure_cell(loader, symbol, window_name, start, end))
    report_path = write_report(rows)
    print(f"[RegimeDistribution] report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
