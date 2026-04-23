# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`. This is a
research child for the ordered `post-entry management` pass.

## Research Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: unchanged from `partial67`
- stop hint: unchanged from `partial67`
- exit rules:
  - keep signal cross-down exit
  - keep trend-gate-lost exit
  - keep `DERISK_PARTIAL_GIVEBACK`
  - add `REMAINDER_RATCHET_EXIT` after a prior partial when:
    - `max_favorable_r >= remainder_ratchet_arm_r`
    - `giveback_r >= remainder_ratchet_giveback_r`
  - keep the original deeper `GIVEBACK_EXIT` as fallback
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
  - remainder_ratchet_arm_r=1.0
  - remainder_ratchet_giveback_r=1.0
- regime: target_regime = TRENDING_UP

## Research Intent
- primary question:
  can the current `working baseline` protect the remaining position after a
  successful partial without reducing the original entry set
- expected gain surface:
  `MIXED`, `sideways transition`, and high-level chop where profitable trades
  often give back before the old `0.25R` floor
- main failure mode:
  clipping old-cycle trend winners before they can compound

## Out of Scope
- entry filtering
- stop ATR retuning
- trend spread retuning
- RANGING-specific mean reversion logic
- bearish / short-side logic
- runtime default enablement
