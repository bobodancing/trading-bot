"""
BacktestBot factory ????conftest.py patch 璅∪?撱箇? TradingBot runtime嚗?
瘜典? MockDataProvider + MockOrderEngine??
"""
import os
import sys
import tempfile
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch


def _resolve_bot_root() -> Path:
    """Resolve the trading bot root for both isolated repos and legacy worktrees."""
    env = os.environ.get("TRADING_BOT_ROOT")
    if env:
        return Path(env).resolve()

    local_repo = Path(__file__).resolve().parents[2]
    if (local_repo / "trader" / "bot.py").exists():
        return local_repo

    workspace = local_repo.parent
    for candidate in (
        workspace / "projects" / "trading_bot" / ".worktrees" / "feat-regime-router",
        workspace / "projects" / "trading_bot" / ".worktrees" / "feat-grid",
        workspace / "projects" / "trading_bot",
    ):
        if (candidate / "trader" / "bot.py").exists():
            return candidate.resolve()

    return local_repo


# ???? ??? trading_bot ??import path ????
TRADING_BOT_ROOT = _resolve_bot_root()
sys.path.insert(0, str(TRADING_BOT_ROOT))

from trader.risk.manager import PrecisionHandler
from time_series_engine import TimeSeriesEngine
from mock_components import MockDataProvider, MockOrderEngine
from bot_compat import get_bot_class, get_config_class

logging.disable(logging.CRITICAL)  # ??葫?????bot log 頛詨?


def create_backtest_bot(
    tse: TimeSeriesEngine,
    mock_engine: MockOrderEngine,
    config_overrides: dict = None,
) -> object:
    """
    撱箇?摰?? mock ??TradingBot runtime嚗???澆?皜研??

    patch 皜??嚗?
    - _init_exchange ??MagicMock嚗????ccxt 蝬脰楝嚗?
    - PrecisionHandler._load_exchange_info ??no-op嚗????Binance HTTP嚗?
    - _restore_positions ??no-op嚗??頛????祕 positions.json嚗?
    - Config.POSITIONS_JSON_PATH ??tempfile
    - Config.DB_PATH ??tempfile

    瘜典?嚗?
    - bot.data_provider ??MockDataProvider(tse)
    - bot.execution_engine ??mock_engine
    - bot.exchange.fetch_ticker ????? tse.get_current_price()
    - bot.perf_db.record_trade ??MagicMock嚗???急??芾?閮?side_effect嚗?
    - bot.persistence ??MagicMock
    - bot._sync_exchange_positions ??MagicMock
    - Config.USE_SCANNER_SYMBOLS ??False
    - Config.DRY_RUN ??False (allows _execute_trade + _handle_close full paths)
    - bot.risk_manager.get_balance ??MagicMock(return_value=10000.0) (blocks API)
    """
    TradingBotClass = get_bot_class()
    Config = get_config_class()

    # 憟?? config overrides
    if config_overrides:
        for k, v in config_overrides.items():
            setattr(Config, k, v)

    mock_exchange = MagicMock()
    mock_exchange.load_markets.return_value = {}
    mock_exchange.markets = {}

    tmp_dir = tempfile.mkdtemp()
    pos_path = str(Path(tmp_dir) / "positions.json")
    db_path = str(Path(tmp_dir) / "perf.db")

    with patch.object(TradingBotClass, "_init_exchange", return_value=mock_exchange), \
         patch.object(PrecisionHandler, "_load_exchange_info"), \
         patch.object(TradingBotClass, "_restore_positions"), \
         patch("trader.bot.Config.POSITIONS_JSON_PATH", pos_path), \
         patch("trader.bot.Config.DB_PATH", db_path):
        bot = TradingBotClass()

    # 瘜典? mock ??辣
    bot.data_provider = MockDataProvider(tse)
    bot.execution_engine = mock_engine

    # fetch_ticker ??TSE ?嗅??寞?嚗?????
    bot.exchange.fetch_ticker = MagicMock(
        side_effect=lambda sym: {
            "last": tse.get_current_price(sym),
            "bid": tse.get_current_price(sym),
            "ask": tse.get_current_price(sym),
        }
    )

    # Telegram: TelegramNotifier 雿輻?????寞?嚗?elegramNotifier.notify_signal()嚗??
    # 銝???? self.notifier??onfig.TELEGRAM_ENABLED ??身 False嚗????HTTP 隢????

    # perf_db.record_trade 靽????MagicMock嚗?acktestEngine 閮?side_effect ?園?鈭斗?嚗?
    bot.perf_db.record_trade = MagicMock()

    # ??? persistence
    bot.persistence = MagicMock()

    # ??? exchange sync
    bot._sync_exchange_positions = MagicMock()

    # Backtest-only cache: BTC regime/trend candles update far slower than the
    # 1H scan loop. Reusing same-candle context keeps replay tractable without
    # changing runtime logic or look-ahead boundaries.
    orig_update_btc_regime_context = bot._update_btc_regime_context
    btc_regime_cache = {}

    def _cached_update_btc_regime_context():
        try:
            bars = tse.get_bars("BTC/USDT", Config.REGIME_TIMEFRAME, limit=1)
            candle_time = bars.index[-1] if not bars.empty else None
        except Exception:
            candle_time = None
        if candle_time is not None and candle_time in btc_regime_cache:
            context, snapshot = btc_regime_cache[candle_time]
            bot._btc_regime_context = dict(context)
            bot._regime_arbiter_snapshot = snapshot
            return bot._btc_regime_context
        context = orig_update_btc_regime_context()
        if candle_time is not None:
            btc_regime_cache[candle_time] = (
                dict(context),
                getattr(bot, "_regime_arbiter_snapshot", None),
            )
        return context

    bot._update_btc_regime_context = _cached_update_btc_regime_context

    orig_daily_context = bot.btc_context_manager.get_daily_btc_trend_context
    btc_daily_cache = {}

    def _cached_daily_context():
        try:
            bars = tse.get_bars("BTC/USDT", "1d", limit=1)
            candle_time = bars.index[-1] if not bars.empty else None
        except Exception:
            candle_time = None
        if candle_time is not None and candle_time in btc_daily_cache:
            return dict(btc_daily_cache[candle_time])
        context = orig_daily_context()
        if candle_time is not None:
            btc_daily_cache[candle_time] = dict(context)
        return context

    bot.btc_context_manager.get_daily_btc_trend_context = _cached_daily_context

    # ??葫?箏???Config.SYMBOLS嚗??霈? scanner JSON
    Config.USE_SCANNER_SYMBOLS = False

    # Mock get_balance() to block all Binance API calls for balance.
    # This lets us set DRY_RUN=False so _execute_trade() creates real
    # PositionManager instances and _handle_close() calls perf_db.record_trade().
    bot.risk_manager.get_balance = MagicMock(return_value=10000.0)

    # DRY_RUN must be False so _execute_trade and _handle_close run their
    # full code paths (create PositionManager, call perf_db.record_trade).
    Config.DRY_RUN = False

    return bot
