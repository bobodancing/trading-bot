import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from backtest_engine import BacktestConfig, BacktestEngine


def make_fake_df(n=720, start_price=40000.0):
    idx = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    prices = [start_price + i * 0.5 for i in range(n)]
    return pd.DataFrame({
        "open":   prices,
        "high":   [p + 100 for p in prices],
        "low":    [p - 100 for p in prices],
        "close":  prices,
        "volume": [100.0] * n,
    }, index=idx)


def test_backtest_engine_smoke(monkeypatch):
    """
    Smoke test: BacktestEngine 執行完成，回傳有效 BacktestResult。
    使用 monkeypatch 替換 DataLoader 避免真實網路請求。
    """
    from data_loader import BacktestDataLoader

    df = make_fake_df(720)

    def fake_get_data(self, symbol, timeframe, start, end):
        return df

    monkeypatch.setattr(BacktestDataLoader, "get_data", fake_get_data)

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
        warmup_bars=50,
    )
    engine = BacktestEngine(config)
    result = engine.run()

    assert result is not None
    assert len(result.equity_curve) > 0
    assert result.summary["total_trades"] >= 0
    # equity_curve values should be in a reasonable range
    first_val = result.equity_curve[0][1]
    assert abs(first_val - 10000.0) < 500  # warmup bars record initial_balance exactly


def test_backtest_result_summary_no_trades():
    """無交易時 summary 應回傳合理預設值"""
    from backtest_engine import BacktestResult, BacktestConfig

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
    )
    idx = pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC")
    equity_curve = [(ts, 10000.0) for ts in idx]

    result = BacktestResult(trades=[], equity_curve=equity_curve, config=config)
    s = result.summary
    assert s["total_trades"] == 0
    assert s["win_rate"] == 0.0
    assert s["profit_factor"] == 0.0
    assert s["total_return_pct"] == 0.0
    assert s["max_drawdown_pct"] == 0.0


def test_backtest_result_summary_with_trades():
    """有盈虧交易時 summary 計算應正確"""
    from backtest_engine import BacktestResult, BacktestConfig

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
    )
    trades = [
        {"pnl_usdt": 200.0},   # win
        {"pnl_usdt": 150.0},   # win
        {"pnl_usdt": -100.0},  # loss
    ]
    idx = pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC")
    values = [10000.0, 10200.0, 10350.0, 10250.0, 10250.0]
    equity_curve = list(zip(idx, values))

    result = BacktestResult(trades=trades, equity_curve=equity_curve, config=config)
    s = result.summary
    assert s["total_trades"] == 3
    assert abs(s["win_rate"] - 2/3) < 0.001
    # gross_profit=350, gross_loss=100 → PF=3.5
    assert abs(s["profit_factor"] - 3.5) < 0.01
    # total_pnl = 250, initial=10000 → 2.5%
    assert abs(s["total_return_pct"] - 2.5) < 0.01
    # peak=10350, trough=10250 → dd=(100/10350)*100 ≈ 0.966%
    assert s["max_drawdown_pct"] > 0


def test_backtest_engine_equity_curve_length(monkeypatch):
    """equity_curve 長度應 == 總 bar 數（warmup + active）"""
    from data_loader import BacktestDataLoader

    n = 200
    df = make_fake_df(n)

    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
        warmup_bars=50,
    )
    engine = BacktestEngine(config)
    result = engine.run()

    # equity_curve 長度應等於 1H bar 總數
    assert len(result.equity_curve) == n


def test_simulation_time_patch_restores_after_run(monkeypatch):
    """
    BacktestEngine.run() 完成後，trader.bot.datetime 應還原為原始 datetime class，
    且 _sim_ts_container 應重置為 None（避免跨 session 污染）。
    """
    import trader.bot as _bot_mod
    import datetime as _real_dt
    from data_loader import BacktestDataLoader

    df = make_fake_df(200)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)

    original_datetime = _bot_mod.datetime

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
        warmup_bars=50,
    )
    engine = BacktestEngine(config)
    engine.run()

    # Patch 應完整還原
    assert _bot_mod.datetime is original_datetime, "trader.bot.datetime was not restored after run()"

    # sim_ts_container 應清回 None
    from backtest_engine import _sim_ts_container
    assert _sim_ts_container[0] is None, "_sim_ts_container not reset to None after run()"


