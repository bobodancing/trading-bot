"""
資料提供者 — 統一交易所 OHLCV 獲取層

封裝 ccxt exchange 實例、fetch_ohlcv 重試邏輯，以及 Binance demo futures
REST fallback，提供 runtime/scanner 共用的市場資料入口。

使用方式（依賴注入）：
    provider = MarketDataProvider(
        exchange,
        max_retry=3,
        retry_delay=5.0,
        sandbox_mode=Config.SANDBOX_MODE,
        trading_mode=Config.TRADING_MODE,
    )
    df = provider.fetch_ohlcv('BTC/USDT', '1h', limit=100)
"""

import time
import logging
import pandas as pd
import requests

try:
    import ccxt
except ImportError:
    ccxt = None  # type: ignore

logger = logging.getLogger(__name__)

DEMO_FAPI_BASE_URL = 'https://demo-fapi.binance.com'
OHLCV_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']


class MarketDataProvider:
    """統一市場數據提供者：封裝 ccxt exchange 與 OHLCV 獲取邏輯"""

    def __init__(
        self,
        exchange,
        max_retry: int = 3,
        retry_delay: float = 5.0,
        sandbox_mode: bool = False,
        trading_mode: str = 'spot',
    ):
        """
        Args:
            exchange: 已初始化的 ccxt exchange 實例（依賴注入）
            max_retry: 最大重試次數
            retry_delay: 重試基礎間隔（秒），NetworkError 時會隨 attempt 線性增長
            sandbox_mode: 是否為 sandbox/demo 模式（啟用 demo-fapi fallback）
            trading_mode: 交易模式 'spot' 或 'future'
        """
        self.exchange = exchange
        self.max_retry = max_retry
        self.retry_delay = retry_delay
        self.sandbox_mode = sandbox_mode
        self.trading_mode = trading_mode

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        獲取 OHLCV K 線數據（含重試與 sandbox fallback）

        Futures sandbox 下，若 ccxt 失敗會切換為 demo-fapi.binance.com。

        Returns:
            pd.DataFrame with columns: timestamp, open, high, low, close, volume
            失敗時回傳空 DataFrame
        """
        for attempt in range(self.max_retry):
            try:
                ohlcv = None

                try:
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                except Exception as exchange_exc:
                    if self._can_use_demo_futures_fallback():
                        ohlcv = self._fetch_demo_futures_ohlcv(symbol, timeframe, limit)
                    if ohlcv is None:
                        raise exchange_exc

                if ohlcv is None or len(ohlcv) == 0:
                    return pd.DataFrame()

                return self._to_dataframe(ohlcv)

            except Exception as e:
                # ccxt.NetworkError 或其他異常：重試
                logger.debug(
                    "OHLCV fetch failed for %s %s attempt %s/%s: %s",
                    symbol,
                    timeframe,
                    attempt + 1,
                    self.max_retry,
                    e,
                )
                is_network = ccxt is not None and isinstance(e, ccxt.NetworkError)
                if attempt < self.max_retry - 1:
                    delay = self.retry_delay * (attempt + 1) if is_network else self.retry_delay
                    time.sleep(delay)
                else:
                    break

        return pd.DataFrame()

    def _can_use_demo_futures_fallback(self) -> bool:
        return self.trading_mode == 'future' and self.sandbox_mode

    def _fetch_demo_futures_ohlcv(self, symbol: str, timeframe: str, limit: int):
        """Fetch OHLCV from Binance demo futures when ccxt sandbox support misses."""
        symbol_id = symbol.replace('/', '')
        resp = requests.get(
            f'{DEMO_FAPI_BASE_URL}/fapi/v1/klines',
            params={'symbol': symbol_id, 'interval': timeframe, 'limit': limit},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.debug(
                "Demo futures OHLCV fallback failed for %s %s: %s %s",
                symbol,
                timeframe,
                resp.status_code,
                resp.text[:200],
            )
            return None

        return [
            [int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
            for c in resp.json()
        ]

    @staticmethod
    def _to_dataframe(ohlcv) -> pd.DataFrame:
        df = pd.DataFrame(ohlcv, columns=OHLCV_COLUMNS)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Keep timestamp as both a column and the index for existing readers
        # that dedupe by the latest completed bar.
        df.index = pd.DatetimeIndex(df['timestamp'], name='timestamp')
        return df
