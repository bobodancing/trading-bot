"""Binance 歷史 Funding Rate 下載 + Parquet cache"""

import ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import time

DEFAULT_CACHE_DIR = Path(__file__).parent / 'cache'


class FundingLoader:
    """下載 Binance Futures 歷史 funding rate，自動 Parquet cache"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })

    def get_funding_rates(
        self,
        symbol: str,
        start: str,
        end: str,
    ) -> pd.Series:
        """
        主入口：回傳 funding rate Series，index=timestamp(UTC)。
        每 8 小時一筆（00:00, 08:00, 16:00 UTC）。
        """
        cache_path = self._cache_path(symbol, start, end)
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            return df["funding_rate"]

        df = self._download(symbol, start, end)
        if not df.empty:
            df.to_parquet(cache_path)
        return df["funding_rate"] if not df.empty else pd.Series(dtype=float)

    def _download(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """分批下載（每批 1000 筆），rate limit 友善"""
        start_ts = self._to_ms(start)
        end_ts = self._to_ms(end)

        all_records = []
        since = start_ts
        batch = 0

        while since < end_ts:
            batch += 1
            try:
                rates = self.exchange.fetch_funding_rate_history(
                    symbol, since=since, limit=1000
                )
            except Exception as e:
                print(f"  [WARN] fetch_funding_rate failed: {e}, retrying in 5s...")
                time.sleep(5)
                continue

            if not rates:
                break

            all_records.extend(rates)

            last_ts = rates[-1]['timestamp']
            if last_ts <= since:
                break
            since = last_ts + 1

            if batch % 5 == 0:
                print(f"  funding batch {batch}: {len(rates)} records")

            time.sleep(0.5)

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'timestamp': r['timestamp'],
            'funding_rate': r['fundingRate'],
        } for r in all_records])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        df = df[df.index <= pd.Timestamp(end, tz='UTC')]
        df = df[~df.index.duplicated(keep='first')]
        df.sort_index(inplace=True)
        return df

    def _cache_path(self, symbol: str, start: str, end: str) -> Path:
        sym_clean = symbol.replace('/', '')
        start_clean = start.replace('-', '')[:8]
        end_clean = end.replace('-', '')[:8]
        return self.cache_dir / f"{sym_clean}_funding_{start_clean}_{end_clean}.parquet"

    @staticmethod
    def _to_ms(date_str: str) -> int:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
