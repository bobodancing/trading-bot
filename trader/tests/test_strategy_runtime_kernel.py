from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

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
from trader.strategies.plugins.fixture import FixtureLongStrategy
from trader.strategy_runtime import StrategyRuntime


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


def _intent(symbol="BTC/USDT", strategy_id="scoped", entry=100.0, stop=95.0):
    return SignalIntent(
        strategy_id=strategy_id,
        symbol=symbol,
        side="LONG",
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


def test_strategy_registry_fail_closed_when_empty():
    registry = StrategyRegistry.from_config({}, [])
    assert registry.plugins == {}


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


def test_allowed_symbol_mismatch_rejects_before_direct_route(monkeypatch):
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ARBITER_ENABLED", False)
    monkeypatch.setattr("trader.strategy_runtime.Config.REGIME_ROUTER_ENABLED", False)
    bot = _FakeBot()
    runtime = StrategyRuntime(bot)
    plugin = _ScopedStrategy()

    runtime._process_intent(plugin, _intent(symbol="ETH/USDT"), _context(bot, ["BTC/USDT"]))

    assert bot.executed_plans == []
    assert bot._signal_audit.rejects[-1]["reject_reason"] == "strategy_symbol_out_of_scope"


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
