# Cartridge Spec: macd_signal_btc_4h_trending_up_confirmed

Derived from: `macd_signal_btc_4h_trending_up` baseline candidate. This is a
new cartridge that keeps the same 1d trend gate, stop rule, and exit logic
while tightening the 4h continuation trigger so we can test whether weak
signal-line crosses are the main source of range-side contamination.

## Locked Spec
- id: macd_signal_btc_4h_trending_up_confirmed
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, macd_hist, ema_20, atr
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: previous_macd <= previous_macd_signal AND macd > macd_signal AND macd > 0 AND macd_hist > 0 AND macd_hist > abs(previous_macd_hist) AND close > ema_20 AND the 1d gate passes (`ema_20 > ema_50` and `(ema_20 - ema_50) / ema_50 >= trend_spread_min`) AND emit_once has not already fired on the 4h candle
- stop hint: entry_price - stop_atr_mult * atr, using the 4h ATR on the entry candle
- exit rules:
  - close when the 4h signal flips back down (`previous_macd >= previous_macd_signal` AND `macd < macd_signal`)
  - close when the 1d trend gate no longer passes
- locked params: stop_atr_mult=1.5, emit_once=True, trend_spread_min=0.005
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the cartridge does not read router or arbiter state directly; it suppresses entries with a 1d EMA trend gate and requires local 4h continuation strength so the trigger does not trade as a naked all-regimes long signal

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: the baseline 4h cartridge solved the low-frequency problem, but its sweeps showed that stop and trend-spread tuning were not the active levers. This variant keeps the same directional thesis and isolates the next structural hypothesis: requiring histogram expansion plus price-over-EMA confirmation on the 4h entry may preserve trend-side participation while removing weaker continuation attempts.

## Out of Scope
- ETH or multi-symbol scope
- short leg
- direct reads of the BTC 4h regime probe or arbiter labels
- macro overlay coupling
- loosening confirmation just to manufacture more trades
- stop or exit redesign before the first candidate review
- runtime default enablement
