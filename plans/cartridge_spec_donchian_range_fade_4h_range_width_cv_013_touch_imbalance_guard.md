# Cartridge Spec: donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard

Derived from: `donchian_range_fade_4h_range_width_cv_013`.
This is a soft structural validation pass for the Donchian lane. It keeps
`range_width_cv_max = 0.13` and adds one extra geometric guard: the two range
boundaries cannot be too one-sided in how often they are tested inside the
detection window. The goal is to check whether the `0.13` uplift still holds
when we reject the most obviously imbalanced touch structures, without falling
back into the hard starvation caused by `mid_drift_guard`.

## Research Spec
- id: `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard`
- scope: BTC/USDT, ETH/USDT on 4h, long-only, single-timeframe
- indicators: unchanged from `donchian_range_fade_4h_range_width_cv_013`
  - registry: `rsi_14`, `atr`
  - plugin-internal: `donchian_high`, `donchian_low`, `donchian_mid`,
    `donchian_width`, `width_cv`, lower/upper touch counts
- entry gate:
  - unchanged from `donchian_range_fade_4h_range_width_cv_013` except:
  - `range_detected` now requires both:
    - `width_cv < 0.13`
    - `touch_imbalance_ratio <= touch_imbalance_ratio_max`
- `touch_imbalance_ratio` definition:
  - `max(lower_touches, upper_touches) / min(lower_touches, upper_touches)`
- default research params:
  - timeframe=4h
  - donchian_len=20
  - range_window=15
  - range_width_cv_max=0.13
  - touch_imbalance_ratio_max=2.5
  - touch_atr_band=0.25
  - min_lower_touches=1
  - min_upper_touches=1
  - rsi_entry=40.0
  - exit_target="mid"
  - break_atr_mult=0.5
  - stop_atr_mult=1.5
  - cooldown_bars=3
  - emit_once=True
- stop hint: unchanged from parent
- exit rules: unchanged from parent
- regime: target_regime = RANGING

## Research Intent
- primary question:
  can the Donchian lane preserve the `0.13` child's revived `RANGING` behavior
  after filtering only the most one-sided `3:1`-style boundary-touch
  structures
- threshold rationale:
  the current `0.13` child's realized entry sample spans touch ratios from
  `1.0` to `3.0`, with the default review-window `RANGING` trades sitting at
  `1.0`; `2.5` is meant to be a soft cut, not a thesis rewrite
- main failure mode:
  even a mild touch-balance requirement may still collapse back into
  `range_detected` starvation if the Donchian lane depends on asymmetric touch
  geometry more than expected

## Family Role
- structural role:
  softer alternative to `mid_drift_guard` for validating the `0.13` child
- evaluation order:
  compare directly against `donchian_range_fade_4h_range_width_cv_013`
- guardrail:
  do not touch RSI, width threshold, cooldown, stop, or exit logic in the same
  pass

## Out of Scope
- changing `range_width_cv_max` again
- changing `touch_atr_band`
- changing lower/upper touch-count minimums
- midpoint drift gating
- changing exits or stop structure
- multi-timeframe confirmation
- runtime default enablement
