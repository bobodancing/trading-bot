"""時間推進引擎 — 防 look-ahead bias"""
import pandas as pd
from typing import Dict, List, Optional


class TimeSeriesEngine:
    """
    控制回測時間視窗。get_bars() 只回傳 <= current_time 的資料。
    data: {symbol: {timeframe: pd.DataFrame}}  (index = pd.DatetimeIndex UTC-aware)
    """

    def __init__(self, data: Dict[str, Dict[str, pd.DataFrame]]):
        self._data = data
        self._current_time: Optional[pd.Timestamp] = None

    def set_time(self, timestamp: pd.Timestamp):
        self._current_time = timestamp

    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """回傳 <= current_time 的最後 limit 根 K 線（timestamp 為 index）"""
        df = self._data.get(symbol, {}).get(timeframe, pd.DataFrame())
        if self._current_time is None:
            raise RuntimeError("set_time() must be called before get_bars()")
        if df.empty:
            return df
        end = df.index.searchsorted(self._current_time, side="right")
        if end <= 0:
            return df.iloc[0:0]
        start = max(0, end - limit)
        return df.iloc[start:end]

    def get_current_price(self, symbol: str) -> float:
        """當前 bar close price"""
        bars = self.get_bars(symbol, "1h", limit=1)
        if bars.empty:
            return 0.0
        return float(bars.iloc[-1]["close"])

    def get_1h_timestamps(self, symbols: List[str]) -> List[pd.Timestamp]:
        """
        回傳所有 symbol 共同的 1H timestamps（取交集，已排序）。
        注意：回傳全量時間戳，不受 current_time 限制。
        BacktestEngine 用此方法取得外層迴圈的完整時間序列。
        """
        sets = []
        for sym in symbols:
            df = self._data.get(sym, {}).get("1h", pd.DataFrame())
            if not df.empty:
                sets.append(set(df.index))
        if not sets:
            return []
        common = sets[0].intersection(*sets[1:])
        return sorted(common)
