# trader/regime.py
"""
Regime Engine — 三態市場偵測 (TRENDING / RANGING / SQUEEZE)
基於 4H ADX + BBW + ATR，帶 hysteresis 防抖。
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from trader.config import Config

logger = logging.getLogger(__name__)


class RegimeEngine:
    """三態 market regime 偵測引擎"""

    def __init__(self):
        self.current_regime: str = "TRENDING"
        self._pending_regime: str = "TRENDING"
        self._confirm_count: int = 0
        self._last_candle_time: Optional[pd.Timestamp] = None
        self._trend_direction: Optional[str] = None  # "LONG" / "SHORT"

    @property
    def trend_direction(self) -> Optional[str]:
        """TRENDING → LONG/SHORT (from +DI/-DI), RANGING/SQUEEZE → None"""
        if self.current_regime != "TRENDING":
            return None
        return self._trend_direction

    def update(self, df_4h: pd.DataFrame) -> str:
        """每 cycle 呼叫，回傳 'TRENDING' | 'RANGING' | 'SQUEEZE'。
        只在新 K 線收盤時更新 counter。
        """
        if df_4h is None or df_4h.empty:
            return self.current_regime

        latest_time = df_4h.index[-1]
        if latest_time == self._last_candle_time:
            return self.current_regime

        self._last_candle_time = latest_time
        detected = self._detect_regime(df_4h)

        if detected is None:
            return self.current_regime

        if detected == self._pending_regime:
            self._confirm_count += 1
        else:
            self._pending_regime = detected
            self._confirm_count = 1

        threshold = getattr(Config, 'REGIME_CONFIRM_CANDLES', 3)
        if self._confirm_count >= threshold:
            if self.current_regime != self._pending_regime:
                logger.info(
                    f"Regime switch: {self.current_regime} → {self._pending_regime} "
                    f"(confirmed {self._confirm_count} candles)"
                )
            self.current_regime = self._pending_regime

        self._update_direction(df_4h)
        return self.current_regime

    def _detect_regime(self, df: pd.DataFrame) -> Optional[str]:
        """根據 ADX / BBW / ATR 判斷當前 regime（單次偵測，不含 hysteresis）"""
        if 'adx' not in df.columns or 'bbw' not in df.columns or 'atr' not in df.columns:
            return None

        adx = df['adx'].iloc[-1]
        if pd.isna(adx):
            return None

        adx_trending = getattr(Config, 'REGIME_ADX_TRENDING', 25)
        adx_ranging = getattr(Config, 'REGIME_ADX_RANGING', 20)
        bbw_history = getattr(Config, 'REGIME_BBW_HISTORY', 50)
        bbw_ranging_pct = getattr(Config, 'REGIME_BBW_RANGING_PCT', 25)
        bbw_squeeze_pct = getattr(Config, 'REGIME_BBW_SQUEEZE_PCT', 10)
        atr_squeeze_mult = getattr(Config, 'REGIME_ATR_SQUEEZE_MULT', 1.1)
        atr_trending_mult = getattr(Config, 'REGIME_ATR_TRENDING_MULT', 1.3)

        # TRENDING: ADX >= 25 單獨即觸發
        if adx >= adx_trending:
            return "TRENDING"

        # ATR expansion check → direct TRENDING
        atr_series = df['atr'].dropna()
        if len(atr_series) >= 20:
            recent_atr = atr_series.iloc[-1]
            avg_atr = atr_series.iloc[-20:].mean()
            if avg_atr > 0 and recent_atr > avg_atr * atr_trending_mult:
                return "TRENDING"

        # BBW percentile calculation
        bbw_series = df['bbw'].dropna()
        if len(bbw_series) < 20:
            return None

        current_bbw = bbw_series.iloc[-1]
        history = bbw_series.iloc[-bbw_history:] if len(bbw_series) >= bbw_history else bbw_series
        bbw_pct = (history < current_bbw).sum() / len(history) * 100
        mean_bbw = history.mean()
        # ratio to mean: robust fallback when all low values are equal (pct collapses to 0)
        bbw_ratio = current_bbw / mean_bbw if mean_bbw > 0 else 1.0

        # SQUEEZE: BBW < 10th pct AND truly extreme (< 15% of mean), ATR not expanding
        # The ratio guard prevents RANGING-level compression from triggering SQUEEZE
        is_squeeze = (bbw_pct < bbw_squeeze_pct) and (bbw_ratio < 0.15)
        if is_squeeze:
            if len(atr_series) >= 20:
                recent_atr = atr_series.iloc[-1]
                avg_atr = atr_series.iloc[-20:].mean()
                if avg_atr > 0 and recent_atr <= avg_atr * atr_squeeze_mult:
                    return "SQUEEZE"

        # RANGING: ADX < 20, BBW < 25th pct (or < 50% of mean as fallback)
        is_ranging = bbw_pct < bbw_ranging_pct or bbw_ratio < 0.5
        if adx < adx_ranging and is_ranging:
            return "RANGING"

        # Ambiguous zone (ADX 20-25, moderate BBW): return None → keep previous
        return None

    def _update_direction(self, df: pd.DataFrame):
        """從 +DI/-DI 判斷趨勢方向"""
        plus_col = [c for c in df.columns if c.startswith('DMP')]
        minus_col = [c for c in df.columns if c.startswith('DMN')]
        if plus_col and minus_col:
            plus_di = df[plus_col[0]].iloc[-1]
            minus_di = df[minus_col[0]].iloc[-1]
            if not pd.isna(plus_di) and not pd.isna(minus_di):
                self._trend_direction = "LONG" if plus_di > minus_di else "SHORT"
                return
        # Fallback: EMA20/50
        close = df['close']
        if len(close) >= 50:
            ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
            ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
            self._trend_direction = "LONG" if ema20 > ema50 else "SHORT"
