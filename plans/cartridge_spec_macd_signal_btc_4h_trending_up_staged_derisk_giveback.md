# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback

Derived from: `macd_signal_btc_4h_trending_up`. This is a new cartridge that
keeps the baseline 4h entry, 1d trend gate, and ATR stop while adding a staged
de-risk path on give-back and a deeper give-back full exit for the remainder.

## Locked Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: identical to `macd_signal_btc_4h_trending_up`
- stop hint: entry_price - stop_atr_mult * atr, using the 4h ATR on the entry candle
- exit rules:
  - close when the 4h signal flips back down (`previous_macd >= previous_macd_signal` AND `macd < macd_signal`)
  - close when the 1d trend gate no longer passes
  - partial close as `DERISK_PARTIAL_GIVEBACK` when the trade has first reached at least `derisk_arm_r` favorable `R`, then gives back at least `derisk_giveback_r`, and open profit has faded back to `derisk_arm_r` `R` or less; move the remaining stop to break-even without loosening the current stop
  - close the remainder as `GIVEBACK_EXIT` once a prior partial de-risk has already happened and the trade had first reached at least `giveback_exit_arm_r` favorable `R`, then fades to `giveback_exit_floor_r` `R` or less
- locked params: stop_atr_mult=1.5, require_signal_confirmation=True, emit_once=True, trend_spread_min=0.005, derisk_arm_r=1.0, derisk_giveback_r=0.75, derisk_close_pct=0.5, giveback_exit_arm_r=1.5, giveback_exit_floor_r=0.25
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the cartridge still does not read router or arbiter state directly; it keeps the baseline 1d EMA trend gate and only changes local position management after favorable excursion has already occurred

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: the next structural question is whether weak capture in mixed conditions comes from trades that do show initial follow-through but then give most of it back before the baseline cross-down exit prints. This variant tests that thesis without tightening entry or reworking the baseline stop.

## Out of Scope
- ETH or multi-symbol scope
- short leg
- direct reads of the BTC 4h regime probe or arbiter labels
- macro overlay coupling
- stop redesign or spread-threshold sweeps
- confirmed-entry tightening
- runtime default enablement
