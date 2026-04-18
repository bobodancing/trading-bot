"""?璇? fixtures for TradingBot integration tests"""

import sys
import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trader.bot import TradingBot
from trader.positions import PositionManager
from trader.risk.manager import PrecisionHandler

def make_pm(**kwargs) -> PositionManager:
    """?梁?????????? PositionManager???恍銵???"""
    defaults = dict(
        symbol='BTC/USDT',
        side='LONG',
        entry_price=50000.0,
        stop_loss=48000.0,
        position_size=0.01,
    )
    defaults.update(kwargs)
    pm = PositionManager(**defaults)
    pm.entry_time = datetime.now(timezone.utc)
    pm.highest_price = 51000.0
    pm.lowest_price = 49000.0
    pm.initial_r = 20.0      # ??怨翰 / 0
    pm.market_regime = 'TRENDING'
    return pm


@pytest.fixture
def mock_bot(tmp_path):
    """
    TradingBot instance????????I/O ??mock??
      - _init_exchange ??MagicMock?????ccxt ?祈璆?????
      - PrecisionHandler._load_exchange_info ??no-op?????Binance exchangeInfo HTTP??
      - _restore_positions ??no-op????撩??鈭???positions.json??
    PositionPersistence ??PerformanceDB ?輯撒? tmp_path???急??????甇?
    """
    mock_exchange = MagicMock()
    mock_exchange.load_markets.return_value = {}
    mock_exchange.markets = {}

    with patch.object(TradingBot, '_init_exchange', return_value=mock_exchange), \
         patch.object(PrecisionHandler, '_load_exchange_info'), \
         patch.object(TradingBot, '_restore_positions'), \
         patch('trader.bot.Config.POSITIONS_JSON_PATH', str(tmp_path / 'positions.json')), \
         patch('trader.bot.Config.DB_PATH', str(tmp_path / 'perf.db')):
        bot = TradingBot()

    # ??? perf_db ???????SQLite ?????
    bot.perf_db.record_trade = MagicMock()

    yield bot


# ????????????????????????????????????????????????????????????????????????????????????????????
# StatefulMockEngine ??Integration Test ??
# ????????????????????????????????????????????????????????????????????????????????????????????

