"""
Trading Bot Config

Single source of truth for runtime configuration. Values here are the
deployment defaults; only credentials are loaded externally from secrets.json.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class Config:
    """Runtime configuration for the strategy-plugin reset."""

    # ==================== Exchange / Account ====================

    EXCHANGE = 'binance'
    API_KEY = 'your_api_key_here'
    API_SECRET = 'your_api_secret_here'
    SANDBOX_MODE = True

    TRADING_MODE = 'future'
    TRADING_DIRECTION = 'both'
    LEVERAGE = 3
    USE_HARD_STOP_LOSS = False

    TELEGRAM_ENABLED = True
    TELEGRAM_BOT_TOKEN = ''
    TELEGRAM_CHAT_ID = ''

    # ==================== Universe / Scanner ====================

    SYMBOLS = ['BTC/USDT', 'ETH/USDT']

    # The promoted StrategyRuntime portfolio is fixed by Config + plugin scope.
    # Scanner output is runtime diagnostics, not a live universe selector.
    USE_SCANNER_SYMBOLS = False
    SCANNER_JSON_PATH = 'hot_symbols.json'
    RUNTIME_SCANNER_JSON_PATH = 'runtime_scanner.json'
    SCANNER_MAX_AGE_MINUTES = 30
    SCANNER_UNIVERSE_ENABLED = False
    SCANNER_UNIVERSE_JSON_PATH = 'scanner_universe.json'
    SCANNER_UNIVERSE_MAX_AGE_MINUTES = 30
    SCANNER_UNIVERSE_TOP_N = 20
    SCANNER_UNIVERSE_MIN_QUOTE_VOLUME_USD = 20_000_000

    # ==================== Signal & Indicators ====================

    TIMEFRAME_TREND = '1d'
    TIMEFRAME_SIGNAL = '1h'
    TIMEFRAME_MTF = '4h'

    EMA_TREND = 200
    MTF_EMA_FAST = 20
    MTF_EMA_SLOW = 50

    VOLUME_MA_PERIOD = 20
    ATR_PERIOD = 13
    ATR_MULTIPLIER = 1.5

    ENABLE_MTF_CONFIRMATION = True

    ENABLE_DYNAMIC_THRESHOLDS = True
    ADX_BASE_THRESHOLD = 15
    ADX_STRONG_THRESHOLD = 25
    ATR_QUIET_MULTIPLIER = 1.2
    ATR_NORMAL_MULTIPLIER = 1.5
    ATR_VOLATILE_MULTIPLIER = 2.0

    ENABLE_MARKET_FILTER = True
    ADX_THRESHOLD = 22
    ATR_SPIKE_MULTIPLIER = 2.0
    EMA_ENTANGLEMENT_THRESHOLD = 0.03

    ENABLE_TIERED_ENTRY = True
    TIER_A_POSITION_MULT = 0.7
    TIER_B_POSITION_MULT = 0.7
    TIER_C_POSITION_MULT = 0.5

    ENABLE_STRUCTURE_BREAK_EXIT = True
    STRUCTURE_BREAK_TOLERANCE = 0.005
    STRUCTURE_BREAK_LOOKBACK = 10
    ATR_QUIET_RATIO = 0.8
    ATR_VOLATILE_RATIO = 1.5

    # ==================== Regime / Arbiter / Router ====================

    REGIME_TIMEFRAME = '4h'
    REGIME_ADX_TRENDING = 25
    REGIME_ADX_RANGING = 20
    REGIME_BBW_RANGING_PCT = 25
    REGIME_BBW_SQUEEZE_PCT = 10
    REGIME_ATR_SQUEEZE_MULT = 1.1
    REGIME_ATR_TRENDING_MULT = 1.3
    REGIME_CONFIRM_CANDLES = 3
    REGIME_BBW_HISTORY = 50

    # R5 testnet candidate: Neutral Arbiter only; Macro overlay disabled.
    REGIME_ARBITER_ENABLED = True
    ARBITER_NEUTRAL_THRESHOLD = 0.50
    ARBITER_NEUTRAL_EXIT_THRESHOLD = 0.50
    ARBITER_NEUTRAL_MIN_BARS = 1
    MACRO_OVERLAY_ENABLED = False
    MACRO_STALLED_SIZE_MULT = 0.0
    MACRO_WEEKLY_EMA_SPREAD_THRESHOLD = 0.015

    REGIME_ROUTER_ENABLED = False
    REGIME_ROUTER_TRACE_ENABLED = True
    STRATEGY_ROUTER_POLICY = "fail_closed"

    # BTC 1D EMA20/50 trend gate; 0.0 blocks counter-trend entries entirely.
    BTC_TREND_FILTER_ENABLED = True
    BTC_TREND_FILTER_RUNTIME_MODE = "diagnostic"  # "diagnostic" | "enforce"
    BTC_COUNTER_TREND_MULT = 0.0
    BTC_EMA_RANGING_THRESHOLD = 0.005

    # ==================== Risk & Lifecycle ====================

    RISK_PER_TRADE = 0.017
    MAX_TOTAL_RISK = 0.0642
    MAX_POSITION_PERCENT = 0.1459
    # Hard cap on SL distance from entry; trips reject when ATR-derived SL exceeds this.
    MAX_SL_DISTANCE_PCT = 0.06

    CHECK_INTERVAL = 60
    MAX_RETRY = 3
    RETRY_DELAY = 5

    EARLY_EXIT_COOLDOWN_HOURS = 10
    # Per-symbol cooldown after a realized loss (perf_db backed; survives restart).
    SYMBOL_LOSS_COOLDOWN_HOURS = 24

    # ==================== Strategy Runtime ====================

    STRATEGY_RUNTIME_ENABLED = True
    STRATEGY_RUNTIME_SIDE_FILTER = "both"  # "long" | "short" | "both"
    ENABLED_STRATEGIES: list = [
        "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter",
        "donchian_range_fade_4h_range_width_cv_013",
        "donchian_range_fade_4h_range_width_cv_013_short",
    ]
    DEFAULT_STRATEGY_RISK_PROFILE = "central_default"

    # ==================== Persistence / Debug ====================

    POSITIONS_JSON_PATH = str(Path(__file__).resolve().parent.parent / '.log' / 'positions.json')
    DB_PATH = "performance.db"
    DRY_RUN = False
    STRATEGY_RUNTIME_OBSERVABILITY_ENABLED = True
    STRATEGY_RUNTIME_OBSERVABILITY_DIR = str(
        Path(__file__).resolve().parent.parent / '.log' / 'runtime_observability'
    )
    STRATEGY_RUNTIME_OBSERVABILITY_JSONL = "strategy_runtime_funnel.jsonl"
    STRATEGY_RUNTIME_OBSERVABILITY_LATEST = "strategy_runtime_latest.json"

    SECRET_KEYS = frozenset({
        "API_KEY",
        "API_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    })

    # ==================== Validation & Secrets ====================

    @classmethod
    def validate(cls):
        """Fail fast on contract violations that would corrupt runtime behavior."""
        if not isinstance(cls.ENABLED_STRATEGIES, list):
            raise ValueError(
                f"ENABLED_STRATEGIES must be a list, got {type(cls.ENABLED_STRATEGIES).__name__}"
            )
        side_filter = str(getattr(cls, "STRATEGY_RUNTIME_SIDE_FILTER", "")).lower()
        if side_filter not in {"long", "short", "both"}:
            raise ValueError(
                "STRATEGY_RUNTIME_SIDE_FILTER must be one of: long, short, both; "
                f"got {cls.STRATEGY_RUNTIME_SIDE_FILTER}"
            )
        if cls.STRATEGY_ROUTER_POLICY != "fail_closed":
            raise ValueError(
                f"STRATEGY_ROUTER_POLICY must be fail_closed, got {cls.STRATEGY_ROUTER_POLICY}"
            )
        btc_filter_mode = str(getattr(cls, "BTC_TREND_FILTER_RUNTIME_MODE", "")).lower()
        if btc_filter_mode not in {"diagnostic", "enforce"}:
            raise ValueError(
                "BTC_TREND_FILTER_RUNTIME_MODE must be one of: diagnostic, enforce; "
                f"got {cls.BTC_TREND_FILTER_RUNTIME_MODE}"
            )
        if not 0.0 <= float(cls.BTC_COUNTER_TREND_MULT) <= 1.0:
            raise ValueError(
                f"BTC_COUNTER_TREND_MULT must be within [0.0, 1.0], got {cls.BTC_COUNTER_TREND_MULT}"
            )
        for attr in ("ARBITER_NEUTRAL_THRESHOLD", "ARBITER_NEUTRAL_EXIT_THRESHOLD"):
            value = getattr(cls, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be within [0.0, 1.0], got {value}")
        for attr in ("TIER_A_POSITION_MULT", "TIER_B_POSITION_MULT", "TIER_C_POSITION_MULT"):
            value = getattr(cls, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be within [0.0, 1.0], got {value}")
        if cls.SCANNER_UNIVERSE_MAX_AGE_MINUTES <= 0:
            raise ValueError(
                f"SCANNER_UNIVERSE_MAX_AGE_MINUTES must be positive, "
                f"got {cls.SCANNER_UNIVERSE_MAX_AGE_MINUTES}"
            )
        if cls.SCANNER_UNIVERSE_TOP_N <= 0:
            raise ValueError(f"SCANNER_UNIVERSE_TOP_N must be positive, got {cls.SCANNER_UNIVERSE_TOP_N}")
        if cls.SCANNER_UNIVERSE_MIN_QUOTE_VOLUME_USD < 0:
            raise ValueError(
                f"SCANNER_UNIVERSE_MIN_QUOTE_VOLUME_USD must be non-negative, "
                f"got {cls.SCANNER_UNIVERSE_MIN_QUOTE_VOLUME_USD}"
            )
        if cls.STRATEGY_RUNTIME_OBSERVABILITY_ENABLED:
            for attr in (
                "STRATEGY_RUNTIME_OBSERVABILITY_DIR",
                "STRATEGY_RUNTIME_OBSERVABILITY_JSONL",
                "STRATEGY_RUNTIME_OBSERVABILITY_LATEST",
            ):
                if not str(getattr(cls, attr, "")).strip():
                    raise ValueError(f"{attr} must not be empty when runtime observability is enabled")
        return True

    @classmethod
    def load_secrets(cls, secrets_file: str = "secrets.json"):
        """Load credentials from an untracked secrets file; defaults stay if missing."""
        secrets_path = os.path.abspath(secrets_file)
        if not os.path.exists(secrets_path):
            logger.warning(f"Secrets file not found: {secrets_path}; using class defaults")
            cls.validate()
            return

        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets_data = json.load(f)
            loaded_keys = []
            ignored_keys = []
            for key, value in secrets_data.items():
                key_upper = str(key).upper()
                if key_upper not in cls.SECRET_KEYS:
                    ignored_keys.append(key_upper)
                    continue
                setattr(cls, key_upper, value)
                loaded_keys.append(key_upper)
            if ignored_keys:
                logger.warning(
                    "Ignored non-secret key(s) in secrets file: %s",
                    ", ".join(sorted(ignored_keys)),
                )
            logger.info(f"Loaded {len(loaded_keys)} secret key(s) from {secrets_path}")
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")

        cls.validate()
