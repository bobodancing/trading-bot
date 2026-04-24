# donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard Candidate Read

Date: 2026-04-24  
Status: `KEEP_RESEARCH_ONLY`

## Scope

- Candidate: `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard`
- Parent candidate: `donchian_range_fade_4h_range_width_cv_013`
- Change set:
  - keep `range_width_cv_max = 0.13`
  - add `touch_imbalance_ratio_max = 2.5`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard`

## Candidate Review

| candidate | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| parent `donchian_range_fade_4h_range_width_cv_013` | 15 | 567.1316 | 2.1990 |
| child `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` | 13 | 446.3331 | 2.1990 |

## Per-Window Comparison

| window | parent trades / pnl | child trades / pnl |
| --- | --- | --- |
| TRENDING_UP | `6 / +272.9137` | `6 / +272.9137` |
| RANGING | `2 / +132.7142` | `2 / +132.7142` |
| MIXED | `7 / +161.5037` | `5 / +40.7051` |

## Read

- This is a successful validation pass, but not a new winner.
- The soft touch-balance guard does what we wanted:
  - it preserves the revived default `RANGING` surface exactly
  - it preserves `TRENDING_UP` exactly
  - it trims only the most imbalanced tail of the Donchian lane
- The cost is concentrated in `MIXED`:
  - trades drop from `7` to `5`
  - net PnL drops from `+161.5037` to `+40.7051`
  - max drawdown does not improve

## Interpretation

- This is much healthier than `mid_drift_guard`.
- The result supports a stronger claim about the `0.13` child:
  the uplift is not pure threshold luck and does not depend on the most
  one-sided `3:1`-style touch structures.
- But the guard still does not beat the parent on performance, so it should
  remain a validation probe, not a replacement baseline.

## Next Step

- Keep `donchian_range_fade_4h_range_width_cv_013` as the leading Donchian
  child.
- Log `touch_imbalance_guard` as the soft structural confirmation pass.
- Unless you want another Donchian micro-pass, the cleaner next move is to
  freeze this lane read and move to `bb_fade_squeeze_1h`.
