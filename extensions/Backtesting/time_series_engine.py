"""Time-series replay engine with closed-bar access semantics."""

from typing import Dict, List, Optional

import pandas as pd


class TimeSeriesEngine:
    """
    Replay bars at the open of each 1H cursor.

    Cached OHLCV timestamps are exchange open-times, so exposing bars whose
    timestamp equals the replay cursor would leak the still-forming candle.
    get_bars() therefore returns only strictly older closed bars.
    """

    def __init__(self, data: Dict[str, Dict[str, pd.DataFrame]]):
        self._data = data
        self._current_time: Optional[pd.Timestamp] = None

    def set_time(self, timestamp: pd.Timestamp):
        self._current_time = timestamp

    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Return the latest closed bars whose timestamp is < current_time."""
        df = self._data.get(symbol, {}).get(timeframe, pd.DataFrame())
        if self._current_time is None:
            raise RuntimeError("set_time() must be called before get_bars()")
        if df.empty:
            return df
        end = df.index.searchsorted(self._current_time, side="left")
        if end <= 0:
            return df.iloc[0:0]
        start = max(0, end - limit)
        return df.iloc[start:end]

    def get_current_price(self, symbol: str) -> float:
        """Return the latest closed 1H close visible at the replay cursor."""
        bars = self.get_bars(symbol, "1h", limit=1)
        if bars.empty:
            return 0.0
        return float(bars.iloc[-1]["close"])

    def get_1h_timestamps(self, symbols: List[str]) -> List[pd.Timestamp]:
        """Return the shared 1H open-time cursor set across all requested symbols."""
        sets = []
        for sym in symbols:
            df = self._data.get(sym, {}).get("1h", pd.DataFrame())
            if not df.empty:
                sets.append(set(df.index))
        if not sets:
            return []
        common = sets[0].intersection(*sets[1:])
        return sorted(common)
