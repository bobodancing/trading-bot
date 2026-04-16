"""
V6.0 主引擎 — 終極滾倉版

基於 V5.3 TradingBotV53 重構：
- 2B 信號 → V7 結構加倉（V7StructureStrategy, 三段 swing-based 加倉）
- EMA Pullback / Volume Breakout → V5.3 SOP（PositionManager, is_v6_pyramid=False）
- [DEPRECATED] V6.0 滾倉仍保留供既有持倉平倉
- positions.json 持久化
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

# 確保從專案根目錄 import v6 package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ccxt
import pandas as pd

# 基礎設施層
from trader.infrastructure.api_client import BinanceFuturesClient
from trader.infrastructure.notifier import TelegramNotifier
from trader.infrastructure.telegram_handler import TelegramCommandHandler
from trader.infrastructure.data_provider import MarketDataProvider
from trader.infrastructure.performance_db import PerformanceDB
# 技術指標層
from trader.indicators.technical import TechnicalAnalysis
# 風險管理層
from trader.risk.manager import PrecisionHandler, RiskManager
from trader.arbiter import RegimeArbiter
from trader.routing import RegimeRouter
from trader.regime import RegimeEngine
from trader.strategies.v8_grid import V8AtrGrid, PoolManager
# 訂單執行層
from trader.execution.order_engine import OrderExecutionEngine
from trader.config import Config
from trader.positions import PositionManager
from trader.persistence import PositionPersistence
from trader.strategies.base import Action
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
        self._verify_config_parity()
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
        # RiskManager 內部用 V5.3 Config 建的 futures_client 拿不到新 key，覆蓋掉
        self.risk_manager.futures_client = self.futures_client
        # 訂單執行引擎（Phase 3: 剝離下單邏輯）
        self.execution_engine = OrderExecutionEngine(
            self.exchange, self.futures_client, self.precision_handler
        )

        # V6.0: PositionManager 取代 TradeManager
        self.active_trades: Dict[str, PositionManager] = {}
        self._scanner_symbol_meta: Dict[str, Dict[str, object]] = {}

        # 冷卻和黑名單
        self.recently_exited: Dict[str, datetime] = {}
        self.order_failed_symbols: Dict[str, datetime] = {}
        self.early_exit_cooldown: Dict[str, datetime] = {}  # 快速止損/超時退出 12h 冷卻

        # 帳戶初始餘額（用於 net_pnl_pct 計算）
        self.initial_balance: float = 0.0

        # V6.0: 持久化層（路徑在 Config，指向專案根目錄）
        pos_path = os.path.expanduser(Config.POSITIONS_JSON_PATH)
        if not os.path.isabs(pos_path):
            pos_path = str(Path(__file__).parent.parent / pos_path)
        Path(pos_path).parent.mkdir(parents=True, exist_ok=True)
        self.persistence = PositionPersistence(pos_path)

        # 啟動時恢復 positions
        self._restore_positions()

        # Phase 0: 績效 DB
        db_path = getattr(Config, 'DB_PATH', 'performance.db')
        self.perf_db = PerformanceDB(db_path=db_path)

        self._log_startup()

        # Telegram 互動指令
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

    @staticmethod
    def _verify_config_parity():
        """Fail closed when runtime-critical config file defaults drift."""
        if os.environ.get("BYPASS_CONFIG_PARITY") == "1":
            logger.warning("Config parity check bypassed via BYPASS_CONFIG_PARITY=1")
            return True

        try:
            from scripts.config_parity_check import compare_config_parity
        except Exception as e:
            raise RuntimeError(f"Config parity check unavailable: {e}") from e

        json_path = Path(__file__).parent.parent / "bot_config.json"
        config_path = Path(__file__).parent / "config.py"
        result = compare_config_parity(json_path=json_path, config_path=config_path)
        critical = result.critical_issues
        if critical:
            findings = ", ".join(f"{issue.category}:{issue.key}" for issue in critical)
            raise RuntimeError(f"Config parity check failed: {findings}")

        noncritical_count = len(result.issues)
        if noncritical_count:
            logger.warning(
                "Config parity check found %s non-critical issue(s); see reports/config_parity_*.md",
                noncritical_count,
            )
        return True

    def _init_exchange(self):
        """初始化交易所（沿用 V5.3）"""
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
                    # ccxt sandbox 會設成 testnet，覆蓋為 Demo Trading 端點
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
                    logger.info("已連接 Binance Demo Trading")
                else:
                    try:
                        exchange.set_sandbox_mode(True)
                    except Exception as e:
                        logger.warning(f"沙盒模式啟用失敗: {e}")

            try:
                exchange.load_markets()
                logger.info(f"已載入 {len(exchange.markets)} 個交易對")
            except Exception as e:
                logger.warning(f"載入市場資訊失敗: {e}")

            if Config.TRADING_MODE == 'future':
                for symbol in Config.SYMBOLS:
                    try:
                        exchange.set_leverage(Config.LEVERAGE, symbol)
                    except Exception:
                        pass

            return exchange

        except Exception as e:
            logger.error(f"交易所初始化失敗: {e}")
            raise

    def _log_startup(self):
        """啟動日誌"""
        logger.info("=" * 60)
        logger.info("TradingBot 已啟動")
        logger.info("=" * 60)
        logger.info(f"模式: {Config.TRADING_MODE} ({Config.TRADING_DIRECTION})")
        logger.info(f"槓桿: {Config.LEVERAGE}x")
        logger.info(f"風險: 每筆 {Config.RISK_PER_TRADE*100:.1f}%")
        logger.info(f"滾倉: {'開啟' if Config.PYRAMID_ENABLED else '關閉'}")
        if Config.PYRAMID_ENABLED:
            logger.info(f"  資金上限: {Config.EQUITY_CAP_PERCENT*100:.0f}%")
            logger.info(f"  三段比例: {Config.STAGE1_RATIO}/{Config.STAGE2_RATIO}/{Config.STAGE3_RATIO}")
        logger.info(f"模擬模式: {'開啟' if Config.V6_DRY_RUN else '關閉'}")
        logger.info(f"已恢復持倉: {len(self.active_trades)}")
        logger.info(f"監控標的: {', '.join(Config.SYMBOLS)}")
        logger.info("=" * 60)

    def _restore_positions(self):
        """從 positions.json 恢復 positions"""
        data = self.persistence.load_positions()
        if not data:
            return

        for symbol, pos_data in data.items():
            try:
                pm = PositionManager.from_dict(pos_data)
                self.active_trades[symbol] = pm
                value_usdt = pm.total_size * pm.avg_entry
                logger.info(
                    f"已恢復 {symbol}: {pm.side} 階段{pm.stage} "
                    f"倉位=${value_usdt:.2f} 止損=${pm.current_sl:.2f}"
                )
            except Exception as e:
                logger.error(f"恢復 {symbol} 失敗: {e}")

    def _save_positions(self):
        """儲存所有 positions 到 JSON"""
        data = {}
        for symbol, pm in self.active_trades.items():
            data[symbol] = pm.to_dict()
        self.persistence.save_positions(data)

    # ==================== 數據獲取 ====================

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """獲取 OHLCV 數據（委託 MarketDataProvider 統一處理重試與沙盒 fallback）"""
        return self.data_provider.fetch_ohlcv(symbol, timeframe, limit)

    def fetch_ticker(self, symbol: str) -> dict:
        """獲取 ticker（含 Demo Trading fallback）"""
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
        """從 Scanner 載入動態標的（沿用 V5.3）"""
        self._scanner_symbol_meta = {}
        try:
            scanner_path = os.path.expanduser(Config.SCANNER_JSON_PATH)
            # 相對路徑 → 基於專案根目錄
            if not os.path.isabs(scanner_path):
                scanner_path = str(Path(__file__).parent.parent / scanner_path)
            if not os.path.exists(scanner_path):
                logger.warning(f"Scanner JSON 不存在: {scanner_path}，使用預設 symbols")
                return Config.SYMBOLS

            with open(scanner_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            scan_time_str = data.get('scan_time', '')
            if scan_time_str:
                try:
                    scan_time = datetime.fromisoformat(scan_time_str.replace('Z', '+00:00'))
                    age_minutes = (datetime.now(timezone.utc) - scan_time).total_seconds() / 60
                    if age_minutes > Config.SCANNER_MAX_AGE_MINUTES:
                        logger.warning(f"Scanner 資料已過期 ({age_minutes:.0f} 分鐘 > {Config.SCANNER_MAX_AGE_MINUTES} 分鐘上限)，使用預設 symbols")
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
            logger.warning(f"Scanner JSON 載入失敗: {e}，使用預設 symbols")
            return Config.SYMBOLS

    # ==================== 訂單執行（委託 OrderExecutionEngine）====================

    def _futures_set_leverage(self, symbol: str) -> bool:
        """設置槓桿"""
        return self.execution_engine.set_leverage(symbol)

    def _futures_create_order(self, symbol: str, side: str, quantity: float) -> dict:
        """下市價單"""
        return self.execution_engine.create_order(symbol, side, quantity)

    @staticmethod
    def _extract_fill_price(order_result: dict, fallback_price: float) -> float:
        """
        從訂單回應取實際成交均價（avgPrice / average）。
        失敗或回傳 0 時使用 fallback（信號價），確保不影響現有邏輯。

        BinanceFuturesClient 路徑：result['avgPrice']（字串）
        CCXT 路徑：result['average']（float）
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
        """平倉"""
        return self.execution_engine.close_position(symbol, side, quantity)

    def _place_hard_stop_loss(self, symbol: str, side: str, size: float, stop_price: float) -> Optional[str]:
        """設置硬止損單，回傳 order ID"""
        return self.execution_engine.place_hard_stop_loss(symbol, side, size, stop_price)

    def _cancel_stop_loss_order(self, symbol: str, order_id: Optional[str]) -> bool:
        """取消止損單"""
        return self.execution_engine.cancel_stop_loss_order(symbol, order_id)

    def _update_hard_stop_loss(self, pm: PositionManager, new_stop: float):
        """更新硬止損單"""
        return self._refresh_stop_loss(pm, new_stop)

    # ==================== 信號掃描 ====================

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
        """計算所有活躍持倉的總風險佔比"""
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
            logger.warning(f"{symbol}{(' ' + label) if label else ''} 低於最小值")
            return None
        return size

    @staticmethod
    def _calculate_pnl(side: str, size: float, price: float, avg_entry: float) -> float:
        return calculate_pnl(side, size, price, avg_entry)

    @staticmethod
    def _build_log_base(event: str, trade_id: str, symbol: str, side: str) -> dict:
        return build_log_base(event, trade_id, symbol, side)

    def _check_total_risk(self, active_positions: List[PositionManager]) -> bool:
        """總風險檢查（改用 PositionManager）"""
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

        if Config.V6_DRY_RUN:
            balance = 10000.0
        else:
            balance = self.risk_manager.get_balance()
        if balance <= 0:
            return False
        return (total_risk / balance) <= Config.MAX_TOTAL_RISK

    # ==================== 開倉執行 ====================

    def _execute_trade(self, symbol: str, signal_details: Dict, signal_type: str,
                       tier_multiplier: float, df_signal: pd.DataFrame):
        """執行開倉"""
        try:
            if symbol in self.active_trades:
                return

            if getattr(Config, 'REGIME_ROUTER_ENABLED', False):
                strategy_name = signal_details.get('_router_strategy_name')
                if strategy_name is None:
                    logger.warning(
                        f"{symbol}: reject entry - router enabled but no selected strategy "
                        f"for signal_type={signal_type}"
                    )
                    return
            else:
                # Hard guard: unmapped signal types are not allowed to fall back.
                strategy_name = Config.SIGNAL_STRATEGY_MAP.get(signal_type)
                if strategy_name is None:
                    logger.warning(
                        f"{symbol}: reject entry - signal_type={signal_type} "
                        "is not mapped in SIGNAL_STRATEGY_MAP"
                    )
                    return

            if Config.V6_DRY_RUN:
                balance = 10000.0  # Dry run: mock balance
            else:
                balance = self.risk_manager.get_balance()
                if balance <= 0:
                    logger.error(f"{symbol}: 餘額不足")
                    return

            side = signal_details['side']
            entry_price = signal_details['entry_price']
            atr = signal_details.get('atr', 0)
            # V5.3 / V54: risk-based sizing
            # 2B 訊號直接用 stop_loss；EMA/VOL 訊號用 extreme + ATR 計算
            if side == 'LONG':
                extreme = signal_details.get('lowest_point', signal_details.get('stop_level'))
            else:
                extreme = signal_details.get('highest_point', signal_details.get('stop_level'))

            if extreme is not None:
                stop_loss = self.risk_manager.calculate_stop_loss(extreme, atr, side, df_signal)
            else:
                stop_loss = signal_details.get('stop_loss', signal_details.get('stop_level', entry_price))
            neckline = signal_details.get('neckline')

            position_size = self.risk_manager.calculate_position_size(
                symbol, balance, entry_price, stop_loss, tier_multiplier
            )
            if position_size <= 0:
                return

            # V5.3 equity cap：避免孤注一擲，但不再吃掉風控
            v53_notional = position_size * entry_price
            v53_cap_notional = balance * Config.V53_EQUITY_CAP_PERCENT
            if v53_notional > v53_cap_notional:
                capped_size = self.precision_handler.round_amount(symbol, v53_cap_notional / entry_price)
                logger.info(
                    f"{symbol}: V5.3 notional 截頂 "
                    f"${v53_notional:.2f} -> ${v53_cap_notional:.2f} "
                    f"(v53_equity_cap={Config.V53_EQUITY_CAP_PERCENT*100:.0f}%)"
                )
                position_size = capped_size

            # === Risk Guard: SL Distance Cap ===
            sl_distance_pct = abs(entry_price - stop_loss) / entry_price
            if sl_distance_pct > Config.MAX_SL_DISTANCE_PCT:
                logger.info(
                    f"{symbol}: 跳過（SL 距離 {sl_distance_pct:.1%} > 上限 "
                    f"{Config.MAX_SL_DISTANCE_PCT:.0%}，entry={entry_price} sl={stop_loss}）"
                )
                return

            # actual risk = capped size * SL distance（dry run 用 signal price）
            initial_r = position_size * abs(entry_price - stop_loss)

            total_risk_budget = balance * Config.MAX_TOTAL_RISK
            current_open_risk = self._calc_total_open_risk_amount()
            if current_open_risk + initial_r > total_risk_budget:
                remaining_risk_budget = total_risk_budget - current_open_risk
                if remaining_risk_budget <= 0:
                    logger.info(
                        f"{symbol}: skip entry, total risk budget exhausted "
                        f"(open=${current_open_risk:.2f} budget=${total_risk_budget:.2f})"
                    )
                    return

                sl_distance = abs(entry_price - stop_loss)
                shrunk_size = self.precision_handler.round_amount(
                    symbol,
                    remaining_risk_budget / sl_distance if sl_distance > 0 else 0.0,
                )
                if (
                    shrunk_size <= 0
                    or not self.precision_handler.check_limits(symbol, shrunk_size, entry_price)
                ):
                    logger.info(
                        f"{symbol}: skip entry, remaining risk budget ${remaining_risk_budget:.2f} "
                        "cannot support a valid minimum order"
                    )
                    return

                logger.info(
                    f"{symbol}: shrink size for total risk budget "
                    f"{position_size:.6f} -> {shrunk_size:.6f} "
                    f"(open=${current_open_risk:.2f} candidate=${initial_r:.2f} "
                    f"budget=${total_risk_budget:.2f})"
                )
                position_size = shrunk_size
                initial_r = position_size * sl_distance

            # === Dry run 模式 ===
            if Config.V6_DRY_RUN:
                logger.info(
                    f"[模擬] {symbol} {side} | 策略={signal_type} | "
                    f"倉位={position_size:.6f} @ ${entry_price:.2f} | "
                    f"止損=${stop_loss:.2f} | neckline={'$' + f'{neckline:.2f}' if neckline else '無'} | "
                    "滾倉=False"
                )
                # Dry run 也生成 trade_id 用於測試
                dry_trade_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '_' + symbol.replace('/', '')
                _trade_log({
                    **self._build_log_base('TRADE_OPEN', dry_trade_id, symbol, side),
                    'strategy': signal_type,
                    'tier': signal_details.get('signal_tier', '?'),
                    'size': f'{position_size:.6f}',
                    'entry': f'{entry_price:.2f}',
                    'sl': f'{stop_loss:.2f}',
                    'value': f'{position_size * entry_price:.2f}',
                    'risk': f'{initial_r:.2f}',
                    'pyramid': False,
                    'vol_ratio': f'{signal_details.get("vol_ratio", 0):.2f}',
                    'regime': signal_details.get('market_regime', 'UNKNOWN'),
                    'btc_trend': signal_details.get('btc_trend', 'UNKNOWN'),
                    'initial_r': f'{initial_r:.2f}',
                })
                return

            # === 實際下單 ===
            order_side = self._get_close_side(side)
            if BinanceFuturesClient.is_enabled():
                order_result = self._futures_create_order(symbol, order_side, position_size)
            else:
                order_result = self.exchange.create_order(
                    symbol=symbol, type='market', side=order_side.lower(), amount=position_size
                )

            # 捕捉實際成交均價（market order 可能有 slippage）
            fill_price = self._extract_fill_price(order_result, entry_price)
            if fill_price != entry_price:
                logger.info(
                    f"{symbol} 成交均價修正: 信號${entry_price:.4f} → 實際${fill_price:.4f}"
                )
            entry_price = fill_price
            # 用實際成交價重算 actual risk
            initial_r = position_size * abs(entry_price - stop_loss)

            logger.info(
                f"{symbol} {side} 開倉成功: {position_size:.6f} @ ${entry_price:.2f} | "
                f"止損=${stop_loss:.2f} 策略={signal_type} 等級={signal_details.get('signal_tier','?')} "
                f"量能={signal_details.get('vol_ratio',0):.2f}x 滾倉=False | "
                f"市場={signal_details.get('_market_reason','')} 趨勢={signal_details.get('_trend_desc','')} "
                f"MTF={signal_details.get('_mtf_reason','')}"
            )

            # 建立 PositionManager（strategy_name 已在入口 hard guard 確認）
            pm = PositionManager(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_size=position_size,
                strategy_name=strategy_name,
                neckline=neckline,
                equity_base=balance,
                initial_r=initial_r,
                signal_tier=signal_details.get('signal_tier', 'B'),
                signal_type=signal_type,
                market_regime=signal_details.get('market_regime', 'UNKNOWN'),
            )
            pm.atr = atr
            pm.entry_adx = signal_details.get('entry_adx')
            pm.fakeout_depth_atr = signal_details.get('fakeout_depth_atr')
            pm.trend_adx = signal_details.get('trend_adx')
            pm.mtf_aligned = signal_details.get('mtf_aligned')
            pm.volume_grade = signal_details.get('volume_grade')
            pm.tier_score = signal_details.get('tier_score')

            # --- BTC Trend Alignment (data collection) ---
            if "BTC" not in symbol:
                btc_trend = signal_details.get('btc_trend', 'UNKNOWN')
                if btc_trend in ("UNKNOWN", "RANGING"):
                    pm.btc_trend_aligned = None
                else:
                    pm.btc_trend_aligned = (side == btc_trend)
            else:
                pm.btc_trend_aligned = None

            # Structured trade log
            _trade_log({
                **self._build_log_base('TRADE_OPEN', pm.trade_id, symbol, side),
                'strategy': signal_type,
                'tier': signal_details.get('signal_tier', '?'),
                'size': f'{position_size:.6f}',
                'entry': f'{entry_price:.2f}',
                'sl': f'{stop_loss:.2f}',
                'value': f'{position_size * entry_price:.2f}',
                'risk': f'{initial_r:.2f}',
                'pyramid': False,
                'vol_ratio': f'{signal_details.get("vol_ratio", 0):.2f}',
                'regime': signal_details.get('market_regime', 'UNKNOWN'),
                'btc_trend': signal_details.get('btc_trend', 'UNKNOWN'),
                'initial_r': f'{initial_r:.2f}',
            })

            # 設置硬止損
            pm.stop_order_id = self._place_hard_stop_loss(symbol, side, position_size, stop_loss)

            self.active_trades[symbol] = pm

            # 持久化
            self._save_positions()

            # Telegram 通知
            TelegramNotifier.notify_signal(symbol, {
                **signal_details,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'is_v6': strategy_name == 'v6_pyramid',
                'strategy_name': strategy_name,
                'neckline': neckline,
            })

        except Exception as e:
            logger.error(f"{symbol} 開倉失敗: {e}")
            self.order_failed_symbols[symbol] = datetime.now(timezone.utc)

    # ==================== 持倉監控 ====================

    def monitor_positions(self):
        self.position_monitor.monitor_positions()

    def _fetch_exchange_stop_map(self) -> Dict[str, float]:
        """
        從交易所取得開放中的止損單。

        先嘗試 algo orders（正式網），若不支援（Demo Trading 回 404）
        再 fallback 到普通 openOrders 中的 STOP_MARKET 訂單。

        Returns:
            {symbol_id: trigger_price}，例如 {'BTCUSDT': 87500.0}
            查不到或 API 失敗回傳 {}
        """
        if not BinanceFuturesClient.is_enabled():
            return {}
        stop_map: Dict[str, float] = {}
        try:
            # 嘗試 algo orders（正式網支援）
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
            # algo endpoint 不支援（Demo Trading 回 404）→ fallback 到普通訂單
            logger.debug(f"[ADOPT] algo openOrders 不支援({response.status_code})，改查普通止損單")
        except Exception as e:
            logger.warning(f"[ADOPT] 查 algo 止損單異常: {e}")

        try:
            # Fallback：普通 openOrders 裡的 STOP_MARKET
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
            logger.warning(f"[ADOPT] 查普通止損單異常: {e}")

        return stop_map

    def _adopt_ghost_positions(self):
        """
        啟動後一次性接管幽靈倉位（exchange 有、positions.json 未記錄）。

        接管邏輯：
        1. 從交易所取 positions
        2. 跳過已追蹤的 symbol
        3. 查 algo 止損單 → 取得 stop_loss；若無，用入場價 × 2% 保守預設
        4. 建 PositionManager（V5.3 保守模式，is_v6_pyramid=False）
        5. 若無止損 → 補設硬止損
        6. 存入 active_trades + _save_positions()
        """
        if Config.V6_DRY_RUN:
            return

        exchange_positions = self.risk_manager.get_positions()
        if not exchange_positions:  # None 或 []
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

            # 轉 ccxt 格式：BTCUSDT → BTC/USDT
            ccxt_sym = sym_id[:-4] + '/' + sym_id[-4:] if sym_id.endswith('USDT') else sym_id

            # 已追蹤 → 跳過
            if ccxt_sym in self.active_trades:
                continue

            # 解析 side / size / entry
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
                logger.warning(f"[ADOPT] {ccxt_sym} entryPrice 無效，跳過")
                continue

            # 取得或預算止損
            stop_loss = stop_map.get(sym_id)
            stop_source = 'exchange'
            if stop_loss is None:
                fallback_pct = getattr(Config, 'GHOST_ADOPT_SL_PCT', 0.02)
                stop_loss = (
                    entry_price * (1 - fallback_pct) if side == 'LONG'
                    else entry_price * (1 + fallback_pct)
                )
                stop_source = f'fallback({fallback_pct * 100:.0f}%)'

            # 建 PositionManager（V5.3 保守模式，不做 pyramid 加倉）
            pm = PositionManager(
                symbol=ccxt_sym,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_size=position_size,
                strategy_name="v53_sop",
                initial_r=position_size * abs(entry_price - stop_loss),
            )
            pm.entry_time = datetime.now(timezone.utc)
            pm.highest_price = entry_price
            pm.lowest_price = entry_price

            # 若無止損單 → 補設
            if stop_map.get(sym_id) is None:
                try:
                    order_id = self.execution_engine.place_hard_stop_loss(
                        ccxt_sym, side, position_size, stop_loss
                    )
                    pm.stop_order_id = order_id
                    logger.info(f"[ADOPT] {ccxt_sym} 補設硬止損 @ ${stop_loss:.4f}")
                except Exception as e:
                    logger.warning(f"[ADOPT] {ccxt_sym} 補設止損失敗: {e}")

            self.active_trades[ccxt_sym] = pm
            adopted += 1
            logger.warning(
                f"[GHOST_ADOPTED] {ccxt_sym}: {side} size={position_size} "
                f"entry=${entry_price:.4f} sl=${stop_loss:.4f} "
                f"(stop_source={stop_source})"
            )

        if adopted > 0:
            self._save_positions()
            logger.warning(f"[ADOPT] 共接管 {adopted} 個幽靈倉位，已存入 positions.json")

    def _sync_exchange_positions(self):
        """
        交易所倉位 reconciliation（每次 monitor_positions 都執行）。

        四重防護：
        1. API 錯誤防護：get_positions 回 None 時跳過（不誤殺）
        2. 正向檢查：bot 有 / exchange 無 → hard_stop_hit
        3. Size 校驗：兩邊都有但數量不一致 → 告警
        4. 反向檢查：exchange 有 / bot 無 → 幽靈倉位告警
        """
        if Config.V6_DRY_RUN:
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
                        f"(差異 {abs(ex_amt - bot_amt):.6f})"
                    )

            for (symbol_id, side), ex_amt in exchange_map.items():
                if ex_amt > 0 and (symbol_id, side) not in internal_map:
                    logger.warning(
                        f"[GHOST_POSITION] {self._exchange_id_to_symbol(symbol_id)}: "
                        f"{side} {ex_amt:.6f}，但 bot 未追蹤！請手動檢查。"
                    )

            if hard_stop_detected:
                self._save_positions()

        except Exception as e:
            logger.warning(f"[SYNC] 交易所同步異常，跳過: {e}")

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

    def _handle_stage2(self, pm: PositionManager, current_price: float, df_1h, decision: dict = None):
        self.position_monitor.handle_stage2(pm, current_price, df_1h, decision=decision)

    def _handle_stage3(self, pm: PositionManager, current_price: float, df_1h, decision: dict = None):
        self.position_monitor.handle_stage3(pm, current_price, df_1h, decision=decision)

    def _handle_v53_reduce(self, pm: PositionManager, pct: int, label: str, current_price: float):
        self.position_monitor.handle_v53_reduce(pm, pct, label, current_price)

    # ==================== 啟動診斷 ====================

    def startup_diagnostics(self) -> bool:
        """啟動診斷"""
        logger.info("執行啟動診斷...")

        try:
            if Config.V6_DRY_RUN:
                balance = 10000.0
                logger.info(f"[模擬] 餘額: ${balance:.2f} USDT")
            else:
                balance = self.risk_manager.get_balance()
                logger.info(f"API 正常 | 餘額: ${balance:.2f} USDT")
            self.initial_balance = balance
        except Exception as e:
            logger.error(f"API 連線失敗: {e}")
            return False

        test_symbol = Config.SYMBOLS[0] if Config.SYMBOLS else 'BTC/USDT'
        df = self.fetch_ohlcv(test_symbol, Config.TIMEFRAME_SIGNAL, limit=50)
        if df.empty:
            logger.error(f"數據獲取失敗: {test_symbol}")
            return False
        logger.info(f"數據正常 | {test_symbol}: {len(df)} 根K線")

        # V6.0: 4H 數據測試
        df_4h = self.fetch_ohlcv(test_symbol, '4h', limit=20)
        if df_4h.empty:
            logger.warning("4H 數據獲取失敗（非關鍵）")
        else:
            logger.info(f"4H 數據正常 | {len(df_4h)} 根K線")

        # V6.0: Config 驗證
        try:
            Config.validate()
            logger.info("Config 驗證通過")
        except ValueError as e:
            logger.error(f"Config 驗證失敗: {e}")
            return False

        logger.info("啟動診斷通過")
        return True

    # ==================== 主循環 ====================

    def run(self):
        """主運行循環"""
        if not self.startup_diagnostics():
            logger.error("啟動診斷失敗，停止運行")
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
                logger.info("Hedge mode already enabled — grid trading ready")
            elif is_hedge is False:
                logger.info("Grid trading enabled — switching to hedge mode")
                if not self.futures_client.set_hedge_mode(True):
                    # Verify: re-query actual state
                    is_hedge = self.futures_client.get_position_mode()
                    if is_hedge is not True:
                        logger.error(
                            "無法啟用 hedge mode — grid trading 已停用"
                            "（有持倉時 Binance 不允許切換，需先平倉或手動在交易所啟用）"
                        )
                        Config.ENABLE_GRID_TRADING = False
            else:
                logger.warning("無法查詢 position mode — grid trading 已停用")
                Config.ENABLE_GRID_TRADING = False
            if Config.ENABLE_GRID_TRADING:
                try:
                    self.execution_engine.hedge_mode = self.futures_client.get_position_side_dual()
                except Exception as e:
                    logger.warning(f"Could not refresh hedge mode state after grid check: {e}")
                self._restore_grid_runtime_state()

        logger.info("機器人開始運行...\n")

        # 接管交易所有但 positions.json 未記錄的倉位（幽靈倉位恢復）
        self._adopt_ghost_positions()

        cycle = 0
        while True:
            try:
                cycle += 1
                logger.debug(f"[循環 #{cycle}]")

                self.scan_for_signals()
                self._monitor_grid_state()
                self._sync_exchange_positions()  # 每 cycle 都執行，active_trades 為空時也偵測幽靈倉位
                self.monitor_positions()
                self.telegram_handler.poll()

                logger.debug(f"休息 {Config.CHECK_INTERVAL} 秒...\n")
                time.sleep(Config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("使用者中斷，停止運行")
                self._save_positions()
                break
            except Exception as e:
                logger.error(f"循環 #{cycle} 錯誤: {e}")
                time.sleep(Config.CHECK_INTERVAL)


TradingBotV6 = TradingBot

# ==================== 入口 ====================
if __name__ == "__main__":
    import argparse

    # SIGTERM → KeyboardInterrupt（systemd stop 時 graceful flush positions）
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    parser = argparse.ArgumentParser(description='Trading Bot')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    # Runtime 目錄（.log/ 子目錄）
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / '.log'
    log_dir.mkdir(exist_ok=True)

    # 設定 logging
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

    # [TRADE] 日誌分流到 .log/trades.log
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

    # WARNING/ERROR 轉發到 Telegram（節流：同訊息 5 分鐘內不重複發送）
    class _TelegramLogHandler(logging.Handler):
        # 不轉發到 Telegram 的訊息（含以下字串即略過）
        _IGNORE_PATTERNS = [
            "Scanner JSON had no usable bot_symbols/hot_symbols",
            "Scanner JSON 中 hot_symbols 為空",
        ]

        def __init__(self):
            super().__init__(level=logging.WARNING)
            self._last_sent = {}  # message_key -> timestamp

        def emit(self, record):
            try:
                msg = self.format(record)
                if any(p in msg for p in self._IGNORE_PATTERNS):
                    return
                # 節流：取前 80 字元作 key，5 分鐘內同 key 不重複
                key = msg[:80]
                now = time.time()
                if now - self._last_sent.get(key, 0) < 300:
                    return
                self._last_sent[key] = now
                # 清理過期 key（避免記憶體洩漏）
                if len(self._last_sent) > 100:
                    cutoff = now - 300
                    self._last_sent = {k: v for k, v in self._last_sent.items() if v > cutoff}
                TelegramNotifier.notify_warning(msg)
            except Exception:
                pass  # 通知失敗不影響主程式

    _tg_handler = _TelegramLogHandler()
    _tg_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(_tg_handler)

    try:
        # bot_config.json 相對於專案根目錄（bot.py 的上層），不依賴 CWD
        config_path = str(Path(__file__).parent.parent / "bot_config.json")
        Config.load_from_json(config_path)
        if args.dry_run:
            Config.V6_DRY_RUN = True  # type: ignore[assignment]

        bot = TradingBot()
        bot.run()
    except Exception as e:
        logger.error(f"機器人啟動失敗: {e}")
        raise
