"""
Unit tests for EMA pullback and volume breakout signal detectors.
"""

import pandas as pd

from trader.signals import detect_ema_pullback, detect_volume_breakout


def _make_df(rows: int = 40, **overrides) -> pd.DataFrame:
    """Build a minimal OHLCV dataframe with indicator columns."""
    base = {
        "open": [100.0] * rows,
        "high": [102.0] * rows,
        "low": [98.0] * rows,
        "close": [101.0] * rows,
        "volume": [1000.0] * rows,
        "ema_fast": [100.0] * rows,
        "ema_slow": [99.0] * rows,
        "atr": [1.0] * rows,
        "vol_ma": [1000.0] * rows,
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestEMAPullback:
    def test_01_long_signal_bullish_trend(self):
        df = _make_df()
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.9, 101.0, 100.0, 100.4]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.5, 102.0, 100.3, 101.6]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        assert details["side"] == "LONG"
        assert details["detection_method"] == "ema_pullback"
        assert details["pullback_bars_ago"] == 0

    def test_02_short_signal_bearish_trend(self):
        df = _make_df()
        for i in range(len(df)):
            df.loc[df.index[i], "ema_fast"] = 100.0
            df.loc[df.index[i], "ema_slow"] = 101.0
            df.loc[df.index[i], "close"] = 99.0

        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [99.3, 100.2, 98.8, 100.1]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.05, 100.2, 98.1, 98.4]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        assert details["side"] == "SHORT"
        assert details["pullback_bars_ago"] == 0

    def test_03_no_signal_flat_ema(self):
        df = _make_df()
        for i in range(len(df)):
            df.loc[df.index[i], "ema_fast"] = 100.0
            df.loc[df.index[i], "ema_slow"] = 100.0

        has_signal, _ = detect_ema_pullback(df)
        assert has_signal is False

    def test_04_no_signal_insufficient_data(self):
        df = _make_df(rows=10)
        has_signal, _ = detect_ema_pullback(df)
        assert has_signal is False

    def test_05_volume_filter(self):
        df = _make_df()
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.9, 101.0, 100.0, 100.4]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.5, 102.0, 100.3, 101.6]
        df.loc[df.index[-1], "volume"] = 100.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, _ = detect_ema_pullback(df)
        assert has_signal is False

    def test_06_details_has_required_fields(self):
        df = _make_df()
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.9, 101.0, 100.0, 100.4]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.5, 102.0, 100.3, 101.6]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        for key in [
            "side",
            "entry_price",
            "lowest_point",
            "atr",
            "vol_ratio",
            "signal_strength",
            "neckline",
            "fakeout_depth_atr",
            "setup_bars",
            "pullback_bars_ago",
            "signal_body_ratio",
            "prev_countertrend_bar",
        ]:
            assert key in details, f"Missing key: {key}"
        assert details["signal_strength"] == "moderate"
        assert details["prev_countertrend_bar"] is True

    def test_07_same_bar_touch_and_reclaim_keeps_same_bar_entry(self):
        df = _make_df()
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.8, 101.0, 100.0, 100.2]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.4, 102.0, 99.8, 101.8]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        assert details["side"] == "LONG"
        assert details["pullback_bars_ago"] == 0
        assert details["setup_bars"] == 1

    def test_08_recent_three_bar_context_can_confirm_without_extra_delay(self):
        df = _make_df()
        df.loc[df.index[-3], ["open", "high", "low", "close"]] = [100.6, 101.0, 99.8, 100.9]
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [101.4, 101.5, 101.1, 101.2]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [101.2, 102.1, 100.9, 101.9]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        assert details["side"] == "LONG"
        assert details["pullback_bars_ago"] == 2
        assert details["setup_bars"] == 3

    def test_09_rejects_weak_signal_candle_body(self):
        df = _make_df()
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.9, 101.0, 100.0, 100.4]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.95, 101.45, 100.55, 101.05]

        has_signal, _ = detect_ema_pullback(df)
        assert has_signal is False

    def test_10_accepts_thin_but_not_doji_signal_body(self):
        df = _make_df()
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.9, 101.0, 100.0, 100.4]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.92, 101.4, 100.5, 101.04]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        assert details["side"] == "LONG"

    def test_11_allows_one_recent_close_across_ema_slow(self):
        df = _make_df()
        for i in range(len(df)):
            df.loc[df.index[i], "ema_fast"] = 100.0
            df.loc[df.index[i], "ema_slow"] = 101.0
            df.loc[df.index[i], "close"] = 99.0

        df.loc[df.index[-3], ["open", "high", "low", "close"]] = [99.2, 100.1, 98.8, 99.3]
        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [99.4, 100.4, 99.2, 101.1]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [100.7, 100.9, 99.4, 99.6]

        has_signal, details = detect_ema_pullback(df)
        assert has_signal is True
        assert details["side"] == "SHORT"

    def test_12_rejects_when_previous_bar_is_not_countertrend(self):
        df = _make_df()
        for i in range(len(df)):
            df.loc[df.index[i], "ema_fast"] = 100.0
            df.loc[df.index[i], "ema_slow"] = 101.0
            df.loc[df.index[i], "close"] = 99.0

        df.loc[df.index[-2], ["open", "high", "low", "close"]] = [100.1, 100.2, 98.8, 99.2]
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [99.1, 99.3, 98.0, 98.4]

        has_signal, _ = detect_ema_pullback(df)
        assert has_signal is False


