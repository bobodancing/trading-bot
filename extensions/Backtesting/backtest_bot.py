"""Factory for a mocked, live-like TradingBot used by backtests."""
import os
import sys
import tempfile
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


# Make trader imports work from this standalone Backtesting workspace.
TRADING_BOT_ROOT = _resolve_bot_root()
sys.path.insert(0, str(TRADING_BOT_ROOT))

from trader.risk.manager import PrecisionHandler
from time_series_engine import TimeSeriesEngine
from mock_components import MockDataProvider, MockOrderEngine
from bot_compat import get_bot_class, get_config_class
from config_presets import validate_backtest_overrides
from plugin_id_filter import install_backtest_plugin_id_filter


def create_backtest_bot(
    tse: TimeSeriesEngine,
    mock_engine: MockOrderEngine,
    config_overrides: dict = None,
    *,
    allowed_plugin_ids=None,
) -> object:
    """
    Create a TradingBot wired to backtest data and mocked exchange I/O.

    Patched during construction:
    - _init_exchange returns a MagicMock instead of a real ccxt exchange.
    - PrecisionHandler._load_exchange_info is skipped to avoid Binance HTTP.
    - _restore_positions is skipped so tests do not read real positions.
    - Config.POSITIONS_JSON_PATH points at a temp file.
    - Config.DB_PATH points at a temp file.

    Backtest wiring after construction:
    - bot.data_provider is MockDataProvider(tse).
    - bot.execution_engine is mock_engine.
    - bot.exchange.fetch_ticker reads from the TimeSeriesEngine.
    - bot.perf_db.record_trade is a MagicMock until BacktestEngine replaces it.
    - bot.persistence is a MagicMock.
    - bot._sync_exchange_positions is a MagicMock.
    - Config.USE_SCANNER_SYMBOLS is forced false.
    - Config.DRY_RUN is forced false so execution and close paths create local
      PositionManager records and trade close payloads.
    - bot.risk_manager.get_balance is mocked to avoid account API calls.
    """
    TradingBotClass = get_bot_class()
    Config = get_config_class()

    # Apply validated per-run Config overrides.
    config_overrides = validate_backtest_overrides(config_overrides, config_cls=Config)
    if config_overrides:
        for k, v in config_overrides.items():
            setattr(Config, k, v)
    Config.validate()

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

    # Replace live data/execution components with deterministic backtest fakes.
    bot.data_provider = MockDataProvider(tse)
    bot.execution_engine = mock_engine

    # Keep ticker reads aligned with the current replay cursor.
    bot.exchange.fetch_ticker = MagicMock(
        side_effect=lambda sym: {
            "last": tse.get_current_price(sym),
            "bid": tse.get_current_price(sym),
            "ask": tse.get_current_price(sym),
        }
    )

    # Telegram is disabled below so notifier calls do not send HTTP requests.

    # BacktestEngine replaces this with a collector side effect.
    bot.perf_db.record_trade = MagicMock()

    # Prevent backtests from writing runtime persistence.
    bot.persistence = MagicMock()

    # Exchange state is already simulated by MockOrderEngine.
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

    # Backtests use explicit Config.SYMBOLS rather than scanner JSON.
    Config.USE_SCANNER_SYMBOLS = False

    # Backtest replay must never send real Telegram messages; user-provided
    # TELEGRAM_* overrides are still rejected by the injection contract.
    Config.TELEGRAM_ENABLED = False

    # Mock get_balance() to block all Binance API calls for balance.
    # This lets us set DRY_RUN=False so _execute_trade() creates real
    # PositionManager instances and _handle_close() calls perf_db.record_trade().
    bot.risk_manager.get_balance = MagicMock(return_value=10000.0)

    # DRY_RUN must be False so _execute_trade and _handle_close run their
    # full code paths (create PositionManager, call perf_db.record_trade).
    Config.DRY_RUN = False

    install_backtest_plugin_id_filter(bot, allowed_plugin_ids)

    return bot
