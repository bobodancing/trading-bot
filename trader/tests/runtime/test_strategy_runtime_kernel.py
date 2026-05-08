from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trader.config import Config
from trader.positions import LEGACY_MANUAL_STRATEGY_ID, PositionManager
from trader.routing import RegimeRouter, StrategyRoute
from trader.strategies import (
    SignalIntent,
    StopHint,
    StrategyContext,
    StrategyPlugin,
    StrategyRegistry,
    StrategyRiskProfile,
)
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.fixture import FixtureLongStrategy
from trader.strategies.plugins.macd_signal_trending_up_4h import MacdSignalTrendingUp4hStrategy
from trader.strategy_runtime import MarketSnapshotBuilder, StrategyRuntime


SLOT_A_LONG = (
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_A_SHORT = (
    "macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_"
    "transition_aware_tightened_late_entry_filter"
)
SLOT_B_LONG = "donchian_range_fade_4h_range_width_cv_013"
SLOT_B_SHORT = "donchian_range_fade_4h_range_width_cv_013_short"


def _frame(rows=80):
    idx = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + rows), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


class _AuditCollector:
    def __init__(self):
        self.rejects = []
        self.entries = []

    def record_reject(self, **kwargs):
        self.rejects.append(kwargs)

    def record_entry(self, **kwargs):
        self.entries.append(kwargs)


class _Precision:
    def round_amount_up(self, symbol, amount, price):
        return float(round(amount, 6))

    def round_amount(self, symbol, amount):
        return float(round(amount, 6))

    def check_limits(self, symbol, amount, price):
        return True


class _FakeBot:
    def __init__(self):
        self.active_trades = {}
        self._signal_audit = _AuditCollector()
        self.signal_scanner = SimpleNamespace(check_cooldowns=lambda symbol: True)
        self.precision_handler = _Precision()
        self.risk_manager = SimpleNamespace(get_balance=lambda: 10000.0)
        self.current_open_risk = 0.0
        self.executed_plans = []

    def _check_total_risk(self, active_positions):
        return True

    def _calc_total_open_risk_amount(self):
        return self.current_open_risk

    def _execute_order_plan(self, order_plan):
        self.executed_plans.append(order_plan)


class _ScopedStrategy(StrategyPlugin):
    id = "scoped"
    version = "1.0.0"
    tags = {"fixture"}
    required_timeframes = {}
    required_indicators = set()
    allowed_symbols = {"BTC/USDT"}
    max_concurrent_positions = 1
    risk_profile = StrategyRiskProfile.fixed_risk_pct(0.01)

    def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
        return []


def _intent(
    symbol="BTC/USDT",
    strategy_id="scoped",
    entry=100.0,
    stop=None,
    side="LONG",
):
    stop = stop if stop is not None else (95.0 if side == "LONG" else 105.0)
    return SignalIntent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        timeframe="1h",
        candle_ts=datetime.now(timezone.utc),
        entry_type="test_market",
        stop_hint=StopHint(price=stop),
        confidence=1.0,
        entry_price=entry,
    )


def _context(bot, symbols=None):
    symbols = symbols or ["BTC/USDT"]
    snapshot = SimpleNamespace(
        get=lambda symbol, timeframe: _frame(),
        latest_timestamp=lambda symbol, timeframe: datetime(2026, 1, 4, tzinfo=timezone.utc),
        latest_close=lambda symbol, timeframe: 100.0,
    )
    return StrategyContext(
        snapshot=snapshot,
        symbols=list(symbols),
        active_positions=bot.active_trades,
        config=SimpleNamespace(),
        now=datetime.now(timezone.utc),
    )


def test_strategy_registry_loads_enabled_plugin():
    registry = StrategyRegistry.from_config(
        {
            "fixture_long": {
                "enabled": True,
                "module": "trader.strategies.plugins.fixture",
                "class": "FixtureLongStrategy",
                "params": {"symbol": "BTC/USDT"},
            }
        },
        ["fixture_long"],
    )

    plugin = registry.require("fixture_long")
    assert isinstance(plugin, FixtureLongStrategy)
    assert plugin.params["symbol"] == "BTC/USDT"


def test_strategy_registry_rejects_unknown_plugin_param():
    with pytest.raises(ValueError, match="unknown param"):
        StrategyRegistry.from_config(
            {
                "fixture_long": {
                    "enabled": True,
                    "module": "trader.strategies.plugins.fixture",
                    "class": "FixtureLongStrategy",
                    "params": {"symbol": "BTC/USDT", "typo_stop": 0.02},
                }
            },
            ["fixture_long"],
        )


