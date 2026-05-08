"""Shared path helpers for the Backtesting workspace."""

from __future__ import annotations

import os
import sys
from pathlib import Path


BACKTEST_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKTEST_ROOT.parents[1]


def _is_repo_root(path: Path) -> bool:
    return (path / "trader" / "bot.py").exists()


def resolve_repo_root() -> Path:
    """Resolve the local trading bot repo root without legacy worktree fallbacks."""
    env = os.environ.get("TRADING_BOT_ROOT")
    if env:
        root = Path(env).expanduser().resolve()
        if not _is_repo_root(root):
            raise RuntimeError(f"TRADING_BOT_ROOT does not point at this repo layout: {root}")
        return root

    root = REPO_ROOT.resolve()
    if not _is_repo_root(root):
        raise RuntimeError(f"Cannot resolve trading bot repo root from Backtesting workspace: {root}")
    return root


def ensure_on_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    resolved_s = str(resolved)
    if resolved_s not in sys.path:
        sys.path.insert(0, resolved_s)
    return resolved


def ensure_repo_root_on_path() -> Path:
    return ensure_on_path(resolve_repo_root())


def ensure_backtest_root_on_path() -> Path:
    return ensure_on_path(BACKTEST_ROOT)
