# donchian_range_fade_4h_range_width_cv_013 Candidate Read

Date: 2026-04-24  
Status: `KEEP_RESEARCH_ONLY`

## Scope

- Candidate: `donchian_range_fade_4h_range_width_cv_013`
- Parent baseline: `donchian_range_fade_4h`
- Change set: only `range_width_cv_max = 0.13`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate donchian_range_fade_4h_range_width_cv_013`

## Candidate Review

| candidate | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| baseline `donchian_range_fade_4h` | 9 | 78.4857 | 2.2463 |
| child `donchian_range_fade_4h_range_width_cv_013` | 15 | 567.1316 | 2.1990 |

## Per-Window Comparison

| window | baseline trades / pnl | child trades / pnl |
| --- | --- | --- |
| TRENDING_UP | `2 / -83.0180` | `6 / +272.9137` |
| RANGING | `0 / 0.0000` | `2 / +132.7142` |
| MIXED | `7 / +161.5037` | `7 / +161.5037` |

## Read

- The child confirms the sweep read: the narrow `0.13` relaxation is enough to convert the Donchian lane from `RANGING` starvation into a live declared-regime candidate.
- This is not just a frequency bump:
  - default `RANGING` moves from zero trades to positive realized output
  - `TRENDING_UP` also improves materially instead of degrading
  - `MIXED` stays unchanged
- Risk stays controlled:
  - run errors = `0`
  - entry-stop violations = `0`
  - max drawdown improves slightly

## Interpretation

- `range_width_cv_max = 0.10` now looks too strict for the current Donchian thesis.
- `0.13` is the first clean child that deserves promotion from sweep cell to named candidate.
- It is still not promotion-shaped yet because this is only the first candidate review on the relaxed child, but it is the new leading Donchian baseline contender.

## Next Step

- Treat `donchian_range_fade_4h_range_width_cv_013` as the leading Donchian child.
- Decide whether to:
  1. re-lock the Donchian baseline around `0.13`, or
  2. run one more narrow structural pass before freezing the Donchian lane and moving to `bb_fade_squeeze_1h`.