def test_strategy_registry_rejects_wrong_plugin_param_type():
    with pytest.raises(ValueError, match="param emit_once must be bool"):
        StrategyRegistry.from_config(
            {
                "fixture_long": {
                    "enabled": True,
                    "module": "trader.strategies.plugins.fixture",
                    "class": "FixtureLongStrategy",
                    "params": {"emit_once": "true"},
                }
            },
            ["fixture_long"],
        )


def test_strategy_registry_rejects_unknown_required_indicator(monkeypatch):
    monkeypatch.setattr(
        "trader.strategies.plugins.fixture.FixtureLongStrategy.required_indicators",
        {"atr", "not_a_real_indicator"},
    )

    with pytest.raises(ValueError, match="unsupported indicator"):
        StrategyRegistry.from_config(
            {
                "fixture_long": {
                    "enabled": True,
                    "module": "trader.strategies.plugins.fixture",
                    "class": "FixtureLongStrategy",
                    "params": {},
                }
            },
            ["fixture_long"],
        )


def test_strategy_registry_fail_closed_when_empty():
    registry = StrategyRegistry.from_config({}, [])
    assert registry.plugins == {}


def test_plugin_catalog_copy_enables_selected_entries_without_mutating_source():
    first = get_strategy_catalog(["fixture_long"])
    second = get_strategy_catalog()

    assert first["fixture_long"]["enabled"] is True
    assert second["fixture_long"]["enabled"] is False


def test_fixture_strategy_generates_deterministic_intent():
    plugin = FixtureLongStrategy(params={"symbol": "BTC/USDT", "stop_pct": 0.02})
    snapshot = SimpleNamespace(
        get=lambda symbol, timeframe: _frame(),
        latest_timestamp=lambda symbol, timeframe: datetime(2026, 1, 4, tzinfo=timezone.utc),
        latest_close=lambda symbol, timeframe: 179.0,
    )
    context = StrategyContext(
        snapshot=snapshot,
        symbols=["BTC/USDT"],
        active_positions={},
        config=SimpleNamespace(),
        now=datetime.now(timezone.utc),
    )

    intents = plugin.generate_candidates(context)

    assert len(intents) == 1
    assert intents[0].strategy_id == "fixture_long"
    assert intents[0].side == "LONG"
    assert intents[0].stop_hint.price == pytest.approx(175.42)
    assert plugin.generate_candidates(context) == []


def test_position_manager_migrates_legacy_position_to_manual_mode():
    pm = PositionManager.from_dict(
        {
            "symbol": "BTC/USDT",
            "side": "LONG",
            "avg_entry": 100.0,
            "current_sl": 95.0,
            "total_size": 0.1,
            "strategy_name": "v54_noscale",
            "trade_id": "legacy1",
        }
    )

    assert pm.strategy_id == LEGACY_MANUAL_STRATEGY_ID
    assert pm.metadata["legacy_strategy_name"] == "v54_noscale"
    assert pm.to_dict()["schema_version"] == 2


def test_router_uses_strategy_id_and_tags():
    router = RegimeRouter(
        routes=[
            StrategyRoute(
                strategy_ids=frozenset({"fixture_long"}),
                strategy_tags=frozenset({"fixture"}),
                allowed_labels=frozenset({"TRENDING_UP"}),
            )
        ]
    )
    snapshot = SimpleNamespace(label="TRENDING_UP", confidence=0.9, entry_allowed=True)

    decision = router.route(
        snapshot,
        strategy_id="fixture_long",
        strategy_tags={"fixture"},
        signal_side="LONG",
    )

    assert decision.allowed
    assert decision.selected_strategy == "fixture_long"


def test_signal_intent_rejects_invalid_side():
    with pytest.raises(ValueError):
        SignalIntent(
            strategy_id="fixture_long",
            symbol="BTC/USDT",
            side="SIDEWAYS",
            timeframe="1h",
            candle_ts=datetime.now(timezone.utc),
            entry_type="bad",
            stop_hint=StopHint(price=1.0),
        )


def test_allowed_symbols_filter_snapshot_and_plugin_context():
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()
    context = _context(bot, ["ETH/USDT", "BTC/USDT", "SOL/USDT"])

    assert runtime._symbols_for_snapshot(context.symbols, [plugin]) == ["BTC/USDT"]
    assert runtime._context_for_plugin(context, plugin).symbols == ["BTC/USDT"]


