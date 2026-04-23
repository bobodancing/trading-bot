# Cartridge Spec: macd_signal_btc_4h_trending_up

Derived from: `macd_zero_line_btc_1d_trending_up` low-frequency probe. This is a
new cartridge that moves the entry trigger down to 4h while keeping a 1d trend
gate. It is not a re-lock of the daily zero-line cartridge.

## Locked Spec
- id: macd_signal_btc_4h_trending_up
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: previous_macd <= previous_macd_signal AND macd > macd_signal AND, when signal confirmation is enabled, macd > 0 AND the 1d gate passes (`ema_20 > ema_50` and `(ema_20 - ema_50) / ema_50 >= trend_spread_min`) AND emit_once has not already fired on the 4h candle
- stop hint: entry_price - stop_atr_mult * atr, using the 4h ATR on the entry candle
- exit rules:
  - close when the 4h signal flips back down (`previous_macd >= previous_macd_signal` AND `macd < macd_signal`)
  - close when the 1d trend gate no longer passes
- locked params: stop_atr_mult=1.5, require_signal_confirmation=True, emit_once=True, trend_spread_min=0.005
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the cartridge does not read router or arbiter state directly; it suppresses entries with the 1d EMA trend gate so the 4h continuation trigger does not trade as a naked all-regimes long signal

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: the daily zero-line cartridge proved that trend-side sign exists but was too sparse for the desired research tempo. This cartridge keeps the same directional thesis while moving the trigger to 4h so we can observe more continuation attempts without removing regime discipline.

## Out of Scope
- ETH or multi-symbol scope
- short leg
- direct reads of the BTC 4h regime probe or arbiter labels
- macro overlay coupling
- loosening the 1d gate just to manufacture more trades
- parameter sweep before the first candidate review
- runtime default enablement
