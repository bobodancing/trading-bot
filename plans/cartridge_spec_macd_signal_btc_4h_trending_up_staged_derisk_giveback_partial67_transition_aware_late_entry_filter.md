# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter`.
This is the first explicit `transition-aware defense` child candidate. It keeps
the `partial67` entry and staged exit path, keeps the late-entry stretch cap as
the side-branch defense action, and only activates that cap when price is still
breaking local highs while 4h `macd_hist` is materially weaker than the prior
positive impulse.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, macd_hist, atr, ema_20, high
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - compute a local transition-aware context over `transition_lookback_bars`:
    - `current_high >= prior_high_max`
    - and `prior_positive_hist_max >= transition_prior_positive_hist_min`
    - and `current_macd_hist / prior_positive_hist_max <= transition_hist_ratio_max`
  - only when that transition-aware context is active, block the signal if
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
  - transition_lookback_bars=12
  - transition_hist_ratio_max=0.25
  - transition_prior_positive_hist_min=10.0
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the side branch localize the old `late_entry_filter` defense onto the
  specific `price still chasing highs while MACD impulse has already faded`
  pattern, instead of relying on `chop_trend` as a noisy proxy
- expected gain surface:
  default `RANGING`, `sideways_transition`, and other transition-heavy slices
  where the unconditional `late_entry_filter` already showed useful loser
  suppression
- main failure mode:
  the divergence proxy may still miss the known weak-tape losers, or it may
  overfit historical impulse peaks and re-introduce winner tax into bullish
  breakout tapes

## Family Role
- structural role:
  first explicit `transition-aware defense` child inside the `weak-tape
  defense` side branch
- evaluation order:
  compare this child first against
  `partial67_chop_trend_tightened_late_entry_filter`, then against the
  unconditional `late_entry_filter`, then against the `partial67` working
  baseline
- guardrail:
  do not score this as a bullish-mainline replacement; it only answers whether
  an explicit transition proxy can localize the side-branch defense better than
  the current `chop_trend` reference

## Out of Scope
- new exit logic
- stop redesign
- adding volume shrink as a second veto in the same pass
- retuning the `chop_trend` proxy again in parallel
- stacking with `remainder_ratchet`
- bearish / short-side logic
- runtime default enablement
