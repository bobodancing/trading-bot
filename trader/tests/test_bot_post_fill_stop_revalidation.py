from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from trader.bot import TradingBot
from trader.config import Config
from trader.strategies import ExecutableOrderPlan, RiskPlan, SignalIntent, StopHint


class _AuditCollector:
    def __init__(self):
        self.rejects = []

    def record_reject(self, **kwargs):
        self.rejects.append(kwargs)


class _Exchange:
    def __init__(self, fill_price: float):
        self.fill_price = fill_price
        self.orders = []

    def create_order(self, **kwargs):
        self.orders.append(kwargs)
        return {
            "avgPrice": self.fill_price,
            "side": str(kwargs.get("side", "")).upper(),
            "status": "FILLED",
        }


class _ExecutionEngine:
    def __init__(self, reverse_fill: float):
        self.reverse_fill = reverse_fill
        self.close_calls = []

    def close_position(self, symbol: str, side: str, quantity: float) -> dict:
        self.close_calls.append((symbol, side, quantity))
        return {
            "avgPrice": self.reverse_fill,
            "side": side,
            "status": "FILLED",
        }


def _plan(*, side: str, entry: float, stop: float) -> ExecutableOrderPlan:
    return ExecutableOrderPlan(
        intent=SignalIntent(
            strategy_id="fixture_long",
            symbol="BTC/USDT",
            side=side,
            timeframe="1h",
            candle_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            entry_type="test_market",
            stop_hint=StopHint(price=stop),
            entry_price=entry,
        ),
        risk_plan=RiskPlan(
            entry_price=entry,
            stop_loss=stop,
            position_size=0.5,
            max_loss_usdt=2.5,
            risk_pct=0.01,
            hard_stop_required=True,
        ),
        strategy_version="1.0.0",
    )


def _bot(*, exchange, execution_engine=None, is_backtest=False):
    bot = TradingBot.__new__(TradingBot)
    bot.exchange = exchange
    bot.execution_engine = execution_engine or MagicMock()
    bot._is_backtest = is_backtest
    bot.active_trades = {}
    bot.order_failed_symbols = {}
    bot._signal_audit = _AuditCollector()
    bot._btc_regime_context = {}
    bot._save_positions = MagicMock()
    bot._place_hard_stop_loss = MagicMock()
    return bot


@pytest.mark.parametrize(
    ("side", "entry", "stop", "fill", "reason"),
    [
        ("LONG", 100.0, 95.0, 94.0, "long_fill_below_stop"),
        ("SHORT", 100.0, 105.0, 106.0, "short_fill_above_stop"),
    ],
)
def test_post_fill_stop_violation_blocks_position_for_backtest_marker(
    monkeypatch,
    side,
    entry,
    stop,
    fill,
    reason,
):
    monkeypatch.setattr(Config, "DRY_RUN", False)
    monkeypatch.setattr("trader.bot.BinanceFuturesClient.is_enabled", staticmethod(lambda: False))

    exchange = MagicMock()
    exchange.create_order.return_value = {
        "avgPrice": entry,
        "side": "BUY" if side == "LONG" else "SELL",
        "status": "FILLED",
    }
    execution_engine = MagicMock()
    bot = _bot(exchange=exchange, execution_engine=execution_engine, is_backtest=True)
    bot._extract_fill_price = MagicMock(return_value=fill)

    bot._execute_order_plan(_plan(side=side, entry=entry, stop=stop))

    assert bot.active_trades == {}
    assert "BTC/USDT" in bot.order_failed_symbols
    bot._save_positions.assert_not_called()
    bot._place_hard_stop_loss.assert_not_called()
    execution_engine.close_position.assert_not_called()
    bot._extract_fill_price.assert_called_once()
    assert bot._signal_audit.rejects[-1]["reject_reason"] == "post_fill_stop_violation"
    assert bot._signal_audit.rejects[-1]["stage"] == "execution"
    assert bot._signal_audit.rejects[-1]["detail"] == reason


def test_post_fill_stop_violation_flattens_live_exchange_without_perfdb(monkeypatch):
    monkeypatch.setattr(Config, "DRY_RUN", False)
    monkeypatch.setattr("trader.bot.BinanceFuturesClient.is_enabled", staticmethod(lambda: False))

    exchange = _Exchange(fill_price=94.0)
    execution_engine = _ExecutionEngine(reverse_fill=94.2)
    bot = _bot(exchange=exchange, execution_engine=execution_engine)
    bot.perf_db = MagicMock()
    bot._extract_fill_price = MagicMock(side_effect=[94.0, 94.2])

    bot._execute_order_plan(_plan(side="LONG", entry=100.0, stop=95.0))

    assert bot.active_trades == {}
    assert len(exchange.orders) == 1
    assert execution_engine.close_calls == [("BTC/USDT", "LONG", 0.5)]
    bot.perf_db.record_trade.assert_not_called()
    bot._save_positions.assert_not_called()
    assert bot._extract_fill_price.call_count == 2
    assert bot._signal_audit.rejects[-1]["reject_reason"] == "post_fill_stop_violation"
    assert bot._signal_audit.rejects[-1]["stage"] == "execution"
