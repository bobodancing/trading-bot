import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import pandas as pd
import pytest
from datetime import datetime, timezone
from trade_replayer import TradeReplayer


def make_test_db(tmp_path) -> str:
    """建立測試用 SQLite，插入一筆假交易"""
    db_path = str(tmp_path / "test_perf.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE,
            symbol TEXT, side TEXT, is_v6_pyramid INTEGER,
            signal_tier TEXT, entry_price REAL, exit_price REAL,
            total_size REAL, initial_r REAL,
            entry_time TEXT, exit_time TEXT, holding_hours REAL,
            pnl_usdt REAL, pnl_pct REAL, realized_r REAL,
            mfe_pct REAL, mae_pct REAL, capture_ratio REAL,
            stage_reached INTEGER, exit_reason TEXT,
            market_regime TEXT, entry_adx REAL, fakeout_depth_atr REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""INSERT INTO trades (
        trade_id, symbol, side, is_v6_pyramid, signal_tier,
        entry_price, exit_price, total_size, initial_r,
        entry_time, exit_time, holding_hours, pnl_usdt, pnl_pct, realized_r,
        mfe_pct, mae_pct, stage_reached, exit_reason, market_regime
    ) VALUES (
        'test_001', 'BTC/USDT', 'LONG', 1, 'A',
        40000.0, 40500.0, 0.01, 200.0,
        '2026-01-15T10:00:00+00:00', '2026-01-15T20:00:00+00:00',
        10.0, 50.0, 1.25, 0.25,
        2.0, -0.5, 1, 'STRUCTURE_TRAIL', 'TRENDING'
    )""")
    conn.commit()
    conn.close()
    return db_path


def test_load_trades(tmp_path):
    db_path = make_test_db(tmp_path)
    replayer = TradeReplayer(db_path=db_path)
    trades = replayer.load_trades(limit=10)
    assert len(trades) == 1
    assert trades[0]["symbol"] == "BTC/USDT"
    assert trades[0]["side"] == "LONG"


def test_load_trades_filter_by_symbol(tmp_path):
    db_path = make_test_db(tmp_path)
    replayer = TradeReplayer(db_path=db_path)
    trades = replayer.load_trades(symbol="ETH/USDT")
    assert len(trades) == 0


def test_replay_with_mock_data(tmp_path, monkeypatch):
    """replay 一筆交易，使用 monkeypatched DataLoader（不下載真實數據）"""
    from data_loader import BacktestDataLoader

    db_path = make_test_db(tmp_path)

    # 建立假 OHLCV（15 根 1H bar 圍繞 entry/exit 時間）
    n = 15
    idx = pd.date_range("2026-01-15T09:00:00", periods=n, freq="1h", tz="UTC")
    prices = [40000 + i * 50 for i in range(n)]
    df = pd.DataFrame({
        "open": prices, "high": [p + 30 for p in prices],
        "low": [p - 30 for p in prices], "close": prices,
        "volume": [100.0] * n,
    }, index=idx)

    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda *a, **k: df)

    replayer = TradeReplayer(db_path=db_path)
    trade = replayer.load_trades()[0]
    result = replayer.replay(trade)

    assert result is not None
    assert len(result["decisions"]) > 0
    assert "actual_exit_reason" in result
    assert "replayed_exit_reason" in result