def test_snapshot_builder_uses_plugin_timeframes_after_param_override(monkeypatch):
    calls = []
    bot = _FakeBot()

    def _fetch_ohlcv(symbol, timeframe, limit=100):
        calls.append((symbol, timeframe, limit))
        return _frame(rows=max(limit, 300))

    bot.fetch_ohlcv = _fetch_ohlcv
    monkeypatch.setattr("trader.strategy_runtime.IndicatorRegistry.apply", lambda df, indicators: df)

    builder = MarketSnapshotBuilder(bot)
    plugin = MacdSignalTrendingUp4hStrategy(
        params={"entry_timeframe": "1h", "trend_timeframe": "1d"}
    )

    snapshot = builder.build(["BTC/USDT"], [plugin])

    assert {(symbol, timeframe) for symbol, timeframe, _limit in calls} == {
        ("BTC/USDT", "1h"),
        ("BTC/USDT", "1d"),
    }
    assert not snapshot.get("BTC/USDT", "1h").empty
    assert not snapshot.get("BTC/USDT", "1d").empty


def test_allowed_symbol_mismatch_rejects_before_direct_route(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(symbol="ETH/USDT"), _context(bot, ["BTC/USDT"]))

    assert bot.executed_plans == []
    assert bot._signal_audit.rejects[-1]["reject_reason"] == "strategy_symbol_out_of_scope"


def test_runtime_side_filter_blocks_short_intent_when_long_only(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.STRATEGY_RUNTIME_SIDE_FILTER", "long")
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="SHORT"), _context(bot))

    assert bot.executed_plans == []
    reject = bot._signal_audit.rejects[-1]
    assert reject["reject_reason"] == "strategy_side_filter_blocked"
    assert reject["signal_side"] == "SHORT"
    assert reject["detail"] == "STRATEGY_RUNTIME_SIDE_FILTER=long"


def test_runtime_side_filter_blocks_long_intent_when_short_only(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.STRATEGY_RUNTIME_SIDE_FILTER", "short")
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))

    assert bot.executed_plans == []
    reject = bot._signal_audit.rejects[-1]
    assert reject["reject_reason"] == "strategy_side_filter_blocked"
    assert reject["signal_side"] == "LONG"
    assert reject["detail"] == "STRATEGY_RUNTIME_SIDE_FILTER=short"


def test_runtime_side_filter_allows_short_when_both(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.STRATEGY_RUNTIME_SIDE_FILTER", "both")
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="SHORT"), _context(bot))

    assert len(bot.executed_plans) == 1
    assert bot.executed_plans[0].intent.side == "SHORT"


def test_btc_trend_filter_diagnostic_mode_does_not_block_counter_trend(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_ENABLED", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_RUNTIME_MODE", "diagnostic")
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    bot._resolve_btc_trend_context = lambda log_event=False: {
        "source": "test",
        "trend": "SHORT",
        "reason": "unit_test",
    }
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))

    assert len(bot.executed_plans) == 1


def test_btc_trend_filter_skips_resolve_for_position_slot_reject(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_ENABLED", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_RUNTIME_MODE", "diagnostic")
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    bot.active_trades["BTC/USDT"] = SimpleNamespace(strategy_id="other", is_closed=False)
    bot._resolve_btc_trend_context = lambda log_event=False: pytest.fail(
        "BTC trend context should not resolve after a cheap slot reject"
    )
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))

    assert bot.executed_plans == []
    assert bot._signal_audit.rejects[-1]["reject_reason"] == "position_slot_occupied"


def test_btc_trend_filter_skips_resolve_for_router_reject(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_ENABLED", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_RUNTIME_MODE", "diagnostic")
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    bot._regime_arbiter_snapshot = SimpleNamespace(label="RANGING")
    bot.regime_arbiter = SimpleNamespace(can_enter=lambda snapshot, side: (False, "unit_router_block"))
    bot._resolve_btc_trend_context = lambda log_event=False: pytest.fail(
        "BTC trend context should not resolve after a router reject"
    )
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))

    assert bot.executed_plans == []
    reject = bot._signal_audit.rejects[-1]
    assert reject["reject_reason"] == "strategy_router_blocked"
    assert reject["detail"] == "unit_router_block"


def test_btc_trend_context_resolves_once_across_intents(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_ENABLED", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_RUNTIME_MODE", "diagnostic")
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    calls = 0

    def resolver(log_event=False):
        nonlocal calls
        calls += 1
        return {"source": "test", "trend": "LONG", "reason": "unit_test"}

    bot._resolve_btc_trend_context = resolver
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))
    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))

    assert calls == 1
    assert len(bot.executed_plans) == 2


def test_btc_trend_filter_enforce_mode_blocks_zero_mult_counter_trend(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_ENABLED", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_TREND_FILTER_RUNTIME_MODE", "enforce")
    monkeypatch.setattr("trader.strategy_runtime.Config.BTC_COUNTER_TREND_MULT", 0.0)
    bot = _FakeBot()
    bot._resolve_btc_trend_context = lambda log_event=False: {
        "source": "test",
        "trend": "SHORT",
        "reason": "unit_test",
    }
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(side="LONG"), _context(bot))

    assert bot.executed_plans == []
    reject = bot._signal_audit.rejects[-1]
    assert reject["reject_reason"] == "btc_trend_filter_blocked"
    assert reject["signal_side"] == "LONG"
    assert "mode=enforce" in reject["detail"]
    assert "trend=SHORT" in reject["detail"]


