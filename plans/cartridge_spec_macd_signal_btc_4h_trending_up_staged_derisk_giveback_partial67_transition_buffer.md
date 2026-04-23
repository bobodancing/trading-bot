# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`. This is a
research child for the ordered `transition bleed` pass.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: unchanged from `partial67`, except require the 1d trend gate to
  have persisted for `trend_persistence_bars`
- stop hint: unchanged from `partial67`
- exit rules: unchanged from `partial67`
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
  - trend_persistence_bars=3
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the current `working baseline` reduce false starts right after 1d trend
  flips without retuning `trend_spread_min`
- expected gain surface:
  `MIXED`, transition-heavy windows, and fresh trend-restoration noise
- main failure mode:
  delaying legitimate early-trend entries and clipping strong new trend starts

## Out of Scope
- changing `trend_spread_min`
- entry stretch filtering
- chop filtering
- post-entry ratchet exits
- stop ATR retuning
- bearish / short-side logic
- runtime default enablement
