# Cartridge Spec: donchian_range_fade_4h

Source: `plans/ranging_strategy_brainstorm_design.md` §3 (2026-04-24).
Design principle: completely sidestep ADX-based ranging detection. Establish "this is a range" via price geometry — Donchian width stability plus dual-boundary touch evidence — so the filter mechanism is decorrelated from C1's ADX+BBW stack and from δ's failure mode.

## Locked Spec
- id: donchian_range_fade_4h
- scope: BTC/USDT, ETH/USDT on 4h, long-only, single-timeframe
- indicators: rsi_14, atr from `trader.indicators.registry`; plus plugin-internal `donchian_high`, `donchian_low`, `donchian_mid` (rolling max/min of high/low over `donchian_len` bars), `width_cv` (std/mean of `donchian_high - donchian_low` over `range_window` bars), and touch counts against both boundaries within the window — none of these are registry columns
- entry gate: range_detected AND close <= donchian_low + touch_atr_band * atr AND rsi_14 < rsi_entry AND bars_since_last_signal >= cooldown_bars
- range_detected iff ALL: (a) `width_cv < range_width_cv_max` over last `range_window` bars, (b) count of bars with `low <= donchian_low + touch_atr_band * atr` ≥ `min_lower_touches`, (c) count of bars with `high >= donchian_high - touch_atr_band * atr` ≥ `min_upper_touches`
- stop hint: entry_price - stop_atr_mult * atr
- locked params: timeframe=4h, donchian_len=20, range_window=15, range_width_cv_max=0.10, touch_atr_band=0.25, min_lower_touches=1, min_upper_touches=1, rsi_entry=40.0, exit_target="mid", break_atr_mult=0.5, stop_atr_mult=1.5, cooldown_bars=3, emit_once=True
- exit rule: (exit_target="mid": close >= donchian_mid; exit_target="opposite": close >= donchian_high - touch_atr_band * atr) OR range_break (donchian_high[now] > donchian_high[now-1] + break_atr_mult * atr OR donchian_low[now] < donchian_low[now-1] - break_atr_mult * atr)
- regime: target_regime = RANGING
- off-regime entry suppression: the `range_detected` gate fails whenever (a) channel width is expanding or contracting beyond `range_width_cv_max`, or (b) either boundary has not been tested within the last `range_window` bars — entries are blocked outside verified range structure regardless of DEFAULT_WINDOW label

## Regime Declaration
- target_regime: RANGING
- rationale: Structural geometric range filter — width stability (CV < 10%) plus both-sides-tested requirement over a 15-bar window (~2.5 days on 4h). Range is observed from price geometry, not inferred from an oscillator. Completely avoids ADX, which motivated this cartridge's design after δ's failure on local ADX.

## Out of Scope
- Short leg (long-only first pass; short mirror documented in brainstorm §3.11 but not implemented)
- ADX-based regime gates at any layer (explicit design principle — decorrelation from C1)
- Dynamic Donchian-based trailing stop (rolling-min channel trails on new lows; fixed ATR stop is more controlled and consistent with sibling cartridges)
- Variable `touch_atr_band` per symbol
- Multi-timeframe confirmation (4h only; no HTF filter — geometric range filter is self-contained)
- Parameter re-derivation before first candidate review; any re-lock requires Ruei approval
- Running alongside C1/C3 in a combined backtest preset; each cartridge first passes individual candidate review before any combined preset
