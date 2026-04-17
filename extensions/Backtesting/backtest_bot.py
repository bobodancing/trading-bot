"""
BacktestBot factory — 用 conftest.py patch 模式建立 TradingBot runtime，
注入 MockDataProvider + MockOrderEngine。
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


# ── 加入 trading_bot 到 import path ──
TRADING_BOT_ROOT = _resolve_bot_root()
sys.path.insert(0, str(TRADING_BOT_ROOT))

from trader.risk.manager import PrecisionHandler
from time_series_engine import TimeSeriesEngine
from mock_components import MockDataProvider, MockOrderEngine
from bot_compat import get_bot_class, get_config_class

logging.disable(logging.CRITICAL)  # 回測時關閉 bot log 輸出


def create_backtest_bot(
    tse: TimeSeriesEngine,
    mock_engine: MockOrderEngine,
    config_overrides: dict = None,
) -> object:
    """
    建立完全 mock 的 TradingBot runtime，用於回測。

    patch 清單：
    - _init_exchange → MagicMock（阻斷 ccxt 網路）
    - PrecisionHandler._load_exchange_info → no-op（阻斷 Binance HTTP）
    - _restore_positions → no-op（不載入真實 positions.json）
    - Config.POSITIONS_JSON_PATH → tempfile
    - Config.DB_PATH → tempfile

    注入：
    - bot.data_provider → MockDataProvider(tse)
    - bot.execution_engine → mock_engine
    - bot.exchange.fetch_ticker → 回傳 tse.get_current_price()
    - bot.perf_db.record_trade → MagicMock（呼叫方自行設 side_effect）
    - bot.persistence → MagicMock
    - bot._sync_exchange_positions → MagicMock
    - Config.USE_SCANNER_SYMBOLS → False
    - Config.V6_DRY_RUN → False (allows _execute_trade + _handle_close full paths)
    - bot.risk_manager.get_balance → MagicMock(return_value=10000.0) (blocks API)
    """
    TradingBotClass = get_bot_class()
    Config = get_config_class()

    # 套用 config overrides
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

    # 注入 mock 元件
    bot.data_provider = MockDataProvider(tse)
    bot.execution_engine = mock_engine

    # fetch_ticker → TSE 當前價格（動態）
    bot.exchange.fetch_ticker = MagicMock(
        side_effect=lambda sym: {
            "last": tse.get_current_price(sym),
            "bid": tse.get_current_price(sym),
            "ask": tse.get_current_price(sym),
        }
    )

    # Telegram: TelegramNotifier 使用靜態方法（TelegramNotifier.notify_signal()），
    # 不透過 self.notifier。Config.TELEGRAM_ENABLED 預設 False，不發 HTTP 請求。

    # perf_db.record_trade 保留為 MagicMock（BacktestEngine 設 side_effect 收集交易）
    bot.perf_db.record_trade = MagicMock()

    # 停用 persistence
    bot.persistence = MagicMock()

    # 停用 exchange sync
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

    # 回測固定用 Config.SYMBOLS，不讀 scanner JSON
    Config.USE_SCANNER_SYMBOLS = False

    # Mock get_balance() to block all Binance API calls for balance.
    # This lets us set V6_DRY_RUN=False so _execute_trade() creates real
    # PositionManager instances and _handle_close() calls perf_db.record_trade().
    bot.risk_manager.get_balance = MagicMock(return_value=10000.0)

    # V6_DRY_RUN must be False so _execute_trade and _handle_close run their
    # full code paths (create PositionManager, call perf_db.record_trade).
    Config.V6_DRY_RUN = False

    return bot
