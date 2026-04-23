# Cartridge Spec: macd_signal_btc_4h_trending_up_underwater_ema_exit

Derived from: `macd_signal_btc_4h_trending_up`. This is a new cartridge that
keeps the baseline 4h entry, 1d trend gate, and ATR stop while adding an
underwater EMA20 exit so failed continuation attempts do not have to wait for a
full MACD cross-down or stop hit.

## Locked Spec
- id: macd_signal_btc_4h_trending_up_underwater_ema_exit
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: identical to `macd_signal_btc_4h_trending_up`
- stop hint: entry_price - stop_atr_mult * atr, using the 4h ATR on the entry candle
- exit rules:
  - close when the 4h signal flips back down (`previous_macd >= previous_macd_signal` AND `macd < macd_signal`)
  - close when the 1d trend gate no longer passes
  - close as `UNDERWATER_EMA20_EXIT` when at least `underwater_ema_exit_bars` 4h bars have elapsed since entry and the latest 4h close is both below the entry price and at or below the 4h ema_20
- locked params: stop_atr_mult=1.5, require_signal_confirmation=True, emit_once=True, trend_spread_min=0.005, underwater_ema_exit_bars=1
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the cartridge still does not read router or arbiter state directly; it keeps the baseline 1d EMA trend gate and only adds a local follow-through failure exit on the 4h management path

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: the baseline cartridge already proved the trend-side sign, but the next research lever is exit structure rather than more stop/spread tuning. This variant isolates the hypothesis that weak continuation attempts should be cut as soon as they are underwater and cannot hold the 4h ema_20.

## Out of Scope
- ETH or multi-symbol scope
- short leg
- direct reads of the BTC 4h regime probe or arbiter labels
- macro overlay coupling
- stop redesign or spread-threshold sweeps
- confirmed-entry tightening
- runtime default enablement
