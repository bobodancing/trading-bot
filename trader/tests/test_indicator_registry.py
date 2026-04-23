from types import SimpleNamespace

import pandas as pd

from trader.indicators.registry import IndicatorRegistry
import trader.indicators.technical as technical


def _price_frame(length=25):
    idx = pd.date_range("2026-01-01", periods=length, freq="4h", tz="UTC")
    close = pd.Series([100.0 + i for i in range(length)], index=idx)
    return pd.DataFrame(
        {
            "open": close - 1.0,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def test_indicator_registry_short_macd_frame_falls_back_when_ta_returns_none(monkeypatch):
    fake_ta = SimpleNamespace(
        ema=lambda series, length: None if len(series) < length else series.ewm(span=length, adjust=False).mean()
    )
    monkeypatch.setattr(technical, "ta", fake_ta)

    frame = IndicatorRegistry.apply(_price_frame(), {"macd", "ema"})

    assert {"macd", "macd_signal", "macd_hist", "ema_20", "ema_50"}.issubset(frame.columns)
    assert len(frame) == 25
    assert frame["macd"].notna().all()