class StatefulMockEngine:
    """
    ?????? mock execution engine???剝甇?
    - balance?????? notional????????notional 蝪?PnL??
    - positions??symbol: {side, size, entry_price}}??
    - open_stop_orders??order_id: {symbol, side, size, stop_price}}??

    ?????OrderExecutionEngine ?????????瘞??
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.positions: dict = {}       # {symbol: {side, size, entry_price}}
        self.open_stops: dict = {}      # {order_id: {symbol, side, size, stop_price}}
        self.order_counter = 0
        self.trade_log: list = []       # ??????????
        self._fault: 'FaultInjector | None' = None

    def attach_fault_injector(self, fi: 'FaultInjector'):
        self._fault = fi

    def _next_order_id(self) -> str:
        self.order_counter += 1
        return f"mock_order_{self.order_counter}"

    def _check_fault(self, method_name: str):
        """????API call ????????fault injector"""
        if self._fault:
            self._fault.check(method_name)

    def set_leverage(self, symbol: str) -> bool:
        self._check_fault('set_leverage')
        return True

    def create_order(self, symbol: str, side: str, quantity: float) -> dict:
        """??????ide='BUY'??ONG, 'SELL'??HORT"""
        self._check_fault('create_order')

        order_id = self._next_order_id()
        self.trade_log.append({
            'action': 'create_order', 'symbol': symbol,
            'side': side, 'quantity': quantity, 'order_id': order_id,
        })
        return {
            'orderId': order_id,
            'avgPrice': '0',  # bot ??_extract_fill_price??allback ??祉????
            'status': 'FILLED',
            'executedQty': str(quantity),
        }

    def close_position(self, symbol: str, side: str, quantity: float) -> dict:
        """???"""
        self._check_fault('close_position')
        order_id = self._next_order_id()
        self.trade_log.append({
            'action': 'close_position', 'symbol': symbol,
            'side': side, 'quantity': quantity, 'order_id': order_id,
        })
        return {
            'orderId': order_id,
            'avgPrice': '0',
            'status': 'FILLED',
            'executedQty': str(quantity),
        }

    def place_hard_stop_loss(self, symbol: str, side: str, size: float,
                              stop_price: float) -> str:
        """?桀??剛?蟡翰??"""
        self._check_fault('place_hard_stop_loss')
        order_id = self._next_order_id()
        self.open_stops[order_id] = {
            'symbol': symbol, 'side': side,
            'size': size, 'stop_price': stop_price,
        }
        self.trade_log.append({
            'action': 'place_stop', 'symbol': symbol,
            'order_id': order_id, 'stop_price': stop_price,
        })
        return order_id

    def cancel_stop_loss_order(self, symbol: str, order_id: str | None) -> bool:
        """????撓?"""
        self._check_fault('cancel_stop_loss_order')
        if order_id and order_id in self.open_stops:
            del self.open_stops[order_id]
        self.trade_log.append({
            'action': 'cancel_stop', 'symbol': symbol, 'order_id': order_id,
        })
        return True

    def update_hard_stop_loss(self, pm, new_stop: float):
        """?皝? trailing stop??ositionManager ?瞉???"""
        self.cancel_stop_loss_order(pm.symbol, pm.stop_order_id)
        pm.stop_order_id = self.place_hard_stop_loss(
            pm.symbol, pm.side, pm.total_size, new_stop
        )


class FaultInjector:
    """
    ???????????????? method call ??摮??Exception??

    ?????
        fi = FaultInjector()
        fi.set_fault('close_position', Exception("API 5xx"), times=1)
        engine.attach_fault_injector(fi)
        # ?????close_position ??? Exception???????箸?餈斗?
    """

    def __init__(self):
        self._faults: dict = {}  # {method_name: {'error': Exception, 'remaining': int}}

    def set_fault(self, method_name: str, error: Exception, times: int = 1):
        """?桀????method ?????? N ???????? error"""
        self._faults[method_name] = {'error': error, 'remaining': times}

    def clear(self):
        """??????????頨急?"""
        self._faults.clear()

    def check(self, method_name: str):
        """??瘣?API call ???????????? raise"""
        fault = self._faults.get(method_name)
        if fault and fault['remaining'] > 0:
            fault['remaining'] -= 1
            if fault['remaining'] <= 0:
                del self._faults[method_name]
            raise fault['error']


@pytest.fixture
def integration_bot(tmp_path):
    """
    Integration test ??? TradingBot??
    - StatefulMockEngine???????? execution engine??
    - FaultInjector??????????
    - DRY_RUN = False??蝎交?? _execute_trade / _handle_close ????
    - perf_db ?輯撒? tmp_path???急??????甇?

    ??? (bot, engine, fault_injector) tuple??
    """
    from trader.config import Config

    engine = StatefulMockEngine(initial_balance=10000.0)
    fi = FaultInjector()
    engine.attach_fault_injector(fi)

    mock_exchange = MagicMock()
    mock_exchange.load_markets.return_value = {}
    mock_exchange.markets = {}

    pos_path = str(tmp_path / 'positions.json')
    db_path = str(tmp_path / 'perf.db')

    with patch.object(TradingBot, '_init_exchange', return_value=mock_exchange), \
         patch.object(PrecisionHandler, '_load_exchange_info'), \
         patch.object(TradingBot, '_restore_positions'), \
         patch('trader.bot.Config.POSITIONS_JSON_PATH', pos_path), \
         patch('trader.bot.Config.DB_PATH', db_path):
        bot = TradingBot()

    # ?? StatefulMockEngine
    bot.execution_engine = engine

    # fetch_ticker ????? test ?桀?? side_effect
    bot.exchange.fetch_ticker = MagicMock(return_value={
        'last': 50000.0, 'bid': 49999.0, 'ask': 50001.0,
    })

    # data_provider.fetch_ohlcv ??MagicMock?????test ????桀?????瞏?
    bot.data_provider = MagicMock()
    bot.data_provider.fetch_ohlcv = MagicMock(return_value=pd.DataFrame())

    # risk_manager.get_balance ???蝞??瞏??擗? Binance API??
    bot.risk_manager.get_balance = MagicMock(return_value=10000.0)

    # risk_manager.get_positions ????頨??敺?list??ync ???
    bot.risk_manager.get_positions = MagicMock(return_value=[])

    # precision_handler ???皝???????瞏??????瞍脤頦???
    bot.precision_handler.round_amount_up = MagicMock(side_effect=lambda sym, amt, price: amt)
    bot.precision_handler.round_amount = MagicMock(side_effect=lambda sym, amt: amt)
    bot.precision_handler.check_limits = MagicMock(return_value=True)

    # persistence ???輯撒???蟡?PositionPersistence??蟡?tmp_path??
    # ??mock???⊿?_save_positions / _restore_positions ????正璆?

    # ?????? Config ??
    _orig = {
        'DRY_RUN': Config.DRY_RUN,
        'USE_SCANNER_SYMBOLS': Config.USE_SCANNER_SYMBOLS,
        'SYMBOLS': Config.SYMBOLS,
        'TELEGRAM_ENABLED': Config.TELEGRAM_ENABLED,
    }

    # Config ?桀??
    Config.DRY_RUN = False
    Config.USE_SCANNER_SYMBOLS = False
    Config.SYMBOLS = ['BTC/USDT']
    Config.TELEGRAM_ENABLED = False

    yield bot, engine, fi

    # teardown????????Config ???????
    for k, v in _orig.items():
        setattr(Config, k, v)
