import pytest

import trader.bot as bot_module
from trader.bot import TradingBot, apply_runtime_mode_args, parse_runtime_args
from trader.config import Config
from trader.execution.order_engine import OrderExecutionEngine
from trader.infrastructure.api_client import (
    DEMO_FUTURES_BASE_URL,
    LIVE_FUTURES_BASE_URL,
    BinanceFuturesClient,
)


class _FakeExchange:
    def __init__(self, _config):
        self.urls = {"api": {"fapi": LIVE_FUTURES_BASE_URL}}
        self.options = {}
        self.markets = {"BTC/USDT": {}, "ETH/USDT": {}}
        self.sandbox_calls = []
        self.leverage_calls = []

    def set_sandbox_mode(self, enabled):
        self.sandbox_calls.append(enabled)

    def load_markets(self):
        return self.markets

    def set_leverage(self, leverage, symbol):
        self.leverage_calls.append((leverage, symbol))


class _FakeFuturesClient:
    def __init__(self):
        self.calls = []

    def signed_request_json(self, method, endpoint, params=None):
        self.calls.append((method, endpoint, dict(params or {})))
        if endpoint == "/fapi/v1/leverage":
            return {"leverage": params["leverage"]}
        return {"orderId": 1, "status": "FILLED"}


class _FakePrecision:
    def format_quantity(self, _symbol, _quantity):
        return "0.010"


def _init_exchange(monkeypatch, sandbox, allow_live_leverage_set):
    created = []

    def _factory(config):
        exchange = _FakeExchange(config)
        created.append(exchange)
        return exchange

    monkeypatch.setattr(Config, "EXCHANGE", "binance")
    monkeypatch.setattr(Config, "TRADING_MODE", "future")
    monkeypatch.setattr(Config, "SANDBOX_MODE", sandbox)
    monkeypatch.setattr(Config, "SYMBOLS", ["BTC/USDT", "ETH/USDT"])
    monkeypatch.setattr(Config, "LEVERAGE", 3)
    monkeypatch.setattr(bot_module.ccxt, "binance", _factory)

    bot = object.__new__(TradingBot)
    bot.allow_live_leverage_set = allow_live_leverage_set
    return bot._init_exchange(), created[0]


def test_dry_run_flag_does_not_imply_live(monkeypatch):
    monkeypatch.setattr(Config, "DRY_RUN", False)
    monkeypatch.setattr(Config, "SANDBOX_MODE", True)

    args = parse_runtime_args(["--dry-run"])
    apply_runtime_mode_args(args)

    assert Config.DRY_RUN is True
    assert Config.SANDBOX_MODE is True


def test_no_live_flag_keeps_demo_default(monkeypatch):
    monkeypatch.setattr(Config, "DRY_RUN", False)
    monkeypatch.setattr(Config, "SANDBOX_MODE", True)

    args = parse_runtime_args([])
    apply_runtime_mode_args(args)

    assert Config.DRY_RUN is False
    assert Config.SANDBOX_MODE is True


def test_live_flag_selects_live_endpoint_process_local(monkeypatch):
    monkeypatch.setattr(Config, "DRY_RUN", False)
    monkeypatch.setattr(Config, "SANDBOX_MODE", True)

    args = parse_runtime_args(["--live"])
    apply_runtime_mode_args(args)

    assert Config.DRY_RUN is False
    assert Config.SANDBOX_MODE is False


def test_live_and_dry_run_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        parse_runtime_args(["--dry-run", "--live"])


def test_live_leverage_flag_requires_live():
    with pytest.raises(SystemExit):
        parse_runtime_args(["--allow-live-leverage-set"])


def test_futures_client_endpoint_selection():
    assert BinanceFuturesClient("key", "secret", sandbox=True).base_url == DEMO_FUTURES_BASE_URL
    assert BinanceFuturesClient("key", "secret", sandbox=False).base_url == LIVE_FUTURES_BASE_URL


def test_startup_leverage_is_skipped_in_live_default(monkeypatch):
    _, exchange = _init_exchange(monkeypatch, sandbox=False, allow_live_leverage_set=False)

    assert exchange.leverage_calls == []


def test_startup_leverage_is_allowed_in_live_only_with_explicit_gate(monkeypatch):
    _, exchange = _init_exchange(monkeypatch, sandbox=False, allow_live_leverage_set=True)

    assert exchange.leverage_calls == [(3, "BTC/USDT"), (3, "ETH/USDT")]


def test_startup_leverage_preserves_demo_behavior(monkeypatch):
    _, exchange = _init_exchange(monkeypatch, sandbox=True, allow_live_leverage_set=False)

    assert exchange.sandbox_calls == [True]
    assert exchange.leverage_calls == [(3, "BTC/USDT"), (3, "ETH/USDT")]


def test_live_order_path_skips_implicit_leverage_by_default(monkeypatch):
    monkeypatch.setattr(Config, "SANDBOX_MODE", False)
    client = _FakeFuturesClient()
    engine = OrderExecutionEngine(None, client, _FakePrecision())

    engine.create_order("ETH/USDT", "BUY", 0.01)

    assert [call[1] for call in client.calls] == ["/fapi/v1/order"]


def test_live_order_path_allows_leverage_only_with_explicit_gate(monkeypatch):
    monkeypatch.setattr(Config, "SANDBOX_MODE", False)
    client = _FakeFuturesClient()
    engine = OrderExecutionEngine(
        None,
        client,
        _FakePrecision(),
        allow_live_leverage_set=True,
    )

    engine.create_order("ETH/USDT", "BUY", 0.01)

    assert [call[1] for call in client.calls] == ["/fapi/v1/leverage", "/fapi/v1/order"]


def test_demo_order_path_preserves_existing_leverage_behavior(monkeypatch):
    monkeypatch.setattr(Config, "SANDBOX_MODE", True)
    client = _FakeFuturesClient()
    engine = OrderExecutionEngine(None, client, _FakePrecision())

    engine.create_order("ETH/USDT", "BUY", 0.01)

    assert [call[1] for call in client.calls] == ["/fapi/v1/leverage", "/fapi/v1/order"]


def test_scanner_and_router_defaults_remain_guarded():
    assert Config.USE_SCANNER_SYMBOLS is False
    assert Config.SCANNER_UNIVERSE_ENABLED is False
    assert Config.STRATEGY_ROUTER_POLICY == "fail_closed"
