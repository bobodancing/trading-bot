"""Strategy runtime pipeline.

This module is intentionally strategy-neutral: plugins describe intent, then
the core runtime handles routing, risk, execution handoff, and audit.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import pandas as pd

from trader.config import Config
from trader.indicators.registry import IndicatorRegistry
from trader.strategies import (
    Action,
    ExecutableOrderPlan,
    MarketSnapshot,
    PositionDecision,
    RiskPlan,
    SignalIntent,
    StrategyContext,
    StrategyPlugin,
    StrategyRegistry,
    StrategyRiskProfile,
)
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.utils import drop_unfinished_candle

logger = logging.getLogger(__name__)


class MarketSnapshotBuilder:
    def __init__(self, bot):
        self.bot = bot

    def build(self, symbols: Iterable[str], plugins: Iterable[StrategyPlugin]) -> MarketSnapshot:
        requirements: dict[str, tuple[int, set[str]]] = {}
        for plugin in plugins:
            for timeframe, warmup in plugin.required_timeframes.items():
                existing_warmup, existing_indicators = requirements.get(timeframe, (0, set()))
                requirements[timeframe] = (
                    max(existing_warmup, int(warmup)),
                    existing_indicators | set(plugin.required_indicators),
                )

        frames: dict[str, dict[str, pd.DataFrame]] = {}
        for symbol in symbols:
            frames[symbol] = {}
            for timeframe, (warmup, indicators) in requirements.items():
                df = self.bot.fetch_ohlcv(symbol, timeframe, limit=max(warmup, 1))
                if df is None or df.empty:
                    frames[symbol][timeframe] = pd.DataFrame()
                    continue
                df = IndicatorRegistry.apply(df, indicators)
                frames[symbol][timeframe] = drop_unfinished_candle(df)
        return MarketSnapshot(frames=frames, generated_at=datetime.now(timezone.utc))


class StrategyRuntime:
    def __init__(self, bot):
        self.bot = bot
        self.registry = StrategyRegistry()
        self.snapshot_builder = MarketSnapshotBuilder(bot)
        self.refresh_registry()

    def refresh_registry(self) -> None:
        enabled = getattr(Config, "ENABLED_STRATEGIES", [])
        self.registry = StrategyRegistry.from_config(
            get_strategy_catalog(enabled),
            enabled,
        )

    def enabled_plugins(self) -> list[StrategyPlugin]:
        if not getattr(Config, "STRATEGY_RUNTIME_ENABLED", False):
            return []
        return list(self.registry.plugins.values())

    def build_context(self, symbols: list[str]) -> StrategyContext:
        plugins = self.enabled_plugins()
        snapshot = self.snapshot_builder.build(symbols, plugins)
        return StrategyContext(
            snapshot=snapshot,
            symbols=symbols,
            active_positions=self.bot.active_trades,
            config=Config,
            now=datetime.now(timezone.utc),
        )

    def scan_for_entries(self) -> None:
        if not getattr(Config, "STRATEGY_RUNTIME_ENABLED", False):
            logger.info("Strategy runtime disabled; no entries will be generated")
            return

        self.refresh_registry()
        plugins = self.enabled_plugins()
        if not plugins:
            logger.info("No enabled strategies; fail-closed no-trade cycle")
            return

        base_symbols = self.bot.load_scanner_results() if Config.USE_SCANNER_SYMBOLS else list(Config.SYMBOLS)
        if not base_symbols:
            logger.info("No symbols available for strategy runtime")
            return

        symbols = self._symbols_for_snapshot(base_symbols, plugins)
        if not symbols:
            logger.info("No symbols in scope for enabled strategies; fail-closed no-trade cycle")
            return

        self._refresh_regime_context()
        context = self.build_context(symbols)
        for plugin in plugins:
            plugin_context = self._context_for_plugin(context, plugin)
            try:
                candidates = plugin.generate_candidates(plugin_context)
            except Exception as exc:
                logger.error("strategy %s candidate generation failed: %s", plugin.id, exc)
                self._audit_reject("*", plugin.id, "candidate_generation_error", str(exc))
                continue

            for intent in candidates:
                self._process_intent(plugin, intent, plugin_context)

    def update_position(self, position, current_price: float) -> PositionDecision:
        plugin = self.registry.get(getattr(position, "strategy_id", ""))
        if plugin is None:
            return PositionDecision(
                action=Action.HOLD,
                reason="PROTECTIVE_MANUAL_NO_PLUGIN",
                metadata={"strategy_id": getattr(position, "strategy_id", None)},
            )
        symbols = [position.symbol]
        context = self.build_context(symbols)
        return plugin.update_position(context, position)

    def _process_intent(
        self,
        plugin: StrategyPlugin,
        intent: SignalIntent,
        context: StrategyContext,
    ) -> None:
        symbol = intent.symbol
        if intent.strategy_id != plugin.id:
            self._audit_reject(symbol, intent.strategy_id, "strategy_id_mismatch", plugin.id)
            return
        if not self._symbol_in_scope(plugin, symbol, context.symbols):
            self._audit_reject(symbol, intent.strategy_id, "strategy_symbol_out_of_scope")
            return
        if symbol in self.bot.active_trades:
            self._audit_reject(symbol, intent.strategy_id, "position_slot_occupied")
            return
        if self._strategy_position_limit_reached(plugin):
            self._audit_reject(symbol, intent.strategy_id, "strategy_position_limit_reached")
            return
        if not self.bot.signal_scanner.check_cooldowns(symbol):
            self._audit_reject(symbol, intent.strategy_id, "cooldown")
            return
        if not self.bot._check_total_risk(list(self.bot.active_trades.values())):
            self._audit_reject(symbol, intent.strategy_id, "total_risk_limit")
            return

        route_allowed, route_reason = self._route(plugin, intent)
        if not route_allowed:
            self._audit_reject(symbol, intent.strategy_id, "strategy_router_blocked", route_reason)
            return

        risk_plan = self._build_risk_plan(plugin, intent, context)
        if not risk_plan.allowed:
            self._audit_reject(symbol, intent.strategy_id, "central_risk_blocked", risk_plan.reject_reason)
            return

        order_plan = ExecutableOrderPlan(
            intent=intent,
            risk_plan=risk_plan,
            strategy_version=plugin.version,
            router_reason=route_reason,
            metadata={"strategy_tags": sorted(plugin.tags)},
        )
        self._audit_entry(order_plan)
        self.bot._execute_order_plan(order_plan)

    def _route(self, plugin: StrategyPlugin, intent: SignalIntent) -> tuple[bool, str]:
        snapshot = getattr(self.bot, "_regime_arbiter_snapshot", None)
        if snapshot is None or not getattr(Config, "REGIME_ARBITER_ENABLED", False):
            return True, "route:direct"
        if getattr(Config, "REGIME_ROUTER_ENABLED", False):
            decision = self.bot.regime_router.route(
                snapshot,
                strategy_id=intent.strategy_id,
                strategy_tags=plugin.tags,
                signal_side=intent.side,
            )
            return decision.allowed, decision.reason
        allowed, reason = self.bot.regime_arbiter.can_enter(snapshot, intent.side)
        return bool(allowed), reason

    def _build_risk_plan(
        self,
        plugin: StrategyPlugin,
        intent: SignalIntent,
        context: StrategyContext,
    ) -> RiskPlan:
        if intent.stop_hint is None:
            return self._reject_risk("missing_stop_hint")

        entry_price = intent.entry_price or context.snapshot.latest_close(intent.symbol, intent.timeframe)
        if entry_price is None or entry_price <= 0:
            return self._reject_risk("missing_entry_price")
        stop_loss = float(intent.stop_hint.price)
        if intent.side == "LONG" and stop_loss >= entry_price:
            return self._reject_risk("invalid_stop_for_long")
        if intent.side == "SHORT" and stop_loss <= entry_price:
            return self._reject_risk("invalid_stop_for_short")

        sl_distance_pct = abs(entry_price - stop_loss) / entry_price
        if sl_distance_pct <= 0:
            return self._reject_risk("zero_stop_distance")
        if sl_distance_pct > Config.MAX_SL_DISTANCE_PCT:
            return self._reject_risk("max_sl_distance")

        balance = 10000.0 if Config.DRY_RUN else self.bot.risk_manager.get_balance()
        if balance <= 0:
            return self._reject_risk("balance_unavailable")

        risk_profile = getattr(plugin, "risk_profile", StrategyRiskProfile.fixed_risk_pct())
        if risk_profile.sizing_mode != "fixed_risk_pct":
            return self._reject_risk(f"unsupported_sizing_mode:{risk_profile.sizing_mode}")
        risk_pct = risk_profile.risk_pct
        if risk_pct is None:
            risk_pct = Config.RISK_PER_TRADE
        risk_pct = float(risk_pct)
        if risk_pct <= 0:
            return self._reject_risk("invalid_risk_pct")

        position_size = self._calculate_fixed_risk_position_size(
            intent.symbol,
            balance,
            entry_price,
            stop_loss,
            risk_pct,
        )
        if position_size <= 0:
            return self._reject_risk("position_size_invalid")

        max_loss_usdt = position_size * abs(entry_price - stop_loss)
        total_risk_budget = balance * Config.MAX_TOTAL_RISK
        current_open_risk = self.bot._calc_total_open_risk_amount()
        if current_open_risk + max_loss_usdt > total_risk_budget:
            remaining = total_risk_budget - current_open_risk
            if remaining <= 0:
                return self._reject_risk("total_risk_budget_exhausted")
            shrunk = self.bot.precision_handler.round_amount(
                intent.symbol,
                remaining / abs(entry_price - stop_loss),
            )
            if (
                shrunk <= 0
                or not self.bot.precision_handler.check_limits(intent.symbol, shrunk, entry_price)
            ):
                return self._reject_risk("remaining_risk_below_min_order")
            position_size = shrunk
            max_loss_usdt = position_size * abs(entry_price - stop_loss)

        return RiskPlan(
            entry_price=float(entry_price),
            stop_loss=stop_loss,
            position_size=position_size,
            max_loss_usdt=max_loss_usdt,
            risk_pct=max_loss_usdt / balance,
            hard_stop_required=bool(Config.USE_HARD_STOP_LOSS),
        )

    def _calculate_fixed_risk_position_size(
        self,
        symbol: str,
        balance: float,
        entry_price: float,
        stop_loss: float,
        risk_pct: float,
    ) -> float:
        risk_amount = balance * risk_pct
        stop_dist_percent = abs(entry_price - stop_loss) / entry_price
        if stop_dist_percent <= 0:
            return 0.0

        position_value = risk_amount / stop_dist_percent
        max_position_value = balance * Config.MAX_POSITION_PERCENT * Config.LEVERAGE
        if position_value > max_position_value:
            position_value = max_position_value

        raw_position = position_value / entry_price
        rounded_position = self.bot.precision_handler.round_amount_up(
            symbol,
            raw_position,
            entry_price,
        )
        if not self.bot.precision_handler.check_limits(symbol, rounded_position, entry_price):
            return 0.0
        return float(rounded_position)

    @staticmethod
    def _reject_risk(reason: str) -> RiskPlan:
        return RiskPlan(
            entry_price=0.0,
            stop_loss=0.0,
            position_size=0.0,
            max_loss_usdt=0.0,
            risk_pct=0.0,
            hard_stop_required=False,
            reject_reason=reason,
        )

    def _refresh_regime_context(self) -> None:
        uses_regime = (
            getattr(Config, "REGIME_ARBITER_ENABLED", False)
            or getattr(Config, "REGIME_ROUTER_ENABLED", False)
        )
        if not uses_regime:
            return
        try:
            self.bot._btc_regime_context = {}
            self.bot._regime_arbiter_snapshot = None
            self.bot._update_btc_regime_context()
        except Exception as exc:
            logger.warning("regime context unavailable for strategy runtime: %s", exc)

    def _audit_reject(
        self,
        symbol: str,
        strategy_id: str,
        reason: str,
        detail: Optional[str] = None,
    ) -> None:
        collector = getattr(self.bot, "_signal_audit", None)
        if collector is not None:
            collector.record_reject(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol=symbol,
                stage="strategy_runtime",
                reject_reason=reason,
                signal_type=strategy_id,
                detail=detail,
            )
        logger.info("strategy reject %s %s: %s %s", symbol, strategy_id, reason, detail or "")

    def _audit_entry(self, order_plan: ExecutableOrderPlan) -> None:
        collector = getattr(self.bot, "_signal_audit", None)
        intent = order_plan.intent
        if collector is not None:
            collector.record_entry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol=intent.symbol,
                signal_type=intent.strategy_id,
                signal_side=intent.side,
                signal_tier="CENTRAL",
                tier_multiplier=1.0,
                tier_score=None,
            )
        logger.info(
            "strategy entry ready %s %s %s size=%.6f risk=%.4f",
            intent.symbol,
            intent.strategy_id,
            intent.side,
            order_plan.risk_plan.position_size,
            order_plan.risk_plan.risk_pct,
        )

    @staticmethod
    def plan_to_log_fields(order_plan: ExecutableOrderPlan) -> dict[str, Any]:
        return {
            "strategy_id": order_plan.intent.strategy_id,
            "strategy_version": order_plan.strategy_version,
            "entry_type": order_plan.intent.entry_type,
            "router_reason": order_plan.router_reason,
            "risk_plan": asdict(order_plan.risk_plan),
        }

    @staticmethod
    def _allowed_symbols(plugin: StrategyPlugin) -> set[str]:
        return {str(symbol) for symbol in getattr(plugin, "allowed_symbols", set()) or set()}

    def _plugin_symbols(self, plugin: StrategyPlugin, base_symbols: Iterable[str]) -> list[str]:
        base = list(dict.fromkeys(str(symbol) for symbol in base_symbols))
        allowed = self._allowed_symbols(plugin)
        if not allowed:
            return base
        return [symbol for symbol in base if symbol in allowed]

    def _symbols_for_snapshot(
        self,
        base_symbols: Iterable[str],
        plugins: Iterable[StrategyPlugin],
    ) -> list[str]:
        symbols: list[str] = []
        seen: set[str] = set()
        for plugin in plugins:
            for symbol in self._plugin_symbols(plugin, base_symbols):
                if symbol not in seen:
                    seen.add(symbol)
                    symbols.append(symbol)
        return symbols

    def _context_for_plugin(self, context: StrategyContext, plugin: StrategyPlugin) -> StrategyContext:
        return StrategyContext(
            snapshot=context.snapshot,
            symbols=self._plugin_symbols(plugin, context.symbols),
            active_positions=context.active_positions,
            config=context.config,
            now=context.now,
        )

    def _symbol_in_scope(
        self,
        plugin: StrategyPlugin,
        symbol: str,
        context_symbols: Iterable[str],
    ) -> bool:
        allowed = self._allowed_symbols(plugin)
        if allowed and symbol not in allowed:
            return False
        return symbol in set(context_symbols)

    def _strategy_position_limit_reached(self, plugin: StrategyPlugin) -> bool:
        limit = getattr(plugin, "max_concurrent_positions", 1)
        if limit is None:
            return False
        limit = int(limit)
        if limit <= 0:
            return False
        active_count = 0
        for position in self.bot.active_trades.values():
            if getattr(position, "is_closed", False):
                continue
            if getattr(position, "strategy_id", None) == plugin.id:
                active_count += 1
        return active_count >= limit
