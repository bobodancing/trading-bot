"""
V6.0 ?????????????????

??? V5.3 TradingBotV53 ?????
- [DEPRECATED] V6.0 ????????????????????
- positions.json ?????
"""

import sys
import os
import time
import json
import signal
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# ????????????? import v6 package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ccxt
import pandas as pd

# ?????????????
from trader.infrastructure.api_client import BinanceFuturesClient
from trader.infrastructure.notifier import TelegramNotifier
from trader.infrastructure.telegram_handler import TelegramCommandHandler
from trader.infrastructure.data_provider import MarketDataProvider
from trader.infrastructure.performance_db import PerformanceDB
# ?????????
from trader.indicators.technical import TechnicalAnalysis
# ??????????
from trader.risk.manager import PrecisionHandler, RiskManager
from trader.arbiter import RegimeArbiter
from trader.routing import RegimeRouter
from trader.regime import RegimeEngine
from trader.strategies.v8_grid import V8AtrGrid, PoolManager
# ????????
from trader.execution.order_engine import OrderExecutionEngine
from trader.config import Config
from trader.positions import PositionManager
from trader.persistence import PositionPersistence
from trader.strategies import ExecutableOrderPlan
from trader.strategy_runtime import StrategyRuntime
from trader.grid_manager import GridManager
from trader.btc_context import BTCContextManager, get_last_candle_time, get_last_closed_candle_time, format_candle_time
from trader.position_monitor import PositionMonitor
from trader.signal_scanner import SignalScanner
from trader.utils import trade_log, calculate_pnl, get_close_side, build_log_base

logger = logging.getLogger(__name__)


# Backward-compat alias
_trade_log = trade_log


