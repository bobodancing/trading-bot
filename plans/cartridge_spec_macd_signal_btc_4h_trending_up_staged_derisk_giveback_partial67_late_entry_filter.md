# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`. This is a
research child that keeps the `partial67` staged exit path intact and adds a
narrow late-entry stretch cap. After the 2026-04-24 family split, this branch
is no longer scored as a bullish-mainline replacement; it is the leading
`weak-tape defense` side branch.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - add a late-entry suppression rule:
    block the signal when `max((close - ema_20) / atr, 0)` is greater than
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
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the family suppress weak-tape losers by refusing overextended 4h entries,
  without paying unacceptable winner tax in clean bullish tapes
- expected gain surface:
  `RANGING`, `sideways transition`, crash-like weak tape, and bearish /
  transition-heavy slices inside the trend-up family review set
- main failure mode:
  over-cutting clean bullish participation and turning defense gains into a
  false aggregate win through heavy selectivity

## Family Role
- structural role:
  leading `weak-tape defense` side branch, not a direct bullish-mainline
  replacement
- evaluation order:
  score this branch first on weak-tape windows and loser-suppression quality;
  only compare aggregate numbers after checking winner tax in bullish windows
- guardrail:
  do not promote this branch into the bullish mainline unless an explicit
  context gate proves that defense activates only where weak-tape suppression
  dominates

## Out of Scope
- stop redesign
- trend spread retuning
- generic confirmation stacking
- bearish / short-side logic
- direct replacement of the bullish `working baseline`
- direct stacking with `remainder_ratchet` without an explicit context gate
- runtime default enablement
