# Cartridge Spec: donchian_range_fade_4h_range_width_cv_013_mid_drift_guard

Derived from: `donchian_range_fade_4h_range_width_cv_013`.
This is a narrow structural probe for the Donchian lane. It keeps the relaxed
`range_width_cv_max = 0.13` child intact and adds one extra geometric guard:
the Donchian channel midpoint must stay locally stable. The goal is to test
whether the `0.13` uplift reflects real range structure or merely admits
drifting channels that happen to have acceptable width CV.

## Research Spec
- id: `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard`
- scope: BTC/USDT, ETH/USDT on 4h, long-only, single-timeframe
- indicators: unchanged from `donchian_range_fade_4h_range_width_cv_013`
  - registry: `rsi_14`, `atr`
  - plugin-internal: `donchian_high`, `donchian_low`, `donchian_mid`,
    `donchian_width`, `width_cv`, lower/upper touch counts
- entry gate:
  - unchanged from `donchian_range_fade_4h_range_width_cv_013` except:
  - `range_detected` now requires both:
    - `width_cv < 0.13`
    - `mid_drift_ratio <= mid_drift_ratio_max`
- `mid_drift_ratio` definition:
  - `abs(donchian_mid[now] - donchian_mid[now-range_window+1]) / donchian_width[now]`
- default research params:
  - timeframe=4h
  - donchian_len=20
  - range_window=15
  - range_width_cv_max=0.13
  - mid_drift_ratio_max=0.10
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
  can the Donchian lane keep the `0.13` child's revived `RANGING` behavior
  after filtering out channels whose midpoint is sliding too far during the
  detection window
- desired read:
  preserve most of the `RANGING` recovery while reducing the chance that the
  `0.13` improvement is just drifting, off-thesis tape
- main failure mode:
  the drift guard may be too strict and collapse the lane back into
  `range_detected` starvation

## Family Role
- structural role:
  orthogonal structural validation pass on top of the `0.13` child
- evaluation order:
  compare directly against `donchian_range_fade_4h_range_width_cv_013`
- guardrail:
  do not touch RSI, touch counts, touch band, cooldown, stop, or exits in the
  same pass

## Out of Scope
- re-locking the Donchian baseline
- changing `range_width_cv_max` again
- changing `touch_atr_band`
- changing lower/upper touch-count requirements
- changing exits or stop structure
- multi-timeframe confirmation
- runtime default enablement
