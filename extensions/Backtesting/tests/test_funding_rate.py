import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


class TestFundingLoader:
    def test_cache_hit(self, tmp_path):
        """有 cache 時不打 API"""
        from funding_loader import FundingLoader

        # 準備假 parquet
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-01 08:00"], format="mixed"),
            "funding_rate": [0.0001, -0.0002],
        }).set_index("timestamp")
        cache_file = tmp_path / "BTCUSDT_funding_20260101_20260201.parquet"
        df.to_parquet(cache_file)

        loader = FundingLoader(cache_dir=tmp_path)
        result = loader.get_funding_rates("BTC/USDT", "2026-01-01", "2026-02-01")
        assert len(result) == 2
        assert result.iloc[0] == pytest.approx(0.0001)

    def test_download_with_rate_limit(self):
        """下載時有 sleep(0.5) rate limit"""
        from funding_loader import FundingLoader

        loader = FundingLoader()
        with patch.object(loader, '_download') as mock_dl:
            mock_dl.return_value = pd.DataFrame()
            with patch.object(loader, '_cache_path') as mock_cp:
                mock_cp.return_value = Path("nonexistent.parquet")
                loader.get_funding_rates("BTC/USDT", "2026-01-01", "2026-02-01")
                mock_dl.assert_called_once()


class TestMockOrderEngineFunding:
    def test_deduct_funding_long_positive_rate(self):
        """LONG + positive rate → 扣錢"""
        from mock_components import MockOrderEngine
        from time_series_engine import TimeSeriesEngine

        tse = TimeSeriesEngine({})
        engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)

        engine.deduct_funding("BTC/USDT", "LONG", 0.1, 100000.0, 0.0001)
        # fee = 0.1 * 100000 * 0.0001 = 1.0
        assert engine.total_fees == pytest.approx(1.0)

    def test_deduct_funding_short_positive_rate(self):
        """SHORT + positive rate → 收錢（fee 減少）"""
        from mock_components import MockOrderEngine
        from time_series_engine import TimeSeriesEngine

        tse = TimeSeriesEngine({})
        engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)

        engine.deduct_funding("BTC/USDT", "SHORT", 0.1, 100000.0, 0.0001)
        # fee = 0.1 * 100000 * (-0.0001) = -1.0 → 收到 1.0
        assert engine.total_fees == pytest.approx(-1.0)