def test_backtest_engine_warmup_uses_initial_balance(monkeypatch):
    """warmup 期間的 equity_curve 值應等於 initial_balance"""
    from data_loader import BacktestDataLoader

    n = 100
    warmup = 30
    df = make_fake_df(n)

    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
        warmup_bars=warmup,
    )
    engine = BacktestEngine(config)
    result = engine.run()

    # warmup 期間全部應等於 initial_balance
    for _, val in result.equity_curve[:warmup]:
        assert val == 10000.0


def test_trades_per_week_in_summary():
    """summary 應包含 trades_per_week，且計算正確"""
    from backtest_engine import BacktestResult, BacktestConfig

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-29",  # 28 days = 4 weeks
        initial_balance=10000.0,
    )
    trades = [{"pnl_usdt": 100.0}] * 20  # 20 trades in 4 weeks = 5/week
    idx = pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC")
    equity_curve = [(ts, 10000.0) for ts in idx]

    result = BacktestResult(trades=trades, equity_curve=equity_curve, config=config)
    assert "trades_per_week" in result.summary
    assert result.summary["trades_per_week"] == 5.0


def test_trades_per_week_no_trades():
    """無交易時 trades_per_week 應為 0"""
    from backtest_engine import BacktestResult, BacktestConfig

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
    )
    idx = pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC")
    equity_curve = [(ts, 10000.0) for ts in idx]

    result = BacktestResult(trades=[], equity_curve=equity_curve, config=config)
    assert result.summary["trades_per_week"] == 0.0


def test_run_single_returns_result(monkeypatch):
    """run_single() 應回傳 BacktestResult（與 run() 行為一致）"""
    from data_loader import BacktestDataLoader

    df = make_fake_df(200)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
        warmup_bars=50,
    )
    engine = BacktestEngine(config)
    result = engine.run_single(verbose=False)

    assert result is not None
    assert len(result.equity_curve) > 0
    assert "trades_per_week" in result.summary


def test_record_regime_probe_records_unique_candles():
    from backtest_engine import _record_regime_probe
    from signal_audit import SignalAuditCollector

    contexts = [
        {
            "regime": "TRENDING",
            "direction": "LONG",
            "candle_time": "2026-01-01T00:00:00+00:00",
            "reason": "regime_updated",
        },
        {
            "regime": "TRENDING",
            "direction": "LONG",
            "candle_time": "2026-01-01T00:00:00+00:00",
            "reason": "regime_updated",
        },
        {
            "regime": "RANGING",
            "direction": "SHORT",
            "candle_time": "2026-01-01T04:00:00+00:00",
            "reason": "regime_updated",
        },
    ]

    audit = SignalAuditCollector()
    bot = SimpleNamespace(
        _signal_audit=audit,
        _update_btc_regime_context=lambda: contexts.pop(0),
    )

    _record_regime_probe(bot, "2026-01-01T00:00:00+00:00", grid_enabled=False)
    _record_regime_probe(bot, "2026-01-01T01:00:00+00:00", grid_enabled=False)
    _record_regime_probe(bot, "2026-01-01T04:00:00+00:00", grid_enabled=False)

    df = audit.btc_trend_df()
    assert len(df) == 2
    assert df["source"].tolist() == ["regime_probe", "regime_probe"]
    assert df["regime"].tolist() == ["TRENDING", "RANGING"]
    assert df["trend"].tolist() == ["LONG", "RANGING"]


def test_backtest_engine_records_regime_probe_when_grid_disabled(monkeypatch):
    from data_loader import BacktestDataLoader

    df = make_fake_df(200)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        initial_balance=10000.0,
        warmup_bars=20,
    )
    engine = BacktestEngine(config)
    result = engine.run_single(verbose=False)

    summary = result.signal_audit.summary()
    assert summary["btc_source_distribution"].get("regime_probe", 0) > 0


def test_effective_overrides_enable_strategy_runtime_without_catalog_override():
    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        enabled_strategies=["fixture_long"],
        dry_count_only=True,
        precompute_indicators=True,
    )
    engine = BacktestEngine(config)

    overrides = engine._effective_config_overrides(config)

    assert overrides["STRATEGY_RUNTIME_ENABLED"] is True
    assert overrides["ENABLED_STRATEGIES"] == ["fixture_long"]
    assert "STRATEGY_CATALOG" not in overrides
    assert "BACKTEST_DRY_COUNT_ONLY" not in overrides
    assert "BACKTEST_USE_PRECOMPUTED_INDICATORS" not in overrides


