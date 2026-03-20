"""
Tests for Three-Tier Defense structural trailing (Tier 2 / Tier 3 dispatch).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from trader.structure import StructureAnalysis


def _make_swing_df(prices, n_flat_prefix=10, atr_val=1.0):
    """
    Build a 1H OHLCV DataFrame with explicit price path.
    prices: list of close prices forming the swing pattern.
    Prepends n_flat_prefix flat bars so swing detection has enough left context.
    """
    base = prices[0] if prices else 100.0
    flat = [base] * n_flat_prefix
    full = flat + list(prices)
    n = len(full)
    df = pd.DataFrame({
        'open':   full,
        'high':   [p + 0.5 for p in full],
        'low':    [p - 0.5 for p in full],
        'close':  full,
        'volume': [1000.0] * n,
        'atr':    [atr_val] * n,
    })
    return df


class TestGetFastTrailingSwing:
    """Tier 2: get_fast_trailing_swing — HL/LH only, no BOS"""

    def test_fast_trail_finds_hl(self):
        """加速追蹤應能找到 Higher Low（不需要 BOS）"""
        # 構造 swing low: 左 7 右 2 確認
        # Pattern: flat at 100, dip to 95 (swing low), recover to 100+
        prices = [100, 100, 100, 100, 100, 100, 100,  # left context
                  95,  # swing low candidate
                  97, 98]  # right confirmation (2 bars)
        df = _make_swing_df(prices, n_flat_prefix=0)

        result = StructureAnalysis.get_fast_trailing_swing(
            df, side='LONG', current_sl=90.0, left_bars=7, right_bars=2
        )
        # swing low at 95 > current_sl 90 → should return 95
        assert result is not None, "Fast trail should find HL swing"
        assert result == 95.0 or abs(result - 95.0) < 1.0

    def test_fast_trail_no_hl_below_sl(self):
        """swing low 低於 current_sl → 不移損"""
        prices = [100, 100, 100, 100, 100, 100, 100,
                  85,  # below current_sl=90
                  87, 88]
        df = _make_swing_df(prices, n_flat_prefix=0)

        result = StructureAnalysis.get_fast_trailing_swing(
            df, side='LONG', current_sl=90.0, left_bars=7, right_bars=2
        )
        assert result is None

    def test_fast_trail_short_finds_lh(self):
        """SHORT: 找到 Lower High"""
        prices = [100, 100, 100, 100, 100, 100, 100,
                  108,  # swing high candidate
                  106, 105]
        df = _make_swing_df(prices, n_flat_prefix=0)

        result = StructureAnalysis.get_fast_trailing_swing(
            df, side='SHORT', current_sl=115.0, left_bars=7, right_bars=2
        )
        # swing high ~108 < current_sl 115 → should return
        assert result is not None, "Fast trail should find LH swing for SHORT"


class TestTierDispatch:
    """確認 Stage 1 用 Tier 2，Stage 2+ 用 Tier 3"""

    def test_stage1_no_profit_pullback(self):
        """Stage 1 大幅回撤不會觸發 PROFIT_PULLBACK"""
        from trader.positions import PositionManager
        from datetime import datetime, timezone, timedelta

        pm = PositionManager(
            symbol='TEST/USDT', side='LONG',
            entry_price=100.0, stop_loss=90.0,
            position_size=1.0, is_v6_pyramid=True,
            neckline=120.0, equity_base=10000.0, initial_r=10.0,
        )
        pm.stage = 1
        pm.entry_time = datetime.now(timezone.utc) - timedelta(hours=1)
        pm.highest_price = 115.0  # MFE 1.5R

        df = pd.DataFrame({
            'open':     [105.0] * 20,
            'high':     [106.0] * 20,
            'low':      [104.0] * 20,
            'close':    [105.0] * 20,
            'volume':   [1000.0] * 20,
            'vol_ma':   [1000.0] * 20,
            'atr':      [1.0] * 20,
            'ema_slow': [105.0] * 20,
            'ema_fast': [105.0] * 20,
        })

        result = pm.monitor(105.0, df)
        assert result.get('reason') != 'PROFIT_PULLBACK', \
            f"Stage 1 should not trigger pullback, got {result}"
