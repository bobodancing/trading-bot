"""Strategy runtime entry scanner.

The reset runtime keeps this object intentionally thin. Signal generation lives
inside strategy plugins; this class preserves cooldown checks and delegates the
entry pipeline to StrategyRuntime.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from trader.config import Config

logger = logging.getLogger(__name__)


class SignalScanner:
    def __init__(self, bot):
        self.bot = bot

    def scan_for_signals(self):
        self.bot.strategy_runtime.scan_for_entries()

    def check_cooldowns(self, symbol: str) -> bool:
        return self._check_cooldowns(symbol)

    def _check_cooldowns(self, symbol: str) -> bool:
        bot = self.bot

        if symbol in bot.recently_exited:
            hours = (datetime.now(timezone.utc) - bot.recently_exited[symbol]).total_seconds() / 3600
            if hours < 2:
                logger.debug("%s: skip recent exit cooldown %.1fh", symbol, hours)
                return False
            del bot.recently_exited[symbol]

        if symbol in bot.order_failed_symbols:
            hours = (datetime.now(timezone.utc) - bot.order_failed_symbols[symbol]).total_seconds() / 3600
            if hours < 1:
                logger.debug("%s: skip order failure cooldown", symbol)
                return False
            del bot.order_failed_symbols[symbol]

        if symbol in bot.early_exit_cooldown:
            hours = (datetime.now(timezone.utc) - bot.early_exit_cooldown[symbol]).total_seconds() / 3600
            if hours < Config.EARLY_EXIT_COOLDOWN_HOURS:
                logger.debug(
                    "%s: skip early exit cooldown %.1fh/%sh",
                    symbol,
                    hours,
                    Config.EARLY_EXIT_COOLDOWN_HOURS,
                )
                return False
            del bot.early_exit_cooldown[symbol]

        if Config.SYMBOL_LOSS_COOLDOWN_HOURS > 0:
            last_loss_exit = bot.perf_db.get_last_loss_exit_time(symbol)
            if last_loss_exit:
                try:
                    exit_dt = datetime.fromisoformat(last_loss_exit)
                    if exit_dt.tzinfo is None:
                        exit_dt = exit_dt.replace(tzinfo=timezone.utc)
                    hours_since = (datetime.now(timezone.utc) - exit_dt).total_seconds() / 3600
                    if hours_since < Config.SYMBOL_LOSS_COOLDOWN_HOURS:
                        logger.info(
                            "%s: skip last-loss cooldown %.1fh/%sh",
                            symbol,
                            hours_since,
                            Config.SYMBOL_LOSS_COOLDOWN_HOURS,
                        )
                        return False
                except (TypeError, ValueError):
                    pass

        return True