def test_config_rejects_invalid_runtime_side_filter(monkeypatch):
    monkeypatch.setattr(Config, "STRATEGY_RUNTIME_SIDE_FILTER", "sideways")

    with pytest.raises(ValueError, match="STRATEGY_RUNTIME_SIDE_FILTER"):
        Config.validate()


def test_config_rejects_invalid_btc_trend_filter_mode(monkeypatch):
    monkeypatch.setattr(Config, "BTC_TREND_FILTER_RUNTIME_MODE", "surprise")

    with pytest.raises(ValueError, match="BTC_TREND_FILTER_RUNTIME_MODE"):
        Config.validate()


def test_config_rejects_invalid_btc_counter_trend_mult(monkeypatch):
    monkeypatch.setattr(Config, "BTC_COUNTER_TREND_MULT", 1.5)

    with pytest.raises(ValueError, match="BTC_COUNTER_TREND_MULT"):
        Config.validate()


def test_runtime_defaults_promote_slot_b_short_overlay_without_slot_a_short():
    assert Config.STRATEGY_RUNTIME_ENABLED is True
    assert Config.STRATEGY_RUNTIME_SIDE_FILTER == "both"
    assert Config.ENABLED_STRATEGIES == [SLOT_A_LONG, SLOT_B_LONG, SLOT_B_SHORT]
    assert SLOT_A_SHORT not in Config.ENABLED_STRATEGIES


def test_strategy_position_limit_rejects_second_symbol_with_audit(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    bot.active_trades = {
        "BTC/USDT": SimpleNamespace(strategy_id="scoped", is_closed=False),
    }
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()
    plugin.allowed_symbols = {"BTC/USDT", "ETH/USDT"}

    runtime._process_intent(plugin, _intent(symbol="ETH/USDT"), _context(bot, ["BTC/USDT", "ETH/USDT"]))

    assert bot.executed_plans == []
    assert bot._signal_audit.rejects[-1]["reject_reason"] == "strategy_position_limit_reached"


def test_fixed_risk_profile_controls_position_size(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.DRY_RUN", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_SL_DISTANCE_PCT", 0.20)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_TOTAL_RISK", 0.50)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_POSITION_PERCENT", 1.0)
    monkeypatch.setattr("trader.strategy_runtime.Config.LEVERAGE", 1)
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()
    plugin.risk_profile = StrategyRiskProfile.fixed_risk_pct(0.01)

    plan = runtime._build_risk_plan(plugin, _intent(entry=100.0, stop=90.0), _context(bot))

    assert plan.allowed
    assert plan.position_size == pytest.approx(10.0)
    assert plan.max_loss_usdt == pytest.approx(100.0)
    assert plan.risk_pct == pytest.approx(0.01)


def test_fixed_risk_profile_still_shrinks_to_total_risk_budget(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.DRY_RUN", True)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_SL_DISTANCE_PCT", 0.20)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_TOTAL_RISK", 0.05)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_POSITION_PERCENT", 1.0)
    monkeypatch.setattr("trader.strategy_runtime.Config.LEVERAGE", 1)
    bot = _FakeBot()
    bot.current_open_risk = 490.0
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()
    plugin.risk_profile = StrategyRiskProfile.fixed_risk_pct(0.04)

    plan = runtime._build_risk_plan(plugin, _intent(entry=100.0, stop=90.0), _context(bot))

    assert plan.allowed
    assert plan.position_size == pytest.approx(1.0)
    assert plan.max_loss_usdt == pytest.approx(10.0)
    assert plan.risk_pct == pytest.approx(0.001)


def test_btc_trend_filter_risk_multiplier_scales_fixed_risk(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_SL_DISTANCE_PCT", 0.20)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_TOTAL_RISK", 0.50)
    monkeypatch.setattr("trader.strategy_runtime.Config.MAX_POSITION_PERCENT", 1.0)
    monkeypatch.setattr("trader.strategy_runtime.Config.LEVERAGE", 1)
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    plan = runtime._build_risk_plan(
        plugin,
        _intent(entry=100.0, stop=95.0),
        _context(bot),
        risk_multiplier=0.5,
    )

    assert plan.allowed
    assert plan.position_size == pytest.approx(10.0)
    assert plan.max_loss_usdt == pytest.approx(50.0)
    assert plan.risk_pct == pytest.approx(0.005)
