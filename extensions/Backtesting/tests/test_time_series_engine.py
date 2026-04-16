# tests/test_time_series_engine.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from time_series_engine import TimeSeriesEngine


def make_df(n=10):
    """建立 n 根 1H 測試 K 線（UTC-aware index）"""
    idx = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({
        "open": range(n), "high": range(n), "low": range(n),
        "close": range(n), "volume": range(n)
    }, index=idx)


def test_no_lookahead():
    """set_time(bar_5) 只能看到 <= bar_5 的資料"""
    df = make_df(10)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    bar5_ts = df.index[4]  # 0-indexed → 第 5 根
    tse.set_time(bar5_ts)
    result = tse.get_bars("BTC/USDT", "1h", limit=100)
    assert len(result) == 5
    assert result.index[-1] == bar5_ts


def test_get_bars_respects_limit():
    df = make_df(10)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(df.index[-1])
    result = tse.get_bars("BTC/USDT", "1h", limit=3)
    assert len(result) == 3


def test_get_current_price():
    df = make_df(5)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(df.index[2])  # bar index 2, close=2
    assert tse.get_current_price("BTC/USDT") == 2.0


def test_get_1h_timestamps_intersection():
    """只回傳所有 symbol 共同的 timestamps"""
    df1 = make_df(5)
    df2 = make_df(3)
    tse = TimeSeriesEngine({
        "BTC/USDT": {"1h": df1},
        "ETH/USDT": {"1h": df2},
    })
    ts_list = tse.get_1h_timestamps(["BTC/USDT", "ETH/USDT"])
    assert len(ts_list) == 3  # 取交集


def test_get_bars_raises_if_no_time_set():
    """get_bars() before set_time() should raise RuntimeError"""
    df = make_df(5)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    with pytest.raises(RuntimeError, match="set_time"):
        tse.get_bars("BTC/USDT", "1h")


def test_get_bars_unknown_symbol_returns_empty():
    """Unknown symbol returns empty DataFrame (no crash)"""
    df = make_df(5)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(df.index[-1])
    result = tse.get_bars("UNKNOWN/USDT", "1h")
    assert result.empty
