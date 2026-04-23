# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`. This is a
research child that keeps the `partial67` exit path intact and only adds a
local 4h EMA spread floor so the family can test whether `chop / no-trade
discipline` works better via entanglement suppression than via a raw ADX floor.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20, ema_50
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - add a local chop suppression rule:
    block the signal unless 4h `ema_20 > ema_50` and
    `(ema_20 - ema_50) / ema_50 >= entry_local_spread_min`
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
  - entry_local_spread_min=0.002
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the family avoid locally entangled 4h tape without paying the strong
  participation cost seen in the late-entry branch or the poor `MIXED` result
  seen in the raw ADX-floor branch
- expected gain surface:
  `MIXED`, `RANGING`, and the `sideways transition` supplemental window
- main failure mode:
  turning into a tighter-entry branch that cuts trend participation too hard

## Out of Scope
- stop redesign
- trend spread retuning on the 1d gate
- late-entry stretch suppression
- bearish / short-side logic
- runtime default enablement
