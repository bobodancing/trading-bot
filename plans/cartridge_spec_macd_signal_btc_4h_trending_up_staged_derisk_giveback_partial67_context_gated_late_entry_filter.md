# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`.
This is the first concrete candidate in the `weak-tape defense` side branch.
It keeps the `partial67` entry and staged exit path, but only activates the
late-entry stretch cap when a weak-tape context proxy is present.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20, adx, bbw
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - compute weak-tape context as either:
    - 1d `trend_spread_delta <= weak_tape_trend_spread_delta_max` over
      `trend_spread_slope_bars`
    - or local `chop-trend` context where `adx_slope_5 < 0` and
      `bbw_ratio < entry_bbw_ratio_min`
  - only when weak-tape context is active, block the signal if
    `max((close - ema_20) / atr, 0)` is greater than
    `entry_ema_extension_atr_max`
- stop hint: unchanged from `partial67`
- exit rules: unchanged from `partial67`
  - signal cross-down exit
  - trend-gate-lost exit
  - `DERISK_PARTIAL_GIVEBACK`
  - `GIVEBACK_EXIT`
- default research params:
  - stop_atr_mult=1.5
  - require_signal_confirmation=True
  - emit_once=True
  - trend_spread_min=0.005
  - derisk_arm_r=1.0
  - derisk_giveback_r=0.75
  - derisk_close_pct=0.67
  - giveback_exit_arm_r=1.5
  - giveback_exit_floor_r=0.25
  - entry_ema_extension_atr_max=1.25
  - trend_spread_slope_bars=3
  - weak_tape_trend_spread_delta_max=0.0
  - entry_bbw_ratio_min=0.75
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the family keep the late-entry defense only where weak-tape proxies are
  active, instead of taxing clean bullish tapes unconditionally
- expected gain surface:
  `RANGING`, `sideways transition`, crash-like weak tape, and bearish /
  transition-heavy slices inside the trend-up family review set
- main failure mode:
  the weak-tape proxy may still trigger too often and import the old
  `late_entry_filter` winner tax into bullish tapes

## Family Role
- structural role:
  first candidate in the `weak-tape defense` side branch
- evaluation order:
  score this cartridge on weak-tape windows first, then verify that bullish
  winner tax is smaller than the unconditional `late_entry_filter`
- guardrail:
  this is not a bullish-mainline replacement unless a later pass shows the
  context gate keeps defense localized to weak tape

## Out of Scope
- new exit logic
- stop redesign
- trend spread retuning outside the weak-tape context proxy
- bearish / short-side logic
- direct replacement of the bullish `working baseline`
- stacking with `remainder_ratchet` before the context gate is validated
- runtime default enablement
