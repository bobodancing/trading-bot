"""
Trading Bot Config ??????????

Runtime configuration for the strategy-plugin reset.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Config:
    """
    Trading Bot ????????????

    ????????????????+ ??????????冽伍???
    """

    # ==================== V5.3 ?????? ====================

    # ????獢???
    EXCHANGE = 'binance'
    API_KEY = 'your_api_key_here'
    API_SECRET = 'your_api_secret_here'
    SANDBOX_MODE = True

    # ??????穿??
    TRADING_MODE = 'future'
    TRADING_DIRECTION = 'both'
    LEVERAGE = 3
    USE_HARD_STOP_LOSS = False

    # Telegram
    TELEGRAM_ENABLED = True
    TELEGRAM_BOT_TOKEN = ''
    TELEGRAM_CHAT_ID = ''

    # ???????
    SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

    # ?閰剁???豯??
    RISK_PER_TRADE = 0.017
    MAX_TOTAL_RISK = 0.05
    MAX_POSITIONS_PER_GROUP = 6
    MAX_POSITION_PERCENT = 0.146

    # ???????
    LOOKBACK_PERIOD = 20
    VOLUME_MA_PERIOD = 20
    ATR_PERIOD = 13
    ATR_MULTIPLIER = 1.5

    # ??????
    TIMEFRAME_TREND = '1d'
    TIMEFRAME_SIGNAL = '1h'
    EMA_TREND = 200

    # ????????銋??
    ENABLE_MTF_CONFIRMATION = True
    TIMEFRAME_MTF = '4h'
    MTF_EMA_FAST = 20
    MTF_EMA_SLOW = 50

    # ???????????
    ENABLE_DYNAMIC_THRESHOLDS = True
    ADX_BASE_THRESHOLD = 15
    ADX_STRONG_THRESHOLD = 25
    ATR_QUIET_MULTIPLIER = 1.2
    ATR_NORMAL_MULTIPLIER = 1.5
    ATR_VOLATILE_MULTIPLIER = 2.0

    # ???????賹???
    ENABLE_TIERED_ENTRY = True
    TIER_A_POSITION_MULT = 1.0
    TIER_B_POSITION_MULT = 0.7
    TIER_C_POSITION_MULT = 0.5

    # EMA ???????鞈??

    # ??????????鞈??

    # ????????
    ENABLE_MARKET_FILTER = True
    ADX_THRESHOLD = 22
    ATR_SPIKE_MULTIPLIER = 2.0
    EMA_ENTANGLEMENT_THRESHOLD = 0.02

    # ??????
    ENABLE_VOLUME_GRADING = True
    VOL_EXPLOSIVE_THRESHOLD = 2.5
    VOL_STRONG_THRESHOLD = 1.5
    VOL_MODERATE_THRESHOLD = 1.0
    VOL_MINIMUM_THRESHOLD = 0.7
    ACCEPT_WEAK_SIGNALS = False

    # Position lifecycle defaults
    CHECK_INTERVAL = 60
    MAX_RETRY = 3
    RETRY_DELAY = 5
    TREND_CACHE_HOURS = 4

    # Generic structure/risk context used by shared indicators and gates.
    ENABLE_STRUCTURE_BREAK_EXIT = True
    STRUCTURE_BREAK_TOLERANCE = 0.005
    STRUCTURE_BREAK_LOOKBACK = 10
    ATR_QUIET_RATIO = 0.8
    ATR_VOLATILE_RATIO = 1.5

    # ==================== Strategy Runtime ====================

    # ==================== Grid & Regime System ====================
    # Regime Engine
    ENABLE_GRID_TRADING = False
    REGIME_TIMEFRAME = '4h'             # Regime ??謚叟??? K ?????
    REGIME_ADX_TRENDING = 25            # ADX >= ???????TRENDING
    REGIME_ADX_RANGING = 20             # ADX < ???????RANGING candidate
    REGIME_BBW_RANGING_PCT = 25         # BBW < ???? N% ??? ??RANGING candidate
    REGIME_BBW_SQUEEZE_PCT = 10         # BBW < ???? N% ??? ??SQUEEZE candidate
    REGIME_ATR_SQUEEZE_MULT = 1.1      # ATR <= avg * mult ??SQUEEZE (?????悻?)
    REGIME_ATR_TRENDING_MULT = 1.3     # ATR > avg * mult ??TRENDING (??踝????
    REGIME_CONFIRM_CANDLES = 3          # ???????? N ??K ????遴狗?
    REGIME_BBW_HISTORY = 50             # BBW ?????????????

    # Regime Arbiter (R5 candidate: Neutral Arbiter only, Macro disabled)
    REGIME_ARBITER_ENABLED = True
    ARBITER_NEUTRAL_THRESHOLD = 0.50
    ARBITER_NEUTRAL_EXIT_THRESHOLD = 0.50
    ARBITER_NEUTRAL_MIN_BARS = 1
    MACRO_OVERLAY_ENABLED = False
    MACRO_STALLED_SIZE_MULT = 0.0
    MACRO_WEEKLY_EMA_SPREAD_THRESHOLD = 0.015
    REGIME_ROUTER_ENABLED = False
    STRATEGY_ROUTER_POLICY = "fail_closed"
    REGIME_ROUTER_TRACE_ENABLED = True

    # Capital Pool
    GRID_CAPITAL_RATIO = 0.30           # ?蟡???????芷??????
    TREND_CAPITAL_RATIO = 0.70          # ?豯歹???????芷??????

    # ATR Grid Parameters
    GRID_SMA_PERIOD = 20                # ?豲???SMA ???
    GRID_ATR_PERIOD = 14                # ATR ???
    GRID_ATR_MULTIPLIER = 2.5           # k ????????= SMA ??k*ATR
    GRID_LEVELS = 5                     # ???????????2*N ???
    GRID_WEIGHT_CENTER = 0.5            # ?豲???????????
    GRID_WEIGHT_EDGE = 1.5              # ????????????

    # Grid Risk
    GRID_MAX_TOTAL_RISK = 0.075         # ?蟡??????????迎??? 7.5%?????2.5% ?????
    GRID_RISK_PER_TRADE = 0.025         # ????閰剁?? 2.5%
    GRID_MAX_DRAWDOWN = 0.05            # ???????5% ???謢????擗?
    GRID_MAX_NOTIONAL = 0.0             # ??????嚗???擗?0 = grid_balance * LEVERAGE??
    GRID_COOLDOWN_HOURS = 6             # ???????????
    GRID_CONVERGE_TIMEOUT_HOURS = 72    # ?????穿????????????????????????恬?????
    GRID_RESET_DRIFT_RATIO = 0.5       # SMA ???堊?????????* spacing ??reset

    # ?撖???擗??????????????????
    EARLY_EXIT_COOLDOWN_HOURS = 10

    # === Risk Guard V1 ===

    # BTC ?豯歹??????????BTC ?豯歹???????????????.0 = ?????擗??.5 = ?????
    # ????????TC/USDT 1D EMA20 vs EMA50
    BTC_TREND_FILTER_ENABLED = True
    BTC_COUNTER_TREND_MULT = 0.0  # 0.0 = ??擗??????
    BTC_EMA_RANGING_THRESHOLD = 0.005  # BTC EMA20/50 ??魂馳? < 0.5% ??RANGING ???????擗???????

    # SL ????????? entry price ????????
    # ?????軋?????????????豲????????豰???謘???????????
    MAX_SL_DISTANCE_PCT = 0.06  # 6%

    # ???????????????
    # ??symbol ??????????????????????????????
    # ????????? perf_db ??凋????estart ??????
    SYMBOL_LOSS_COOLDOWN_HOURS = 24
    STRATEGY_RUNTIME_ENABLED = False
    ENABLED_STRATEGIES: list = []
    DEFAULT_STRATEGY_RISK_PROFILE = "central_default"

    # ????????

    # Signal ??Strategy ????????????????鞈芰??????+ register class??
    # Strategy plugins are disabled unless explicitly enabled in the catalog.
    STRATEGY_CATALOG: dict = {
        "fixture_long": {"enabled": False, "module": "trader.strategies.plugins.fixture", "class": "FixtureLongStrategy", "params": {}},
        "fixture_exit": {"enabled": False, "module": "trader.strategies.plugins.fixture", "class": "FixtureExitStrategy", "params": {}},
        "macd_zero_line_btc_1d": {
            "enabled": False,
            "module": "trader.strategies.plugins.macd_zero_line",
            "class": "MacdZeroLineLongStrategy",
            "params": {"symbol": "BTC/USDT", "timeframe": "1d"},
        },
    }

    # Debug & ???
    DRY_RUN = False

    # --- Strategy ---
    LEGACY_STRATEGY_SELECTOR_REMOVED = True

    # ==================== Persistence ====================

    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    _LOG_DIR = str(Path(__file__).resolve().parent.parent / '.log')

    POSITIONS_JSON_PATH = str(Path(__file__).resolve().parent.parent / '.log' / 'positions.json')
    LOG_FILE_PATH = str(Path(__file__).resolve().parent.parent / '.log' / 'bot.log')
    AUTO_BACKUP_ON_STAGE_CHANGE = True
    DB_PATH = "performance.db"

    # ==================== Scanner ??? ====================

    USE_SCANNER_SYMBOLS = True
    SCANNER_JSON_PATH = 'hot_symbols.json'
    SCANNER_MAX_AGE_MINUTES = 60

    # ==================== Config Validation ====================

    @classmethod
    def validate(cls):
        """Validate strategy-runtime reset config."""
        if not isinstance(cls.ENABLED_STRATEGIES, list):
            raise ValueError(
                f"ENABLED_STRATEGIES must be a list, got {type(cls.ENABLED_STRATEGIES).__name__}"
            )
        if not isinstance(cls.STRATEGY_CATALOG, dict):
            raise ValueError(
                f"STRATEGY_CATALOG must be a dict, got {type(cls.STRATEGY_CATALOG).__name__}"
            )
        if cls.STRATEGY_ROUTER_POLICY != "fail_closed":
            raise ValueError(
                f"STRATEGY_ROUTER_POLICY must be fail_closed, got {cls.STRATEGY_ROUTER_POLICY}"
            )
        return True
    @classmethod
    def load_from_json(cls, config_file: str = "bot_config.json"):
        """Load JSON config overrides."""
        if not os.path.exists(config_file):
            logger.warning(f"Config file not found: {config_file}; using class defaults")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            loaded_count = 0
            unknown_keys = []
            replace_dict_keys = {"STRATEGY_CATALOG"}
            for json_key, value in config_data.items():
                attr_name = json_key.upper()
                if hasattr(cls, attr_name):
                    current = getattr(cls, attr_name)
                    # Most dicts merge for backward compatibility; routing maps replace to avoid stale signals.
                    if isinstance(current, dict) and isinstance(value, dict):
                        if attr_name in replace_dict_keys:
                            value = dict(value)
                        else:
                            current.update(value)
                            value = current
                    setattr(cls, attr_name, value)
                    loaded_count += 1
                else:
                    unknown_keys.append(json_key)

            logger.info(f"Loaded {loaded_count} config key(s) from {config_file}")
            if unknown_keys:
                logger.debug(f"Ignored unknown config key(s): {unknown_keys}")

        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            logger.info("Using class defaults")
            return

        # --- ??? secrets.json ---
        config_dir = os.path.dirname(os.path.abspath(config_file))
        secrets_path = os.path.join(config_dir, "secrets.json")
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets_data = json.load(f)
                for key, value in secrets_data.items():
                    attr_name = key.upper()
                    setattr(cls, attr_name, value)
                logger.info(f"Loaded {len(secrets_data)} secret key(s) from {secrets_path}")
            except Exception as e:
                logger.error(f"Failed to load secrets: {e}")
        else:
            logger.warning(f"Secrets file not found: {secrets_path}; using class defaults")

        # ???????????
        try:
            cls.validate()
        except ValueError as e:
            logger.error(f"??Config validation failed: {e}")
            raise


# Alias for convenience
