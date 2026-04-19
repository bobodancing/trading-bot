"""Historical OHLCV loader with local Parquet cache for backtests."""

import os
import ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import time

CACHE_DIR = Path(os.environ.get("BACKTEST_CACHE_DIR", str(Path(__file__).parent / 'cache')))


class BacktestDataLoader:
    """Download Binance OHLCV candles and cache them as Parquet."""

    def __init__(self):
        self.exchange = ccxt.binance({'enableRateLimit': True})
        CACHE_DIR.mkdir(exist_ok=True)

    def get_data(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """
        Load OHLCV data for a symbol/timeframe/date range.

        Args:
            symbol: 'BTC/USDT'
            timeframe: '1h', '4h', '1d'
            start: '2026-01-01' (ISO date string)
            end: '2026-02-27'
        Returns:
            DataFrame, index=timestamp(UTC), columns=[open,high,low,close,volume]
        """
        cache_path = self._cache_path(symbol, timeframe, start, end)
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            return df

        df = self._download(symbol, timeframe, start, end)
        if not df.empty:
            df.to_parquet(cache_path)
        return df

    def _download(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """Download OHLCV candles in batches while respecting rate limits."""
        start_ts = self._to_ms(start)
        end_ts = self._to_ms(end)

        all_dfs = []
        since = start_ts
        batch = 0

        while since < end_ts:
            batch += 1
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=1500
                )
            except Exception as e:
                print(f"  [WARN] fetch_ohlcv failed: {e}, retrying in 5s...")
                time.sleep(5)
                continue

            if not ohlcv:
                break

            df = pd.DataFrame(
                ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)

            # Trim the final batch to the requested end timestamp.
            df = df[df.index <= pd.Timestamp(end, tz='UTC')]
            all_dfs.append(df)

            # Advance by one millisecond to avoid duplicate last candles.
            last_ts = int(df.index[-1].timestamp() * 1000)
            if last_ts <= since:
                break
            since = last_ts + 1

            if batch % 5 == 0:
                print(f"  batch {batch}: {len(df)} rows, up to {df.index[-1]}")

            time.sleep(0.5)  # rate limit buffer

        if not all_dfs:
            return pd.DataFrame()

        result = pd.concat(all_dfs)
        result = result[~result.index.duplicated(keep='first')]
        result.sort_index(inplace=True)
        return result

    def _cache_path(self, symbol: str, tf: str, start: str, end: str) -> Path:
        """Return cache path like cache/BTCUSDT_1h_20260101_20260227.parquet."""
        sym_clean = symbol.replace('/', '')
        start_clean = start.replace('-', '')[:8]
        end_clean = end.replace('-', '')[:8]
        return CACHE_DIR / f"{sym_clean}_{tf}_{start_clean}_{end_clean}.parquet"

    @staticmethod
    def _to_ms(date_str: str) -> int:
        """Convert an ISO date string to a millisecond timestamp."""
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)


if __name__ == '__main__':
    # Quick test
    loader = BacktestDataLoader()
    print("Downloading BTC/USDT 1h 2026-01-01 ~ 2026-02-27...")
    df = loader.get_data('BTC/USDT', '1h', '2026-01-01', '2026-02-27')
    print(f"Rows: {len(df)}, Columns: {list(df.columns)}")
    print(f"First: {df.index[0]}, Last: {df.index[-1]}")
    print(f"Cache file exists: {loader._cache_path('BTC/USDT','1h','2026-01-01','2026-02-27').exists()}")
