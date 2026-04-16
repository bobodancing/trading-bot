"""歷史 K 線下載 + Parquet 本地快取"""

import os
import ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import time

CACHE_DIR = Path(os.environ.get("BACKTEST_CACHE_DIR", str(Path(__file__).parent / 'cache')))


class BacktestDataLoader:
    """下載 Binance 歷史 K 線，自動 Parquet 快取"""

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
        主入口：先查快取，沒有才下載。
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
        """分批下載（每批 1500 根），rate limit 友善"""
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

            # 只保留 end 以前的數據
            df = df[df.index <= pd.Timestamp(end, tz='UTC')]
            all_dfs.append(df)

            # 下一批從最後一根的下一根開始
            last_ts = int(df.index[-1].timestamp() * 1000)
            if last_ts <= since:
                break  # 沒有新數據了
            since = last_ts + 1

            if batch % 5 == 0:
                print(f"  batch {batch}: {len(df)} rows, up to {df.index[-1]}")

            time.sleep(0.5)  # rate limit 保護

        if not all_dfs:
            return pd.DataFrame()

        result = pd.concat(all_dfs)
        result = result[~result.index.duplicated(keep='first')]
        result.sort_index(inplace=True)
        return result

    def _cache_path(self, symbol: str, tf: str, start: str, end: str) -> Path:
        """快取命名: cache/BTCUSDT_1h_20260101_20260227.parquet"""
        sym_clean = symbol.replace('/', '')
        start_clean = start.replace('-', '')[:8]
        end_clean = end.replace('-', '')[:8]
        return CACHE_DIR / f"{sym_clean}_{tf}_{start_clean}_{end_clean}.parquet"

    @staticmethod
    def _to_ms(date_str: str) -> int:
        """ISO date string → milliseconds timestamp"""
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