class TestVolumeBreakout:
    def test_01_long_breakout(self):
        df = _make_df()
        df.loc[df.index[-1], "open"] = 101.0
        df.loc[df.index[-1], "close"] = 103.0
        df.loc[df.index[-1], "volume"] = 3000.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, details = detect_volume_breakout(df, volume_breakout_mult=2.0)
        assert has_signal is True
        assert details["side"] == "LONG"
        assert details["vol_ratio"] >= 2.0
        assert "lowest_point" in details

    def test_02_short_breakout(self):
        df = _make_df()
        df.loc[df.index[-1], "open"] = 99.0
        df.loc[df.index[-1], "close"] = 97.0
        df.loc[df.index[-1], "volume"] = 2500.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, details = detect_volume_breakout(df, volume_breakout_mult=2.0)
        assert has_signal is True
        assert details["side"] == "SHORT"
        assert "highest_point" in details

    def test_03_no_signal_low_volume(self):
        df = _make_df()
        df.loc[df.index[-1], "open"] = 101.0
        df.loc[df.index[-1], "close"] = 103.0
        df.loc[df.index[-1], "volume"] = 1500.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, _ = detect_volume_breakout(df, volume_breakout_mult=2.0)
        assert has_signal is False

    def test_04_no_signal_price_in_range(self):
        df = _make_df()
        df.loc[df.index[-1], "close"] = 100.5
        df.loc[df.index[-1], "volume"] = 3000.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, _ = detect_volume_breakout(df, volume_breakout_mult=2.0)
        assert has_signal is False

    def test_05_no_signal_wrong_candle(self):
        df = _make_df()
        df.loc[df.index[-1], "open"] = 104.0
        df.loc[df.index[-1], "close"] = 103.0
        df.loc[df.index[-1], "volume"] = 3000.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, _ = detect_volume_breakout(df, volume_breakout_mult=2.0)
        assert has_signal is False

    def test_06_details_has_required_fields(self):
        df = _make_df()
        df.loc[df.index[-1], "open"] = 101.0
        df.loc[df.index[-1], "close"] = 103.0
        df.loc[df.index[-1], "volume"] = 3000.0
        df.loc[df.index[-1], "vol_ma"] = 1000.0

        has_signal, details = detect_volume_breakout(df, volume_breakout_mult=2.0)
        assert has_signal is True
        for key in [
            "side",
            "entry_price",
            "lowest_point",
            "atr",
            "vol_ratio",
            "signal_strength",
            "neckline",
            "fakeout_depth_atr",
        ]:
            assert key in details, f"Missing key: {key}"
        assert details["signal_strength"] == "strong"
