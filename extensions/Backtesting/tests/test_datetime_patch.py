"""驗證 datetime patch 覆蓋所有使用 datetime.now() 的 module"""
import sys
from pathlib import Path

TRADING_BOT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "projects" / "trading_bot"
sys.path.insert(0, str(TRADING_BOT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
from backtest_engine import _backtest_context, _sim_ts_container
from bot_compat import get_strategy_modules


def test_strategy_datetime_uses_simulated_time():
    """v53_sop 和 v6_pyramid 的 datetime.now() 必須回傳模擬時間"""
    from datetime import timezone

    strategy_modules = get_strategy_modules()
    v53_sop = strategy_modules["v53"]
    v6_pyramid = strategy_modules["v6"]

    sim_time = pd.Timestamp("2026-02-15 12:00:00", tz="UTC")

    with _backtest_context({}):
        _sim_ts_container[0] = sim_time

        # 取 strategy module 中的 datetime class，呼叫 now()
        v53_now = v53_sop.datetime.now(timezone.utc)
        v6_now = v6_pyramid.datetime.now(timezone.utc)

        assert v53_now.year == 2026
        assert v53_now.month == 2
        assert v53_now.day == 15
        assert v53_now.hour == 12

        assert v6_now.year == 2026
        assert v6_now.month == 2
        assert v6_now.day == 15
        assert v6_now.hour == 12


def test_strategy_datetime_restored_after_context():
    """離開 context 後 datetime 必須還原"""
    strategy_modules = get_strategy_modules()
    v53_sop = strategy_modules["v53"]
    v6_pyramid = strategy_modules["v6"]

    original_v53 = v53_sop.datetime
    original_v6 = v6_pyramid.datetime

    with _backtest_context({}):
        pass  # just enter and exit

    assert v53_sop.datetime is original_v53
    assert v6_pyramid.datetime is original_v6
