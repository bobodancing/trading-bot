# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter`.
This is the first `chop_trend localization` child candidate. It keeps the
`partial67` entry and staged exit path, keeps the same `falling ADX +
compressed BBW` proxy, and tightens that proxy by requiring a more extreme
late-entry stretch before the side-branch veto is allowed to fire.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20, adx, bbw
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - compute `chop_trend` as local
    `adx_slope_5 < 0` and `bbw_ratio < entry_bbw_ratio_min`
  - only allow the side-branch veto when:
    - `chop_trend` is active
    - and `max((close - ema_20) / atr, 0)` is at least
      `chop_trend_extension_atr_trigger`
  - if that tightened veto context is active, reject the signal
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
  - chop_trend_extension_atr_trigger=1.5
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the `chop_trend` proxy keep part of its defensive uplift if it only vetoes
  the most obviously stretched chase entries, instead of every
  `> 1.25 ATR` overshoot
- expected gain surface:
  preserve more `bull_strong_up_1` participation while still blocking the
  ugliest `bear_persistent_down` chase entries
- main failure mode:
  localizing the proxy so much that it becomes nearly inactive and collapses
  back toward the `partial67` baseline without repairing the known
  `sideways_transition` surface

## Family Role
- structural role:
  first localization child inside the `weak-tape defense` side branch after
  gate attribution
- evaluation order:
  compare this child first against `partial67_chop_trend_only_late_entry_filter`,
  then against the OR-gated `context_gated` reference, then against the
  unconditional `late_entry_filter`
- guardrail:
  do not score this as a bullish-mainline replacement; it only answers whether
  the active `chop_trend` proxy can be localized without losing the branch
  thesis

## Out of Scope
- new exit logic
- stop redesign
- re-opening `trend_decay` as the main lever
- adding a direct `sideways_transition` trigger in the same pass
- stacking with `remainder_ratchet`
- bearish / short-side logic
- runtime default enablement
