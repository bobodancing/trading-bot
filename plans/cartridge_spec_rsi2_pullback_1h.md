# Cartridge Spec: rsi2_pullback_1h

Source: `plans/ranging_strategy_brainstorm_design.md` §4 (2026-04-24).
Connors-style short-window pullback inside a long-trend filter. Classified alongside C1 and C2 in the RANGING brainstorm because it completes a three-mechanism edge portfolio, but its own thesis spans regimes (see §Regime Declaration).

## Locked Spec
- id: rsi2_pullback_1h
- scope: BTC/USDT, ETH/USDT on 1h entry timeframe with 4h HTF trend gate, long-only
- indicators: sma_200 (on 1h and 4h), atr (on 1h) from `trader.indicators.registry`; plus plugin-internal `rsi_2` (RSI with length=2 — registry only emits rsi_14) and `sma_5` on 1h (registry only emits sma_20/50/200), following the `_with_emas` precedent in `trader/strategies/plugins/ema_cross_7_19.py`
- entry gate: rsi_2[1h] < rsi_entry AND close[1h] > sma_200[1h] AND close[4h] > sma_200[4h] AND bars_since_last_signal >= cooldown_bars
- stop hint: entry_price - stop_atr_mult * atr[1h]
- locked params: timeframe=1h, htf_timeframe=4h, rsi_period=2, rsi_entry=10.0, rsi_exit=70.0, sma_trend_len=200, sma_exit_len=5, htf_sma_trend_len=200, stop_atr_mult=2.0, max_hold_bars=10, cooldown_bars=4, emit_once=True
- exit rule: rsi_2[1h] > rsi_exit (primary target) OR close[1h] > sma_5[1h] OR bars_in_position >= max_hold_bars (time stop) OR close[4h] < sma_200[4h] (HTF regime flip)
- regime: target_regime = ANY
- off-regime entry suppression: N/A under ANY

## Regime Declaration
- target_regime: ANY
- rationale: Long-trend + short-pullback thesis spans regimes. Edge is conditional on long-term uptrend (1h and 4h SMA(200) dual filter), not on a specific ADX/ranging state. Checklist §3.2 under ANY requires `net_pnl > 0` in ≥ 2 of 3 DEFAULT_WINDOWS; expected strongest in TRENDING_UP and MIXED, weakest in RANGING (rsi_2 < 10 is rare in pure consolidation). Forcing non-ANY would misalign §3.2 with the actual edge profile.

## Out of Scope
- Short leg (long-only first pass; short mirror documented in brainstorm §4.10 but not implemented)
- ADX-based HTF gate (brainstorm §4.0 revision: ADX is directionless but Connors thesis is direction-sensitive; superseded by 4h SMA(200) close-above filter)
- Trailing stop via UPDATE_SL (fixed ATR stop; exits are signal- or time-based)
- Dynamic risk_pct adjustment
- Cross-symbol correlation filter
- Parameter re-derivation before first candidate review; any re-lock requires Ruei approval
- Promoting to runtime if §5.7 fee-drag gate fails (proposed hard fail at `fee_drag_ratio > 0.20`; see brainstorm §4.12 / §5.7 — this gate is not yet checklist law but governs C3 promotion decisions)
- Running alongside C1/C2 in a combined backtest preset; each cartridge first passes individual candidate review before any combined preset
