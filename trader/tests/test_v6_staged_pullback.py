"""
Tests for V6 staged pullback protection.

Stage 1 : MIN_MFE_R = 1.0R, threshold = 55%
Stage 2+ : MIN_MFE_R = 0.5R, threshold = 40%
"""
import sys
import os
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


class TestV6StagedPullback:

    def test_stage1_below_mfe_threshold_holds(self):
        """Stage 1, MFE 0.5R (< 1.0R) -> 不觸發 pullback, HOLD"""
        # mfe = 5, risk_dist = 10, mfe_r = 0.5 < 1.0
        pm = _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
                      highest_price=105.0)
        current_price = 102.0  # pullback = 3/5 = 60%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] != 'CLOSE' or result.get('reason') != 'PROFIT_PULLBACK', \
            f"Should NOT trigger pullback at MFE 0.5R (S1 needs 1.0R), got {result}"

    def test_stage1_above_threshold_closes(self):
        """Stage 1, MFE 1.2R (>= 1.0R), pullback 60% (>= 55%) -> CLOSE"""
        # mfe = 12, risk_dist = 10, mfe_r = 1.2
        pm = _make_pm(side='LONG', stage=1, avg_entry=100.0, risk_dist=10.0,
                      highest_price=112.0)
        current_price = 104.8  # pullback = 7.2/12 = 60%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] == 'CLOSE', f"Expected CLOSE, got {result}"
        assert result['reason'] == 'PROFIT_PULLBACK'

    def test_stage2_tighter_threshold_closes(self):
        """Stage 2, MFE 0.7R (>= 0.5R), pullback 45% (>= 40%) -> CLOSE"""
        # mfe = 7, risk_dist = 10, mfe_r = 0.7
        pm = _make_pm(side='LONG', stage=2, avg_entry=100.0, risk_dist=10.0,
                      highest_price=107.0)
        current_price = 103.85  # pullback = 3.15/7 = 45%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] == 'CLOSE', f"Expected CLOSE, got {result}"
        assert result['reason'] == 'PROFIT_PULLBACK'

    def test_stage2_below_mfe_threshold_holds(self):
        """Stage 2, MFE 0.3R (< 0.5R) -> HOLD"""
        # mfe = 3, risk_dist = 10, mfe_r = 0.3 < 0.5
        pm = _make_pm(side='LONG', stage=2, avg_entry=100.0, risk_dist=10.0,
                      highest_price=103.0)
        current_price = 101.5  # pullback = 1.5/3 = 50%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] != 'CLOSE' or result.get('reason') != 'PROFIT_PULLBACK', \
            f"Should NOT trigger pullback at MFE 0.3R (S2 needs 0.5R), got {result}"

    def test_stage1_short_above_threshold_closes(self):
        """SHORT Stage 1, MFE 1.5R (>= 1.0R), pullback 60% (>= 55%) -> CLOSE"""
        # mfe = 15, risk_dist = 10, mfe_r = 1.5
        pm = _make_pm(side='SHORT', stage=1, avg_entry=100.0, risk_dist=10.0,
                      lowest_price=85.0)
        current_price = 94.0  # pullback = (94-85)/15 = 60%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] == 'CLOSE', f"Expected CLOSE, got {result}"
        assert result['reason'] == 'PROFIT_PULLBACK'

    def test_stage2_short_tighter_closes(self):
        """SHORT Stage 2, MFE 0.6R (>= 0.5R), pullback 42% (>= 40%) -> CLOSE"""
        # mfe = 6, risk_dist = 10, mfe_r = 0.6
        pm = _make_pm(side='SHORT', stage=2, avg_entry=100.0, risk_dist=10.0,
                      lowest_price=94.0)
        current_price = 96.52  # pullback = (96.52-94)/6 = 42%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] == 'CLOSE', f"Expected CLOSE, got {result}"
        assert result['reason'] == 'PROFIT_PULLBACK'

    def test_stage3_uses_s2_threshold(self):
        """Stage 3 使用 S2+ 門檻 (0.5R / 40%)"""
        # mfe = 6, risk_dist = 10, mfe_r = 0.6 >= 0.5
        pm = _make_pm(side='LONG', stage=3, avg_entry=100.0, risk_dist=10.0,
                      highest_price=106.0)
        current_price = 103.6  # pullback = 2.4/6 = 40%
        result = pm.monitor(current_price, _make_df(current_price))
        assert result['action'] == 'CLOSE', f"Expected CLOSE, got {result}"
        assert result['reason'] == 'PROFIT_PULLBACK'
