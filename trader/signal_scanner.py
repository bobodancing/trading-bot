"""
Signal scanner -- extracted from bot.py (Phase 3).

Scans configured symbols for trading signals (2B, EMA_PULLBACK, VOLUME_BREAKOUT),
applies filters (trend, MTF, BTC trend, tier, risk), and dispatches to _execute_trade.
"""

import logging
from datetime import datetime, timezone

import pandas as pd

from trader.config import Config
from trader.indicators.technical import (
    TechnicalAnalysis,
    MTFConfirmation,
    MarketFilter,
)
from trader.risk.manager import SignalTierSystem
from trader.signals import detect_2b_with_pivots, detect_ema_pullback, detect_volume_breakout
from trader.utils import drop_unfinished_candle

logger = logging.getLogger(__name__)


class SignalScanner:
    """Scans symbols for entry signals, applies all filters, dispatches trades."""

    def __init__(self, bot):
        self.bot = bot

    def scan_for_signals(self):
        """Scan all configured symbols for trading signals."""
        bot = self.bot
        symbols = bot.load_scanner_results() if Config.USE_SCANNER_SYMBOLS else Config.SYMBOLS
        logger.debug(f"Scanning {len(symbols)} symbols...")

        bot._btc_regime_context = {}
        bot._btc_trend_context = {}

        # RegimeEngine routing (only when grid trading enabled)
        if Config.ENABLE_GRID_TRADING:
            btc_regime_context = bot._update_btc_regime_context()
            regime = btc_regime_context.get('regime')
            if regime == "RANGING":
                return
            elif regime == "SQUEEZE":
                if bot.grid_engine.state and not bot.grid_engine.state.converging:
                    bot.grid_engine.converge(market_ts=bot._get_regime_market_ts())
                return
            elif regime == "TRENDING" and bot.grid_engine.state:
                if not bot.grid_engine.state.converging:
                    bot.grid_engine.converge(market_ts=bot._get_regime_market_ts())
                return

        if Config.BTC_TREND_FILTER_ENABLED:
            bot._btc_trend_context = bot._resolve_btc_trend_context(log_event=True)

        for symbol in symbols:
            try:
                if symbol in bot.active_trades:
                    t = bot.active_trades[symbol]
                    logger.debug(f"{symbol}: skip (active {t.side}/stage{t.stage})")
                    continue

                if not self._check_cooldowns(symbol):
                    continue

                # Total risk check
                active_list = list(bot.active_trades.values())
                if not bot._check_total_risk(active_list):
                    logger.debug("Total risk limit reached, stop scanning")
                    break

                # Fetch data
                df_trend = bot.fetch_ohlcv(symbol, Config.TIMEFRAME_TREND, limit=250)
                df_signal = bot.fetch_ohlcv(symbol, Config.TIMEFRAME_SIGNAL, limit=100)
                df_mtf = pd.DataFrame()
                if Config.ENABLE_MTF_CONFIRMATION:
                    df_mtf = bot.fetch_ohlcv(symbol, Config.TIMEFRAME_MTF, limit=100)

                if df_trend.empty or len(df_trend) < 100:
                    logger.debug(f"{symbol}: skip (trend data insufficient: {len(df_trend) if not df_trend.empty else 0})")
                    continue
                if df_signal.empty or len(df_signal) < 50:
                    logger.debug(f"{symbol}: skip (signal data insufficient: {len(df_signal) if not df_signal.empty else 0})")
                    continue

                df_trend = TechnicalAnalysis.calculate_indicators(df_trend)
                df_signal = TechnicalAnalysis.calculate_indicators(df_signal)
                if not df_mtf.empty:
                    df_mtf = TechnicalAnalysis.calculate_indicators(df_mtf)

                # Drop current unclosed candle (confirmed candle only)
                df_signal = drop_unfinished_candle(df_signal)

                # Market filter
                market_ok, market_reason, is_strong_market = MarketFilter.check_market_condition(df_trend, symbol)
                if not market_ok:
                    logger.info(f"{symbol}: skip (market filter: {market_reason})")
                    continue

                # Multi-strategy signal scan
                signals_found = []

                has_2b, details_2b = detect_2b_with_pivots(
                    df_signal,
                    left_bars=Config.SWING_LEFT_BARS,
                    right_bars=Config.SWING_RIGHT_BARS,
                    vol_minimum_threshold=Config.VOL_MINIMUM_THRESHOLD,
                    accept_weak_signals=Config.ACCEPT_WEAK_SIGNALS,
                    enable_volume_grading=Config.ENABLE_VOLUME_GRADING,
                    vol_explosive_threshold=Config.VOL_EXPLOSIVE_THRESHOLD,
                    vol_strong_threshold=Config.VOL_STRONG_THRESHOLD,
                    vol_moderate_threshold=Config.VOL_MODERATE_THRESHOLD,
                    min_fakeout_atr=Config.MIN_FAKEOUT_ATR,
                )
                if has_2b and details_2b is not None:
                    details_2b['signal_type'] = '2B'
                    signals_found.append(('2B', details_2b))

                if Config.ENABLE_EMA_PULLBACK:
                    has_pb, details_pb = detect_ema_pullback(
                        df_signal,
                        ema_pullback_threshold=Config.EMA_PULLBACK_THRESHOLD,
                    )
                    if has_pb and details_pb is not None:
                        details_pb['signal_type'] = 'EMA_PULLBACK'
                        signals_found.append(('EMA_PULLBACK', details_pb))

                if Config.ENABLE_VOLUME_BREAKOUT:
                    has_bo, details_bo = detect_volume_breakout(
                        df_signal,
                        volume_breakout_mult=Config.VOLUME_BREAKOUT_MULT,
                    )
                    if has_bo and details_bo is not None:
                        details_bo['signal_type'] = 'VOLUME_BREAKOUT'
                        signals_found.append(('VOLUME_BREAKOUT', details_bo))

                if not signals_found:
                    logger.debug(f"{symbol}: no signals (market OK: {market_reason})")
                    continue

                # Priority: 2B > VOLUME_BREAKOUT > EMA_PULLBACK
                _signal_priority = {'2B': 1, 'VOLUME_BREAKOUT': 2, 'EMA_PULLBACK': 3}
                signals_found.sort(key=lambda x: _signal_priority.get(x[0], 99))

                all_sigs = ', '.join(
                    f"{t} {d['side']} vol={d.get('vol_ratio',0):.2f}x"
                    for t, d in signals_found
                )
                best_type, signal_details = signals_found[0]
                logger.info(f"{symbol}: signals detected [{all_sigs}]")
                signal_side = signal_details['side']

                # Direction filter
                trading_dir = Config.TRADING_DIRECTION.lower()
                if trading_dir == 'long' and signal_side != 'LONG':
                    logger.debug(f"{symbol}: skip ({best_type} {signal_side} vs direction=long)")
                    continue
                if trading_dir == 'short' and signal_side != 'SHORT':
                    logger.debug(f"{symbol}: skip ({best_type} {signal_side} vs direction=short)")
                    continue

                # Trend check
                trend_ok, trend_desc = TechnicalAnalysis.check_trend(df_trend, signal_side)
                if not trend_ok:
                    logger.info(f"{symbol}: skip (trend={trend_desc}, signal={signal_side})")
                    continue

                # MTF confirmation
                mtf_aligned = True
                mtf_reason = "MTF disabled"
                if Config.ENABLE_MTF_CONFIRMATION and not df_mtf.empty:
                    mtf_aligned, mtf_reason = MTFConfirmation.check_mtf_alignment(df_mtf, signal_side)
                    logger.info(f"{symbol}: MTF {mtf_reason}")

                # Signal tier
                signal_tier, tier_multiplier, tier_score = SignalTierSystem.calculate_signal_tier(
                    signal_details, mtf_aligned, is_strong_market,
                    signal_details.get('signal_strength', 'moderate')
                )
                signal_details['signal_tier'] = signal_tier
                signal_details['market_regime'] = 'STRONG' if is_strong_market else 'TRENDING'
                signal_details['entry_adx'] = (
                    round(float(df_signal['adx'].iloc[-1]), 2)
                    if 'adx' in df_signal.columns and not pd.isna(df_signal['adx'].iloc[-1])
                    else None
                )
                signal_details['_market_reason'] = market_reason
                signal_details['_trend_desc'] = trend_desc
                signal_details['_mtf_reason'] = mtf_reason
                signal_details['tier_score'] = tier_score
                signal_details['mtf_aligned'] = mtf_aligned
                signal_details['volume_grade'] = signal_details.get('signal_strength', 'moderate')
                signal_details['trend_adx'] = (
                    round(float(df_trend['adx'].iloc[-1]), 2)
                    if 'adx' in df_trend.columns and len(df_trend) > 0
                    and not pd.isna(df_trend['adx'].iloc[-1])
                    else None
                )

                # Risk Guard: Tier filter
                _tier_rank = {'A': 3, 'B': 2, 'C': 1}
                _min_tier = getattr(Config, 'V7_MIN_SIGNAL_TIER', 'C')
                if _tier_rank.get(signal_tier, 0) < _tier_rank.get(_min_tier, 0):
                    logger.info(
                        f"{symbol}: skip (Tier {signal_tier} < min {_min_tier}, score={tier_score})"
                    )
                    continue

                # Risk Guard: BTC Trend Filter
                if Config.BTC_TREND_FILTER_ENABLED and "BTC" not in symbol:
                    btc_context = bot._btc_trend_context or bot._resolve_btc_trend_context()
                    btc_trend = btc_context.get('trend')
                    signal_details['btc_trend'] = btc_trend or "UNKNOWN"

                    if btc_trend in ("RANGING", None):
                        ranging_label = "RANGING" if btc_trend == "RANGING" else "UNKNOWN"
                        pause_msg = (
                            f"{symbol}: skip (BTC {ranging_label}, "
                            f"trend strategy paused, waiting for grid)"
                        )
                        logger.info(pause_msg)
                        continue

                    elif signal_side != btc_trend:
                        if Config.BTC_COUNTER_TREND_MULT <= 0:
                            logger.info(
                                f"{symbol}: skip (BTC trend={btc_trend}, signal={signal_side} counter, "
                                f"BTC_COUNTER_TREND_MULT=0)"
                            )
                            continue
                        else:
                            tier_multiplier *= Config.BTC_COUNTER_TREND_MULT
                            logger.info(
                                f"{symbol}: BTC counter (BTC={btc_trend}, signal={signal_side}), "
                                f"size mult x{Config.BTC_COUNTER_TREND_MULT}"
                            )

                logger.info(
                    f"Entry ready: {symbol} {best_type} {signal_side} | "
                    f"tier={signal_tier} vol={signal_details.get('vol_ratio', 0):.2f}x | "
                    f"market={market_reason} trend={trend_desc} MTF={'pass' if mtf_aligned else 'fail'}"
                )

                bot._execute_trade(symbol, signal_details, best_type, tier_multiplier, df_signal)

            except Exception as e:
                logger.error(f"{symbol} scan error: {e}")

        active_str = ', '.join(
            f'{s}({t.side}/S{t.stage}/${t.total_size * t.avg_entry:.0f})'
            for s, t in bot.active_trades.items()
        ) or "none"
        logger.debug(f"Scan done | active: {active_str}")

    def _check_cooldowns(self, symbol: str) -> bool:
        """Check all cooldown conditions for a symbol. Returns True if clear."""
        bot = self.bot

        if symbol in bot.recently_exited:
            hours = (datetime.now(timezone.utc) - bot.recently_exited[symbol]).total_seconds() / 3600
            if hours < 2:
                logger.debug(f"{symbol}: skip (cooldown {hours:.1f}h)")
                return False
            else:
                del bot.recently_exited[symbol]

        if symbol in bot.order_failed_symbols:
            hours = (datetime.now(timezone.utc) - bot.order_failed_symbols[symbol]).total_seconds() / 3600
            if hours < 1:
                logger.debug(f"{symbol}: skip (order fail blacklist)")
                return False
            else:
                del bot.order_failed_symbols[symbol]

        if symbol in bot.early_exit_cooldown:
            hours = (datetime.now(timezone.utc) - bot.early_exit_cooldown[symbol]).total_seconds() / 3600
            if hours < Config.EARLY_EXIT_COOLDOWN_HOURS:
                logger.debug(f"{symbol}: skip (early exit cooldown {hours:.1f}h/{Config.EARLY_EXIT_COOLDOWN_HOURS}h)")
                return False
            else:
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
                            f"{symbol}: skip (last loss {hours_since:.1f}h ago, "
                            f"cooldown {Config.SYMBOL_LOSS_COOLDOWN_HOURS}h)"
                        )
                        return False
                except (ValueError, TypeError):
                    pass

        return True
