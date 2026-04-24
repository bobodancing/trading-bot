# Cartridge Spec: bb_fade_squeeze_1h

Source: `plans/ranging_strategy_brainstorm_design.md` §2 (2026-04-24).
Addresses δ (`rsi_mean_reversion_1h`) failure learning 3(a): local `adx < adx_max` is not a reliable ranging-edge filter (research note: 65.6% of the nominal RANGING window was classified TRENDING by the arbiter).

## Locked Spec
- id: bb_fade_squeeze_1h
- scope: BTC/USDT, ETH/USDT on 1h entry timeframe with 4h HTF gate, long-only
- indicators: rsi_14, bb_lower, bb_mid, bb_upper, bbw, adx (on 4h), atr (on 1h) from `trader.indicators.registry`; plus plugin-internal `bbw_pctrank` (rolling percentile rank of `bbw` over `bbw_pctrank_window` bars — not a registry column)
- entry gate: rsi_14[1h] < rsi_entry AND close[1h] <= bb_lower[1h] AND bbw_pctrank[1h] < bbw_pctrank_max AND adx[4h] < htf_adx_max AND bars_since_last_signal >= cooldown_bars
- stop hint: entry_price - stop_atr_mult * atr[1h]
- locked params: timeframe=1h, htf_timeframe=4h, rsi_entry=30.0, rsi_exit=55.0, bbw_pctrank_max=20.0, bbw_pctrank_window=100, htf_adx_max=20.0, htf_adx_exit=25.0, stop_atr_mult=1.5, cooldown_bars=5, emit_once=True
- exit rule: close[1h] > bb_mid[1h] (primary target) OR rsi_14[1h] > rsi_exit OR adx[4h] > htf_adx_exit
- regime: target_regime = RANGING
- off-regime entry suppression: the `adx[4h] < htf_adx_max` clause of the entry gate blocks every bar where the HTF 4h ADX is at or above `htf_adx_max`, regardless of DEFAULT_WINDOW label

## Regime Declaration
- target_regime: RANGING
- rationale: Two-layer ranging detection — (i) 4h ADX gate filters HTF-trending structure that δ's 1h-only gate missed, and (ii) BBW percentile over a 100-bar window confirms current volatility compression is historically atypical (true squeeze), not casually low. Bollinger-lower fade thesis requires compressed, non-trending structure.

## Out of Scope
- Short leg (long-only first pass; short mirror documented in brainstorm §2.10 but not implemented)
- 1h ADX filter (redundant with HTF gate; kept out to preserve single regime-detection mechanism per layer)
- Trailing stop via UPDATE_SL (fixed ATR stop hint only; exits are signal-based)
- Dynamic risk_pct adjustment
- Multi-symbol correlation filter
- Parameter re-derivation before first candidate review; any re-lock requires Ruei approval
- Running alongside C2/C3 in a combined backtest preset; each cartridge first passes individual candidate review before any combined preset
