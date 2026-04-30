"""
Position monitoring manager -- extracted from bot.py (Phase 3).

Handles position lifecycle: monitoring, close, stage add, partial reduce.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from trader.config import Config
from trader.infrastructure.notifier import TelegramNotifier
from trader.positions import PositionManager
from trader.strategies.base import Action
from trader.utils import trade_log as _trade_log, calculate_pnl, build_log_base

logger = logging.getLogger(__name__)


class PositionMonitor:
    """Manages position monitoring, close, staging, and partial reduce."""

    def __init__(self, bot):
        self.bot = bot

    def monitor_positions(self):
        """Monitor active positions through strategy-neutral lifecycle."""
        bot = self.bot
        if not bot.active_trades:
            self._emit_cycle_summary(closed_count=0)
            return

        logger.debug(f"Monitoring {len(bot.active_trades)} positions...")

        closed_symbols = []
        state_changed = False

        for symbol, pm in list(bot.active_trades.items()):
            try:
                if pm.is_closed:
                    closed_symbols.append(symbol)
                    continue

                if getattr(pm, 'closed_on_exchange', False):
                    assumed_exit_price = (
                        getattr(pm, 'external_exit_price', None)
                        or pm.current_sl
                        or pm.avg_entry
                    )
                    if self.handle_close(
                        pm,
                        assumed_exit_price,
                        external_close=True,
                        exit_price_source=getattr(pm, 'external_exit_price_source', None) or 'assumed_sl',
                    ):
                        closed_symbols.append(symbol)
                        state_changed = True
                    continue

                ticker = bot.fetch_ticker(symbol)
                current_price = ticker['last']

                pm.highest_price = max(pm.highest_price, current_price)
                pm.lowest_price = min(pm.lowest_price, current_price)
                pm.monitor_count += 1

                if self._stop_hit(pm, current_price):
                    pm.exit_reason = "sl_hit"
                    if self.handle_close(pm, current_price, decision_reason="SL_HIT"):
                        closed_symbols.append(symbol)
                        state_changed = True
                    continue

                decision_obj = bot.strategy_runtime.update_position(pm, current_price)
                decision = decision_obj.as_dict() if hasattr(decision_obj, "as_dict") else dict(decision_obj or {})
                action = decision.get('action', Action.HOLD)
                new_sl = decision.get('new_sl')
                decision_reason = decision.get('reason')

                if new_sl is not None:
                    old_sl = pm.current_sl
                    if bot._update_hard_stop_loss(pm, new_sl):
                        state_changed = True
                    else:
                        pm.current_sl = old_sl
                    if old_sl > 0 and abs(new_sl - old_sl) / old_sl > 0.01 and pm.current_sl == new_sl:
                        TelegramNotifier.notify_action(
                            symbol, '1.5R蝘餅?',
                            current_price,
                            f"SL ${old_sl:.2f} ??${new_sl:.2f}"
                        )

                if action == Action.CLOSE:
                    if self.handle_close(pm, current_price, decision_reason=decision_reason):
                        closed_symbols.append(symbol)
                        state_changed = True

                elif action == Action.PARTIAL_CLOSE:
                    close_pct = decision.get('close_pct', 0.3)
                    pct_int = round(close_pct * 100)
                    reason = decision.get('reason', 'PARTIAL_CLOSE')
                    label = "2.0R" if "20R" in reason or "25R" in reason else "1.5R"
                    self.handle_partial_close(pm, pct_int, label, current_price)
                    state_changed = True

                if pm.side == 'LONG':
                    profit_pct = (current_price - pm.avg_entry) / pm.avg_entry * 100
                else:
                    profit_pct = (pm.avg_entry - current_price) / pm.avg_entry * 100

                mode = pm.strategy_id
                logger.debug(
                    f"{symbol} [{mode}]: ${current_price:.2f} | "
                    f"PnL={profit_pct:+.2f}% | SL=${pm.current_sl:.2f}"
                )

                _trade_log({
                    **build_log_base('POSITION_UPDATE', pm.trade_id, symbol, pm.side),
                    'price': f'{current_price:.2f}',
                    'pnl_pct': f'{profit_pct:+.2f}',
                    'sl': f'{pm.current_sl:.2f}',
                    'stage': pm.stage,
                    'mode': mode,
                })

            except Exception as e:
                logger.error(f"{symbol} monitor error: {e}")

            if pm.pending_stop_cancels:
                order_id = pm.pending_stop_cancels[0]
                try:
                    success = bot.execution_engine.cancel_stop_loss_order(pm.symbol, order_id)
                    if success:
                        pm.pending_stop_cancels.pop(0)
                        logger.info(f"[{pm.symbol}] pending stop cancel cleared: {order_id}")
                except Exception as e:
                    logger.warning(f"[{pm.symbol}] pending stop cancel retry failed: {e}")

        # Clean up closed positions
        for symbol in closed_symbols:
            pm = bot.active_trades.get(symbol)
            if pm:
                for order_id in pm.pending_stop_cancels:
                    try:
                        success = bot.execution_engine.cancel_stop_loss_order(pm.symbol, order_id)
                        if success:
                            logger.info(f"[{pm.symbol}] cleanup residual stop: {order_id}")
                        else:
                            logger.warning(f"[{pm.symbol}] cleanup residual stop returned false: {order_id}")
                    except Exception as e:
                        logger.warning(f"[{pm.symbol}] cleanup residual stop failed: {order_id} -- {e}")

                if pm.exit_reason in ('early_stop_r', 'stage1_timeout'):
                    bot.early_exit_cooldown[symbol] = datetime.now(timezone.utc)

            if symbol in bot.active_trades:
                del bot.active_trades[symbol]
                bot.recently_exited[symbol] = datetime.now(timezone.utc)

        if state_changed or closed_symbols:
            bot._save_positions()

        logger.debug(f"Monitor done | remaining: {len(bot.active_trades)}")
        self._emit_cycle_summary(closed_count=len(closed_symbols))

    @staticmethod
    def _stop_hit(pm: PositionManager, current_price: float) -> bool:
        if pm.side == "LONG":
            return current_price <= pm.current_sl
        return current_price >= pm.current_sl

    def _emit_cycle_summary(self, closed_count: int = 0):
        """Emit CYCLE_SUMMARY trade log -- called even when active_trades is empty."""
        bot = self.bot
        active_summary = ','.join(
            f'{s}({t.side}/S{t.stage}/${t.total_size * t.avg_entry:.0f})'
            for s, t in bot.active_trades.items()
        ) or "none"

        cycle_balance = bot.risk_manager.get_balance() if not Config.DRY_RUN else 10000.0
        cycle_unrealized_pnl = 0.0
        for pos in bot.active_trades.values():
            try:
                current_price = bot.fetch_ticker(pos.symbol)['last']
                if current_price and pos.avg_entry and pos.total_size:
                    if pos.side == 'LONG':
                        pnl = (current_price - pos.avg_entry) * pos.total_size
                    else:
                        pnl = (pos.avg_entry - current_price) * pos.total_size
                    cycle_unrealized_pnl += pnl
            except Exception:
                pass

        net_pnl_pct = round(
            (cycle_balance - bot.initial_balance) / bot.initial_balance * 100, 2
        ) if bot.initial_balance else 0.0
        _trade_log({
            'event': 'CYCLE_SUMMARY',
            'ts': datetime.now(timezone.utc).isoformat(),
            'bot': 'v7.0',
            'cycle': getattr(bot, 'cycle_count', 0),
            'active': len(bot.active_trades),
            'active_trades_count': len(bot.active_trades),
            'closed': closed_count,
            'symbols': active_summary,
            'balance': f'{cycle_balance:.2f}',
            'unrealized_pnl': f'{cycle_unrealized_pnl:.2f}',
            'net_pnl_pct': f'{net_pnl_pct:+.2f}',
        })

    @staticmethod
    def _calc_max_r_reached(pm: PositionManager) -> Optional[float]:
        """Best favorable excursion expressed in R, using tracked extremes."""
        if pm.risk_dist <= 0:
            return None

        if pm.side == 'LONG':
            max_r = (pm.highest_price - pm.avg_entry) / pm.risk_dist
        else:
            max_r = (pm.avg_entry - pm.lowest_price) / pm.risk_dist

        return round(max(max_r, 0.0), 4)

    @staticmethod
    def _resolve_exit_price(order_result: dict, fallback_price: float) -> tuple[float, str]:
        try:
            avg = order_result.get('avgPrice') or order_result.get('average')
            if avg:
                price = float(avg)
                if price > 0:
                    return price, 'exchange_fill'
        except Exception:
            pass
        return fallback_price, 'observed_price'

    @staticmethod
    def _map_decision_reason(decision_reason: Optional[str]) -> Optional[str]:
        """Normalize strategy decision reasons into persisted exit reason codes."""
        if not decision_reason or decision_reason == 'NONE':
            return None

        decision_map = {
            'TIME_EXIT': 'stage1_timeout',
            'FAST_STOP_067R': 'early_stop_r',
            'BACKTEST_STOP_TRIGGER': 'sl_hit',
            'BACKTEST_END': 'backtest_end',
            'RSI2_EXIT_TARGET': 'rsi2_exit_target',
            'SMA5_BOUNCE_EXIT': 'sma5_bounce_exit',
            'TIME_STOP': 'time_stop',
            'HTF_TREND_FLIP': 'htf_trend_flip',
        }
        return decision_map.get(decision_reason)

    @staticmethod
    def _infer_stop_hit_reason(pm: PositionManager, observed_price: float) -> Optional[str]:
        """Recover SL exits conservatively when the explicit reason was not preserved."""
        if pm.current_sl is None:
            return None

        if pm.side == 'LONG' and observed_price <= pm.current_sl:
            return 'sl_hit'
        if pm.side == 'SHORT' and observed_price >= pm.current_sl:
            return 'sl_hit'
        return None

    @classmethod
    def _resolve_close_reason(
        cls,
        pm: PositionManager,
        observed_price: float,
        *,
        external_close: bool,
        decision_reason: Optional[str] = None,
    ) -> str:
        """Resolve a persisted close reason without altering trade decisions."""
        if external_close and getattr(pm, 'external_close_reason', None):
            return pm.external_close_reason

        if getattr(pm, 'exit_reason', None):
            return pm.exit_reason

        mapped_reason = cls._map_decision_reason(decision_reason)
        if mapped_reason:
            logger.warning(
                f"{pm.symbol} close missing pm.exit_reason, "
                f"using decision reason fallback: {decision_reason} -> {mapped_reason}"
            )
            return mapped_reason

        inferred_reason = cls._infer_stop_hit_reason(pm, observed_price)
        if inferred_reason:
            logger.warning(
                f"{pm.symbol} close missing explicit reason, "
                f"inferred {inferred_reason} from price={observed_price:.4f} vs SL={pm.current_sl:.4f}"
            )
            return inferred_reason

        if decision_reason and decision_reason != 'NONE':
            logger.warning(
                f"{pm.symbol} close reason unresolved; "
                f"decision_reason={decision_reason} current_price={observed_price:.4f}"
            )
        return 'unknown'

    def handle_close(
        self,
        pm: PositionManager,
        current_price: float = 0.0,
        external_close: bool = False,
        exit_price_source: Optional[str] = None,
        decision_reason: Optional[str] = None,
    ) -> bool:
        """
        Handle position close.

        Returns:
            True  -- close succeeded, caller should remove position
            False -- close failed, pm.is_closed stays False, retry next cycle
        """
        bot = self.bot
        try:
            if current_price <= 0:
                if external_close:
                    current_price = (
                        getattr(pm, 'external_exit_price', None)
                        or pm.current_sl
                        or pm.avg_entry
                    )
                else:
                    try:
                        ticker = bot.fetch_ticker(pm.symbol)
                        current_price = ticker['last']
                    except Exception:
                        current_price = pm.avg_entry
            observed_price = current_price
            exit_price = observed_price
            exit_price_source = exit_price_source or ('assumed_sl' if external_close else 'observed_price')
            duration_h = (datetime.now(timezone.utc) - pm.entry_time).total_seconds() / 3600
            exit_reason = self._resolve_close_reason(
                pm,
                observed_price,
                external_close=external_close,
                decision_reason=decision_reason,
            )

            if Config.DRY_RUN:
                logger.info(f"[DRY_RUN] Close {pm.symbol} {pm.side} size={pm.total_size:.6f}")
            else:
                if external_close:
                    exit_price = observed_price
                    exit_price_source = exit_price_source or 'assumed_sl'
                    logger.info(
                        f"{pm.symbol} finalized from exchange close: "
                        f"{pm.side} size={pm.total_size:.6f} price=${exit_price:.4f}"
                    )
                else:
                    try:
                        close_result = bot._futures_close_position(pm.symbol, pm.side, pm.total_size)
                        exit_price, exit_price_source = self._resolve_exit_price(close_result, observed_price)
                    except Exception as close_err:
                        logger.error(
                            f"{pm.symbol} close order failed (position preserved, retry next cycle): {close_err}"
                        )
                        bot._save_positions()
                        return False

                    if pm.stop_order_id:
                        pm.pending_stop_cancels.append(pm.stop_order_id)
                        pm.stop_order_id = None

                    if abs(exit_price - observed_price) > 1e-9:
                        logger.info(
                            f"{pm.symbol} exit fill adjusted: observed=${observed_price:.4f} -> fill=${exit_price:.4f}"
                        )
                    logger.info(f"{pm.symbol} closed: {pm.side} size={pm.total_size:.6f}")

            pm.highest_price = max(pm.highest_price, observed_price, exit_price)
            pm.lowest_price = min(pm.lowest_price, observed_price, exit_price)

            final_pnl = calculate_pnl(pm.side, pm.total_size, exit_price, pm.avg_entry)
            pnl_usdt = final_pnl + pm.realized_partial_pnl
            original_notional = pm.original_size * pm.avg_entry
            pnl_pct = (pnl_usdt / original_notional * 100) if original_notional > 0 else 0

            avg_entry = pm.avg_entry
            if avg_entry and avg_entry > 0:
                if pm.side == 'LONG':
                    mfe_pct = round((pm.highest_price - avg_entry) / avg_entry * 100, 4)
                    mae_pct = round((pm.lowest_price - avg_entry) / avg_entry * 100, 4)
                else:
                    mfe_pct = round((avg_entry - pm.lowest_price) / avg_entry * 100, 4)
                    mae_pct = round((avg_entry - pm.highest_price) / avg_entry * 100, 4)
            else:
                mfe_pct = 0.0
                mae_pct = 0.0

            realized_r = round(pnl_usdt / pm.initial_r, 2) if pm.initial_r else 0.0
            capture_ratio = round(pnl_pct / mfe_pct, 2) if mfe_pct > 0.0001 else None
            safe_capture = round(pnl_pct / mfe_pct, 4) if mfe_pct > 0.0001 else None
            holding_time_min = round(duration_h * 60, 1)
            max_r_reached = self._calc_max_r_reached(pm)
            _trade_log({
                **build_log_base('TRADE_CLOSE', pm.trade_id, pm.symbol, pm.side),
                'exit_price': f'{exit_price:.2f}',
                'exit_price_source': exit_price_source,
                'entry': f'{pm.avg_entry:.2f}',
                'size': f'{pm.total_size:.6f}',
                'pnl_pct': f'{pnl_pct:+.2f}',
                'pnl_usdt': f'{pnl_usdt:+.2f}',
                'exit_reason': exit_reason,
                'duration_h': f'{duration_h:.1f}',
                'holding_time_min': f'{holding_time_min}',
                'stage': pm.stage,
                'realized_r': f'{realized_r:.2f}',
                'mfe_pct': f'{mfe_pct:.4f}',
                'mae_pct': f'{mae_pct:.4f}',
                'capture_ratio': f'{capture_ratio or 0:.2f}',
                'signal_type': getattr(pm, 'signal_type', None),
                'decision_reason': decision_reason,
                'max_r_reached': f'{max_r_reached:.4f}' if max_r_reached is not None else None,
                'protection_state': None,
                'protected_exit': None,
            })

            if not Config.DRY_RUN:
                bot.perf_db.record_trade({
                    "trade_id":      pm.trade_id,
                    "symbol":        pm.symbol,
                    "side":          pm.side,
                    "is_v6_pyramid": 0,
                    "signal_tier":   pm.signal_tier,
                    "signal_type":   getattr(pm, 'signal_type', None),
                    "entry_price":   pm.avg_entry,
                    "exit_price":    exit_price,
                    "exit_price_source": exit_price_source,
                    "total_size":    pm.total_size,
                    "initial_r":     pm.initial_r,
                    "entry_time":    pm.entry_time.isoformat() if hasattr(pm.entry_time, 'isoformat') else str(pm.entry_time),
                    "exit_time":     datetime.now(timezone.utc).isoformat(),
                    "holding_hours": duration_h,
                    "pnl_usdt":      pnl_usdt,
                    "pnl_pct":       pnl_pct,
                    "realized_r":    realized_r,
                    "mfe_pct":       mfe_pct,
                    "mae_pct":       mae_pct,
                    "capture_ratio": safe_capture,
                    "max_r_reached": max_r_reached,
                    "stage_reached":   pm.stage,
                    "exit_reason":     exit_reason,
                    "protection_state": None,
                    "protected_exit": None,
                    "market_regime":   pm.market_regime,
                    "entry_adx":          getattr(pm, 'entry_adx', None),
                    "fakeout_depth_atr":  getattr(pm, 'fakeout_depth_atr', None),
                    "reverse_2b_depth_atr": getattr(pm, 'reverse_2b_depth_atr', None),
                    "original_size":       pm.original_size,
                    "partial_pnl_usdt":    pm.realized_partial_pnl,
                    "btc_trend_aligned":   getattr(pm, 'btc_trend_aligned', None),
                    "trend_adx":       getattr(pm, 'trend_adx', None),
                    "mtf_aligned":     int(pm.mtf_aligned) if getattr(pm, 'mtf_aligned', None) is not None else None,
                    "volume_grade":    getattr(pm, 'volume_grade', None),
                    "tier_score":      getattr(pm, 'tier_score', None),
                    "strategy_id":     getattr(pm, 'strategy_id', None),
                    "strategy_version": getattr(pm, 'strategy_version', None),
                    "strategy_name":   pm.strategy_name,
                })

                TelegramNotifier.notify_exit(pm.symbol, {
                    'side': pm.side,
                    'entry_price': pm.avg_entry,
                    'exit_reason': exit_reason,
                    'position_size': pm.total_size,
                    'pnl_pct': pnl_pct,
                })

            if external_close and pm.stop_order_id:
                pm.pending_stop_cancels.append(pm.stop_order_id)
                pm.stop_order_id = None
            pm.closed_on_exchange = False
            pm.external_close_reason = None
            pm.external_exit_price = None
            pm.external_exit_price_source = None
            pm.is_closed = True
            return True

        except Exception as e:
            logger.error(f"{pm.symbol} _handle_close unexpected error: {e}")
            return False

    def handle_partial_close(self, pm: PositionManager, pct: int, label: str, current_price: float):
        """Handle strategy-neutral partial close."""
        bot = self.bot
        try:
            reduce_size = pm.total_size * (pct / 100.0)
            if reduce_size <= 0:
                return

            reduce_size = float(bot.precision_handler.format_quantity(pm.symbol, reduce_size))

            if Config.DRY_RUN:
                partial_pnl = calculate_pnl(pm.side, reduce_size, current_price, pm.avg_entry)
                pm.realized_partial_pnl += partial_pnl
                logger.info(
                    f"[DRY_RUN] {pm.symbol} {label} reduce: -{reduce_size:.6f} "
                    f"@ ${current_price:.2f} PnL=${partial_pnl:+.2f}"
                )
                TelegramNotifier.notify_action(
                    pm.symbol, 'target reduce',
                    current_price,
                    f"{label} -{reduce_size:.6f} PnL=${partial_pnl:+.2f}"
                )
                pm.total_size -= reduce_size
                _trade_log({
                    **build_log_base('PARTIAL_CLOSE', pm.trade_id, pm.symbol, pm.side),
                    'label': label,
                    'reduce_size': f'{reduce_size:.6f}',
                    'reduce_price': f'{current_price:.2f}',
                    'partial_pnl': f'{partial_pnl:+.2f}',
                    'cumulative_partial_pnl': f'{pm.realized_partial_pnl:+.2f}',
                    'remaining_size': f'{pm.total_size:.6f}',
                })
                return

            order_result = bot._futures_close_position(pm.symbol, pm.side, reduce_size)

            fill_price = bot._extract_fill_price(order_result, current_price)
            if fill_price != current_price:
                logger.info(
                    f"{pm.symbol} {label} reduce fill correction: "
                    f"ticker${current_price:.4f} -> actual${fill_price:.4f}"
                )

            partial_pnl = calculate_pnl(pm.side, reduce_size, fill_price, pm.avg_entry)
            pm.realized_partial_pnl += partial_pnl

            pm.total_size -= reduce_size

            bot._refresh_stop_loss(pm, pm.current_sl)

            logger.info(
                f"{pm.symbol} {label} reduce: -{reduce_size:.6f} @ ${fill_price:.2f} | "
                f"PnL=${partial_pnl:+.2f} cumul=${pm.realized_partial_pnl:+.2f} | "
                f"remaining={pm.total_size:.6f} | SL=${pm.current_sl:.2f}"
            )
            TelegramNotifier.notify_action(
                pm.symbol, 'target reduce',
                fill_price,
                f"{label} -{reduce_size:.6f} PnL=${partial_pnl:+.2f} remaining={pm.total_size:.6f}"
            )

            _trade_log({
                **build_log_base('PARTIAL_CLOSE', pm.trade_id, pm.symbol, pm.side),
                'label': label,
                'reduce_size': f'{reduce_size:.6f}',
                'reduce_price': f'{fill_price:.2f}',
                'partial_pnl': f'{partial_pnl:+.2f}',
                'cumulative_partial_pnl': f'{pm.realized_partial_pnl:+.2f}',
                'remaining_size': f'{pm.total_size:.6f}',
            })

        except Exception as e:
            logger.error(f"{pm.symbol} reduce failed: {e}")
