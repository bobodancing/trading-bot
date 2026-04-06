"""
Shared utility functions -- extracted from bot.py (Phase 3, C6).

Common helpers used by bot.py, position_monitor.py, grid_manager.py, etc.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def trade_log(fields: dict):
    """Emit structured [TRADE] log line for log_summarizer.py"""
    parts = ' | '.join(f'{k}={v}' for k, v in fields.items())
    logger.info(f"[TRADE] {parts}")


def calculate_pnl(side: str, size: float, price: float, avg_entry: float) -> float:
    """Calculate unrealised/realised PnL for a position."""
    if side == 'LONG':
        return size * (price - avg_entry)
    return size * (avg_entry - price)


def get_close_side(side: str) -> str:
    """Return exchange order side for closing a position."""
    return 'BUY' if side == 'LONG' else 'SELL'


def drop_unfinished_candle(df):
    """Drop the last (current/unfinished) candle from OHLCV DataFrame.

    Both entry (signal_scanner) and exit (position_monitor) must use
    confirmed candles only; using live candle data causes alpha leak.
    """
    if df is not None and not df.empty and len(df) > 1:
        return df.iloc[:-1]
    return df


def build_log_base(event: str, trade_id: str, symbol: str, side: str) -> dict:
    """Build common fields for trade_log calls."""
    return {
        'event': event,
        'trade_id': trade_id,
        'ts': datetime.now(timezone.utc).isoformat(),
        'bot': 'v7.0',
        'symbol': symbol,
        'side': side,
    }
