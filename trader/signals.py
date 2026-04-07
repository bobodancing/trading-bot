"""
Signal detection helpers.
"""

import logging
from typing import Dict, Optional, Tuple

import pandas as pd

from trader.config import Config
from trader.structure import StructureAnalysis

logger = logging.getLogger(__name__)


def detect_2b_with_pivots(
    df: pd.DataFrame,
    left_bars: int = 5,
    right_bars: int = 2,
    vol_minimum_threshold: float = 0.7,
    accept_weak_signals: bool = True,
    enable_volume_grading: bool = True,
    vol_explosive_threshold: float = 2.5,
    vol_strong_threshold: float = 1.5,
    vol_moderate_threshold: float = 1.0,
    min_fakeout_atr: float = 0.3,
) -> Tuple[bool, Optional[Dict]]:
    """Detect 2B reversals using confirmed pivot structure."""
    min_bars = left_bars + right_bars + 5
    if df is None or len(df) < min_bars:
        return False, None

    swings = StructureAnalysis.find_swing_points(df, left_bars, right_bars)
    last_swing_low = swings["last_swing_low"]
    last_swing_high = swings["last_swing_high"]

    if last_swing_low is None and last_swing_high is None:
        return False, None

    current = df.iloc[-1]
    close = current["close"]
    low = current["low"]
    high = current["high"]
    atr = current.get("atr", 0)
    volume = current.get("volume", 0)
    vol_ma = current.get("vol_ma", 0)

    signal_side = None
    signal_details: Dict = {}

    if last_swing_low is not None:
        if low < last_swing_low and close > last_swing_low:
            signal_side = "LONG"
            neckline = StructureAnalysis.find_neckline(
                df,
                "LONG",
                swings,
                left_bars,
                right_bars,
                entry_price=close,
            )
            signal_details = {
                "side": "LONG",
                "entry_price": close,
                "lowest_point": low,
                "stop_level": last_swing_low,
                "target_ref": last_swing_high,
                "prev_low": last_swing_low,
                "prev_high": last_swing_high,
                "neckline": neckline,
                "atr": atr,
                "volume": volume,
                "vol_ma": vol_ma,
                "signal_time": current.get("timestamp"),
                "candle_confirmed": close > current["open"],
                "detection_method": "swing_pivot",
            }

    if signal_side is None and last_swing_high is not None:
        if high > last_swing_high and close < last_swing_high:
            signal_side = "SHORT"
            neckline = StructureAnalysis.find_neckline(
                df,
                "SHORT",
                swings,
                left_bars,
                right_bars,
                entry_price=close,
            )
            signal_details = {
                "side": "SHORT",
                "entry_price": close,
                "highest_point": high,
                "stop_level": last_swing_high,
                "target_ref": last_swing_low,
                "prev_low": last_swing_low,
                "prev_high": last_swing_high,
                "neckline": neckline,
                "atr": atr,
                "volume": volume,
                "vol_ma": vol_ma,
                "signal_time": current.get("timestamp"),
                "candle_confirmed": close < current["open"],
                "detection_method": "swing_pivot",
            }

    if signal_side is None:
        return False, None

    vol_ratio = volume / vol_ma if vol_ma > 0 else 0
    if vol_ratio >= vol_explosive_threshold:
        signal_strength = "explosive"
    elif vol_ratio >= vol_strong_threshold:
        signal_strength = "strong"
    elif vol_ratio >= vol_moderate_threshold:
        signal_strength = "moderate"
    else:
        signal_strength = "weak"

    signal_details["vol_ratio"] = vol_ratio
    signal_details["signal_strength"] = signal_strength

    if enable_volume_grading:
        if vol_ratio < vol_minimum_threshold:
            logger.debug(
                f"2B {signal_side} filtered: vol {vol_ratio:.2f}x < min {vol_minimum_threshold}x"
            )
            return False, None

        if not accept_weak_signals and signal_strength == "weak":
            logger.debug(
                f"2B {signal_side} filtered: weak signal ({vol_ratio:.2f}x), weak signals disabled"
            )
            return False, None
    else:
        if volume <= vol_ma:
            return False, None

    if signal_side == "LONG":
        fakeout_depth = abs(low - last_swing_low)
    else:
        fakeout_depth = abs(high - last_swing_high)

    fakeout_depth_atr = round(fakeout_depth / atr, 3) if atr > 0 else 0.0
    if atr > 0 and fakeout_depth < atr * min_fakeout_atr:
        logger.debug(
            f"2B {signal_side} filtered: penetration too shallow "
            f"({fakeout_depth_atr:.2f}x ATR < {min_fakeout_atr}x ATR)"
        )
        return False, None

    if atr > 0 and fakeout_depth > atr * Config.MAX_FAKEOUT_ATR:
        logger.debug(
            f"2B {signal_side} filtered: fakeout too deep "
            f"({fakeout_depth:.2f} > {atr * Config.MAX_FAKEOUT_ATR:.2f})"
        )
        return False, None

    signal_details["fakeout_depth_atr"] = fakeout_depth_atr

    if signal_strength == "explosive":
        logger.debug(
            f"2B {signal_side} filtered: explosive volume ({vol_ratio:.2f}x) "
            f"likely genuine breakout, not fakeout"
        )
        return False, None

    adx = current.get("adx", 0)
    adx_max = getattr(Config, "ADX_MAX_2B", 50)
    if adx and adx > adx_max:
        logger.debug(
            f"2B {signal_side} filtered: ADX {adx:.1f} > {adx_max} "
            f"trend too strong for reversal"
        )
        return False, None

    sl_buffer = atr * Config.SL_ATR_BUFFER_SIGNAL if atr > 0 else 0
    if signal_side == "LONG":
        signal_details["stop_loss"] = last_swing_low - sl_buffer
    else:
        signal_details["stop_loss"] = last_swing_high + sl_buffer

    neck_str = f"${signal_details['neckline']:.2f}" if signal_details["neckline"] else "N/A"
    swing_type = "low" if signal_side == "LONG" else "high"
    logger.info(
        f"[2B] {signal_side} detected: "
        f"price=${close:.2f} | swing_{swing_type}=${signal_details['stop_level']:.2f} | "
        f"neckline={neck_str} | vol={vol_ratio:.2f}x ({signal_strength})"
    )

    return True, signal_details


