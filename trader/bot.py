"""Primary StrategyRuntime bot process."""

import sys
import os
import time
import json
import signal
import logging
import logging.handlers
import warnings
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Make repo-root imports work when this file is executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pyzt emits a SyntaxWarning on Python 3.12 through a third-party import path.
# Keep bot startup output focused on runtime state.
warnings.filterwarnings("ignore", category=SyntaxWarning, module=r"pyzt(\.|$)")

import ccxt
import pandas as pd

# Infrastructure.
from trader.infrastructure.api_client import BinanceFuturesClient
from trader.infrastructure.notifier import TelegramNotifier
from trader.infrastructure.telegram_handler import TelegramCommandHandler
from trader.infrastructure.data_provider import MarketDataProvider
from trader.infrastructure.performance_db import PerformanceDB
# Runtime services.
from trader.risk.manager import PrecisionHandler, RiskManager
from trader.arbiter import RegimeArbiter
from trader.routing import RegimeRouter
from trader.regime import RegimeEngine
# Execution and runtime kernel.
from trader.execution.order_engine import OrderExecutionEngine
from trader.config import Config
from trader.positions import PositionManager
from trader.persistence import PositionPersistence
from trader.runtime_observability import RuntimeFunnelRecorder
from trader.strategies import ExecutableOrderPlan
from trader.strategy_runtime import StrategyRuntime
from trader.btc_context import BTCContextManager, get_last_candle_time, get_last_closed_candle_time, format_candle_time
from trader.position_monitor import PositionMonitor
from trader.signal_scanner import SignalScanner
from trader.utils import RUNTIME_LABEL, trade_log, calculate_pnl, get_close_side, build_log_base

logger = logging.getLogger(__name__)

