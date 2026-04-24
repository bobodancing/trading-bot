# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`.
This is a `weak-tape gate attribution` child candidate. It keeps the
`partial67` entry and staged exit path, preserves the same late-entry stretch
cap, and isolates activation to the local `chop_trend` proxy only.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20, adx, bbw
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - compute `chop_trend` as local
    `adx_slope_5 < 0` and `bbw_ratio < entry_bbw_ratio_min`
  - only when `chop_trend` is active, block the signal if
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
  - entry_bbw_ratio_min=0.75
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  is the useful `weak-tape defense` activation mostly coming from local
  `falling ADX + compressed BBW`, rather than higher-timeframe trend decay
- expected gain surface:
  `RANGING`, `sideways transition`, and low-energy tapes where the 4h trigger is
  technically valid but local structure is stale and compressing
- main failure mode:
  overreacting inside healthy bullish impulses and recreating the old
  late-entry winner tax through noisy local compression reads

## Family Role
- structural role:
  attribution child inside the `weak-tape defense` side branch
- evaluation order:
  compare this child first against the OR-gated `context_gated` candidate, then
  against the unconditional `late_entry_filter`
- guardrail:
  do not score this as a bullish-mainline replacement; it only answers whether
  `chop_trend` deserves to stay inside the defense gate

## Out of Scope
- new exit logic
- stop redesign
- retuning the `chop_trend` threshold family
- adding `trend_decay` back into the activation rule
- stacking with `remainder_ratchet`
- bearish / short-side logic
- runtime default enablement
