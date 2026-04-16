# tools/Backtesting/tests/test_report_generator.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from backtest_engine import BacktestConfig, BacktestResult
from report_generator import ReportGenerator


def make_fake_result():
    idx = pd.date_range("2026-01-01", periods=10, freq="1h", tz="UTC")
    equity = [(ts, 10000 + i * 50) for i, ts in enumerate(idx)]
    trades = [
        {"pnl_usdt": 100.0, "pnl_pct": 1.0, "exit_reason": "STRUCTURE_TRAIL",
         "stage_reached": 2, "symbol": "BTC/USDT", "side": "LONG",
         "entry_price": 40000.0, "exit_price": 40100.0,
         "entry_time": str(idx[0]), "exit_time": str(idx[5]),
         "holding_hours": 5.0, "realized_r": 1.5,
         "mfe_pct": 0.5, "mae_pct": -0.1},
        {"pnl_usdt": -50.0, "pnl_pct": -0.5, "exit_reason": "FAST_STOP",
         "stage_reached": 1, "symbol": "ETH/USDT", "side": "LONG",
         "entry_price": 2000.0, "exit_price": 1990.0,
         "entry_time": str(idx[1]), "exit_time": str(idx[3]),
         "holding_hours": 2.0, "realized_r": -1.0,
         "mfe_pct": 0.1, "mae_pct": -0.5},
    ]
    cfg = BacktestConfig(symbols=["BTC/USDT"], start="2026-01-01", end="2026-01-10")
    return BacktestResult(trades=trades, equity_curve=equity, config=cfg)


def test_report_generates_files(tmp_path):
    result = make_fake_result()
    gen = ReportGenerator()
    gen.generate(result, output_dir=tmp_path)
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "equity_curve.html").exists()


def test_trades_csv_has_correct_columns(tmp_path):
    result = make_fake_result()
    gen = ReportGenerator()
    gen.generate(result, output_dir=tmp_path)
    import pandas as pd
    df = pd.read_csv(tmp_path / "trades.csv")
    for col in ["symbol", "side", "pnl_usdt", "exit_reason", "stage_reached"]:
        assert col in df.columns


def test_summary_json_has_required_keys(tmp_path):
    import json
    result = make_fake_result()
    gen = ReportGenerator()
    gen.generate(result, output_dir=tmp_path)
    with open(tmp_path / "summary.json") as f:
        s = json.load(f)
    for key in ["total_trades", "win_rate", "profit_factor",
                "total_return_pct", "max_drawdown_pct", "sharpe"]:
        assert key in s
