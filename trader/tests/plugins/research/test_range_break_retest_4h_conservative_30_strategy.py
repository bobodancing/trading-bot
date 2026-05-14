from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from trader.strategies.base import Action, MarketSnapshot, StrategyContext
from trader.strategies.plugins.range_break_retest_4h_conservative_30 import (
    RangeBreakRetest4hConservative30Strategy,
)


def _context(frame: pd.DataFrame, symbol: str = "BTC/USDT") -> StrategyContext:
    return StrategyContext(
        snapshot=MarketSnapshot(
            frames={symbol: {"4h": frame}},
            generated_at=datetime.now(timezone.utc),
        ),
        symbols=[symbol],
        active_positions={},
        config=None,
        now=datetime.now(timezone.utc),
    )


def _range_break_frame(*, side: str = "LONG", latest_close: float | None = None) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=90, freq="4h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": 100.0,
            "high": 110.0,
            "low": 90.0,
            "close": 100.0,
            "volume": 1000.0,
            "atr": 2.0,
            "adx": 15.0,
            "bbw": 0.06,
            "ema_20": 101.0,
            "ema_50": 100.0,
        },
        index=idx,
    )
    frame.loc[idx[-60:], "bbw"] = 0.05
    frame.loc[idx[-7], "adx"] = 16.0
    frame.loc[idx[-2:], "bbw"] = 0.01
    if side == "LONG":
        frame.loc[idx[-2], ["open", "high", "low", "close"]] = [110.0, 113.0, 109.0, 112.0]
        frame.loc[idx[-1], ["open", "high", "low", "close"]] = [
            111.0,
            112.0,
            110.4,
            latest_close or 111.5,
        ]
    else:
        frame.loc[idx[-2], ["open", "high", "low", "close"]] = [90.0, 91.0, 87.0, 88.0]
        frame.loc[idx[-1], ["open", "high", "low", "close"]] = [
            89.0,
            89.6,
            88.0,
            latest_close or 88.5,
        ]
    return frame


class _Position:
    symbol = "BTC/USDT"
    side = "LONG"
    avg_entry = 111.5
    initial_sl = 108.5
    metadata = {
        "range_boundary": 110.0,
        "candle_ts": "2026-01-15T20:00:00+00:00",
        "profit_target_r": 1.5,
        "max_hold_bars": 18,
        "failure_atr_mult": 0.25,
    }


def test_range_break_retest_emits_long_candidate_from_first_boundary_retest() -> None:
    plugin = RangeBreakRetest4hConservative30Strategy()

    intents = plugin.generate_candidates(_context(_range_break_frame()))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.strategy_id == "range_break_retest_4h_conservative_30"
    assert intent.side == "LONG"
    assert intent.entry_type == "range_break_retest_continuation"
    assert intent.stop_hint.price == pytest.approx(108.5)
    assert intent.metadata["range_boundary"] == pytest.approx(110.0)
    assert intent.metadata["retest_lag_bars"] == 1
    assert intent.metadata["break_strength_atr"] == pytest.approx(1.0)
    assert intent.metadata["candidate_family"] == "range_break_retest_frequency_complement"


def test_range_break_retest_emits_short_candidate_with_stop_above_entry() -> None:
    plugin = RangeBreakRetest4hConservative30Strategy()

    intents = plugin.generate_candidates(_context(_range_break_frame(side="SHORT")))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.side == "SHORT"
    assert intent.entry_price == pytest.approx(88.5)
    assert intent.stop_hint.price == pytest.approx(91.5)
    assert intent.metadata["range_boundary"] == pytest.approx(90.0)


def test_range_break_retest_rejects_low_quality_breakout() -> None:
    frame = _range_break_frame()
    frame.iloc[-2, frame.columns.get_loc("close")] = 110.2
    plugin = RangeBreakRetest4hConservative30Strategy()

    assert plugin.generate_candidates(_context(frame)) == []


def test_range_break_retest_rejects_wide_range_pct_override() -> None:
    plugin = RangeBreakRetest4hConservative30Strategy(
        params={"range_width_pct_max": 0.05}
    )

    assert plugin.generate_candidates(_context(_range_break_frame())) == []


def test_range_break_retest_rejects_deep_boundary_pierce_override() -> None:
    plugin = RangeBreakRetest4hConservative30Strategy(
        params={"min_retest_distance_atr": 0.25}
    )

    assert plugin.generate_candidates(_context(_range_break_frame())) == []


def test_range_break_retest_closes_on_boundary_failure() -> None:
    frame = _range_break_frame(latest_close=109.0)
    position = _Position()
    plugin = RangeBreakRetest4hConservative30Strategy()

    decision = plugin.update_position(_context(frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "RANGE_BREAK_RETEST_BOUNDARY_FAIL"


def test_range_break_retest_closes_on_target_r() -> None:
    frame = _range_break_frame(latest_close=116.1)
    position = _Position()
    plugin = RangeBreakRetest4hConservative30Strategy()

    decision = plugin.update_position(_context(frame), position)

    assert decision.action == Action.CLOSE
    assert decision.reason == "RANGE_BREAK_RETEST_TARGET_R"
