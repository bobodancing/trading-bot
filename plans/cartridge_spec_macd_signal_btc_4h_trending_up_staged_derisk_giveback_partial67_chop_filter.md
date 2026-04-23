# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`. This is a
research child that keeps the `partial67` exit path intact and only adds a
local 4h ADX floor so the family can test a cleaner `chop / no-trade
discipline` pass.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, adx
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - add a local chop suppression rule:
    block the signal when 4h `adx` is below `entry_adx_min`
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
  - entry_adx_min=22.0
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the current `working baseline` avoid weak local chop entries without
  paying the large participation cost seen in the late-entry filter branch
- expected gain surface:
  `RANGING`, `MIXED`, and the `sideways transition` supplemental window
- main failure mode:
  cutting too much clean trend participation, especially in the long windows

## Out of Scope
- stop redesign
- trend spread retuning
- late-entry stretch suppression
- bearish / short-side logic
- runtime default enablement
