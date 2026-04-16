"""驗證路徑解析邏輯"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backtest_engine import _resolve_bot_root


def test_trading_bot_root_from_env(monkeypatch):
    """TRADING_BOT_ROOT 環境變數優先"""
    monkeypatch.setenv("TRADING_BOT_ROOT", "/custom/path")
    result = _resolve_bot_root()
    assert result == Path("/custom/path").resolve()


def test_trading_bot_root_fallback(monkeypatch):
    """沒有環境變數時優先解析目前獨立 repo，再 fallback 到舊 worktree。"""
    monkeypatch.delenv("TRADING_BOT_ROOT", raising=False)
    local_repo = Path(__file__).resolve().parents[3]
    if (local_repo / "trader" / "bot.py").exists():
        expected = local_repo
    else:
        workspace = local_repo.parent
        candidates = (
            workspace / "projects" / "trading_bot" / ".worktrees" / "feat-regime-router",
            workspace / "projects" / "trading_bot" / ".worktrees" / "feat-grid",
            workspace / "projects" / "trading_bot",
        )
        expected = next((p for p in candidates if (p / "trader" / "bot.py").exists()), local_repo)
    result = _resolve_bot_root()
    assert result == expected.resolve()
