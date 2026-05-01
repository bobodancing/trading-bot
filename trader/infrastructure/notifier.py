"""Telegram notification helpers."""

import html
import logging
from typing import Dict, Optional

import requests

from trader.config import Config

logger = logging.getLogger(__name__)


STRATEGY_LABELS = {
    "legacy_manual": "Manual/Protective",
    "manual_protective": "Manual/Protective",
    "v8_atr_grid": "V8 ATR Grid",
}


def format_strategy_label(strategy_name: Optional[str] = None, _compat_flag: Optional[bool] = None) -> str:
    """Resolve strategy identifiers to stable Telegram labels."""
    if strategy_name:
        return STRATEGY_LABELS.get(strategy_name, strategy_name)
    return "Unknown"


class TelegramNotifier:
    """Small Telegram notifier used by runtime and grid modules."""

    @staticmethod
    def send_message(message: str):
        if not Config.TELEGRAM_ENABLED:
            return
        if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
            return

        try:
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': Config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
            }
            resp = requests.post(url, data=payload, timeout=10)
            if not resp.ok:
                logger.error(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
        except Exception as exc:
            logger.error(f"Telegram send failed: {exc}")

    @staticmethod
    def notify_signal(symbol: str, details: Dict):
        """Notify when an entry order is accepted."""
        esc = html.escape
        strength = str(details.get('signal_strength', 'unknown')).upper()
        tier = details.get('signal_tier', 'N/A')
        side = details.get('side', 'LONG')
        entry = float(details.get('entry_price', 0) or 0)
        stop = float(details.get('stop_loss', 0) or 0)
        risk = abs(entry - stop)
        if risk > 0:
            r15_val = entry + 1.5 * risk if side == 'LONG' else entry - 1.5 * risk
            r15 = f"${r15_val:.2f}"
        else:
            r15 = "N/A"

        strategy = format_strategy_label(details.get('strategy_id') or details.get('strategy_name'))
        market = esc(str(details.get('market_regime', 'N/A')))
        target = esc(str(details.get('target_ref', 'N/A')))

        lines = [
            f"<b>Signal Accepted - {esc(str(strength))} ({esc(str(side))})</b>",
            f"Tier: {esc(str(tier))}",
            "------------------------------",
            f"Strategy: {esc(strategy)}",
            f"Symbol: {esc(str(symbol))}",
            f"Side: {esc(str(side))}",
            f"Market regime: {market}",
            f"Volume ratio: {float(details.get('vol_ratio', 0) or 0):.2f}x",
            f"Entry: ${entry:.2f}",
            f"Stop: ${stop:.2f}",
            f"Target: {target}",
            f"Size: {float(details.get('position_size', 0) or 0):.6f}",
            f"1.5R: {r15}",
        ]

        if details.get('arbiter_label') is not None:
            conf = details.get('arbiter_confidence')
            try:
                conf_text = f"{float(conf):.2f}"
            except (TypeError, ValueError):
                conf_text = "N/A"
            lines.append(
                "Arbiter: "
                f"{esc(str(details.get('arbiter_label', 'N/A')))} "
                f"conf={conf_text} "
                f"reason={esc(str(details.get('arbiter_reason', 'N/A')))}"
            )

        TelegramNotifier.send_message("\n".join(lines))

    @staticmethod
    def notify_arbiter_block(symbol: str, details: Dict):
        """Notify when the arbiter blocks an otherwise eligible entry."""
        esc = html.escape
        conf = details.get('arbiter_confidence')
        try:
            conf_text = f"{float(conf):.2f}"
        except (TypeError, ValueError):
            conf_text = "N/A"

        msg = f"""
<b>Arbiter Block</b>
Symbol: {esc(str(symbol))}
Signal: {esc(str(details.get('signal_type', 'N/A')))} {esc(str(details.get('side', 'N/A')))}
Tier: {esc(str(details.get('signal_tier', 'N/A')))}
Arbiter: {esc(str(details.get('arbiter_label', 'N/A')))} conf={conf_text}
Reason: {esc(str(details.get('arbiter_reason', 'N/A')))}
Regime: {esc(str(details.get('market_regime', 'N/A')))}
        """
        TelegramNotifier.send_message(msg.strip())

    @staticmethod
    def notify_action(symbol: str, action: str, price: float, details: str = ""):
        msg = f"<b>{html.escape(action)}</b>\nSymbol: {html.escape(symbol)}\nPrice: ${price:.2f}"
        if details:
            msg += f"\n{html.escape(details)}"
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_warning(message: str):
        """Forward warning/error logs to Telegram."""
        msg = f"<b>Bot Alert</b>\n<pre>{html.escape(message[:500])}</pre>"
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_exit(symbol: str, details: dict):
        """Notify when a position exits."""
        side = details.get('side', '?')
        entry = float(details.get('entry_price', 0) or 0)
        reason = details.get('exit_reason', 'unknown')
        pnl = float(details.get('pnl_pct', 0) or 0)
        size = float(details.get('position_size', 0) or 0)
        msg = (
            f"<b>Exit {html.escape(symbol)} {html.escape(str(side))}</b>\n"
            f"Reason: {html.escape(str(reason))}\n"
            f"Entry: ${entry:.2f}\n"
            f"Size: {size:.6f}\n"
            f"PnL: {pnl:+.2f}%"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_regime_change(old_regime: str, new_regime: str, confirm_candles: int):
        msg = (
            f"<b>Regime: {html.escape(old_regime)} -> {html.escape(new_regime)}</b>\n"
            f"Confirmed bars: {confirm_candles}"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_activated(center: float, lower: float, upper: float, levels: int):
        msg = (
            "<b>Grid activated</b>\n"
            f"Center: {center:.0f}\n"
            f"Range: {lower:.0f} - {upper:.0f}\n"
            f"Levels: {levels * 2}"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_action(action_type: str, side: str, level: int, price: float, size: float):
        msg = (
            f"Grid L{abs(level)} {html.escape(action_type)} {html.escape(side)} "
            f"@ {price:.0f} (size: {size:.4f} BTC)"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_close(level: int, side: str, price: float, pnl: float):
        msg = (
            f"Grid L{abs(level)} {html.escape(side)} closed "
            f"@ {price:.0f} ({'+' if pnl >= 0 else ''}{pnl:.2f} USDT)"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_stopped(reason: str, details: str = ""):
        msg = f"<b>Grid stopped:</b> {html.escape(reason)}"
        if details:
            msg += f"\n{html.escape(details)}"
        TelegramNotifier.send_message(msg)


# Alias for compatibility with grid strategy code.
Notifier = TelegramNotifier
