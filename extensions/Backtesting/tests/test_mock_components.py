import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from time_series_engine import TimeSeriesEngine
from mock_components import MockDataProvider, MockOrderEngine


def make_tse():
    idx = pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC")
    df = pd.DataFrame({
        "open":   [100, 101, 102, 103, 104],
        "high":   [105, 106, 107, 108, 109],
        "low":    [95,  96,  97,  98,  99],
        "close":  [102, 103, 104, 105, 106],
        "volume": [10]*5,
    }, index=idx)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(idx[-1])
    return tse, idx


def test_mock_data_provider_returns_df_with_timestamp_column():
    """MockDataProvider 回傳格式需與 data_provider 一致：timestamp 為 column，非 index"""
    tse, _ = make_tse()
    provider = MockDataProvider(tse)
    df = provider.fetch_ohlcv("BTC/USDT", "1h", limit=3)
    assert "timestamp" in df.columns
    assert not isinstance(df.index, pd.DatetimeIndex) or df.index.dtype == "int64"
    assert len(df) == 3


def test_mock_order_engine_create_order_returns_fill():
    tse, _ = make_tse()
    engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)
    result = engine.create_order("BTC/USDT", "BUY", 0.1)
    assert "avgPrice" in result
    assert result["avgPrice"] == pytest.approx(106.0)  # current bar close


def test_mock_order_engine_deducts_fee():
    tse, _ = make_tse()
    engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)
    engine.create_order("BTC/USDT", "BUY", 0.1)
    expected_fee = 106.0 * 0.1 * 0.0004
    assert engine.total_fees == pytest.approx(expected_fee)


def test_place_stop_loss_stores_order():
    tse, _ = make_tse()
    engine = MockOrderEngine(tse, fee_rate=0.0, initial_balance=10000.0)
    order_id = engine.place_hard_stop_loss("BTC/USDT", "LONG", 0.1, 95.0)
    assert order_id is not None
    assert order_id in engine.open_orders


def test_check_stop_triggers_long_hit():
    """LONG 持倉，bar.low <= stop_price → 觸發"""
    tse, idx = make_tse()
    tse.set_time(idx[0])  # bar 0: low=95
    engine = MockOrderEngine(tse, fee_rate=0.0, initial_balance=10000.0)
    engine.place_hard_stop_loss("BTC/USDT", "LONG", 0.1, stop_price=96.0)  # low=95 <= 96
    triggered = engine.check_stop_triggers()
    assert "BTC/USDT" in triggered


def test_check_stop_triggers_long_not_hit():
    """LONG 持倉，bar.low > stop_price → 不觸發"""
    tse, idx = make_tse()
    tse.set_time(idx[0])  # bar 0: low=95
    engine = MockOrderEngine(tse, fee_rate=0.0, initial_balance=10000.0)
    engine.place_hard_stop_loss("BTC/USDT", "LONG", 0.1, stop_price=90.0)  # low=95 > 90
    triggered = engine.check_stop_triggers()
    assert "BTC/USDT" not in triggered


def test_cancel_stop_loss_removes_order():
    tse, _ = make_tse()
    engine = MockOrderEngine(tse, fee_rate=0.0, initial_balance=10000.0)
    oid = engine.place_hard_stop_loss("BTC/USDT", "LONG", 0.1, 90.0)
    engine.cancel_stop_loss_order("BTC/USDT", oid)
    assert oid not in engine.open_orders


def test_update_hard_stop_loss_writes_pm_stop_order_id():
    """update_hard_stop_loss 必須寫入 pm.stop_order_id — trailing stop 的關鍵合約"""
    from unittest.mock import MagicMock
    tse, _ = make_tse()
    engine = MockOrderEngine(tse)
    pm = MagicMock()
    pm.symbol = "BTC/USDT"
    pm.side = "LONG"
    pm.total_size = 0.1
    pm.stop_order_id = None
    engine.update_hard_stop_loss(pm, new_stop=95.0)
    assert pm.stop_order_id is not None
    assert pm.stop_order_id in engine.open_orders


def test_check_stop_triggers_short_hit():
    """SHORT 持倉，bar.high >= stop_price → 觸發"""
    tse, idx = make_tse()
    tse.set_time(idx[0])  # bar 0: high=105
    engine = MockOrderEngine(tse, fee_rate=0.0, initial_balance=10000.0)
    engine.place_hard_stop_loss("BTC/USDT", "SHORT", 0.1, stop_price=104.0)  # high=105 >= 104
    triggered = engine.check_stop_triggers()
    assert "BTC/USDT" in triggered
