# Cartridge Spec: macd_zero_line_btc_1d_trending_up

Derived from: `macd_zero_line_btc_1d` baseline probe. This is a fresh
regime-scoped cartridge, not a re-lock of the baseline plugin.

## Locked Spec
- id: macd_zero_line_btc_1d_trending_up
- scope: BTC/USDT on 1d, long-only
- indicators: macd, macd_signal, atr, ema_20, ema_50 (all from trader.indicators.registry)
- entry gate: previous_macd <= 0 < macd AND macd >= macd_signal AND ema_20 > ema_50 AND (ema_20 - ema_50) / ema_50 >= trend_spread_min AND emit_once has not already fired on the candle
- stop hint: entry_price - stop_atr_mult * atr
- locked params: stop_atr_mult=1.5, require_signal_confirmation=True, emit_once=True, trend_spread_min=0.005
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the `ema_20 > ema_50` plus `trend_spread_min` clauses block entries when the BTC daily context is structurally SHORT or RANGING under the repo's 1d EMA fallback semantics

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: MACD zero-line cross is a trend-continuation trigger. The baseline probe proved the signal shape, but EMA research notes showed that naked long-only trend cartridges fail promotion when they trade through ranging windows without explicit suppression.

## Out of Scope
- ETH or multi-symbol scope
- Short leg
- 4h regime-engine coupling or direct arbiter snapshot reads
- Macro overlay coupling
- Counter-trend size reduction in place of suppression
- Custom EMA trend lengths beyond the registry `ema_20` / `ema_50` pair
- Parameter sweep before the first candidate review
- Runtime default enablement
