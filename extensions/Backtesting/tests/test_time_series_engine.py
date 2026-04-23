import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from time_series_engine import TimeSeriesEngine


def make_df(n=10):
    idx = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(
        {
            "open": range(n),
            "high": range(n),
            "low": range(n),
            "close": range(n),
            "volume": range(n),
        },
        index=idx,
    )


def test_no_lookahead_excludes_current_open_time_bar():
    df = make_df(10)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    bar5_ts = df.index[4]

    tse.set_time(bar5_ts)
    result = tse.get_bars("BTC/USDT", "1h", limit=100)

    assert len(result) == 4
    assert result.index[-1] == df.index[3]


def test_get_bars_respects_limit():
    df = make_df(10)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(df.index[-1])

    result = tse.get_bars("BTC/USDT", "1h", limit=3)

    assert len(result) == 3
    assert result.index.tolist() == list(df.index[-4:-1])


def test_get_current_price_uses_last_closed_bar():
    df = make_df(5)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(df.index[2])

    assert tse.get_current_price("BTC/USDT") == 1.0


def test_get_1h_timestamps_intersection():
    df1 = make_df(5)
    df2 = make_df(3)
    tse = TimeSeriesEngine(
        {
            "BTC/USDT": {"1h": df1},
            "ETH/USDT": {"1h": df2},
        }
    )

    ts_list = tse.get_1h_timestamps(["BTC/USDT", "ETH/USDT"])

    assert len(ts_list) == 3


def test_get_bars_raises_if_no_time_set():
    df = make_df(5)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})

    with pytest.raises(RuntimeError, match="set_time"):
        tse.get_bars("BTC/USDT", "1h")


def test_get_bars_unknown_symbol_returns_empty():
    df = make_df(5)
    tse = TimeSeriesEngine({"BTC/USDT": {"1h": df}})
    tse.set_time(df.index[-1])

    result = tse.get_bars("UNKNOWN/USDT", "1h")

    assert result.empty
