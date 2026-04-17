"""Debug script: run one bar through scan_for_signals with verbose output"""
import sys
import logging
from pathlib import Path

# Show ALL log output
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s: %(message)s')

sys.path.insert(0, str(Path(__file__).parent))
TRADING_BOT_ROOT = Path(__file__).resolve().parent.parent.parent / "projects" / "trading_bot"
sys.path.insert(0, str(TRADING_BOT_ROOT))

import pandas as pd
from data_loader import BacktestDataLoader
from time_series_engine import TimeSeriesEngine
from mock_components import MockOrderEngine
from backtest_bot import create_backtest_bot
from bot_compat import get_config_class

loader = BacktestDataLoader()
print("Loading data...")
df_1h = loader.get_data("BTC/USDT", "1h", "2026-01-01", "2026-02-28")
df_4h = loader.get_data("BTC/USDT", "4h", "2026-01-01", "2026-02-28")
print(f"1H: {len(df_1h)} rows, 4H: {len(df_4h)} rows")

data = {"BTC/USDT": {"1h": df_1h, "4h": df_4h}}
tse = TimeSeriesEngine(data)
mock_engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)
bot = create_backtest_bot(tse, mock_engine)

Config = get_config_class()
Config.SYMBOLS = ["BTC/USDT"]
print(f"Config.SYMBOLS = {Config.SYMBOLS}")
print(f"Config.V6_DRY_RUN = {Config.V6_DRY_RUN}")
print(f"Config.USE_SCANNER_SYMBOLS = {Config.USE_SCANNER_SYMBOLS}")
print(f"Config.TIMEFRAME_TREND = {Config.TIMEFRAME_TREND}")
print(f"Config.TIMEFRAME_SIGNAL = {Config.TIMEFRAME_SIGNAL}")
print(f"Config.TIMEFRAME_MTF = {Config.TIMEFRAME_MTF}")
print(f"Config.ENABLE_MARKET_FILTER = {Config.ENABLE_MARKET_FILTER}")
print(f"Config.ADX_BASE_THRESHOLD = {Config.ADX_BASE_THRESHOLD}")

all_ts = tse.get_1h_timestamps(["BTC/USDT"])
print(f"Total timestamps: {len(all_ts)}")

# Run bars 200-210 (well past warmup) with full exception visibility
errors = 0
for i, ts in enumerate(all_ts[200:220]):
    tse.set_time(ts)
    print(f"\n--- Bar {200+i}: {ts} ---")
    try:
        bot.scan_for_signals()
        print(f"  active_trades after scan: {list(bot.active_trades.keys())}")
    except Exception as e:
        errors += 1
        import traceback
        print(f"  EXCEPTION: {e}")
        traceback.print_exc()

print(f"\nDone. Errors: {errors}, Active trades: {list(bot.active_trades.keys())}")

# Try one specific bar where conditions might be met
ts = all_ts[500]
tse.set_time(ts)
bars_1h = tse.get_bars("BTC/USDT", "1h", limit=200)
bars_1d = tse.get_bars("BTC/USDT", "1d", limit=200)
print(f"\nBar 500: {ts}, close={bars_1h.iloc[-1]['close']:.2f}, rows_1h={len(bars_1h)}, rows_1d={len(bars_1d)}")
print(f"  -> 1d bars from TSE (no '1d' in data dict): empty={bars_1d.empty}")

# Simulate what fetch_ohlcv does for TREND timeframe
df_trend = bot.fetch_ohlcv("BTC/USDT", Config.TIMEFRAME_TREND, limit=250)
df_signal = bot.fetch_ohlcv("BTC/USDT", Config.TIMEFRAME_SIGNAL, limit=100)
print(f"\nfetch_ohlcv results at bar 500:")
print(f"  df_trend ({Config.TIMEFRAME_TREND}): empty={df_trend.empty}, len={len(df_trend)}")
print(f"  df_signal ({Config.TIMEFRAME_SIGNAL}): empty={df_signal.empty}, len={len(df_signal)}")
print(f"\nConclusion: df_trend.empty={df_trend.empty} -> scan would skip at 'df_trend.empty or len < 100' check")
