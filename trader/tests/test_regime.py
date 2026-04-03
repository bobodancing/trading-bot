# trader/tests/test_regime.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import pandas as pd
import numpy as np
from trader.regime import RegimeEngine


def _make_df(adx_values, bbw_values, atr_values, n=60):
    """Build a minimal 4H DataFrame with required columns."""
    dates = pd.date_range('2026-01-01', periods=n, freq='4h')
    close = [87000 + i * 10 for i in range(n)]
    df = pd.DataFrame({
        'open': close, 'high': [c + 100 for c in close],
        'low': [c - 100 for c in close], 'close': close,
        'volume': [1000] * n,
        'adx': adx_values, 'bbw': bbw_values, 'atr': atr_values,
    }, index=dates)
    return df


class TestRegimeDetection:
    def test_trending_high_adx(self):
        """ADX >= 25 → TRENDING (even without rising)"""
        engine = RegimeEngine()
        adx = [30, 29, 28] + [28] * 57  # ADX >= 25 but declining — still TRENDING
        bbw = [0.05] * 60
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        # Feed 3 different candle times to pass hysteresis
        for i in range(3):
            sub = df.iloc[:50 + i]
            result = engine.update(sub)
        assert result == "TRENDING"

    def test_ranging_low_adx_low_bbw(self):
        """ADX < 20, BBW < 25th pct → RANGING"""
        engine = RegimeEngine()
        # 50 candles of BBW history, last ones very low
        bbw = [0.08] * 40 + [0.01] * 20  # last 20 are very low (< 25th pct)
        adx = [15] * 60  # ADX consistently below 20
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        for i in range(3):
            sub = df.iloc[:50 + i]
            result = engine.update(sub)
        assert result == "RANGING"

    def test_squeeze_very_low_bbw_no_atr_expansion(self):
        """BBW < 10th pct, ATR not expanding → SQUEEZE"""
        engine = RegimeEngine()
        bbw = [0.08] * 40 + [0.002] * 20  # extremely low BBW
        adx = [18] * 60  # low ADX
        atr = [200] * 60  # stable ATR (not expanding)
        df = _make_df(adx, bbw, atr)
        for i in range(3):
            sub = df.iloc[:50 + i]
            result = engine.update(sub)
        assert result == "SQUEEZE"


class TestHysteresis:
    def test_no_switch_without_confirmation(self):
        """Single candle anomaly should not trigger switch"""
        engine = RegimeEngine()
        engine.current_regime = "TRENDING"
        # One RANGING signal then back to TRENDING
        adx_ranging = [15] * 60
        bbw_low = [0.01] * 60
        atr = [200] * 60
        df_ranging = _make_df(adx_ranging, bbw_low, atr)
        # Only one new candle
        engine.update(df_ranging.iloc[:51])
        assert engine.current_regime == "TRENDING"  # Not switched yet

    def test_switch_after_3_candles(self):
        """3 consecutive confirming candles triggers switch"""
        engine = RegimeEngine()
        engine.current_regime = "TRENDING"
        adx = [15] * 60
        bbw = [0.08] * 40 + [0.01] * 20
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        for i in range(3):
            engine.update(df.iloc[:50 + i])
        assert engine.current_regime == "RANGING"

    def test_same_candle_dedup(self):
        """Calling update with same candle time should not increment counter"""
        engine = RegimeEngine()
        engine.current_regime = "TRENDING"
        adx = [15] * 60
        bbw = [0.08] * 40 + [0.01] * 20
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        # Call 5 times with same data (same last candle time)
        for _ in range(5):
            engine.update(df.iloc[:51])
        assert engine.current_regime == "TRENDING"  # Only 1 real update

    def test_datetime_index_advances_confirmation_counter(self):
        """Different completed candle times should count even with the same frame length"""
        engine = RegimeEngine()
        engine.current_regime = "TRENDING"
        adx = [15] * 60
        bbw = [0.08] * 40 + [0.01] * 20
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)

        first = df.iloc[:51].copy()
        second = df.iloc[:51].copy()
        second.index = second.index + pd.Timedelta(hours=4)

        engine.update(first)
        engine.update(second)

        assert engine._confirm_count == 2

    def test_adx_middle_zone_keeps_previous(self):
        """ADX 20-25 (ambiguous) should keep previous regime"""
        engine = RegimeEngine()
        engine.current_regime = "RANGING"
        adx = [22] * 60  # middle zone
        bbw = [0.04] * 60  # moderate BBW
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        for i in range(5):
            engine.update(df.iloc[:50 + i])
        assert engine.current_regime == "RANGING"  # Stays the same


class TestTrendDirection:
    def test_trending_long(self):
        """TRENDING + plus_di > minus_di → direction LONG"""
        engine = RegimeEngine()
        adx = [30] * 60
        bbw = [0.05] * 60
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        df['DMP_14'] = [25.0] * 60  # plus_di > minus_di
        df['DMN_14'] = [15.0] * 60
        for i in range(3):
            engine.update(df.iloc[:50 + i])
        assert engine.trend_direction == "LONG"

    def test_trending_short(self):
        """TRENDING + minus_di > plus_di → direction SHORT"""
        engine = RegimeEngine()
        adx = [30] * 60
        bbw = [0.05] * 60
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        df['DMP_14'] = [12.0] * 60
        df['DMN_14'] = [28.0] * 60
        for i in range(3):
            engine.update(df.iloc[:50 + i])
        assert engine.trend_direction == "SHORT"

    def test_ambiguous_zone_keeps_direction_hint(self):
        """ADX 20-25 should still update direction for BTC guard fallback avoidance"""
        engine = RegimeEngine()
        engine.current_regime = "TRENDING"
        adx = [22] * 60
        bbw = [0.04] * 60
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        df['DMP_14'] = [12.0] * 60
        df['DMN_14'] = [28.0] * 60

        for i in range(3):
            engine.update(df.iloc[:50 + i])

        assert engine.current_regime == "TRENDING"
        assert engine.trend_direction == "SHORT"

    def test_ranging_no_direction(self):
        """RANGING → trend_direction is None"""
        engine = RegimeEngine()
        adx = [15] * 60
        bbw = [0.08] * 40 + [0.01] * 20
        atr = [200] * 60
        df = _make_df(adx, bbw, atr)
        df['DMP_14'] = [25.0] * 60
        df['DMN_14'] = [15.0] * 60
        for i in range(3):
            engine.update(df.iloc[:50 + i])
        assert engine.trend_direction is None