class TradingBot:
    """Primary trading bot runtime."""

    def __init__(self):
        Config.validate()
        self.exchange = self._init_exchange()
        self.data_provider = MarketDataProvider(
            self.exchange,
            max_retry=Config.MAX_RETRY,
            retry_delay=Config.RETRY_DELAY,
            sandbox_mode=Config.SANDBOX_MODE,
            trading_mode=Config.TRADING_MODE,
        )
        self.precision_handler = PrecisionHandler(self.exchange)
        self.futures_client = BinanceFuturesClient(Config.API_KEY, Config.API_SECRET, Config.SANDBOX_MODE)
        self.risk_manager = RiskManager(self.exchange, self.precision_handler)
        # RiskManager ?????V5.3 Config ???? futures_client ?????? key??????
        self.risk_manager.futures_client = self.futures_client
        # ???????????hase 3: ????????????
        self.execution_engine = OrderExecutionEngine(
            self.exchange, self.futures_client, self.precision_handler
        )

        # V6.0: PositionManager ????TradeManager
        self.active_trades: Dict[str, PositionManager] = {}
        self._scanner_symbol_meta: Dict[str, Dict[str, object]] = {}

        # ?????????
        self.recently_exited: Dict[str, datetime] = {}
        self.order_failed_symbols: Dict[str, datetime] = {}
        self.early_exit_cooldown: Dict[str, datetime] = {}  # ???????????????12h ???

        # ???????????????net_pnl_pct ?????
        self.initial_balance: float = 0.0

        # V6.0: ?????????????? Config??????????????
        pos_path = os.path.expanduser(Config.POSITIONS_JSON_PATH)
        if not os.path.isabs(pos_path):
            pos_path = str(Path(__file__).parent.parent / pos_path)
        Path(pos_path).parent.mkdir(parents=True, exist_ok=True)
        self.persistence = PositionPersistence(pos_path)

        # ????????positions
        self._restore_positions()

        # Phase 0: ???? DB
        db_path = getattr(Config, 'DB_PATH', 'performance.db')
        self.perf_db = PerformanceDB(db_path=db_path)

        self._log_startup()

        # Telegram ???????
        self.telegram_handler = TelegramCommandHandler(self)

        # Grid / Regime system
        self.regime_engine = RegimeEngine()
        self.regime_arbiter = RegimeArbiter()
        self.regime_router = RegimeRouter()
        self.pool_manager = PoolManager()
        self.grid_engine = V8AtrGrid(
            api_client=self.futures_client,
            notifier=None,
        )
        self.grid_trades: dict = {}
        self._start_time = datetime.now(timezone.utc)
        self._btc_regime_context: Dict[str, object] = {}
        self._btc_trend_context: Dict[str, object] = {}
        self._regime_arbiter_snapshot = None
        self.grid_manager = GridManager(self)
        self.btc_context_manager = BTCContextManager(self)
        self.position_monitor = PositionMonitor(self)
        self.signal_scanner = SignalScanner(self)
        self.strategy_runtime = StrategyRuntime(self)

    def _init_exchange(self):
        """Initialize exchange client."""
        try:
            exchange_class = getattr(ccxt, Config.EXCHANGE)
            exchange_config = {
                'apiKey': Config.API_KEY,
                'secret': Config.API_SECRET,
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {'defaultType': Config.TRADING_MODE}
            }
            exchange = exchange_class(exchange_config)

            if Config.SANDBOX_MODE:
                if Config.TRADING_MODE == 'future':
                    exchange.set_sandbox_mode(True)
                    # ccxt sandbox ?????testnet?????? Demo Trading ????
                    if 'api' in exchange.urls:
                        for key in exchange.urls['api']:
                            url_val = str(exchange.urls['api'].get(key, ''))
                            if 'fapi' in url_val.lower() or 'testnet' in url_val.lower():
                                exchange.urls['api'][key] = url_val.replace(
                                    'testnet.binancefuture.com', 'demo-fapi.binance.com'
                                ).replace(
                                    'fapi.binance.com', 'demo-fapi.binance.com'
                                )
                    exchange.options['sandboxMode'] = True
                    exchange.options['defaultType'] = 'future'
                    logger.info("?????? Binance Demo Trading")
                else:
                    try:
                        exchange.set_sandbox_mode(True)
                    except Exception as e:
                        logger.warning(f"??????????????: {e}")

            try:
                exchange.load_markets()
                logger.info(f"??????{len(exchange.markets)} ??????")
            except Exception as e:
                logger.warning(f"?????????????: {e}")

            if Config.TRADING_MODE == 'future':
                for symbol in Config.SYMBOLS:
                    try:
                        exchange.set_leverage(Config.LEVERAGE, symbol)
                    except Exception:
                        pass

            return exchange

        except Exception as e:
            logger.error(f"?????????????? {e}")
            raise

    def _log_startup(self):
        """Log reset-runtime startup context."""
        logger.info("=" * 60)
        logger.info("TradingBot started")
        logger.info("=" * 60)
        logger.info(f"Mode: {Config.TRADING_MODE} ({Config.TRADING_DIRECTION})")
        logger.info(f"Leverage: {Config.LEVERAGE}x")
        logger.info(f"Risk per trade: {Config.RISK_PER_TRADE*100:.1f}%")
        logger.info(f"Strategy runtime: {'enabled' if Config.STRATEGY_RUNTIME_ENABLED else 'disabled'}")
        logger.info(f"Enabled strategies: {', '.join(Config.ENABLED_STRATEGIES) or 'none'}")
        logger.info(f"Dry run: {'enabled' if Config.DRY_RUN else 'disabled'}")
        logger.info(f"Active positions: {len(self.active_trades)}")
        logger.info(f"Symbols: {', '.join(Config.SYMBOLS)}")
        logger.info("=" * 60)

    def _restore_positions(self):
        """??positions.json ????? positions"""
        data = self.persistence.load_positions()
        if not data:
            return

        for symbol, pos_data in data.items():
            try:
                pm = PositionManager.from_dict(pos_data)
                self.active_trades[symbol] = pm
                value_usdt = pm.total_size * pm.avg_entry
                logger.info(
                    f"Restored {symbol}: {pm.side} stage={pm.stage} "
                    f"value=${value_usdt:.2f} sl=${pm.current_sl:.2f}"
                )
            except Exception as e:
                logger.error(f"????? {symbol} ????: {e}")

    def _save_positions(self):
        """???????positions ??JSON"""
        data = {}
        for symbol, pm in self.active_trades.items():
            data[symbol] = pm.to_dict()
        self.persistence.save_positions(data)

    # ==================== ?????? ====================

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data."""
        return self.data_provider.fetch_ohlcv(symbol, timeframe, limit)

    def fetch_ticker(self, symbol: str) -> dict:
        """Fetch ticker data."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception:
            if Config.TRADING_MODE == 'future' and Config.SANDBOX_MODE:
                import requests as req
                symbol_id = symbol.replace('/', '')
                base_url = 'https://demo-fapi.binance.com'
                resp = req.get(
                    f'{base_url}/fapi/v1/ticker/price',
                    params={'symbol': symbol_id},
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    price = float(data['price'])
                    return {'symbol': symbol, 'last': price, 'bid': price, 'ask': price}
            raise

    @staticmethod
    def _normalize_scanner_symbol(symbol: str) -> str:
        """Normalize futures symbols such as BTC/USDT:USDT to BTC/USDT."""
        return symbol.split(':')[0] if ':' in symbol else symbol

    def _supported_scanner_symbols(self) -> Optional[set]:
        markets = getattr(self.exchange, 'markets', None)
        if not markets:
            return None

        supported = set()
        if isinstance(markets, dict):
            market_iter = markets.items()
        else:
            market_iter = []

        for key, market in market_iter:
            if isinstance(key, str):
                supported.add(self._normalize_scanner_symbol(key))
            if isinstance(market, dict):
                market_symbol = market.get('symbol')
                if isinstance(market_symbol, str):
                    supported.add(self._normalize_scanner_symbol(market_symbol))

        return supported or None

    def _scanner_items_to_symbols(
        self,
        items: List,
        default_source: str,
        supported_symbols: Optional[set],
    ) -> Tuple[List[str], Dict[str, Dict[str, object]], int]:
        symbols: List[str] = []
        metadata: Dict[str, Dict[str, object]] = {}
        unsupported_count = 0

        for raw_item in items or []:
            if isinstance(raw_item, str):
                item = {'symbol': raw_item}
            elif isinstance(raw_item, dict):
                item = raw_item
            else:
                continue

            raw_symbol = item.get('symbol')
            if not raw_symbol:
                continue

            symbol = self._normalize_scanner_symbol(str(raw_symbol))
            if supported_symbols is not None and symbol not in supported_symbols:
                unsupported_count += 1
                continue
            if symbol in metadata:
                continue

            symbols.append(symbol)
            metadata[symbol] = {
                'scanner_source': item.get('source', default_source),
                'scanner_rank': item.get('rank'),
                'scanner_volume_24h': item.get('volume_24h'),
            }

        return symbols, metadata, unsupported_count

    def load_scanner_results(self) -> List[str]:
        """??Scanner ??????????????V5.3??"""
        self._scanner_symbol_meta = {}
        try:
            scanner_path = os.path.expanduser(Config.SCANNER_JSON_PATH)
            # ??????? ?????????????
            if not os.path.isabs(scanner_path):
                scanner_path = str(Path(__file__).parent.parent / scanner_path)
            if not os.path.exists(scanner_path):
                logger.warning(f"Scanner JSON ????? {scanner_path}????????symbols")
                return Config.SYMBOLS

            with open(scanner_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            scan_time_str = data.get('scan_time', '')
            if scan_time_str:
                try:
                    scan_time = datetime.fromisoformat(scan_time_str.replace('Z', '+00:00'))
                    age_minutes = (datetime.now(timezone.utc) - scan_time).total_seconds() / 60
                    if age_minutes > Config.SCANNER_MAX_AGE_MINUTES:
                        logger.warning(f"Scanner ?????????({age_minutes:.0f} ??? > {Config.SCANNER_MAX_AGE_MINUTES} ??????)????????symbols")
                        return Config.SYMBOLS
                except Exception:
                    pass

            supported_symbols = self._supported_scanner_symbols()
            sources = (
                ('bot_symbols', 'l1_history'),
                ('hot_symbols', 'hot_2b'),
            )
            for field_name, default_source in sources:
                raw_items = data.get(field_name, [])
                if not raw_items:
                    continue

                scanner_symbols, metadata, unsupported_count = self._scanner_items_to_symbols(
                    raw_items,
                    default_source,
                    supported_symbols,
                )
                if scanner_symbols:
                    self._scanner_symbol_meta = metadata
                    logger.info(
                        "Scanner loaded %s symbol(s) from %s "
                        "(unsupported_filtered=%s): %s",
                        len(scanner_symbols),
                        field_name,
                        unsupported_count,
                        ', '.join(scanner_symbols),
                    )
                    return scanner_symbols

                if unsupported_count:
                    logger.warning(
                        "Scanner %s had %s symbol(s), all unsupported by exchange markets",
                        field_name,
                        len(raw_items),
                    )

            self._scanner_symbol_meta = {}
            logger.warning("Scanner JSON had no usable bot_symbols/hot_symbols, using default symbols")
            return Config.SYMBOLS
        except Exception as e:
            logger.warning(f"Scanner JSON ???????: {e}????????symbols")
            return Config.SYMBOLS

    # ==================== ???????????OrderExecutionEngine??===================

    def _futures_set_leverage(self, symbol: str) -> bool:
        """?????????????"""
        return self.execution_engine.set_leverage(symbol)

    def _futures_create_order(self, symbol: str, side: str, quantity: float) -> dict:
        """??????"""
        return self.execution_engine.create_order(symbol, side, quantity)

    @staticmethod
    def _extract_fill_price(order_result: dict, fallback_price: float) -> float:
        """
        ??????????????????????vgPrice / average????
        ?????????0 ?????fallback???????????????????????????

        BinanceFuturesClient ??????esult['avgPrice']???????
        CCXT ??????esult['average']??loat??
        """
        try:
            avg = order_result.get('avgPrice') or order_result.get('average')
            if avg:
                price = float(avg)
                if price > 0:
                    return price
        except Exception:
            pass
        return fallback_price

    def _futures_close_position(self, symbol: str, side: str, quantity: float) -> dict:
        """?????"""
        return self.execution_engine.close_position(symbol, side, quantity)

    def _place_hard_stop_loss(self, symbol: str, side: str, size: float, stop_price: float) -> Optional[str]:
        """?????????????????????order ID"""
        return self.execution_engine.place_hard_stop_loss(symbol, side, size, stop_price)

    def _cancel_stop_loss_order(self, symbol: str, order_id: Optional[str]) -> bool:
        """?????????"""
        return self.execution_engine.cancel_stop_loss_order(symbol, order_id)

    def _update_hard_stop_loss(self, pm: PositionManager, new_stop: float):
        """??????????"""
        return self._refresh_stop_loss(pm, new_stop)

    # ==================== ??????? ====================

    def scan_for_signals(self):
        self.signal_scanner.scan_for_signals()

    # ==================== Private Helpers ====================

    # -- Grid management (delegated to GridManager) --

    def _scan_grid_signals(self):
        self.grid_manager.scan_grid_signals()

    def _monitor_grid_state(self):
        self.grid_manager.monitor_grid_state()

    def _execute_grid_action(self, action, current_price: float):
        self.grid_manager.execute_grid_action(action, current_price)

    def _record_grid_trade(self, action, entry_price: float, exit_price: float, pnl: float):
        self.grid_manager.record_grid_trade(action, entry_price, exit_price, pnl)

    def _check_btc_trend(self) -> Optional[str]:
        return self.btc_context_manager.check_btc_trend()

    @staticmethod
    def _get_last_candle_time(df: pd.DataFrame) -> Optional[pd.Timestamp]:
        return get_last_candle_time(df)

    @staticmethod
    def _get_last_closed_candle_time(df: pd.DataFrame) -> Optional[pd.Timestamp]:
        return get_last_closed_candle_time(df)

    def _get_regime_market_ts(self) -> Optional[pd.Timestamp]:
        candle_time = (self._btc_regime_context or {}).get('candle_time')
        if isinstance(candle_time, str) and candle_time and candle_time != "n/a":
            return pd.Timestamp(candle_time)
        if self.regime_engine.last_candle_time is not None:
            return pd.Timestamp(self.regime_engine.last_candle_time)
        return None

    @staticmethod
    def _symbol_to_exchange_id(symbol: str) -> str:
        return symbol.replace('/', '').split(':')[0]

    @staticmethod
    def _exchange_id_to_symbol(symbol_id: str) -> str:
        if symbol_id.endswith('USDT'):
            return f"{symbol_id[:-4]}/USDT"
        return symbol_id

    @staticmethod
    def _extract_position_size(position: dict) -> float:
        raw_value = position.get('positionAmt', position.get('contracts', 0))
        try:
            return abs(float(raw_value or 0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_position_side(position: dict) -> Optional[str]:
        raw_side = (
            position.get('positionSide')
            or position.get('info', {}).get('positionSide')
            or position.get('side')
            or position.get('info', {}).get('side')
        )
        if isinstance(raw_side, str):
            normalized = raw_side.upper()
            if normalized in ('LONG', 'SHORT'):
                return normalized

        raw_amt = position.get('positionAmt', position.get('contracts', 0))
        try:
            amount = float(raw_amt or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount > 0:
            return 'LONG'
        if amount < 0:
            return 'SHORT'
        return None

    def _build_exchange_position_map(self, exchange_positions: Optional[list]) -> Dict[Tuple[str, str], float]:
        exchange_map: Dict[Tuple[str, str], float] = {}
        for position in exchange_positions or []:
            symbol_id = position.get('symbol', '') or position.get('info', {}).get('symbol', '')
            side = self._normalize_position_side(position)
            size = self._extract_position_size(position)
            if not symbol_id or side is None or size <= 0:
                continue
            key = (symbol_id, side)
            exchange_map[key] = exchange_map.get(key, 0.0) + size
        return exchange_map

    def _build_internal_position_map(self) -> Dict[Tuple[str, str], float]:
        internal_map: Dict[Tuple[str, str], float] = {}

        for symbol, pm in self.active_trades.items():
            if pm.is_closed:
                continue
            key = (self._symbol_to_exchange_id(symbol), pm.side)
            internal_map[key] = internal_map.get(key, 0.0) + pm.total_size

        if self.grid_engine.state:
            for position in self.grid_engine.state.active_positions:
                key = ('BTCUSDT', position['side'])
                internal_map[key] = internal_map.get(key, 0.0) + float(position['size'])

        return internal_map

    def _is_grid_exchange_flat(self) -> bool:
        return self.grid_manager.is_exchange_flat()

    def _finalize_grid_shutdown_if_flat(self):
        self.grid_manager.finalize_grid_shutdown_if_flat()

    def _restore_grid_runtime_state(self):
        self.grid_manager.restore_runtime_state()

    @staticmethod
    def _format_candle_time(candle_time: Optional[pd.Timestamp]) -> str:
        return format_candle_time(candle_time)

    def _make_btc_context(self, **kwargs) -> Dict[str, object]:
        return self.btc_context_manager.make_btc_context(**kwargs)

    def _update_btc_regime_context(self) -> Dict[str, object]:
        return self.btc_context_manager.update_btc_regime_context()

    def _get_daily_btc_trend_context(self) -> Dict[str, object]:
        return self.btc_context_manager.get_daily_btc_trend_context()

    def _resolve_btc_trend_context(self, log_event: bool = False) -> Dict[str, object]:
        return self.btc_context_manager.resolve_btc_trend_context(log_event=log_event)

    def _refresh_stop_loss(self, pm: PositionManager, new_sl: float):
        """Cancel existing SL order, place new one, update pm.stop_order_id."""
        if not Config.USE_HARD_STOP_LOSS:
            return True

        old_order_id = pm.stop_order_id
        if old_order_id:
            try:
                canceled = self._cancel_stop_loss_order(pm.symbol, old_order_id)
            except Exception as e:
                logger.warning(f"{pm.symbol} cancel old stop failed before refresh: {e}")
                return False
            if not canceled:
                logger.warning(
                    f"{pm.symbol} cancel old stop returned false; keep existing stop {old_order_id}"
                )
                return False
            pm.stop_order_id = None

        new_order_id = self._place_hard_stop_loss(pm.symbol, pm.side, pm.total_size, new_sl)
        if new_order_id is None:
            logger.warning(
                f"{pm.symbol} place refreshed stop failed after cancel; position temporarily unprotected"
            )
            return False

        pm.stop_order_id = new_order_id
        return True

    def _calc_total_open_risk_amount(self) -> float:
        total_risk = 0.0
        for p in self.active_trades.values():
            if p.is_closed or getattr(p, 'closed_on_exchange', False):
                continue
            if p.side == 'LONG':
                risk_per_unit = p.avg_entry - p.current_sl
            else:
                risk_per_unit = p.current_sl - p.avg_entry
            if risk_per_unit <= 0:
                continue
            total_risk += p.total_size * risk_per_unit
        return total_risk

    def _calc_total_risk_pct(self, balance: float) -> float:
        """???????????????????????????"""
        if balance <= 0:
            return 0.0
        return self._calc_total_open_risk_amount() / balance

    @staticmethod
    def _get_close_side(side: str) -> str:
        return get_close_side(side)

    def _validate_position_size(self, symbol: str, raw_size: float, entry_price: float,
                                 label: str = "") -> Optional[float]:
        """Round amount and check limits. Returns size or None if below minimum."""
        size = self.precision_handler.round_amount_up(symbol, raw_size, entry_price)
        if not self.precision_handler.check_limits(symbol, size, entry_price):
            logger.warning(f"{symbol}{(' ' + label) if label else ''} invalid position size")
            return None
        return size

    @staticmethod
    def _calculate_pnl(side: str, size: float, price: float, avg_entry: float) -> float:
        return calculate_pnl(side, size, price, avg_entry)

    @staticmethod
    def _build_log_base(event: str, trade_id: str, symbol: str, side: str) -> dict:
        return build_log_base(event, trade_id, symbol, side)

    def _check_total_risk(self, active_positions: List[PositionManager]) -> bool:
        """????????????????? PositionManager??"""
        if not active_positions:
            return True

        total_risk = 0.0
        for pm in active_positions:
            if pm.is_closed:
                continue
            if pm.side == 'LONG':
                risk_per_unit = pm.avg_entry - pm.current_sl
            else:
                risk_per_unit = pm.current_sl - pm.avg_entry
            if risk_per_unit <= 0:
                continue
            total_risk += pm.total_size * risk_per_unit

        if Config.DRY_RUN:
            balance = 10000.0
        else:
            balance = self.risk_manager.get_balance()
        if balance <= 0:
            return False
        return (total_risk / balance) <= Config.MAX_TOTAL_RISK

    # ==================== ???????====================

    def _execute_order_plan(self, order_plan: ExecutableOrderPlan):
        """Execute a central-risk-approved strategy order plan."""
        intent = order_plan.intent
        risk_plan = order_plan.risk_plan
        symbol = intent.symbol
        side = intent.side
        try:
            if symbol in self.active_trades:
                logger.info("%s: skip execution, position already active", symbol)
                return

            entry_price = risk_plan.entry_price
            position_size = risk_plan.position_size
            stop_loss = risk_plan.stop_loss
            initial_r = risk_plan.max_loss_usdt

            if Config.DRY_RUN:
                logger.info(
                    "[DRY_RUN] %s %s strategy=%s size=%.6f entry=%.4f sl=%.4f",
                    symbol,
                    side,
                    intent.strategy_id,
                    position_size,
                    entry_price,
                    stop_loss,
                )
                return

            order_side = self._get_close_side(side)
            if BinanceFuturesClient.is_enabled():
                order_result = self._futures_create_order(symbol, order_side, position_size)
            else:
                order_result = self.exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side=order_side.lower(),
                    amount=position_size,
                )

            fill_price = self._extract_fill_price(order_result, entry_price)
            if fill_price != entry_price:
                logger.info("%s fill adjusted: signal=%.4f actual=%.4f", symbol, entry_price, fill_price)
            entry_price = fill_price
            initial_r = position_size * abs(entry_price - stop_loss)

            pm = PositionManager(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_size=position_size,
                strategy_id=intent.strategy_id,
                strategy_version=order_plan.strategy_version,
                risk_plan={
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "position_size": position_size,
                    "max_loss_usdt": initial_r,
                    "risk_pct": risk_plan.risk_pct,
                    "hard_stop_required": risk_plan.hard_stop_required,
                },
                metadata={
                    **dict(intent.metadata),
                    **dict(order_plan.metadata),
                    "entry_type": intent.entry_type,
                    "timeframe": intent.timeframe,
                    "candle_ts": intent.candle_ts.isoformat(),
                    "router_reason": order_plan.router_reason,
                },
                initial_r=initial_r,
                signal_tier="CENTRAL",
                signal_type=intent.strategy_id,
                market_regime=(self._btc_regime_context or {}).get("regime", "UNKNOWN"),
            )

            _trade_log({
                **self._build_log_base("TRADE_OPEN", pm.trade_id, symbol, side),
                "strategy_id": intent.strategy_id,
                "strategy_version": order_plan.strategy_version,
                "entry_type": intent.entry_type,
                "size": f"{position_size:.6f}",
                "entry": f"{entry_price:.2f}",
                "sl": f"{stop_loss:.2f}",
                "value": f"{position_size * entry_price:.2f}",
                "risk": f"{initial_r:.2f}",
                "router_reason": order_plan.router_reason,
            })

            pm.stop_order_id = self._place_hard_stop_loss(symbol, side, position_size, stop_loss)
            self.active_trades[symbol] = pm
            self._save_positions()

            TelegramNotifier.notify_signal(symbol, {
                "side": side,
                "entry_price": entry_price,
                "position_size": position_size,
                "stop_loss": stop_loss,
                "strategy_id": intent.strategy_id,
                "strategy_name": intent.strategy_id,
                "signal_type": intent.strategy_id,
            })

        except Exception as e:
            logger.error("%s strategy execution failed: %s", symbol, e)
            self.order_failed_symbols[symbol] = datetime.now(timezone.utc)

    def _legacy_entry_removed(self, *_args, **_kwargs):
        """Removed legacy signal execution path."""
        raise RuntimeError("legacy entry execution removed; use _execute_order_plan")
    def monitor_positions(self):
        self.position_monitor.monitor_positions()

    def _fetch_exchange_stop_map(self) -> Dict[str, float]:
        """
        ????????????????????????

        ?????algo orders??????????????????????emo Trading ??404??
        ??fallback ?????openOrders ???? STOP_MARKET ?????

        Returns:
            {symbol_id: trigger_price}?????{'BTCUSDT': 87500.0}
            ?????? API ??????? {}
        """
        if not BinanceFuturesClient.is_enabled():
            return {}
        stop_map: Dict[str, float] = {}
        try:
            # ????algo orders???????????????
            response = self.risk_manager.futures_client.signed_request(
                'GET', '/fapi/v1/algoOrder/openOrders'
            )
            if response.status_code == 200:
                for o in response.json().get('orders', []):
                    sym = o.get('symbol', '')
                    trigger = o.get('triggerPrice') or o.get('stopPrice')
                    if sym and trigger:
                        stop_map[sym] = float(trigger)
                return stop_map
            # algo endpoint ??????Demo Trading ??404??? fallback ????????
            logger.debug(f"[ADOPT] algo openOrders ?????{response.status_code})????????????")
        except Exception as e:
            logger.warning(f"[ADOPT] ??algo ????????? {e}")

        try:
            # Fallback?????openOrders ???? STOP_MARKET
            response = self.risk_manager.futures_client.signed_request(
                'GET', '/fapi/v1/openOrders'
            )
            if response.status_code == 200:
                for o in response.json():
                    if o.get('type') in ('STOP_MARKET', 'STOP'):
                        sym = o.get('symbol', '')
                        trigger = o.get('stopPrice') or o.get('triggerPrice')
                        if sym and trigger:
                            stop_map[sym] = float(trigger)
        except Exception as e:
            logger.warning(f"[ADOPT] ?????????????: {e}")

        return stop_map

    def _adopt_ghost_positions(self):
        """
        ???????????????????????xchange ????ositions.json ????????

        ???????????
        1. ????????positions
        2. ???????????? symbol
        3. ??algo ??????????? stop_loss???????????? ? 2% ???????
        4. ???? protective/manual PositionManager
        5. ??????? ????????????????
        6. ??? active_trades + _save_positions()
        """
        if Config.DRY_RUN:
            return

        exchange_positions = self.risk_manager.get_positions()
        if not exchange_positions:  # None ??[]
            return

        stop_map = self._fetch_exchange_stop_map()
        adopted = 0
        symbol_sides: Dict[str, set] = {}

        for pos in exchange_positions:
            sym_id = pos.get('symbol', '') or pos.get('info', {}).get('symbol', '')
            if not sym_id:
                continue
            ccxt_sym = sym_id[:-4] + '/' + sym_id[-4:] if sym_id.endswith('USDT') else sym_id
            if ccxt_sym in self.active_trades:
                continue
            side = self._normalize_position_side(pos)
            position_size = self._extract_position_size(pos)
            if side is None or position_size <= 0:
                continue
            symbol_sides.setdefault(ccxt_sym, set()).add(side)

        ambiguous_symbols = {
            ccxt_sym: sorted(sides)
            for ccxt_sym, sides in symbol_sides.items()
            if len(sides) > 1
        }
        for ccxt_sym, sides in ambiguous_symbols.items():
            logger.critical(f"[ADOPT_SKIP_HEDGE_AMBIGUOUS] {ccxt_sym}: sides={','.join(sides)}")

        for pos in exchange_positions:
            sym_id = pos.get('symbol', '') or pos.get('info', {}).get('symbol', '')
            if not sym_id:
                continue

            # ??ccxt ?????TCUSDT ??BTC/USDT
            ccxt_sym = sym_id[:-4] + '/' + sym_id[-4:] if sym_id.endswith('USDT') else sym_id

            # ?????????????
            if ccxt_sym in self.active_trades:
                continue

            # ??? side / size / entry
            if ccxt_sym in ambiguous_symbols:
                continue
            side = self._normalize_position_side(pos)
            position_size = self._extract_position_size(pos)
            if side is None or position_size <= 0:
                continue
            entry_price = float(
                pos.get('entryPrice', 0) or pos.get('info', {}).get('entryPrice', 0)
            )
            if entry_price <= 0:
                logger.warning(f"[ADOPT] {ccxt_sym} entryPrice is invalid")
                continue

            # ???????????
            stop_loss = stop_map.get(sym_id)
            stop_source = 'exchange'
            if stop_loss is None:
                fallback_pct = getattr(Config, 'GHOST_ADOPT_SL_PCT', 0.02)
                stop_loss = (
                    entry_price * (1 - fallback_pct) if side == 'LONG'
                    else entry_price * (1 + fallback_pct)
                )
                stop_source = f'fallback({fallback_pct * 100:.0f}%)'

            # ??PositionManager??5.3 ????????????pyramid ?????
            pm = PositionManager(
                symbol=ccxt_sym,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_size=position_size,
                strategy_id="legacy_manual",
                initial_r=position_size * abs(entry_price - stop_loss),
            )
            pm.entry_time = datetime.now(timezone.utc)
            pm.highest_price = entry_price
            pm.lowest_price = entry_price

            # ???????????????
            if stop_map.get(sym_id) is None:
                try:
                    order_id = self.execution_engine.place_hard_stop_loss(
                        ccxt_sym, side, position_size, stop_loss
                    )
                    pm.stop_order_id = order_id
                    logger.info(f"[ADOPT] {ccxt_sym} ??????????????@ ${stop_loss:.4f}")
                except Exception as e:
                    logger.warning(f"[ADOPT] {ccxt_sym} ???????????????: {e}")

            self.active_trades[ccxt_sym] = pm
            adopted += 1
            logger.warning(
                f"[GHOST_ADOPTED] {ccxt_sym}: {side} size={position_size} "
                f"entry=${entry_price:.4f} sl=${stop_loss:.4f} "
                f"(stop_source={stop_source})"
            )

        if adopted > 0:
            self._save_positions()
            logger.warning(f"[ADOPT] ?????{adopted} ??????????????? positions.json")

    def _sync_exchange_positions(self):
        """
        ????????? reconciliation?????monitor_positions ????????

        ???????????
        1. API ????????????et_positions ??None ?????????????
        2. ??????????????ot ??/ exchange ????hard_stop_hit
        3. Size ??????????????????????????
        4. ??????????????xchange ??/ bot ???????????????
        """
        if Config.DRY_RUN:
            return
        try:
            exchange_positions = self.risk_manager.get_positions()

            if exchange_positions is None:
                logger.warning("[SYNC] exchange positions unavailable; skip reconciliation for this cycle")
                return

            exchange_map = self._build_exchange_position_map(exchange_positions)
            internal_map = self._build_internal_position_map()
            hard_stop_detected = False

            for symbol, pm in list(self.active_trades.items()):
                key = (self._symbol_to_exchange_id(symbol), pm.side)
                ex_amt = exchange_map.get(key, 0.0)

                if ex_amt <= 0:
                    logger.warning(f"[SYNC] {symbol} {pm.side} missing on exchange -> HARD_STOP_HIT")
                    pm.exit_reason = 'hard_stop_hit'
                    pm.closed_on_exchange = True
                    pm.external_close_reason = 'hard_stop_hit'
                    pm.external_exit_price = pm.current_sl or pm.initial_sl or pm.avg_entry
                    pm.external_exit_price_source = 'assumed_sl'
                    hard_stop_detected = True
                    TelegramNotifier.notify_action(
                        symbol,
                        'STOP HIT',
                        pm.current_sl,
                        "Exchange no longer reports this tracked position",
                    )
                    continue

                if getattr(pm, 'closed_on_exchange', False):
                    pm.closed_on_exchange = False
                    pm.external_close_reason = None
                    pm.external_exit_price = None
                    pm.external_exit_price_source = None

                bot_amt = pm.total_size
                if bot_amt > 0 and abs(ex_amt - bot_amt) / bot_amt > 0.05:
                    logger.warning(
                        f"[SIZE_MISMATCH] {symbol}: side={pm.side} "
                        f"bot={bot_amt:.6f} vs exchange={ex_amt:.6f} "
                        f"(???? {abs(ex_amt - bot_amt):.6f})"
                    )

            for (symbol_id, side), ex_amt in exchange_map.items():
                if ex_amt > 0 and (symbol_id, side) not in internal_map:
                    logger.warning(
                        f"[GHOST_POSITION] {self._exchange_id_to_symbol(symbol_id)}: "
                        f"{side} {ex_amt:.6f} exists on exchange but not in bot state"
                    )

            if hard_stop_detected:
                self._save_positions()

        except Exception as e:
            logger.warning(f"[SYNC] ?????????????????? {e}")

    def _handle_close(
        self,
        pm: PositionManager,
        current_price: float = 0.0,
        external_close: bool = False,
        exit_price_source: Optional[str] = None,
        decision_reason: Optional[str] = None,
    ) -> bool:
        return self.position_monitor.handle_close(
            pm,
            current_price,
            external_close=external_close,
            exit_price_source=exit_price_source,
            decision_reason=decision_reason,
        )

    # ==================== ??????????? ====================

    def startup_diagnostics(self) -> bool:
        """???????????"""
        logger.info("??????????????...")

        try:
            if Config.DRY_RUN:
                balance = 10000.0
                logger.info(f"[????] ???: ${balance:.2f} USDT")
            else:
                balance = self.risk_manager.get_balance()
                logger.info(f"API ????| ???: ${balance:.2f} USDT")
            self.initial_balance = balance
        except Exception as e:
            logger.error(f"API ???????: {e}")
            return False

        test_symbol = Config.SYMBOLS[0] if Config.SYMBOLS else 'BTC/USDT'
        df = self.fetch_ohlcv(test_symbol, Config.TIMEFRAME_SIGNAL, limit=50)
        if df.empty:
            logger.error(f"??????????: {test_symbol}")
            return False
        logger.info(f"Data check passed for {test_symbol}: {len(df)} rows")

        # Check higher-timeframe data availability.
        df_4h = self.fetch_ohlcv(test_symbol, '4h', limit=20)
        if df_4h.empty:
            logger.warning("4h data unavailable")
        else:
            logger.info(f"4h data check passed: {len(df_4h)} rows")

        # Validate config.
        try:
            Config.validate()
            logger.info("Config ??????")
        except ValueError as e:
            logger.error(f"Config ???????: {e}")
            return False

        logger.info("??????????????")
        return True

    # ==================== ??????====================

    def run(self):
        """?????????"""
        if not self.startup_diagnostics():
            logger.error("Startup diagnostics failed")
            return

        try:
            dual_mode = self.futures_client.get_position_side_dual()
            self.execution_engine.hedge_mode = dual_mode
            if dual_mode:
                logger.info('Account is in Hedge Mode, execution_engine.hedge_mode=True')
        except Exception as e:
            logger.warning(f'Could not determine hedge mode state: {e}')

        # Ensure hedge mode for grid trading
        if Config.ENABLE_GRID_TRADING:
            is_hedge = self.futures_client.get_position_mode()
            if is_hedge is True:
                logger.info("Hedge mode already enabled ??grid trading ready")
            elif is_hedge is False:
                logger.info("Grid trading enabled ??switching to hedge mode")
                if not self.futures_client.set_hedge_mode(True):
                    # Verify: re-query actual state
                    is_hedge = self.futures_client.get_position_mode()
                    if is_hedge is not True:
                        logger.error(
                            "Failed to switch account into hedge mode; disabling grid trading"
                        )
                        Config.ENABLE_GRID_TRADING = False
            else:
                logger.warning("Unable to determine position mode; disabling grid trading")
            if Config.ENABLE_GRID_TRADING:
                try:
                    self.execution_engine.hedge_mode = self.futures_client.get_position_side_dual()
                except Exception as e:
                    logger.warning(f"Could not refresh hedge mode state after grid check: {e}")
                self._restore_grid_runtime_state()

        logger.info("?????????????..\n")

        # ?????????????? positions.json ????????????????????????
        self._adopt_ghost_positions()

        cycle = 0
        while True:
            try:
                cycle += 1
                logger.debug(f"[???? #{cycle}]")

                self.scan_for_signals()
                self._monitor_grid_state()
                self._sync_exchange_positions()  # ??cycle ??????active_trades ??????????????????
                self.monitor_positions()
                self.telegram_handler.poll()

                logger.debug(f"??? {Config.CHECK_INTERVAL} ??..\n")
                time.sleep(Config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("???????????????????")
                self._save_positions()
                break
            except Exception as e:
                logger.error(f"???? #{cycle} ????: {e}")
                time.sleep(Config.CHECK_INTERVAL)


TradingBotV6 = TradingBot

# ==================== ??? ====================
if __name__ == "__main__":
    import argparse

    # SIGTERM ??KeyboardInterrupt??ystemd stop ??graceful flush positions??
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    parser = argparse.ArgumentParser(description='Trading Bot')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    # Runtime ?????log/ ??????
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / '.log'
    log_dir.mkdir(exist_ok=True)

    # ???????? logging
    log_file = str(log_dir / 'bot.log')
    log_level = logging.DEBUG if args.debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
            ),
        ],
    )

    # [TRADE] ????????.log/trades.log
    class _TradeFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return isinstance(msg, str) and '[TRADE]' in msg

    _trade_handler = logging.handlers.RotatingFileHandler(
        str(log_dir / 'trades.log'), maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    _trade_handler.setFormatter(logging.Formatter('%(message)s'))
    _trade_handler.addFilter(_TradeFilter())
    _trade_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(_trade_handler)

    # WARNING/ERROR ?????Telegram???????????5 ??????????????
    class _TelegramLogHandler(logging.Handler):
        # ?????? Telegram ??????????????????????
        _IGNORE_PATTERNS = [
            "Scanner JSON had no usable bot_symbols/hot_symbols",
            "Scanner JSON ??hot_symbols ????",
        ]

        def __init__(self):
            super().__init__(level=logging.WARNING)
            self._last_sent = {}  # message_key -> timestamp

        def emit(self, record):
            try:
                msg = self.format(record)
                if any(p in msg for p in self._IGNORE_PATTERNS):
                    return
                # ???????? 80 ?????key?? ?????? key ?????
                key = msg[:80]
                now = time.time()
                if now - self._last_sent.get(key, 0) < 300:
                    return
                self._last_sent[key] = now
                # ?????? key???????????????
                if len(self._last_sent) > 100:
                    cutoff = now - 300
                    self._last_sent = {k: v for k, v in self._last_sent.items() if v > cutoff}
                TelegramNotifier.notify_warning(msg)
            except Exception:
                pass  # ?????????????????

    _tg_handler = _TelegramLogHandler()
    _tg_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(_tg_handler)

    try:
        # Defaults live in trader/config.py; load_secrets only pulls credentials.
        secrets_path = str(Path(__file__).parent.parent / "secrets.json")
        Config.load_secrets(secrets_path)
        if args.dry_run:
            Config.DRY_RUN = True  # type: ignore[assignment]

        bot = TradingBot()
        bot.run()
    except Exception as e:
        logger.error(f"???????????? {e}")
        raise
