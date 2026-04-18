"""Backtest-only Config override presets and validation.

Runtime defaults still live in trader.config.Config. Presets here are opt-in
per-run overlays used by Backtesting callers; they must not become a second
source of runtime defaults.
"""

from __future__ import annotations

import copy
from typing import Iterable, Mapping, Any

from bot_compat import get_config_class


FORBIDDEN_BACKTEST_OVERRIDES = {
    "API_KEY",
    "API_SECRET",
    "STRATEGY_ROUTER_POLICY",
    "DB_PATH",
    "POSITIONS_JSON_PATH",
}

FORBIDDEN_BACKTEST_OVERRIDE_PREFIXES = ("TELEGRAM_",)

ALLOWED_BACKTEST_OVERRIDES = {
    # Backtest universe / loop controls.
    "SYMBOLS",
    "USE_SCANNER_SYMBOLS",
    "SYMBOL_LOSS_COOLDOWN_HOURS",
    # Risk sizing and execution constraints.
    "LEVERAGE",
    "USE_HARD_STOP_LOSS",
    "RISK_PER_TRADE",
    "MAX_TOTAL_RISK",
    "MAX_POSITION_PERCENT",
    "MAX_SL_DISTANCE_PCT",
    # Tier / legacy signal gates retained for compatibility with older plans.
    "ENABLE_TIERED_ENTRY",
    "V7_MIN_SIGNAL_TIER",
    "TIER_A_POSITION_MULT",
    "TIER_B_POSITION_MULT",
    "TIER_C_POSITION_MULT",
    "SIGNAL_STRATEGY_MAP",
    "ENABLE_EMA_PULLBACK",
    "ENABLE_VOLUME_BREAKOUT",
    # Regime, arbiter, and router behavior.
    "REGIME_TIMEFRAME",
    "REGIME_ADX_TRENDING",
    "REGIME_ADX_RANGING",
    "REGIME_BBW_RANGING_PCT",
    "REGIME_BBW_SQUEEZE_PCT",
    "REGIME_ATR_SQUEEZE_MULT",
    "REGIME_ATR_TRENDING_MULT",
    "REGIME_CONFIRM_CANDLES",
    "REGIME_BBW_HISTORY",
    "REGIME_ARBITER_ENABLED",
    "ARBITER_NEUTRAL_THRESHOLD",
    "ARBITER_NEUTRAL_EXIT_THRESHOLD",
    "ARBITER_NEUTRAL_MIN_BARS",
    "MACRO_OVERLAY_ENABLED",
    "MACRO_STALLED_SIZE_MULT",
    "MACRO_WEEKLY_EMA_SPREAD_THRESHOLD",
    "REGIME_ROUTER_ENABLED",
    "REGIME_ROUTER_TRACE_ENABLED",
    "BTC_TREND_FILTER_ENABLED",
    "BTC_COUNTER_TREND_MULT",
    "BTC_EMA_RANGING_THRESHOLD",
    # Strategy-plugin reset runtime.
    "STRATEGY_RUNTIME_ENABLED",
    "ENABLED_STRATEGIES",
    "STRATEGY_CATALOG",
    "DEFAULT_STRATEGY_RISK_PROFILE",
    # Dormant grid lane, useful for explicit diagnostics only.
    "ENABLE_GRID_TRADING",
}

_RUNTIME_PARITY_DEFAULT_KEYS = (
    "V7_MIN_SIGNAL_TIER",
    "REGIME_ARBITER_ENABLED",
    "ARBITER_NEUTRAL_THRESHOLD",
    "ARBITER_NEUTRAL_EXIT_THRESHOLD",
    "ARBITER_NEUTRAL_MIN_BARS",
    "MACRO_OVERLAY_ENABLED",
    "BTC_TREND_FILTER_ENABLED",
    "BTC_COUNTER_TREND_MULT",
    "USE_SCANNER_SYMBOLS",
    "REGIME_ROUTER_ENABLED",
    "REGIME_ROUTER_TRACE_ENABLED",
    "ENABLE_TIERED_ENTRY",
    "TIER_A_POSITION_MULT",
    "TIER_B_POSITION_MULT",
    "TIER_C_POSITION_MULT",
)


def _is_forbidden_override(key: str) -> bool:
    key_upper = key.upper()
    return (
        key_upper in FORBIDDEN_BACKTEST_OVERRIDES
        or any(key_upper.startswith(prefix) for prefix in FORBIDDEN_BACKTEST_OVERRIDE_PREFIXES)
    )


def validate_backtest_overrides(
    overrides: Mapping[str, Any] | None,
    *,
    config_cls=None,
) -> dict[str, Any]:
    """Validate and copy opt-in Config overrides before applying them."""
    checked = dict(overrides or {})
    if not checked:
        return {}

    forbidden = sorted(key for key in checked if _is_forbidden_override(str(key)))
    if forbidden:
        raise ValueError(f"Forbidden backtest Config override(s): {', '.join(forbidden)}")

    unknown = sorted(key for key in checked if key not in ALLOWED_BACKTEST_OVERRIDES)
    if unknown:
        raise ValueError(f"Unknown backtest Config override(s): {', '.join(unknown)}")

    Config = config_cls or get_config_class()
    missing = sorted(key for key in checked if not hasattr(Config, key))
    if missing:
        raise ValueError(f"Backtest Config override target does not exist: {', '.join(missing)}")

    return checked


def _existing_defaults(keys: Iterable[str]) -> dict[str, Any]:
    Config = get_config_class()
    return {
        key: copy.deepcopy(getattr(Config, key))
        for key in keys
        if hasattr(Config, key)
    }


def runtime_parity() -> dict[str, Any]:
    """R5-compatible promotion baseline, copied from current Config defaults."""
    return _existing_defaults(_RUNTIME_PARITY_DEFAULT_KEYS)


def diagnostic_arbiter_off() -> dict[str, Any]:
    """Diagnostic-only overlay for explaining zero-trade arbiter blocks."""
    overrides = runtime_parity()
    overrides["REGIME_ARBITER_ENABLED"] = False
    return validate_backtest_overrides(overrides)


def explicit_symbol_universe(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Use BacktestConfig.symbols instead of scanner JSON for isolated runs."""
    scoped = dict(runtime_parity() if overrides is None else overrides)
    scoped["USE_SCANNER_SYMBOLS"] = False
    return validate_backtest_overrides(scoped)


def lane_allowlist(signal_types: Iterable[str]) -> dict[str, list[str]]:
    """Return BacktestConfig kwargs for a backtest-only signal-type allowlist."""
    allowed = [str(item) for item in signal_types]
    if not allowed:
        raise ValueError("allowed_signal_types must contain at least one signal type")
    return {"allowed_signal_types": list(dict.fromkeys(allowed))}


def ema_lane_enabled() -> dict[str, list[str]]:
    return lane_allowlist(["EMA_PULLBACK"])


def vb_lane_enabled() -> dict[str, list[str]]:
    return lane_allowlist(["VOLUME_BREAKOUT"])
