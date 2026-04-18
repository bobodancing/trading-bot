"""Compatibility helpers for trading_bot main vs feat-grid layouts."""

from importlib import import_module
from types import ModuleType
from typing import Iterable


def import_optional(module_name: str) -> ModuleType | None:
    try:
        return import_module(module_name)
    except (ModuleNotFoundError, ImportError):
        return None


def import_first(module_names: Iterable[str]) -> ModuleType:
    last_error = None
    for module_name in module_names:
        try:
            return import_module(module_name)
        except ModuleNotFoundError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ModuleNotFoundError("No module names provided")


def get_bot_class():
    bot_module = import_module("trader.bot")
    bot_cls = getattr(bot_module, "TradingBot", None) or getattr(bot_module, "TradingBotV6", None)
    if bot_cls is None:
        raise AttributeError("trader.bot missing TradingBot/TradingBotV6")
    return bot_cls


def get_config_class():
    config_module = import_module("trader.config")
    config_cls = getattr(config_module, "Config", None) or getattr(config_module, "ConfigV6", None)
    if config_cls is None:
        raise AttributeError("trader.config missing Config/ConfigV6")
    return config_cls


def get_strategy_modules() -> dict[str, ModuleType]:
    return {}


def get_datetime_patch_modules() -> list[ModuleType]:
    modules: list[ModuleType] = [
        import_module("trader.bot"),
        import_module("trader.positions"),
    ]

    for module_name in (
        "trader.signal_scanner",
        "trader.position_monitor",
        "trader.grid_manager",
        "trader.utils",
    ):
        module = import_optional(module_name)
        if module is not None:
            modules.append(module)

    modules.extend(get_strategy_modules().values())
    return modules


def get_datetime_patch_module_names() -> set[str]:
    names = {module.__name__ for module in get_datetime_patch_modules()}
    names.update({
        "trader.bot",
        "trader.positions",
        "trader.signal_scanner",
        "trader.position_monitor",
        "trader.grid_manager",
        "trader.utils",
        "trader.strategy_runtime",
    })
    return names
