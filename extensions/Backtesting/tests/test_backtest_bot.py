import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from time_series_engine import TimeSeriesEngine
from mock_components import MockDataProvider, MockOrderEngine
from backtest_bot import create_backtest_bot


def make_tse_with_data():
    idx = pd.date_range("2026-01-01", periods=20, freq="1h", tz="UTC")
    df = pd.DataFrame({
        "open":   [100+i for i in range(20)],
        "high":   [105+i for i in range(20)],
        "low":    [95+i  for i in range(20)],
        "close":  [102+i for i in range(20)],
        "volume": [100]*20,
    }, index=idx)
    tse = TimeSeriesEngine({
        "BTC/USDT": {"1h": df, "4h": df},
    })
    tse.set_time(idx[-1])
    return tse


def test_create_backtest_bot_no_network():
    """建立 backtest bot 時不應發出任何網路請求"""
    tse = make_tse_with_data()
    mock_engine = MockOrderEngine(tse, initial_balance=10000.0)
    bot = create_backtest_bot(tse, mock_engine)
    assert bot is not None
    # data_provider 應為 MockDataProvider
    from mock_components import MockDataProvider
    assert isinstance(bot.data_provider, MockDataProvider)
    # execution_engine 應為 MockOrderEngine
    assert bot.execution_engine is mock_engine


def test_fetch_ohlcv_uses_tse():
    """bot.fetch_ohlcv 應回傳 TSE 的數據，不打 API"""
    tse = make_tse_with_data()
    mock_engine = MockOrderEngine(tse, initial_balance=10000.0)
    bot = create_backtest_bot(tse, mock_engine)
    df = bot.fetch_ohlcv("BTC/USDT", "1h", limit=5)
    assert not df.empty
    assert "timestamp" in df.columns  # 格式與 data_provider 一致


def test_fetch_ticker_uses_tse():
    """bot.fetch_ticker 應回傳 TSE 的當前價格"""
    tse = make_tse_with_data()
    mock_engine = MockOrderEngine(tse, initial_balance=10000.0)
    bot = create_backtest_bot(tse, mock_engine)
    ticker = bot.fetch_ticker("BTC/USDT")
    assert "last" in ticker
    assert ticker["last"] > 0
