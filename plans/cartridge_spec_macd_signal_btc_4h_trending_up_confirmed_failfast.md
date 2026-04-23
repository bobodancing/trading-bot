# Cartridge Spec: macd_signal_btc_4h_trending_up_confirmed_failfast

Derived from: `macd_signal_btc_4h_trending_up_confirmed`. This is a new
cartridge that keeps the same confirmed 4h entry, 1d trend gate, and ATR stop
while adding a plugin-owned failed-continuation exit so weak follow-through
does not wait for a full signal flip or stop hit.

## Locked Spec
- id: macd_signal_btc_4h_trending_up_confirmed_failfast
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, macd_hist, ema_20, atr
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate: identical to `macd_signal_btc_4h_trending_up_confirmed`
- stop hint: entry_price - stop_atr_mult * atr, using the 4h ATR on the entry candle
- exit rules:
  - close when the 4h signal flips back down (`previous_macd >= previous_macd_signal` AND `macd < macd_signal`)
  - close when the 1d trend gate no longer passes
  - close as `FAILED_CONTINUATION_EXIT` when at least `failed_continuation_bars` 4h bars have elapsed since entry and the latest 4h close is still not above both the entry price and the 4h ema_20
- locked params: stop_atr_mult=1.5, emit_once=True, trend_spread_min=0.005, failed_continuation_bars=2
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the cartridge does not read router or arbiter state directly; it suppresses entries with a 1d EMA trend gate and uses a local 4h fail-fast exit so continuation attempts that stall quickly do not linger as all-regimes risk.

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: the confirmed-entry variant improved drawdown and reduced range-side contamination, but it also showed that stricter entry alone can cut too much participation. This variant isolates the next structural hypothesis: keep the same higher-quality entry, then exit faster when the trade fails to follow through within the first two 4h bars.

## Out of Scope
- ETH or multi-symbol scope
- short leg
- direct reads of the BTC 4h regime probe or arbiter labels
- macro overlay coupling
- loosening entry confirmation just to recover lost trade count
- stop redesign before the first candidate review
- runtime default enablement
