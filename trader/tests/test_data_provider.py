import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trader.infrastructure.data_provider import MarketDataProvider


class TestMarketDataProvider:
    def test_fetch_ohlcv_uses_datetime_index_and_keeps_timestamp_column(self):
        exchange = MagicMock()
        exchange.fetch_ohlcv.return_value = [
            [1711929600000, 100.0, 110.0, 95.0, 105.0, 1000.0],
            [1711944000000, 105.0, 112.0, 101.0, 108.0, 900.0],
        ]

        provider = MarketDataProvider(exchange)
        df = provider.fetch_ohlcv("BTC/USDT", "4h", limit=2)

        assert not df.empty
        assert 'timestamp' in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == 'timestamp'
        assert df.index[-1] == df['timestamp'].iloc[-1]
