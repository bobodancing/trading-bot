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
            "STRATEGY_CATALOG": {
                "fixture_long": {
                    "enabled": True,
                    "module": "trader.strategies.plugins.fixture",
                    "class": "FixtureLongStrategy",
                    "params": {"symbol": "BTC/USDT", "stop_pct": 0.02},
                }
            },
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
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
            "STRATEGY_RUNTIME_ENABLED": True,
            "ENABLED_STRATEGIES": ["macd_zero_line_btc_1d"],
            "STRATEGY_CATALOG": {
                "macd_zero_line_btc_1d": {
                    "enabled": True,
                    "module": "trader.strategies.plugins.macd_zero_line",
                    "class": "MacdZeroLineLongStrategy",
                    "params": {
                        "symbol": "BTC/USDT",
                        "timeframe": "1d",
                        "stop_atr_mult": 1.0,
                    },
                }
            },
        },
    )

    bot.scan_for_signals()

    assert "BTC/USDT" in bot.active_trades
    pm = bot.active_trades["BTC/USDT"]
    assert pm.strategy_id == "macd_zero_line_btc_1d"
    assert pm.current_sl < pm.avg_entry
