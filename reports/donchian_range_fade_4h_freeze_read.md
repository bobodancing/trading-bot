# donchian_range_fade_4h Freeze Read

Date: 2026-04-24  
Status: `FROZEN_RESEARCH_READ`

## Decision

- Freeze the Donchian lane at
  `donchian_range_fade_4h_range_width_cv_013`.
- Do not promote it.
- Do not keep running more Donchian micro-passes for now.
- Resume the ranging pipeline at `bb_fade_squeeze_1h`.

## Why

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `donchian_range_fade_4h` | 9 | 78.4857 | 2.2463 | locked baseline starved default `RANGING` |
| `donchian_range_fade_4h_range_width_cv_013` | 15 | 567.1316 | 2.1990 | first child that woke the declared thesis surface |
| `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` | 8 | 312.8271 | 0.0353 | useful falsification pass, but over-tightened back into `RANGING` starvation |
| `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` | 13 | 446.3331 | 2.1990 | softer validation pass; preserved `RANGING`, but did not beat the parent |

## Frozen Read

- `range_width_cv_max = 0.13` is the meaningful Donchian unlock.
- The uplift is not pure threshold luck:
  - hard `mid_drift_guard` proved the lane can be over-tightened back into starvation
  - soft `touch_imbalance_guard` proved the parent does not depend on the most one-sided `3:1` touch structures
- But the lane is still only `KEEP_RESEARCH_ONLY`.

## 2026-04-25 Portfolio Re-Validation

Artifacts:

- `reports/donchian_range_fade_4h_range_width_cv_013_supplemental_matrix.md`
- `reports/strategy_plugin_parameter_sweep_donchian_range_fade_4h_range_width_cv_013_touch_atr_band_0p20_0p25_0p30.md`

Supplemental matrix read:

| scope | trades | net_pnl | max_window_dd_pct | run_errors |
| --- | ---: | ---: | ---: | ---: |
| combined | 61 | 2722.0087 | 4.5660 | 0 |
| BTC/USDT slices | 37 | 1807.9676 | 2.1908 | 0 |
| ETH/USDT slices | 24 | 914.0412 | 3.5115 | 0 |

Touch-band robustness read:

| touch_atr_band | trades | net_pnl | max_dd_pct | read |
| ---: | ---: | ---: | ---: | --- |
| 0.20 | 9 | 330.9428 | 2.1649 | too tight; default `RANGING` falls to 0 trades |
| 0.25 | 15 | 567.1316 | 2.1990 | locked default; preserves current candidate shape |
| 0.30 | 16 | 630.5373 | 2.1990 | loose side is not brittle, but only adds one `MIXED` trade |

Updated read:

- Portfolio re-validation does not overturn the freeze.
- The supplemental matrix is mechanically clean and positive in every non-zero window, but it is BTC-heavy and long-window dependent.
- The per-symbol cut matters: 2025 weak-tape windows are BTC-driven, with ETH silent in `bear_persistent_down` and `range_low_vol`.
- The regime caveat remains: supplemental window names are not arbiter classifications; generated reports still classify most 4h bars as BTC `TRENDING`.
- Do not re-lock `touch_atr_band` from `0.25` to `0.30` based on one extra `MIXED` trade.
- Do not create another Donchian structural child from this result.

Verdict remains `KEEP_RESEARCH_ONLY`.

## Next Lane

- `bb_fade_squeeze_1h`
- then `rsi2_pullback_1h`
