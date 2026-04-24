# donchian_range_fade_4h_range_width_cv_013_mid_drift_guard Candidate Read

Date: 2026-04-24  
Status: `KEEP_RESEARCH_ONLY`

## Scope

- Candidate: `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard`
- Parent candidate: `donchian_range_fade_4h_range_width_cv_013`
- Change set:
  - keep `range_width_cv_max = 0.13`
  - add `mid_drift_ratio_max = 0.10`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate donchian_range_fade_4h_range_width_cv_013_mid_drift_guard`

## Candidate Review

| candidate | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| parent `donchian_range_fade_4h_range_width_cv_013` | 15 | 567.1316 | 2.1990 |
| child `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` | 8 | 312.8271 | 0.0353 |

## Per-Window Comparison

| window | parent trades / pnl | child trades / pnl |
| --- | --- | --- |
| TRENDING_UP | `6 / +272.9137` | `4 / +145.9096` |
| RANGING | `2 / +132.7142` | `0 / 0.0000` |
| MIXED | `7 / +161.5037` | `4 / +166.9175` |

## Read

- This is a useful falsification pass, but not a winning child.
- The guard is structurally meaningful:
  - it cuts total trade count from `15` to `8`
  - it drops `max_dd_pct` from `2.1990` to `0.0353`
  - it trims `TRENDING_UP` exposure instead of expanding it
- But it over-tightens the Donchian thesis:
  - default `RANGING` falls back to `0 trades`
  - the RANGING audit shows `0 entries` and `0 rejects`, which means the starvation happens inside plugin gating, not at runtime arbitration

## Interpretation

- The `0.13` child is not pure threshold luck, but this pass shows that some of its uplift depends on allowing channels whose midpoint still drifts.
- The new `mid_drift_ratio_max = 0.10` guard is too strict to serve as the next Donchian baseline contender.
- `donchian_range_fade_4h_range_width_cv_013` remains the leading Donchian child.

## Next Step

- Do not re-lock around `mid_drift_guard`.
- If we want one more Donchian localization pass, it should be softer than this:
  - either widen `mid_drift_ratio_max` slightly, or
  - gate drift only when it coincides with one-sided touch imbalance
- If we want to keep pipeline momentum, the cleaner move is to freeze the Donchian read at `range_width_cv_013` and move to `bb_fade_squeeze_1h`.