def detect_ema_pullback(
    df: pd.DataFrame,
    ema_pullback_threshold: float = 0.02,
) -> Tuple[bool, Optional[Dict]]:
    """Detect EMA pullback using recent context while keeping same-bar entry timing."""
    if df is None or len(df) < 30:
        return False, None

    if "ema_fast" not in df.columns or "ema_slow" not in df.columns:
        return False, None

    lookback_bars = max(int(getattr(Config, "EMA_PULLBACK_LOOKBACK_BARS", 3)), 2)
    min_body_ratio = float(getattr(Config, "EMA_PULLBACK_MIN_BODY_RATIO", 0.25))
    required_trend_bars = min(
        lookback_bars,
        max(2, int(getattr(Config, "EMA_PULLBACK_MIN_TREND_SIDE_BARS", lookback_bars - 1))),
    )
    require_prev_counter_bar = bool(
        getattr(Config, "EMA_PULLBACK_REQUIRE_PREV_COUNTER_BAR", False)
    )

    recent_window = df.iloc[-lookback_bars:]
    current = recent_window.iloc[-1]

    ema_fast = current["ema_fast"]
    ema_slow = current["ema_slow"]
    price = current["close"]
    atr = current.get("atr", 0)
    volume = current.get("volume", 0)
    vol_ma = current.get("vol_ma", 0)

    current_range = current["high"] - current["low"]
    if pd.isna(current_range) or current_range <= 0:
        body_ratio = 0.0
    else:
        body_ratio = abs(price - current["open"]) / current_range

    threshold_series = recent_window["ema_fast"].abs() * ema_pullback_threshold
    body_near_series = recent_window["ema_fast"].abs() * (ema_pullback_threshold * 0.5)
    signal_side = None
    signal_details: Dict = {}

    if ema_fast > ema_slow:
        trend_side_mask = recent_window["close"] > recent_window["ema_slow"]
        prev_bar = recent_window.iloc[-2]
        touch_mask = (
            (recent_window["low"] <= recent_window["ema_fast"] + threshold_series)
            & (
                recent_window[["open", "close"]].min(axis=1)
                <= recent_window["ema_fast"] + body_near_series
            )
        )
        touch_positions = [i for i, touched in enumerate(touch_mask.tolist()) if touched]
        trend_intact = bool(trend_side_mask.iloc[-1] and trend_side_mask.sum() >= required_trend_bars)
        prev_countertrend_bar = bool(prev_bar["close"] < prev_bar["open"])
        reclaim_ok = price > ema_fast and price > current["open"] and body_ratio >= min_body_ratio

        if touch_positions and trend_intact and reclaim_ok and (
            not require_prev_counter_bar or prev_countertrend_bar
        ):
            touch_pos = touch_positions[-1]
            setup_slice = recent_window.iloc[touch_pos:]
            if price >= setup_slice["close"].max():
                lowest_point = float(setup_slice["low"].min())
                slow_guard = float(setup_slice["ema_slow"].min())
                signal_side = "LONG"
                signal_details = {
                    "side": "LONG",
                    "entry_price": price,
                    "lowest_point": lowest_point,
                    "stop_level": min(lowest_point, slow_guard) - atr * Config.SL_ATR_BUFFER_SIGNAL,
                    "target_ref": df["high"].iloc[-20:].max(),
                    "atr": atr,
                    "volume": volume,
                    "vol_ma": vol_ma,
                    "signal_type": "EMA_PULLBACK",
                    "candle_confirmed": price > current["open"],
                    "neckline": None,
                    "fakeout_depth_atr": 0.0,
                    "detection_method": "ema_pullback",
                    "setup_bars": len(setup_slice),
                    "pullback_bars_ago": len(recent_window) - touch_pos - 1,
                    "signal_body_ratio": round(body_ratio, 4),
                    "prev_countertrend_bar": prev_countertrend_bar,
                }

    elif ema_fast < ema_slow:
        trend_side_mask = recent_window["close"] < recent_window["ema_slow"]
        prev_bar = recent_window.iloc[-2]
        touch_mask = (
            (recent_window["high"] >= recent_window["ema_fast"] - threshold_series)
            & (
                recent_window[["open", "close"]].max(axis=1)
                >= recent_window["ema_fast"] - body_near_series
            )
        )
        touch_positions = [i for i, touched in enumerate(touch_mask.tolist()) if touched]
        trend_intact = bool(trend_side_mask.iloc[-1] and trend_side_mask.sum() >= required_trend_bars)
        prev_countertrend_bar = bool(prev_bar["close"] > prev_bar["open"])
        reclaim_ok = price < ema_fast and price < current["open"] and body_ratio >= min_body_ratio

        if touch_positions and trend_intact and reclaim_ok and (
            not require_prev_counter_bar or prev_countertrend_bar
        ):
            touch_pos = touch_positions[-1]
            setup_slice = recent_window.iloc[touch_pos:]
            if price <= setup_slice["close"].min():
                highest_point = float(setup_slice["high"].max())
                slow_guard = float(setup_slice["ema_slow"].max())
                signal_side = "SHORT"
                signal_details = {
                    "side": "SHORT",
                    "entry_price": price,
                    "highest_point": highest_point,
                    "stop_level": max(highest_point, slow_guard) + atr * Config.SL_ATR_BUFFER_SIGNAL,
                    "target_ref": df["low"].iloc[-20:].min(),
                    "atr": atr,
                    "volume": volume,
                    "vol_ma": vol_ma,
                    "signal_type": "EMA_PULLBACK",
                    "candle_confirmed": price < current["open"],
                    "neckline": None,
                    "fakeout_depth_atr": 0.0,
                    "detection_method": "ema_pullback",
                    "setup_bars": len(setup_slice),
                    "pullback_bars_ago": len(recent_window) - touch_pos - 1,
                    "signal_body_ratio": round(body_ratio, 4),
                    "prev_countertrend_bar": prev_countertrend_bar,
                }

    if signal_side is None:
        return False, None

    vol_ratio = volume / vol_ma if vol_ma > 0 else 0
    if vol_ratio < Config.VOLUME_PULLBACK_MIN_RATIO:
        return False, None

    signal_details["vol_ratio"] = vol_ratio
    signal_details["signal_strength"] = "moderate"

    logger.info(
        f"EMA pullback detected: {signal_side} "
        f"(setup={signal_details.get('setup_bars')}, body={signal_details.get('signal_body_ratio')})"
    )

    return True, signal_details


