# Cartridge Spec: rsi_mean_reversion_1h

Supersedes: `rsi_mean_reversion_15m` (promotion-ineligible under current timeframe support constraints; see checklist §5).

## Locked Spec
- id: rsi_mean_reversion_1h
- scope: BTC/USDT, ETH/USDT on 1h, long-only
- indicators: rsi_14, bb_lower, bb_mid, adx, atr (all from trader.indicators.registry)
- entry gate: rsi_14 < rsi_entry AND close <= bb_lower AND adx < adx_max AND bars_since_last_signal >= cooldown_bars
- stop hint: entry_price - stop_atr_mult * atr
- locked params: rsi_entry=25.0, rsi_exit=60.0, adx_max=25.0, adx_exit=30.0, stop_atr_mult=1.5, cooldown_bars=5
- regime: target_regime = RANGING
- off-regime entry suppression: the `adx < adx_max` clause of the entry gate blocks every bar where the registry `adx` column is at or above `adx_max`, regardless of DEFAULT_WINDOW label

## Regime Declaration
- target_regime: RANGING
- rationale: Mean reversion thesis requires price to return to its statistical mean within a bounded range; persistent trend turns the reversion side into the losing side of momentum. ADX gate enforces the regime restriction at entry, not at stop-loss.

## Out of Scope
- Short leg (cartridge is long-only)
- Cross-symbol correlation filter
- Trailing stop via UPDATE_SL (cartridge uses fixed stop hint only; exits are signal-based, not trailing)
- Dynamic risk_pct adjustment
- Multi-timeframe confirmation (1h only; no higher-tf filter)
- Parameter re-derivation before the 1h regime-distribution baseline lands; if that baseline does not support the declared RANGING thesis, Ruei may re-lock or withdraw the regime declaration.
