# Cartridge Spec: donchian_range_fade_4h_range_width_cv_013

Derived from: `donchian_range_fade_4h`.
This is the first narrow structural child candidate for the Donchian lane. It
keeps the baseline price-geometry thesis unchanged and only relaxes
`range_width_cv_max` from `0.10` to `0.13`, because the first-pass baseline
starved the default `RANGING` window and the narrow second-pass sweep showed
that `0.13` is the first cell that wakes the declared regime surface.

## Research Spec
- id: donchian_range_fade_4h_range_width_cv_013
- scope: BTC/USDT, ETH/USDT on 4h, long-only, single-timeframe
- indicators: unchanged from `donchian_range_fade_4h`
  - registry: `rsi_14`, `atr`
  - plugin-internal: `donchian_high`, `donchian_low`, `donchian_mid`,
    `donchian_width`, `width_cv`, lower/upper touch counts
- entry gate: unchanged from `donchian_range_fade_4h` except:
  - `range_detected` now uses `width_cv < 0.13`
  - lower-touch, upper-touch, lower-band entry, RSI confirmation, and cooldown
    stay unchanged
- stop hint: unchanged from `donchian_range_fade_4h`
- exit rules: unchanged from `donchian_range_fade_4h`
  - `DONCHIAN_MID_TARGET` or `DONCHIAN_OPPOSITE_TARGET`
  - `DONCHIAN_RANGE_BREAK_UP`
  - `DONCHIAN_RANGE_BREAK_DOWN`
- default research params:
  - timeframe=4h
  - donchian_len=20
  - range_window=15
  - range_width_cv_max=0.13
  - touch_atr_band=0.25
  - min_lower_touches=1
  - min_upper_touches=1
  - rsi_entry=40.0
  - exit_target="mid"
  - break_atr_mult=0.5
  - stop_atr_mult=1.5
  - cooldown_bars=3
  - emit_once=True
- regime: target_regime = RANGING

## Research Intent
- primary question:
  does a narrow relaxation of the structural width-stability gate convert the
  Donchian baseline from `range_detected` starvation into a real `RANGING`
  cartridge without contaminating the thesis with a broader mechanism rewrite
- expected gain surface:
  default `RANGING` should print non-zero trades and positive PnL
- main failure mode:
  the wider CV gate may improve frequency only by admitting too much
  off-thesis trend noise

## Family Role
- structural role:
  first threshold-specific child candidate under the Donchian ranging lane
- evaluation order:
  compare this child first against baseline `donchian_range_fade_4h`,
  then decide whether the Donchian lane is ready for a new locked contender
- guardrail:
  keep attribution clean; do not change touch logic, RSI gate, exit target, or
  cooldown in the same pass

## Out of Scope
- changing `touch_atr_band`
- changing lower/upper touch-count requirements
- changing `rsi_entry`
- changing exits or stop structure
- multi-timeframe confirmation
- runtime default enablement
