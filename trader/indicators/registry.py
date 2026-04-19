"""Indicator registry shared by runtime and backtests."""

from __future__ import annotations

import pandas as pd

from trader.indicators.technical import _adx, _atr, _bbw, _ema, _sma


class IndicatorRegistry:
    DEFAULT_INDICATORS = {
        "ema",
        "sma",
        "atr",
        "adx",
        "bbw",
        "rsi",
        "macd",
        "bollinger",
        "supertrend",
    }

    @classmethod
    def supported_indicators(cls) -> set[str]:
        return set(cls.DEFAULT_INDICATORS)

    @classmethod
    def apply(cls, df: pd.DataFrame, required: set[str] | None = None) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        required = set(required or cls.DEFAULT_INDICATORS)
        out = df.copy()

        if "ema" in required:
            out["ema_20"] = _ema(out["close"], length=20)
            out["ema_50"] = _ema(out["close"], length=50)
            out["ema_200"] = _ema(out["close"], length=200)
        if "sma" in required:
            out["sma_20"] = _sma(out["close"], length=20)
            out["sma_50"] = _sma(out["close"], length=50)
            out["sma_200"] = _sma(out["close"], length=200)
        if "atr" in required:
            out["atr"] = _atr(out["high"], out["low"], out["close"], length=14)
        if "adx" in required:
            adx = _adx(out["high"], out["low"], out["close"], length=14)
            if isinstance(adx, pd.DataFrame):
                cols = [c for c in adx.columns if c.startswith("ADX")]
                if cols:
                    out["adx"] = adx[cols[0]]
            elif adx is not None:
                out["adx"] = adx
        if "bbw" in required:
            out["bbw"] = _bbw(out["close"], length=20, std_dev=2.0)
        if "rsi" in required:
            out["rsi_14"] = cls._rsi(out["close"], length=14)
        if "macd" in required:
            macd, signal, hist = cls._macd(out["close"])
            out["macd"] = macd
            out["macd_signal"] = signal
            out["macd_hist"] = hist
        if "bollinger" in required:
            middle = out["close"].rolling(window=20).mean()
            std = out["close"].rolling(window=20).std()
            out["bb_mid"] = middle
            out["bb_upper"] = middle + 2.0 * std
            out["bb_lower"] = middle - 2.0 * std
        if "supertrend" in required:
            st, direction = cls._supertrend(out)
            out["supertrend"] = st
            out["supertrend_direction"] = direction
        return out

    @staticmethod
    def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
        delta = close.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.ewm(alpha=1 / length, adjust=False).mean()
        avg_loss = losses.ewm(alpha=1 / length, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        fast = _ema(close, length=12)
        slow = _ema(close, length=26)
        macd = fast - slow
        signal = _ema(macd, length=9)
        return macd, signal, macd - signal

    @staticmethod
    def _supertrend(df: pd.DataFrame, length: int = 10, multiplier: float = 3.0):
        atr = _atr(df["high"], df["low"], df["close"], length=length)
        hl2 = (df["high"] + df["low"]) / 2.0
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        trend = pd.Series(index=df.index, dtype="float64")
        direction = pd.Series(index=df.index, dtype="int64")
        if df.empty:
            return trend, direction

        trend.iloc[0] = upper.iloc[0]
        direction.iloc[0] = 1
        for i in range(1, len(df)):
            prev_dir = direction.iloc[i - 1]
            close = df["close"].iloc[i]
            if close > upper.iloc[i - 1]:
                direction.iloc[i] = 1
            elif close < lower.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = prev_dir
                if prev_dir == 1 and lower.iloc[i] < lower.iloc[i - 1]:
                    lower.iloc[i] = lower.iloc[i - 1]
                if prev_dir == -1 and upper.iloc[i] > upper.iloc[i - 1]:
                    upper.iloc[i] = upper.iloc[i - 1]
            trend.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]
        return trend, direction
