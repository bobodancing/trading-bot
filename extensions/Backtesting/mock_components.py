"""MockDataProvider + MockOrderEngine — 替換 bot 的真實 I/O 元件"""
import uuid
import pandas as pd
from typing import Dict, List, Optional
from time_series_engine import TimeSeriesEngine


class MockDataProvider:
    """
    替換 MarketDataProvider。fetch_ohlcv 從 TimeSeriesEngine 取數據。
    回傳格式必須與 MarketDataProvider 一致：timestamp 為 column，UTC-naive。
    """

    def __init__(self, tse: TimeSeriesEngine):
        self.tse = tse

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        df = self.tse.get_bars(symbol, timeframe, limit)
        if df.empty:
            return pd.DataFrame()
        df = df.copy()
        df.index.name = "timestamp"  # 確保 reset_index 後 column 名為 timestamp
        df = df.reset_index()  # timestamp index → column
        # 轉 UTC-naive（與 data_provider 格式一致）
        if "timestamp" in df.columns:
            col = df["timestamp"]
            if hasattr(col.dtype, "tz") and col.dt.tz is not None:
                df["timestamp"] = col.dt.tz_convert(None)
        return df


class MockOrderEngine:
    """
    替換 OrderExecutionEngine。不打 API，記錄 fee 和 stop orders。
    stop trigger 交由 check_stop_triggers() 檢查，BacktestEngine 負責呼叫。
    """

    def __init__(self, tse: TimeSeriesEngine, fee_rate: float = 0.0004,
                 initial_balance: float = 10000.0):
        self.tse = tse
        self.fee_rate = fee_rate
        self.initial_balance = initial_balance
        self.total_fees: float = 0.0
        # {order_id: {symbol, side, size, stop_price}}
        self.open_orders: Dict[str, dict] = {}

    def _current_price(self, symbol: str) -> float:
        return self.tse.get_current_price(symbol)

    def _charge_fee(self, symbol: str, qty: float):
        price = self._current_price(symbol)
        fee = price * qty * self.fee_rate
        self.total_fees += fee

    def create_order(self, symbol: str, side: str, quantity: float) -> dict:
        price = self._current_price(symbol)
        self._charge_fee(symbol, quantity)
        return {
            "orderId": str(uuid.uuid4()),
            "avgPrice": price,
            "status": "FILLED",
            "executedQty": str(quantity),
        }

    def close_position(self, symbol: str, side: str, quantity: float) -> dict:
        price = self._current_price(symbol)
        self._charge_fee(symbol, quantity)
        return {
            "orderId": str(uuid.uuid4()),
            "avgPrice": price,
            "status": "FILLED",
            "executedQty": str(quantity),
        }

    def place_hard_stop_loss(self, symbol: str, side: str, size: float,
                              stop_price: float) -> Optional[str]:
        order_id = str(uuid.uuid4())
        self.open_orders[order_id] = {
            "symbol": symbol, "side": side,
            "size": size, "stop_price": stop_price,
        }
        return order_id

    def cancel_stop_loss_order(self, symbol: str, order_id: Optional[str]) -> bool:
        if order_id:
            self.open_orders.pop(order_id, None)
        return True

    def update_hard_stop_loss(self, pm, new_stop: float):
        """PositionManager 呼叫此方法更新 trailing stop"""
        self.cancel_stop_loss_order(pm.symbol, pm.stop_order_id)
        pm.stop_order_id = self.place_hard_stop_loss(
            pm.symbol, pm.side, pm.total_size, new_stop
        )

    def set_leverage(self, symbol: str) -> bool:
        return True

    def check_stop_triggers(self) -> List[str]:
        """
        檢查當前 bar 是否觸及 stop price。
        LONG: bar.low <= stop_price → triggered
        SHORT: bar.high >= stop_price → triggered
        觸發後自動移除 open_orders 中的該單。
        回傳觸發的 symbol list（去重）。
        """
        triggered_symbols = []
        triggered_ids = []

        for order_id, order in self.open_orders.items():
            symbol = order["symbol"]
            # 假設 BacktestEngine 以 1H bar 為主推進迴圈。
            # 若改用其他時間框架驅動，需同步更新此處。
            bars = self.tse.get_bars(symbol, "1h", limit=1)
            if bars.empty:
                continue
            bar = bars.iloc[-1]
            stop = order["stop_price"]
            if order["side"] == "LONG" and bar["low"] <= stop:
                triggered_symbols.append(symbol)
                triggered_ids.append(order_id)
            elif order["side"] == "SHORT" and bar["high"] >= stop:
                triggered_symbols.append(symbol)
                triggered_ids.append(order_id)

        for oid in triggered_ids:
            self.open_orders.pop(oid, None)

        return list(set(triggered_symbols))

    def deduct_funding(self, symbol: str, side: str, size: float,
                       entry_price: float, funding_rate: float):
        """
        結算 funding fee。
        LONG + positive rate → 付錢（fee 增加）
        SHORT + positive rate → 收錢（fee 減少）
        """
        if side == "LONG":
            fee = size * entry_price * funding_rate
        else:
            fee = size * entry_price * (-funding_rate)
        self.total_fees += fee
