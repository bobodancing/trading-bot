"""
Tests for V6 Three-Tier Defense (replaces staged pullback).

Tier 1: Breakeven Bridge — MFE >= 1.5R → SL to entry + 0.1R
Tier 2: Fast Structural Trail — Stage 1, HL/LH only, right_bars=2
Tier 3: Standard BOS Trail — Stage 2+, left=7 right=3 + BOS
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from datetime import datetime, timezone, timedelta

from trader.positions import PositionManager


def _make_df(close=100.0, n=20):
    return pd.DataFrame({
        'open':     [close] * n,
        'high':     [close + 1.0] * n,
        'low':      [close - 1.0] * n,
        'close':    [close] * n,
        'volume':   [1000.0] * n,
        'vol_ma':   [1000.0] * n,
        'atr':      [1.0] * n,
        'ema_slow': [close] * n,
        'ema_fast': [close] * n,
    })


def _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
             highest_price=None, lowest_price=None):
    sl = avg_entry - risk_dist if side == 'LONG' else avg_entry + risk_dist
    pm = PositionManager(
        symbol='BTC/USDT', side=side,
        entry_price=avg_entry, stop_loss=sl,
        position_size=1.0, is_v6_pyramid=True,
        neckline=avg_entry + risk_dist * 2,
        equity_base=10000.0, initial_r=risk_dist,
    )
    pm.stage = stage
    pm.entry_time = datetime.now(timezone.utc) - timedelta(hours=1)
    if highest_price is not None:
        pm.highest_price = highest_price
    if lowest_price is not None:
        pm.lowest_price = lowest_price
    return pm


class TestPullbackRemoved:
    """確認 profit_pullback 已完全移除"""

    def test_no_pullback_stage1_long(self):
        """MFE 2R + 回撤 60%，不再觸發 PROFIT_PULLBACK"""
        pm = _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
                      highest_price=120.0)
        current_price = 112.0  # pullback = 8/20 = 40%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result.get('reason') != 'PROFIT_PULLBACK', \
            f"profit_pullback should be removed, got {result}"

    def test_no_pullback_stage2_short(self):
        """Stage 2 SHORT MFE 1R + 回撤 50%，不再觸發"""
        pm = _make_pm(side='SHORT', stage=2, avg_entry=100.0, risk_dist=10.0,
                      lowest_price=90.0)
        current_price = 95.0  # pullback = 5/10 = 50%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result.get('reason') != 'PROFIT_PULLBACK', \
            f"profit_pullback should be removed, got {result}"


class TestTier1Breakeven:
    """Tier 1: Breakeven Bridge"""

    def test_breakeven_long_triggered(self):
        """LONG MFE 2R → SL 應移到 entry + 0.1R"""
        pm = _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
                      highest_price=120.0)
        current_price = 118.0
        pm.monitor(current_price, _make_df(current_price))
        # entry=100, buffer=10*0.1=1, expected SL >= 101
        assert pm.current_sl >= 101.0, \
            f"Breakeven should move SL to entry+0.1R=101, got {pm.current_sl}"

    def test_breakeven_short_triggered(self):
        """SHORT MFE 2R → SL 應移到 entry - 0.1R"""
        pm = _make_pm(side='SHORT', stage=1, avg_entry=100.0, risk_dist=10.0,
                      lowest_price=80.0)
        current_price = 82.0
        pm.monitor(current_price, _make_df(current_price))
        # entry=100, buffer=10*0.1=1, expected SL <= 99
        assert pm.current_sl <= 99.0, \
            f"Breakeven should move SL to entry-0.1R=99, got {pm.current_sl}"

    def test_breakeven_not_triggered_below_threshold(self):
        """MFE 1.0R (< 1.5R) → SL 不動"""
        pm = _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
                      highest_price=110.0)
        original_sl = pm.current_sl  # 90
        current_price = 108.0
        pm.monitor(current_price, _make_df(current_price))
        assert pm.current_sl == original_sl, \
            f"SL should not move at MFE 1.0R, got {pm.current_sl}"

    def test_breakeven_ratchet(self):
        """保本移損只上不下（棘輪）"""
        pm = _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
                      highest_price=120.0)
        # 第一次觸發
        pm.monitor(118.0, _make_df(118.0))
        sl_after_be = pm.current_sl
        assert sl_after_be >= 101.0

        # highest 不變，再 monitor 一次不會降回去
        pm.monitor(105.0, _make_df(105.0))
        assert pm.current_sl >= sl_after_be, \
            f"Breakeven ratchet failed: {pm.current_sl} < {sl_after_be}"
