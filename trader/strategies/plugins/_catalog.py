"""Plugin catalog for StrategyRuntime research cartridges.

Catalog presence is not runtime promotion. Runtime activation still requires
Config.STRATEGY_RUNTIME_ENABLED plus an explicit Config.ENABLED_STRATEGIES list.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from typing import Any


STRATEGY_CATALOG: dict[str, dict[str, Any]] = {
    "fixture_long": {
        "enabled": False,
        "module": "trader.strategies.plugins.fixture",
        "class": "FixtureLongStrategy",
        "params": {},
    },
    "fixture_exit": {
        "enabled": False,
        "module": "trader.strategies.plugins.fixture",
        "class": "FixtureExitStrategy",
        "params": {},
    },
    "macd_zero_line_btc_1d": {
        "enabled": False,
        "module": "trader.strategies.plugins.macd_zero_line",
        "class": "MacdZeroLineLongStrategy",
        "params": {"symbol": "BTC/USDT", "timeframe": "1d"},
    },
    "ema_cross_7_19_long_only": {
        "enabled": False,
        "module": "trader.strategies.plugins.ema_cross_7_19",
        "class": "EmaCross719LongOnlyStrategy",
        "params": {"timeframe": "4h", "atr_mult": 1.5},
    },
}


def get_strategy_catalog(enabled: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """Return a per-call catalog copy with selected plugin ids enabled."""
    catalog = copy.deepcopy(STRATEGY_CATALOG)
    for strategy_id in enabled or []:
        entry = catalog.get(str(strategy_id))
        if entry is not None:
            entry["enabled"] = True
    return catalog