STRATEGY_DISPLAY_NAMES = {
    (
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
        "transition_aware_tightened_late_entry_filter"
    ): "Slot A LONG / BTC 4h MACD",
    "donchian_range_fade_4h_range_width_cv_013": "Slot B LONG / Donchian range fade",
    "donchian_range_fade_4h_range_width_cv_013_short": "Slot B SHORT / Donchian range fade",
}


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
        # RiskManager still expects this futures client hook for account calls.
        self.risk_manager.futures_client = self.futures_client
        # All live orders go through the execution engine.
        self.execution_engine = OrderExecutionEngine(
            self.exchange, self.futures_client, self.precision_handler
        )

        # Active PositionManager records keyed by symbol.
        self.active_trades: Dict[str, PositionManager] = {}
        self._scanner_symbol_meta: Dict[str, Dict[str, object]] = {}
        self._scanner_symbol_source: Dict[str, object] = {}

        # Local cooldown state.
        self.recently_exited: Dict[str, datetime] = {}
        self.order_failed_symbols: Dict[str, datetime] = {}
        self.early_exit_cooldown: Dict[str, datetime] = {}

        # Startup diagnostics records this for cycle summaries.
        self.initial_balance: float = 0.0

        # Runtime persistence path is owned by Config defaults.
        pos_path = os.path.expanduser(Config.POSITIONS_JSON_PATH)
        if not os.path.isabs(pos_path):
            pos_path = str(Path(__file__).parent.parent / pos_path)
        Path(pos_path).parent.mkdir(parents=True, exist_ok=True)
        self.persistence = PositionPersistence(pos_path)

        # Restore persisted positions before entering runtime services.
        self._restore_positions()

        # Performance DB.
        db_path = getattr(Config, 'DB_PATH', 'performance.db')
        self.perf_db = PerformanceDB(db_path=db_path)

        self.runtime_observer = RuntimeFunnelRecorder.from_config(Config)
        self._log_startup()
        if self.runtime_observer is not None:
            self.runtime_observer.record_config_snapshot(
                Config,
                active_positions=len(self.active_trades),
                positions_json_path=pos_path,
                db_path=db_path,
            )

        # Telegram command handler.
        self.telegram_handler = TelegramCommandHandler(self)

        # Regime system
        self.regime_engine = RegimeEngine()
        self.regime_arbiter = RegimeArbiter()
        self.regime_router = RegimeRouter()
        self._start_time = datetime.now(timezone.utc)
        self._btc_regime_context: Dict[str, object] = {}
        self._btc_trend_context: Dict[str, object] = {}
        self._regime_arbiter_snapshot = None
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
                    # Binance Futures testnet is now routed through Demo Trading.
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
                    logger.info("Exchange sandbox: Binance Demo Trading")
                else:
                    try:
                        exchange.set_sandbox_mode(True)
                    except Exception as e:
                        logger.warning(f"Sandbox mode setup failed: {e}")

            try:
                exchange.load_markets()
                logger.info("Exchange markets loaded: %s", len(exchange.markets))
            except Exception as e:
                logger.warning(f"Market loading failed: {e}")

            if Config.TRADING_MODE == 'future':
                for symbol in Config.SYMBOLS:
                    try:
                        exchange.set_leverage(Config.LEVERAGE, symbol)
                    except Exception:
                        pass

            return exchange

        except Exception as e:
            logger.error(f"Exchange initialization failed: {e}")
            raise

    def _log_startup(self):
        """Log concise StrategyRuntime startup context."""
        observer = getattr(self, "runtime_observer", None)
        latest_path = self._short_path(observer.latest_path) if observer is not None else "off"
        logger.info("%s starting", RUNTIME_LABEL)
        logger.info(
            "  account: mode=%s direction=%s sandbox=%s dry_run=%s leverage=%sx",
            Config.TRADING_MODE,
            Config.TRADING_DIRECTION,
            Config.SANDBOX_MODE,
            Config.DRY_RUN,
            Config.LEVERAGE,
        )
        logger.info(
            "  runtime: enabled=%s side=%s arbiter=%s router=%s btc_trend_filter=%s mode=%s",
            Config.STRATEGY_RUNTIME_ENABLED,
            Config.STRATEGY_RUNTIME_SIDE_FILTER,
            Config.REGIME_ARBITER_ENABLED,
            Config.REGIME_ROUTER_ENABLED,
            Config.BTC_TREND_FILTER_ENABLED,
            Config.BTC_TREND_FILTER_RUNTIME_MODE,
        )
        logger.info(
            "  risk: per_trade=%.2f%% max_total=%.2f%% max_position=%.2f%% max_sl=%.2f%%",
            Config.RISK_PER_TRADE * 100,
            Config.MAX_TOTAL_RISK * 100,
            Config.MAX_POSITION_PERCENT * 100,
            Config.MAX_SL_DISTANCE_PCT * 100,
        )
        logger.info(
            "  universe: fixed=%s scanner=%s scanner_universe=%s",
            ", ".join(Config.SYMBOLS) or "none",
            Config.USE_SCANNER_SYMBOLS,
            Config.SCANNER_UNIVERSE_ENABLED,
        )
        logger.info(
            "  state: positions=%s performance_db=%s observability=%s",
            len(self.active_trades),
            self._short_path(getattr(Config, "DB_PATH", "performance.db")),
            latest_path,
        )
        strategy_names = self._strategy_display_names(Config.ENABLED_STRATEGIES)
        logger.info("  portfolio: %s", ", ".join(strategy_names) if strategy_names else "none")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("  strategy_ids: %s", ", ".join(Config.ENABLED_STRATEGIES) or "none")

    @staticmethod
    def _strategy_display_names(strategy_ids: List[str]) -> List[str]:
        names = []
        for strategy_id in strategy_ids:
            label = STRATEGY_DISPLAY_NAMES.get(strategy_id, strategy_id)
            if len(label) > 88:
                label = f"{label[:85]}..."
            names.append(label)
        return names

    @staticmethod
    def _short_path(path_value) -> str:
        path = Path(str(path_value))
        try:
            return str(path.resolve().relative_to(Path(__file__).resolve().parent.parent))
        except Exception:
            return str(path)

    def _record_runtime_event(self, event: str, **fields):
        observer = getattr(self, "runtime_observer", None)
        if observer is not None:
            observer.record_event(event, **fields)

    def _restore_positions(self):
        """Restore positions from positions.json."""
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
                logger.error(f"Failed to restore {symbol}: {e}")

    def _save_positions(self):
        """Persist active positions to JSON."""
        data = {}
        for symbol, pm in self.active_trades.items():
            data[symbol] = pm.to_dict()
        self.persistence.save_positions(data)

    # ==================== Market Data ====================

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
        """Load scanner symbols with Config.SYMBOLS as the safe fallback."""
        self._scanner_symbol_meta = {}
        self._scanner_symbol_source = {}
        try:
            scanner_path = os.path.expanduser(Config.SCANNER_JSON_PATH)
            # Relative scanner paths are resolved from the project root.
            if not os.path.isabs(scanner_path):
                scanner_path = str(Path(__file__).parent.parent / scanner_path)
            if not os.path.exists(scanner_path):
                self._scanner_symbol_source = {
                    'source': 'config_symbols',
                    'fallback_reason': 'scanner_json_missing',
                    'scanner_path': scanner_path,
                }
                logger.warning(f"Scanner JSON not found at {scanner_path}; using default symbols")
                return Config.SYMBOLS

            with open(scanner_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            scan_time_str = data.get('scan_time', '')
            if scan_time_str:
                try:
                    scan_time = datetime.fromisoformat(scan_time_str.replace('Z', '+00:00'))
                    age_minutes = (datetime.now(timezone.utc) - scan_time).total_seconds() / 60
                    if age_minutes > Config.SCANNER_MAX_AGE_MINUTES:
                        self._scanner_symbol_source = {
                            'source': 'config_symbols',
                            'fallback_reason': 'scanner_json_stale',
                            'scanner_path': scanner_path,
                            'age_minutes': round(age_minutes, 2),
                            'max_age_minutes': Config.SCANNER_MAX_AGE_MINUTES,
                        }
                        logger.warning(
                            "Scanner JSON stale "
                            f"({age_minutes:.0f} min > {Config.SCANNER_MAX_AGE_MINUTES} min); "
                            "using default symbols"
                        )
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
                    self._scanner_symbol_source = {
                        'source': field_name,
                        'fallback_reason': None,
                        'scanner_path': scanner_path,
                        'symbol_count': len(scanner_symbols),
                        'unsupported_filtered': unsupported_count,
                    }
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
            self._scanner_symbol_source = {
                'source': 'config_symbols',
                'fallback_reason': 'scanner_json_no_usable_symbols',
                'scanner_path': scanner_path,
            }
            logger.warning("Scanner JSON had no usable bot_symbols/hot_symbols, using default symbols")
            return Config.SYMBOLS
        except Exception as e:
            self._scanner_symbol_source = {
                'source': 'config_symbols',
                'fallback_reason': 'scanner_json_load_failed',
                'error': str(e),
            }
            logger.warning(f"Scanner JSON load failed: {e}; using default symbols")
            return Config.SYMBOLS

    # ==================== OrderExecutionEngine wrappers ====================

    def _futures_set_leverage(self, symbol: str) -> bool:
        """Set futures leverage through the execution engine."""
        return self.execution_engine.set_leverage(symbol)

    def _futures_create_order(self, symbol: str, side: str, quantity: float) -> dict:
        """Create a futures market order through the execution engine."""
        return self.execution_engine.create_order(symbol, side, quantity)

    @staticmethod
    def _extract_fill_price(order_result: dict, fallback_price: float) -> float:
        """
        Prefer exchange-reported fill prices and fall back to the approved entry.

        BinanceFuturesClient returns result['avgPrice']; CCXT returns
        result['average']. Some venues return 0 until fully settled.
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
        """Close a futures position through the execution engine."""
        return self.execution_engine.close_position(symbol, side, quantity)

    def _place_hard_stop_loss(self, symbol: str, side: str, size: float, stop_price: float) -> Optional[str]:
        """Place a hard stop order and return its exchange order id."""
        return self.execution_engine.place_hard_stop_loss(symbol, side, size, stop_price)

    def _cancel_stop_loss_order(self, symbol: str, order_id: Optional[str]) -> bool:
        """Cancel a hard stop order through the execution engine."""
        return self.execution_engine.cancel_stop_loss_order(symbol, order_id)

    def _update_hard_stop_loss(self, pm: PositionManager, new_stop: float):
        """Refresh a tracked position's hard stop."""
        return self._refresh_stop_loss(pm, new_stop)

    # ==================== Signal Scan ====================

    def scan_for_signals(self):
        self.signal_scanner.scan_for_signals()

    # ==================== Private Helpers ====================

    def _check_btc_trend(self) -> Optional[str]:
        return self.btc_context_manager.check_btc_trend()

    @staticmethod
    def _get_last_candle_time(df: pd.DataFrame) -> Optional[pd.Timestamp]:
        return get_last_candle_time(df)

    @staticmethod
    def _get_last_closed_candle_time(df: pd.DataFrame) -> Optional[pd.Timestamp]:
        return get_last_closed_candle_time(df)

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

        return internal_map

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
        """Return open-risk percentage against the supplied balance."""
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
        """Check total open risk for the supplied PositionManager list."""
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

    # ==================== Execution Guardrails ====================

    def _abort_post_fill_stop_violation(
        self,
        order_plan: ExecutableOrderPlan,
        fill_price: float,
        stop_loss: float,
        reason: str,
    ) -> None:
        intent = order_plan.intent
        symbol = intent.symbol
        side = intent.side
        position_size = order_plan.risk_plan.position_size
        now = datetime.now(timezone.utc)
        if hasattr(self, "order_failed_symbols"):
            self.order_failed_symbols[symbol] = now

        collector = getattr(self, "_signal_audit", None)
        if collector is not None:
            collector.record_reject(
                timestamp=now.isoformat(),
                symbol=symbol,
                stage="execution",
                reject_reason="post_fill_stop_violation",
                signal_type=intent.strategy_id,
                signal_side=side,
                detail=reason,
            )
        logger.error(
            "%s post-fill stop violation strategy=%s side=%s fill=%.4f sl=%.4f reason=%s",
            symbol,
            intent.strategy_id,
            side,
            fill_price,
            stop_loss,
            reason,
        )
        self._record_runtime_event(
            "execution_failure",
            symbol=symbol,
            strategy_id=intent.strategy_id,
            side=side,
            reason="post_fill_stop_violation",
            detail=reason,
            fill_price=fill_price,
            stop_loss=stop_loss,
        )

        log_fields = {
            **self._build_log_base("POST_FILL_STOP_VIOLATION", "post_fill_abort", symbol, side),
            "strategy_id": intent.strategy_id,
            "strategy_version": order_plan.strategy_version,
            "fill_price": f"{fill_price:.4f}",
            "stop_loss": f"{stop_loss:.4f}",
            "size": f"{position_size:.6f}",
            "reason": reason,
        }

        if getattr(self, "_is_backtest", False):
            _trade_log({
                **log_fields,
                "flatten_action": "skipped_backtest",
            })
            return

        try:
            reverse_result = self._futures_close_position(symbol, side, position_size)
            reverse_fill = self._extract_fill_price(reverse_result, fill_price)
            realized_pnl = self._calculate_pnl(side, position_size, reverse_fill, fill_price)
            _trade_log({
                **log_fields,
                "flatten_action": "reverse_market_order",
                "reverse_fill": f"{reverse_fill:.4f}",
                "realized_pnl": f"{realized_pnl:+.4f}",
            })
        except Exception as exc:
            logger.error("%s post-fill violation flatten failed: %s", symbol, exc)
            _trade_log({
                **log_fields,
                "flatten_action": "reverse_market_order_failed",
                "error": str(exc),
            })

    def _execute_order_plan(self, order_plan: ExecutableOrderPlan):
        """Execute a central-risk-approved strategy order plan."""
        intent = order_plan.intent
        risk_plan = order_plan.risk_plan
        symbol = intent.symbol
        side = intent.side
        try:
            if symbol in self.active_trades:
                logger.info("%s: skip execution, position already active", symbol)
                self._record_runtime_event(
                    "execution_skipped",
                    symbol=symbol,
                    strategy_id=intent.strategy_id,
                    side=side,
                    reason="position_already_active",
                )
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
                self._record_runtime_event(
                    "execution_skipped",
                    symbol=symbol,
                    strategy_id=intent.strategy_id,
                    side=side,
                    reason="dry_run",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
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
            if side == "LONG" and stop_loss >= entry_price:
                self._abort_post_fill_stop_violation(
                    order_plan,
                    entry_price,
                    stop_loss,
                    "long_fill_below_stop",
                )
                return
            if side == "SHORT" and stop_loss <= entry_price:
                self._abort_post_fill_stop_violation(
                    order_plan,
                    entry_price,
                    stop_loss,
                    "short_fill_above_stop",
                )
                return
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
            self._record_runtime_event(
                "execution_filled",
                symbol=symbol,
                strategy_id=intent.strategy_id,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_size=position_size,
                risk_usdt=initial_r,
                router_reason=order_plan.router_reason,
            )

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
            logger.exception("%s strategy execution failed", symbol)
            self._record_runtime_event(
                "execution_failure",
                symbol=symbol,
                strategy_id=intent.strategy_id,
                side=side,
                reason="order_execution_exception",
                error_type=type(e).__name__,
                error=str(e),
            )
            self.order_failed_symbols[symbol] = datetime.now(timezone.utc)

    def _legacy_entry_removed(self, *_args, **_kwargs):
        """Removed legacy signal execution path."""
        raise RuntimeError("legacy entry execution removed; use _execute_order_plan")
    def monitor_positions(self):
        self.position_monitor.monitor_positions()

    def _fetch_exchange_stop_map(self) -> Dict[str, float]:
        """
        Fetch open exchange-side stop orders keyed by exchange symbol id.

        Prefer the algo openOrders endpoint; Demo Trading may return 404, so
        fall back to regular openOrders and STOP_MARKET orders.

        Returns:
            {symbol_id: trigger_price}, e.g. {'BTCUSDT': 87500.0}.
            Returns {} when the Futures API is unavailable.
        """
        if not BinanceFuturesClient.is_enabled():
            return {}
        stop_map: Dict[str, float] = {}
        try:
            # Prefer the algo-orders endpoint when available.
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
            logger.debug(
                f"[ADOPT] algo openOrders returned {response.status_code}; falling back"
            )
        except Exception as e:
            logger.warning(f"[ADOPT] algo stop-order fetch failed: {e}")

        try:
            # Fallback: scan regular openOrders for STOP_MARKET/STOP orders.
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
            logger.warning(f"[ADOPT] fallback stop-order fetch failed: {e}")

        return stop_map

    def _adopt_ghost_positions(self):
        """
        Adopt exchange positions that exist outside positions.json.

        Safety flow:
        1. read exchange positions;
        2. skip symbols already tracked by the bot;
        3. prefer exchange stop orders, otherwise use a conservative fallback SL;
        4. create protective/manual PositionManager entries;
        5. place a protective stop when one is missing;
        6. persist adopted entries to positions.json.
        """
        if Config.DRY_RUN:
            return

        exchange_positions = self.risk_manager.get_positions()
        if not exchange_positions:
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

            # Convert exchange ids such as BTCUSDT to CCXT symbols.
            ccxt_sym = sym_id[:-4] + '/' + sym_id[-4:] if sym_id.endswith('USDT') else sym_id

            # Skip positions already tracked by the bot.
            if ccxt_sym in self.active_trades:
                continue

            # Resolve side, size, and entry.
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

            # Prefer an exchange stop; otherwise create a fallback stop.
            stop_loss = stop_map.get(sym_id)
            stop_source = 'exchange'
            if stop_loss is None:
                fallback_pct = getattr(Config, 'GHOST_ADOPT_SL_PCT', 0.02)
                stop_loss = (
                    entry_price * (1 - fallback_pct) if side == 'LONG'
                    else entry_price * (1 + fallback_pct)
                )
                stop_source = f'fallback({fallback_pct * 100:.0f}%)'

            # Rebuild a manual PositionManager without legacy pyramid state.
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

            # Missing exchange stop: place one immediately after adoption.
            if stop_map.get(sym_id) is None:
                try:
                    order_id = self.execution_engine.place_hard_stop_loss(
                        ccxt_sym, side, position_size, stop_loss
                    )
                    pm.stop_order_id = order_id
                    logger.info(f"[ADOPT] {ccxt_sym} protective stop placed @ ${stop_loss:.4f}")
                except Exception as e:
                    logger.warning(f"[ADOPT] {ccxt_sym} protective stop placement failed: {e}")

            self.active_trades[ccxt_sym] = pm
            adopted += 1
            logger.warning(
                f"[GHOST_ADOPTED] {ccxt_sym}: {side} size={position_size} "
                f"entry=${entry_price:.4f} sl=${stop_loss:.4f} "
                f"(stop_source={stop_source})"
            )

        if adopted > 0:
            self._save_positions()
            logger.warning(f"[ADOPT] adopted {adopted} exchange position(s) into positions.json")

    def _sync_exchange_positions(self):
        """
        Reconcile exchange positions before monitor_positions cleanup.

        Safety rules:
        1. skip when get_positions returns None;
        2. mark tracked positions missing on exchange as hard_stop_hit;
        3. warn on size mismatches without mutating state;
        4. warn on exchange positions missing from bot state.
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
                        f"(delta {abs(ex_amt - bot_amt):.6f})"
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
            logger.warning(f"[SYNC] exchange reconciliation failed: {e}")

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

    # ==================== Startup Diagnostics ====================

    def startup_diagnostics(self) -> bool:
        """Run startup checks before entering the main loop."""
        logger.info("Startup checks running")

        try:
            if Config.DRY_RUN:
                balance = 10000.0
                logger.info("Balance OK: %.2f USDT (dry_run)", balance)
            else:
                balance = self.risk_manager.get_balance()
                logger.info("Balance OK: %.2f USDT", balance)
            self.initial_balance = balance
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return False

        test_symbol = Config.SYMBOLS[0] if Config.SYMBOLS else 'BTC/USDT'
        df = self.fetch_ohlcv(test_symbol, Config.TIMEFRAME_SIGNAL, limit=50)
        if df.empty:
            logger.error("Market data check failed: %s %s", test_symbol, Config.TIMEFRAME_SIGNAL)
            return False
        logger.info("Market data OK: %s %s rows=%s", test_symbol, Config.TIMEFRAME_SIGNAL, len(df))

        # Check higher-timeframe data availability.
        df_4h = self.fetch_ohlcv(test_symbol, '4h', limit=20)
        if df_4h.empty:
            logger.warning("Market data unavailable: %s 4h", test_symbol)
        else:
            logger.info("Market data OK: %s 4h rows=%s", test_symbol, len(df_4h))

        # Validate config.
        try:
            Config.validate()
            logger.info("Config validation OK")
        except ValueError as e:
            logger.error(f"Config validation failed: {e}")
            return False

        logger.info("Startup checks OK")
        return True

    # ==================== Main Loop ====================

    def run(self):
        """Run the bot main loop."""
        if not self.startup_diagnostics():
            logger.error("Startup checks failed")
            return

        try:
            dual_mode = self.futures_client.get_position_side_dual()
            self.execution_engine.hedge_mode = dual_mode
            if dual_mode:
                logger.info("Account mode: hedge")
            else:
                logger.info("Account mode: one-way")
        except Exception as e:
            logger.warning(f'Could not determine hedge mode state: {e}')

        logger.info("Main loop started: interval=%ss", Config.CHECK_INTERVAL)

        # Adopt unmanaged exchange positions before normal monitoring.
        self._adopt_ghost_positions()

        cycle = 0
        while True:
            try:
                cycle += 1
                logger.debug(f"[cycle #{cycle}]")

                self.scan_for_signals()
                self._sync_exchange_positions()
                self.monitor_positions()
                self.telegram_handler.poll()

                logger.debug(f"Sleeping {Config.CHECK_INTERVAL} seconds...\n")
                time.sleep(Config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Shutdown requested; saving positions")
                self._save_positions()
                break
            except Exception as e:
                logger.exception("Cycle #%s failed", cycle)
                self._record_runtime_event(
                    "cycle_failure",
                    cycle=cycle,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                time.sleep(Config.CHECK_INTERVAL)

def _configure_utf8_stdio() -> None:
    """Prefer UTF-8 console output so valid Unicode logs do not degrade."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass


# ==================== Entry Point ====================
if __name__ == "__main__":
    import argparse

    # Convert SIGTERM into KeyboardInterrupt so systemd stop flushes positions.
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    parser = argparse.ArgumentParser(description='Trading Bot')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    _configure_utf8_stdio()

    # Runtime owns .log/ output.
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / '.log'
    log_dir.mkdir(exist_ok=True)

    # Configure logging for both console and rotating UTF-8 log files.
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

    # Mirror [TRADE] records into .log/trades.log.
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

    # Forward warning/error logs to Telegram with simple 5-minute dedupe.
    class _TelegramLogHandler(logging.Handler):
        # Ignore noisy fallback warnings that should stay local only.
        _IGNORE_PATTERNS = [
            "Scanner JSON had no usable bot_symbols/hot_symbols",
            "Scanner JSON not found",
            "Scanner JSON stale",
            "Telegram send failed",
        ]

        def __init__(self):
            super().__init__(level=logging.WARNING)
            self._last_sent = {}  # message_key -> timestamp

        def emit(self, record):
            try:
                msg = self.format(record)
                if any(p in msg for p in self._IGNORE_PATTERNS):
                    return
                # Use the first 80 chars as a stable dedupe key.
                key = msg[:80]
                now = time.time()
                if now - self._last_sent.get(key, 0) < 300:
                    return
                self._last_sent[key] = now
                # Keep the dedupe cache bounded.
                if len(self._last_sent) > 100:
                    cutoff = now - 300
                    self._last_sent = {k: v for k, v in self._last_sent.items() if v > cutoff}
                TelegramNotifier.notify_warning(msg)
            except Exception:
                pass

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
        logger.error(f"TradingBot crashed: {e}")
        raise
