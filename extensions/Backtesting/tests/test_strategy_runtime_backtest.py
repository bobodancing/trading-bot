import sys
from pathlib import Path

import pandas as pd

BACKTEST_ROOT = Path(__file__).resolve().parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from backtest_bot import create_backtest_bot
from mock_components import MockOrderEngine
from time_series_engine import TimeSeriesEngine


def _ohlcv(rows=90):
    idx = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + rows), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def _macd_cross_ohlcv():
    # SnapshotBuilder drops the latest live candle, so the cross is placed on
    # the penultimate row and the final row acts as the unfinished candle.
    closes = list(range(300, 240, -1)) + [361.0, 362.0]
    idx = pd.date_range("2025-01-01", periods=len(closes), freq="D", tz="UTC")
    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 1.0,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def _ema_cross_ohlcv():
    # SnapshotBuilder drops the latest live candle, so the EMA cross is placed
    # on the penultimate row and the final row acts as the unfinished candle.
    closes = [100.0] * 93 + [99.0, 98.0, 97.0, 96.0, 95.0, 98.0, 102.0, 106.0, 107.0]
    idx = pd.date_range("2025-01-01", periods=len(closes), freq="4h", tz="UTC")
    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def test_fixture_strategy_runs_through_live_like_backtest_path():
    data = {
        "BTC/USDT": {
            "1h": _ohlcv(),
            "4h": _ohlcv(40),
            "1d": _ohlcv(20),
        }
    }
    tse = TimeSeriesEngine(data)
    tse.set_time(data["BTC/USDT"]["1h"].index[-1])
    engine = MockOrderEngine(tse, initial_balance=10000.0)
    bot = create_backtest_bot(
        tse,
        engine,
        {
            "SYMBOLS": ["BTC/USDT"],
            "USE_SCANNER_SYMBOLS": False,
            "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
            "STRATEGY_RUNTIME_ENABLED": True,
            "ENABLED_STRATEGIES": ["fixture_long"],
        },
    )

    bot.scan_for_signals()

    assert "BTC/USDT" in bot.active_trades
    pm = bot.active_trades["BTC/USDT"]
    assert pm.strategy_id == "fixture_long"
    assert pm.current_sl < pm.avg_entry


def test_macd_zero_line_strategy_runs_through_live_like_backtest_path():
    daily = _macd_cross_ohlcv()
    hourly = daily.copy()
    data = {
        "BTC/USDT": {
            "1h": hourly,
            "1d": daily,
        }
    }
    tse = TimeSeriesEngine(data)
    tse.set_time(daily.index[-1])
    engine = MockOrderEngine(tse, initial_balance=10000.0)
    bot = create_backtest_bot(
        tse,
        engine,
        {
            "SYMBOLS": ["BTC/USDT"],
            "USE_SCANNER_SYMBOLS": False,
            "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
            # Plugin default stop_atr_mult=2.0 on synthetic daily ATR overshoots
            # the stock 6% SL cap; relax for this backtest-only test only.
            "MAX_SL_DISTANCE_PCT": 0.20,
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
            "STRATEGY_RUNTIME_ENABLED": True,
            "ENABLED_STRATEGIES": ["macd_zero_line_btc_1d"],
        },
    )

    bot.scan_for_signals()

    assert "BTC/USDT" in bot.active_trades
    pm = bot.active_trades["BTC/USDT"]
    assert pm.strategy_id == "macd_zero_line_btc_1d"
    assert pm.current_sl < pm.avg_entry


def test_ema_cross_7_19_strategy_opens_one_position_per_symbol():
    btc_4h = _ema_cross_ohlcv()
    eth_4h = _ema_cross_ohlcv()
    data = {
        "BTC/USDT": {
            "1h": btc_4h.copy(),
            "4h": btc_4h,
        },
        "ETH/USDT": {
            "1h": eth_4h.copy(),
            "4h": eth_4h,
        },
    }
    tse = TimeSeriesEngine(data)
    tse.set_time(btc_4h.index[-1])
    engine = MockOrderEngine(tse, initial_balance=10000.0)
    bot = create_backtest_bot(
        tse,
        engine,
        {
            "SYMBOLS": ["BTC/USDT", "ETH/USDT"],
            "USE_SCANNER_SYMBOLS": False,
            "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
            "STRATEGY_RUNTIME_ENABLED": True,
            "ENABLED_STRATEGIES": ["ema_cross_7_19_long_only"],
        },
        allowed_plugin_ids=["ema_cross_7_19_long_only"],
    )

    bot.scan_for_signals()

    assert sorted(bot.active_trades) == ["BTC/USDT", "ETH/USDT"]
    for symbol in ("BTC/USDT", "ETH/USDT"):
        pm = bot.active_trades[symbol]
        assert pm.strategy_id == "ema_cross_7_19_long_only"
        assert pm.strategy_version == "0.1.0"
        assert pm.current_sl < pm.avg_entry
