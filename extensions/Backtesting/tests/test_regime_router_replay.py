import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import regime_router_replay


def _bot_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    candidate = root / "projects" / "trading_bot" / ".worktrees" / "feat-regime-router"
    if not (candidate / "trader" / "bot.py").exists():
        pytest.skip("feat-regime-router worktree is not available")
    return candidate


def _btc_4h(rows: int = 90) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=rows, freq="4h", tz="UTC")
    close = np.linspace(100.0, 130.0, rows)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(rows, 1000.0),
        },
        index=idx,
    )


def test_replay_outputs_router_schema(tmp_path, monkeypatch):
    bot_root = _bot_root()
    regime_router_replay._bootstrap_bot_root(bot_root)

    from data_loader import BacktestDataLoader

    monkeypatch.setattr(BacktestDataLoader, "get_data", lambda *args, **kwargs: _btc_4h())

    rows, summary = regime_router_replay.run_replay(
        symbols=["BTC/USDT"],
        start="2025-01-01",
        end="2025-01-20",
        output_dir=tmp_path,
        bot_root=bot_root,
        warmup_bars=60,
    )

    assert not rows.empty
    assert {
        "raw_regime",
        "arbiter_label",
        "arbiter_confidence",
        "router_decision",
        "router_allowed",
        "router_selected_strategy",
        "router_block_reason",
        "mixed_bucket",
    }.issubset(rows.columns)
    assert (tmp_path / "regime_router_replay.csv").exists()
    assert (tmp_path / "regime_router_replay_summary.json").exists()
    assert summary["rows"] == len(rows)


def test_backtest_context_restores_config(monkeypatch):
    bot_root = _bot_root()
    regime_router_replay._bootstrap_bot_root(bot_root)

    from backtest_engine import _backtest_context
    from bot_compat import get_config_class

    Config = get_config_class()
    monkeypatch.setattr(Config, "REGIME_ROUTER_ENABLED", True, raising=False)

    with _backtest_context({"REGIME_ROUTER_ENABLED": False}) as ScopedConfig:
        assert ScopedConfig.REGIME_ROUTER_ENABLED is False

    assert Config.REGIME_ROUTER_ENABLED is True
