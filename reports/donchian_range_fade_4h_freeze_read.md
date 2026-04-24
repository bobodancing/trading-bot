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

## Next Lane

- `bb_fade_squeeze_1h`
- then `rsi2_pullback_1h`
