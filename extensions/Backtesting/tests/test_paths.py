"""Validate Backtesting path resolution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backtest_engine import _resolve_bot_root
from paths import resolve_repo_root


def test_trading_bot_root_from_env(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "trader").mkdir(parents=True)
    (repo / "trader" / "bot.py").write_text("# fake bot\n", encoding="utf-8")

    monkeypatch.setenv("TRADING_BOT_ROOT", str(repo))
    result = _resolve_bot_root()
    assert result == repo.resolve()


def test_trading_bot_root_from_env_rejects_wrong_layout(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADING_BOT_ROOT", str(tmp_path))

    with pytest.raises(RuntimeError, match="TRADING_BOT_ROOT"):
        resolve_repo_root()


def test_trading_bot_root_fallback(monkeypatch):
    monkeypatch.delenv("TRADING_BOT_ROOT", raising=False)
    local_repo = Path(__file__).resolve().parents[3]
    result = _resolve_bot_root()
    assert result == local_repo.resolve()