def detect_volume_breakout(
    df: pd.DataFrame,
    volume_breakout_mult: float = 2.0,
) -> Tuple[bool, Optional[Dict]]:
    """Detect volume breakout entries."""
    if df is None or len(df) < 30:
        return False, None

    current = df.iloc[-1]
    volume = current.get("volume", 0)
    vol_ma = current.get("vol_ma", 0)
    atr = current.get("atr", 0)

    vol_ratio = volume / vol_ma if vol_ma > 0 else 0
    if vol_ratio < volume_breakout_mult:
        return False, None

    recent_high = df["high"].iloc[-10:-1].max()
    recent_low = df["low"].iloc[-10:-1].min()

    price = current["close"]
    signal_side = None
    signal_details: Dict = {}

    if price > recent_high and price > current["open"]:
        signal_side = "LONG"
        signal_details = {
            "side": "LONG",
            "entry_price": price,
            "lowest_point": recent_low,
            "stop_level": recent_low - atr * 0.5,
            "target_ref": price + (price - recent_low),
            "atr": atr,
            "volume": volume,
            "vol_ma": vol_ma,
            "signal_type": "VOLUME_BREAKOUT",
            "candle_confirmed": True,
            "neckline": None,
            "fakeout_depth_atr": 0.0,
            "detection_method": "volume_breakout",
        }
    elif price < recent_low and price < current["open"]:
        signal_side = "SHORT"
        signal_details = {
            "side": "SHORT",
            "entry_price": price,
            "highest_point": recent_high,
            "stop_level": recent_high + atr * 0.5,
            "target_ref": price - (recent_high - price),
            "atr": atr,
            "volume": volume,
            "vol_ma": vol_ma,
            "signal_type": "VOLUME_BREAKOUT",
            "candle_confirmed": True,
            "neckline": None,
            "fakeout_depth_atr": 0.0,
            "detection_method": "volume_breakout",
        }

    if signal_side is None:
        return False, None

    signal_details["vol_ratio"] = vol_ratio
    signal_details["signal_strength"] = "strong"

    logger.info(f"Volume breakout detected: {signal_side} (vol {vol_ratio:.2f}x)")

    return True, signal_details
