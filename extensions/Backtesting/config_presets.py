"""Backtest-only Config override presets and validation.

Runtime defaults still live in trader.config.Config. Presets here are opt-in
per-run overlays used by Backtesting callers; they must not become a second
source of runtime defaults.
"""

from __future__ import annotations

import copy
import importlib
from collections.abc import Iterable, Mapping
from typing import Any

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
    # Current Config risk tier multipliers.
    "ENABLE_TIERED_ENTRY",
    "TIER_A_POSITION_MULT",
    "TIER_B_POSITION_MULT",
    "TIER_C_POSITION_MULT",
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
    "DEFAULT_STRATEGY_RISK_PROFILE",
    # Dormant grid lane, useful for explicit diagnostics only.
    "ENABLE_GRID_TRADING",
}

_PLUGIN_RUNTIME_DEFAULT_KEYS = (
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
    "STRATEGY_RUNTIME_ENABLED",
    "ENABLED_STRATEGIES",
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


def apply_strategy_params_override(
    catalog: Mapping[str, Mapping[str, Any]],
    strategy_params_override: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """
    Apply backtest-only plugin params to a catalog copy.

    This is intentionally separate from Config overrides: plugin params live in
    the research catalog, and second-pass backtests may only modify the per-run
    catalog copy returned by get_strategy_catalog().
    """
    scoped_catalog = copy.deepcopy(dict(catalog or {}))
    if strategy_params_override is not None and not isinstance(strategy_params_override, Mapping):
        raise ValueError("strategy_params_override must be a mapping")

    overrides = {}
    for strategy_id, params in (strategy_params_override or {}).items():
        if not isinstance(params, Mapping):
            raise ValueError(f"strategy_params_override for {strategy_id} must be a mapping")
        overrides[str(strategy_id)] = dict(params)
    if not overrides:
        return scoped_catalog

    for strategy_id, params in overrides.items():
        if strategy_id not in scoped_catalog:
            raise ValueError(f"Unknown strategy_params_override plugin id: {strategy_id}")
        entry = scoped_catalog[strategy_id]
        merged_params = dict(entry.get("params") or {})
        merged_params.update(params)
        _validate_strategy_params(strategy_id, entry, merged_params)
        entry["params"] = merged_params

    return scoped_catalog


def _validate_strategy_params(strategy_id: str, entry: Mapping[str, Any], params: Mapping[str, Any]) -> None:
    module_name = entry.get("module")
    class_name = entry.get("class")
    if not module_name or not class_name:
        raise ValueError(f"strategy catalog entry incomplete: {strategy_id}")

    module = importlib.import_module(str(module_name))
    plugin_cls = getattr(module, str(class_name))
    from trader.strategies import StrategyRegistry

    StrategyRegistry._validate_params(strategy_id, plugin_cls, params)


def _existing_defaults(keys: Iterable[str]) -> dict[str, Any]:
    Config = get_config_class()
    return {
        key: copy.deepcopy(getattr(Config, key))
        for key in keys
        if hasattr(Config, key)
    }


def plugin_runtime_defaults() -> dict[str, Any]:
    """Current plugin-runtime baseline copied from Config defaults."""
    return _existing_defaults(_PLUGIN_RUNTIME_DEFAULT_KEYS)


def diagnostic_arbiter_off() -> dict[str, Any]:
    """Diagnostic-only overlay for explaining zero-trade arbiter blocks."""
    overrides = plugin_runtime_defaults()
    overrides["REGIME_ARBITER_ENABLED"] = False
    return validate_backtest_overrides(overrides)


def explicit_symbol_universe(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Use BacktestConfig.symbols instead of scanner JSON for isolated runs."""
    scoped = dict(plugin_runtime_defaults() if overrides is None else overrides)
    scoped["USE_SCANNER_SYMBOLS"] = False
    return validate_backtest_overrides(scoped)


def strategy_id_allowlist(strategy_ids: Iterable[str]) -> dict[str, list[str]]:
    """Return BacktestConfig kwargs for a backtest-only strategy-id allowlist."""
    allowed = [str(item) for item in strategy_ids]
    if not allowed:
        raise ValueError("allowed_plugin_ids must contain at least one strategy id")
    return {"allowed_plugin_ids": list(dict.fromkeys(allowed))}
