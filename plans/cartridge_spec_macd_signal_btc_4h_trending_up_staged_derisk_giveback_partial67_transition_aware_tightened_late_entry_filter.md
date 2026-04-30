# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter`.
This is the first `transition-aware narrowing` child candidate. It keeps the
same explicit transition-risk proxy, but only lets that proxy veto the signal
when the entry is an extreme `>= 3.0 ATR` chase instead of any
`> 1.25 ATR` overshoot.

## Locked Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - keep the explicit transition context:
    - `current_high >= prior_high_max`
    - `prior_positive_hist_max >= transition_prior_positive_hist_min`
    - `current_macd_hist / prior_positive_hist_max <= transition_hist_ratio_max`
  - only allow the side-branch veto when:
    - that transition context is active
    - and `max((close - ema_20) / atr, 0)` is at least
      `transition_extension_atr_trigger`
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
  - transition_lookback_bars=12
  - transition_hist_ratio_max=0.25
  - transition_prior_positive_hist_min=10.0
  - transition_extension_atr_trigger=3.0
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the 1d trend gate suppresses entries unless
  `ema_20 > ema_50` and `(ema_20 - ema_50) / ema_50 >= trend_spread_min`.

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: The cartridge is a BTC 4h long-only continuation strategy guarded
  by a 1d bullish EMA trend gate; the tightened transition veto is a weak-tape
  defense layer, not a separate ranging thesis.

## Research Intent
- primary question:
  can the explicit transition proxy keep its `RANGING` /
  `sideways_transition` repair if it only vetoes the most obviously stretched
  chase entries
- expected gain surface:
  recover default `TRENDING_UP` participation without reintroducing the known
  `2023-06-23` transition losers
- main failure mode:
  localizing the proxy so much that it collapses back to the `partial67`
  baseline and gives away the transition-surface repair

## Family Role
- structural role:
  first narrowing child inside the explicit `transition-aware` side-branch lane
- evaluation order:
  compare this child first against `partial67_transition_aware_late_entry_filter`,
  then against `partial67`, then against `partial67_chop_trend_tightened_late_entry_filter`
- guardrail:
  do not treat this as a bullish-mainline promotion test; it is still a
  side-branch defense probe

## Out of Scope
- reworking the divergence proxy itself
- adding volume divergence in the same pass
- OR-stacking with `chop_trend`
- new exit logic
- stop redesign
- stacking with `remainder_ratchet`
- bearish / short-side logic
- runtime default enablement
