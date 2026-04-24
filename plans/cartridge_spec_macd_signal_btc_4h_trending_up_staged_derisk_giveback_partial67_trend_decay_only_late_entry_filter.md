# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`.
This is a `weak-tape gate attribution` child candidate. It keeps the
`partial67` entry and staged exit path, preserves the same late-entry stretch
cap, and isolates activation to the 1d `trend_decay` proxy only.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - compute `trend_decay` as 1d
    `trend_spread_delta <= weak_tape_trend_spread_delta_max` over
    `trend_spread_slope_bars`
  - only when `trend_decay` is active, block the signal if
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
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  is the useful `weak-tape defense` activation mostly coming from higher-timeframe
  trend decay, rather than the local chop proxy
- expected gain surface:
  `RANGING`, `sideways transition`, and bearish / transition-heavy windows where
  the 1d trend is rolling over but the 4h trigger still fires late
- main failure mode:
  missing the known weak surfaces because `trend_decay` reacts too slowly, while
  still importing some winner tax into bullish recovery tapes

## Family Role
- structural role:
  attribution child inside the `weak-tape defense` side branch
- evaluation order:
  compare this child first against the OR-gated `context_gated` candidate, then
  against the unconditional `late_entry_filter`
- guardrail:
  do not score this as a bullish-mainline replacement; it only answers whether
  `trend_decay` deserves to stay inside the defense gate

## Out of Scope
- new exit logic
- stop redesign
- retuning the `trend_decay` threshold family
- adding `chop_trend` back into the activation rule
- stacking with `remainder_ratchet`
- bearish / short-side logic
- runtime default enablement
