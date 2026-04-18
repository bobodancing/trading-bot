"""Telegram command polling handler.

The handler is optional and must never interrupt the trading loop.
"""

import html
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

import requests

from trader.config import Config
from trader.infrastructure.notifier import format_strategy_label

logger = logging.getLogger(__name__)


class TelegramCommandHandler:
    """Polling Telegram command handler."""

    def __init__(self, bot):
        """Initialize with a TradingBot-like object."""
        self.bot = bot
        self.last_update_id = 0
        self.base_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"

    def poll(self):
        """Poll Telegram once."""
        if not Config.TELEGRAM_ENABLED:
            return

        try:
            updates = self._get_updates()
            for update in updates:
                self._handle_update(update)
        except Exception as exc:
            logger.debug("Telegram poll failed: %s", exc)

    def _get_updates(self) -> list:
        """Fetch pending updates without blocking."""
        url = f"{self.base_url}/getUpdates"
        params = {
            'offset': self.last_update_id + 1,
            'timeout': 0,
            'allowed_updates': '["message"]',
        }
        resp = requests.get(url, params=params, timeout=5)
        if not resp.ok:
            return []

        data = resp.json()
        return data.get('result', [])

    def _handle_update(self, update: dict):
        """Handle one Telegram update."""
        update_id = update.get('update_id', 0)
        if update_id > self.last_update_id:
            self.last_update_id = update_id

        message = update.get('message', {})
        chat_id = str(message.get('chat', {}).get('id', ''))
        text = message.get('text', '').strip()

        # Ignore messages from any chat except the configured control chat.
        if chat_id != str(Config.TELEGRAM_CHAT_ID):
            return

        if not text.startswith('/'):
            return

        cmd = text.split()[0].lower()
        # Support commands sent as /positions@botname.
        cmd = cmd.split('@')[0]

        handlers = {
            '/positions': self._cmd_positions,
            '/status': self._cmd_status,
            '/balance': self._cmd_balance,
            '/help': self._cmd_help,
        }

        handler = handlers.get(cmd)
        if handler:
            try:
                reply = handler()
                self._send_reply(chat_id, reply)
            except Exception as exc:
                logger.error("Telegram command %s failed: %s", cmd, exc)
                self._send_reply(chat_id, f"<b>Error:</b> {html.escape(str(exc))}")

    def _send_reply(self, chat_id: str, text: str):
        """Send an HTML-formatted reply."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
        }
        try:
            resp = requests.post(url, data=payload, timeout=10)
            if not resp.ok:
                logger.error("Telegram send failed: %s", resp.status_code)
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)

    def _strategy_label(self, pm) -> str:
        strategy_id = getattr(pm, 'strategy_id', None)
        if not isinstance(strategy_id, str) or not strategy_id:
            strategy_id = getattr(pm, 'strategy_name', None)
        if not isinstance(strategy_id, str) or not strategy_id:
            strategy_id = None
        return format_strategy_label(strategy_id)

    def _cmd_positions(self) -> str:
        """Render open positions."""
        trades = self.bot.active_trades
        if not trades:
            return "<b>No open positions</b>"

        lines = [f"<b>Open Positions ({len(trades)})</b>", "------------------------------"]

        for symbol, pm in trades.items():
            now = datetime.now(timezone.utc)
            hold_hours = (now - pm.entry_time).total_seconds() / 3600
            strategy = self._strategy_label(pm)

            # Approximate MFE from the local position manager highs/lows.
            if pm.side == 'LONG':
                pnl_pct = (pm.highest_price - pm.avg_entry) / pm.avg_entry * 100
            else:
                pnl_pct = (pm.avg_entry - pm.lowest_price) / pm.avg_entry * 100
            pnl_prefix = '+' if pnl_pct >= 0 else ''

            lines.append(
                f"\n<b>{html.escape(symbol)}</b> {pm.side} ({strategy})\n"
                f"  Entry: ${pm.avg_entry:.4f}\n"
                f"  Stop: ${pm.current_sl:.4f}\n"
                f"  Size: {pm.total_size:.6f}\n"
                f"  Stage: {pm.stage}\n"
                f"  Tier: {pm.signal_tier}\n"
                f"  Hold: {hold_hours:.1f}h\n"
                f"  MFE: {pnl_prefix}{pnl_pct:.2f}%"
            )

        return "\n".join(lines)

    def _cmd_status(self) -> str:
        """Render bot status."""
        trades = self.bot.active_trades
        active_count = len(trades)

        start_time = getattr(self.bot, '_start_time', None)
        if start_time:
            uptime_hours = (datetime.now(timezone.utc) - start_time).total_seconds() / 3600
            uptime_str = f"{uptime_hours:.1f}h"
        else:
            uptime_str = "N/A"

        counts = Counter(self._strategy_label(pm) for pm in trades.values())
        label_order = [
            "Manual/Protective",
            "V8 ATR Grid",
        ]
        parts = [f"{label}: {counts[label]}" for label in label_order if counts.get(label)]
        extra_labels = sorted(label for label in counts.keys() if label not in label_order)
        parts.extend(f"{label}: {counts[label]}" for label in extra_labels)
        distribution = " | ".join(parts) if parts else "None"

        arbiter_enabled = getattr(Config, 'REGIME_ARBITER_ENABLED', False) is True
        macro_enabled = getattr(Config, 'MACRO_OVERLAY_ENABLED', False) is True
        threshold = getattr(Config, 'ARBITER_NEUTRAL_THRESHOLD', None)
        try:
            threshold_text = f"{float(threshold):.2f}"
        except (TypeError, ValueError):
            threshold_text = "N/A"

        snapshot = getattr(self.bot, '_regime_arbiter_snapshot', None)
        snap_label = getattr(snapshot, 'label', None)
        snap_conf = getattr(snapshot, 'confidence', None)
        if isinstance(snap_label, str) and isinstance(snap_conf, (int, float)):
            snapshot_text = f"{snap_label} conf={snap_conf:.2f}"
        else:
            snapshot_text = "N/A"

        lines = [
            "<b>Bot Status</b>",
            "------------------------------",
            f"Uptime: {uptime_str}",
            f"Active positions: {active_count}",
            f"Strategy mix: {distribution}",
            f"Arbiter: {'ON' if arbiter_enabled else 'OFF'} | Neutral<{threshold_text} | snapshot={snapshot_text}",
            f"Macro Overlay: {'ON' if macro_enabled else 'OFF'}",
            f"Symbols: {len(Config.SYMBOLS)}",
            f"DRY RUN: {'Yes' if Config.DRY_RUN else 'No'}",
        ]

        return "\n".join(lines)

    def _cmd_balance(self) -> str:
        """Render account balance."""
        try:
            if Config.DRY_RUN:
                balance = 10000.0
            else:
                balance = self.bot.risk_manager.get_balance()
        except Exception:
            balance = 0.0

        initial = getattr(self.bot, 'initial_balance', None)
        pnl_line = ""
        if initial and initial > 0:
            pnl = balance - initial
            pnl_pct = pnl / initial * 100
            pnl_prefix = '+' if pnl >= 0 else ''
            pnl_line = f"\nPnL: {pnl_prefix}${pnl:.2f} ({pnl_prefix}{pnl_pct:.2f}%)"

        lines = [
            "<b>Balance</b>",
            "------------------------------",
            f"Balance: ${balance:.2f} USDT",
            pnl_line if pnl_line else "",
        ]

        return "\n".join(line for line in lines if line)

    def _cmd_help(self) -> str:
        """Return Telegram command help."""
        return (
            "<b>Commands</b>\n"
            "/positions - show open positions\n"
            "/status - show bot status\n"
            "/balance - show account balance\n"
            "/help - show this help"
        )