def test_dry_count_only_records_candidate_without_opening_trade(monkeypatch):
    from data_loader import BacktestDataLoader
    from funding_loader import FundingLoader

    df = make_fake_df(200)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)
    monkeypatch.setattr(FundingLoader, "get_funding_rates", lambda self, *a, **kw: pd.Series(dtype=float))

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        warmup_bars=20,
        enabled_strategies=["fixture_long"],
        allowed_plugin_ids=["fixture_long"],
        dry_count_only=True,
        config_overrides={
            "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
        },
    )

    result = BacktestEngine(config).run_single(verbose=False)

    assert result.trades == []
    assert result.summary["total_trades"] == 0
    assert result.signal_audit.summary()["entries_by_signal_type"]["fixture_long"] > 0


def test_backtest_trade_records_strategy_trace(monkeypatch):
    from data_loader import BacktestDataLoader
    from funding_loader import FundingLoader

    df = make_fake_df(200)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)
    monkeypatch.setattr(FundingLoader, "get_funding_rates", lambda self, *a, **kw: pd.Series(dtype=float))

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        warmup_bars=20,
        enabled_strategies=["fixture_long"],
        allowed_plugin_ids=["fixture_long"],
        config_overrides={
            "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
        },
    )

    result = BacktestEngine(config).run_single(verbose=False)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade["strategy_id"] == "fixture_long"
    assert trade["strategy_version"] == "1.0.0"
    assert trade["exit_strategy"] == "fixture_long"


def test_backtest_strategy_params_override_changes_per_run_plugin_params(monkeypatch):
    from data_loader import BacktestDataLoader
    from funding_loader import FundingLoader

    df = make_fake_df(200)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)
    monkeypatch.setattr(FundingLoader, "get_funding_rates", lambda self, *a, **kw: pd.Series(dtype=float))

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-30",
        warmup_bars=20,
        enabled_strategies=["fixture_long"],
        allowed_plugin_ids=["fixture_long"],
        strategy_params_override={"fixture_long": {"stop_pct": 0.02}},
        config_overrides={
            "SYMBOL_LOSS_COOLDOWN_HOURS": 0,
            "REGIME_ARBITER_ENABLED": False,
            "REGIME_ROUTER_ENABLED": False,
        },
    )

    result = BacktestEngine(config).run_single(verbose=False)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert float(trade["entry_initial_sl"]) == pytest.approx(float(trade["entry_price"]) * 0.98)


def test_backtest_loop_records_scanner_exception(monkeypatch):
    import backtest_engine as engine_mod
    from data_loader import BacktestDataLoader
    from funding_loader import FundingLoader

    df = make_fake_df(5)
    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda self, *a, **kw: df)
    monkeypatch.setattr(FundingLoader, "get_funding_rates", lambda self, *a, **kw: pd.Series(dtype=float))

    calls = {"scan": 0}

    def scan_for_signals():
        calls["scan"] += 1
        if calls["scan"] == 1:
            raise RuntimeError("scanner boom")

    fake_bot = SimpleNamespace(
        active_trades={},
        regime_engine=None,
        perf_db=SimpleNamespace(),
        scan_for_signals=scan_for_signals,
        monitor_positions=lambda: None,
        _update_btc_regime_context=lambda: {
            "regime": "TRENDING",
            "direction": "LONG",
            "candle_time": "2026-01-01T00:00:00+00:00",
            "reason": "test",
        },
    )
    monkeypatch.setattr(engine_mod, "create_backtest_bot", lambda *a, **kw: fake_bot)

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start="2026-01-01",
        end="2026-01-02",
        warmup_bars=0,
    )
    result = BacktestEngine(config).run_single(verbose=False)

    assert result.summary["backtest_run_error_count"] == 1
    assert result.summary["backtest_run_errors"][0]["stage"] == "scan_for_signals"
    assert result.summary["backtest_run_errors"][0]["exc_type"] == "RuntimeError"
    assert "scanner boom" in result.summary["backtest_run_errors"][0]["message"]
