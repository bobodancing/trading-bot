"""
Telegram 通知器

封裝所有 Telegram Bot 推送邏輯，從 v6/core.py 提取。
"""

import html
import logging
import requests
from typing import Dict

from trader.config import Config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 推送通知類"""

    @staticmethod
    def send_message(message: str):
        if not Config.TELEGRAM_ENABLED:
            return

        try:
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': Config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            resp = requests.post(url, data=payload, timeout=10)
            if not resp.ok:
                logger.error(f"Telegram 發送失敗: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Telegram 發送失敗: {e}")

    @staticmethod
    def notify_signal(symbol: str, details: Dict):
        """通知交易信號"""
        strength_emoji = {
            'explosive': '🔥🔥🔥',
            'strong': '💪💪',
            'moderate': '✅',
            'weak': '⚠️'
        }
        tier_emoji = {
            'A': '🏆',
            'B': '🥈',
            'C': '🥉'
        }
        strength = details.get('signal_strength', 'unknown')
        tier = details.get('signal_tier', 'B')
        emoji = strength_emoji.get(strength, '🚀')
        side = details.get('side', 'LONG')

        esc = html.escape
        market = esc(str(details.get('market_regime', 'N/A')))
        target = esc(str(details.get('target_ref', 'N/A')))

        entry = details.get('entry_price', 0)
        stop = details.get('stop_loss', 0)
        risk = abs(entry - stop)
        side_val = details.get('side', 'LONG')
        if risk > 0:
            r15_val = entry + 1.5 * risk if side_val == 'LONG' else entry - 1.5 * risk
            r15 = f"${r15_val:.2f}"
        else:
            r15 = "N/A"

        strategy = 'V6 Pyramid' if details.get('is_v6') else 'V53 SOP'

        msg = f"""
{emoji} <b>交易信號 - {strength.upper()} ({side})</b>
{tier_emoji.get(tier, '')} 信號等級: {tier}
──────────────────
策略: {strategy}
幣種: {esc(symbol)}
方向: {side}
市場狀態: {market}
量能強度: {details.get('vol_ratio', 0):.2f}x 均量
入場價: ${details.get('entry_price', 0):.2f}
止損價: ${details.get('stop_loss', 0):.2f}
目標位: {target}
倉位: {details.get('position_size', 0):.6f}
1.5R: {r15}
──────────────────
        """
        TelegramNotifier.send_message(msg.strip())

    @staticmethod
    def notify_action(symbol: str, action: str, price: float, details: str = ""):
        emoji_map = {
            '1.5R移損': '🛡',
            '目標減倉': '💰',
            '止損出場': '🚨',
            '結構破壞': '⚠️',
            '硬止損觸發': '🔴'
        }
        emoji = emoji_map.get(action, '🔔')

        msg = f"{emoji} <b>{html.escape(action)}</b>\n幣種: {html.escape(symbol)}\n價格: ${price:.2f}"
        if details:
            msg += f"\n{html.escape(details)}"
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_warning(message: str):
        """轉發 WARNING/ERROR 級別 log 到 Telegram（有節流）"""
        msg = f"<b>Bot Alert</b>\n<pre>{html.escape(message[:500])}</pre>"
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_exit(symbol: str, details: dict):
        """通知交易平倉"""
        side = details.get('side', '?')
        entry = details.get('entry_price', 0)
        reason = details.get('exit_reason', 'unknown')
        pnl = details.get('pnl_pct', 0)
        size = details.get('position_size', 0)
        emoji = '🟢' if pnl >= 0 else '🔴'
        msg = (
            f"{emoji} <b>平倉: {html.escape(symbol)} {html.escape(side)}</b>\n"
            f"原因: {html.escape(reason)}\n"
            f"入場: ${entry:.2f}\n"
            f"倉位: {size:.6f}\n"
            f"PnL: {pnl:+.2f}%"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_regime_change(old_regime: str, new_regime: str, confirm_candles: int):
        """Regime 狀態切換通知"""
        msg = (
            f"🔄 <b>Regime: {old_regime} → {new_regime}</b>\n"
            f"已確認 {confirm_candles} 根 4H K 線"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_activated(center: float, lower: float, upper: float, levels: int):
        msg = (
            f"📊 <b>Grid activated</b>\n"
            f"Center: {center:.0f}\n"
            f"Range: {lower:.0f} - {upper:.0f}\n"
            f"Levels: {levels * 2}"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_action(action_type: str, side: str, level: int, price: float, size: float):
        msg = (
            f"📊 Grid L{abs(level)} {action_type} {side} "
            f"@ {price:.0f} (size: {size:.4f} BTC)"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_close(level: int, side: str, price: float, pnl: float):
        emoji = "🟢" if pnl >= 0 else "🔴"
        msg = (
            f"{emoji} Grid L{abs(level)} {side} closed "
            f"@ {price:.0f} ({'+' if pnl >= 0 else ''}{pnl:.2f} USDT)"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_grid_stopped(reason: str, details: str = ""):
        msg = f"⚠️ <b>Grid stopped:</b> {reason}"
        if details:
            msg += f"\n{details}"
        TelegramNotifier.send_message(msg)


# Alias for compatibility with grid strategy code
Notifier = TelegramNotifier
