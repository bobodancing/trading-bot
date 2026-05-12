# Promoted Three-Leg Weekly Feasibility Review

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_1_WEEKLY_FEASIBILITY_REVIEW_COMPLETE`

## Executive Read

Participation gap dominates. The contiguous 2026 window remains net-positive after the fee estimate, but the portfolio does not touch enough calendar weeks to support the weekly-machine objective.

The promoted runtime portfolio remains:

- Slot A LONG: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`

## Method

- Source summary: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\portfolio_ab_short_ablation_summary.json`
- Primary cadence anchor: `custom/2026_01_01_2026_04_30`
- Calendar slicing uses UTC ISO weeks anchored on Monday.
- Participation uses entry week; realized weekly outcome uses exit week.
- Week buckets overlap the requested date window; the first and last calendar buckets can therefore be partial weeks.
- The Phase 1 decision label uses exploratory screens only, not the Phase 2 KPI contract: active-entry week ratio `< 0.5000` and all-week after-fee positive ratio `< 0.5000` flag the first visible gap.
- Fee estimate uses the existing backtest convention: `0.0004` per side on entry and exit notional.
- Default and supplemental matrices overlap by design, so they are reviewed per window only.

## Primary Contiguous Read

| metric | value |
| --- | ---: |
| weeks | 18 |
| entry trades | 13 |
| exit trades | 13 |
| active entry weeks | 7 |
| zero-entry weeks | 11 |
| active entry week ratio | 0.3889 |
| after-fee positive week ratio, all weeks | 0.3333 |
| after-fee positive week ratio, exit-active weeks | 0.6667 |
| gross pnl | 254.9240 |
| fee estimate | 43.4431 |
| net after fee estimate | 211.4808 |
| worst after-fee week | -123.3480 |
| longest losing-week streak, after fee | 1 |
| longest non-positive-week streak, after fee | 4 |

## Primary Weekly Count Distribution

| trade count in week | entry-week count | exit-week count |
| ---: | ---: | ---: |
| 0 | 11 | 9 |
| 1 | 3 | 5 |
| 2 | 2 | 4 |
| 3 | 2 | 0 |

## Primary Contribution Attribution

### Slot Net After Fee Estimate

| slot | net after fee estimate |
| --- | ---: |
| `Slot A LONG` | -87.0605 |
| `Slot B LONG` | 141.1916 |
| `Slot B SHORT` | 157.3497 |

### Symbol Net After Fee Estimate

| symbol | net after fee estimate |
| --- | ---: |
| `BTC/USDT` | 93.9702 |
| `ETH/USDT` | 117.5106 |

## Scenario Window Feasibility

| matrix | window | weeks | entry trades | exit trades | active-entry ratio | positive-week ratio, all | positive-week ratio, active exits | net after fee est | worst week est | longest non-positive streak |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `default` | `TRENDING_UP` | 27 | 33 | 33 | 0.5185 | 0.4074 | 0.7333 | 1595.7505 | -236.3211 | 3 |
| `default` | `RANGING` | 14 | 5 | 5 | 0.1429 | 0.0714 | 0.5000 | 271.6890 | -48.8050 | 11 |
| `default` | `MIXED` | 31 | 24 | 24 | 0.4194 | 0.1935 | 0.4615 | 240.3876 | -116.1779 | 16 |
| `supplemental` | `bull_strong_up_1` | 27 | 18 | 18 | 0.3704 | 0.1852 | 0.5000 | 805.9770 | -91.2551 | 11 |
| `supplemental` | `bear_persistent_down` | 22 | 24 | 24 | 0.5909 | 0.2727 | 0.4615 | 240.3876 | -116.1779 | 7 |
| `supplemental` | `range_low_vol` | 18 | 3 | 3 | 0.1111 | 0.0556 | 0.5000 | 84.6192 | -14.7797 | 9 |
| `supplemental` | `bull_recovery_2026` | 9 | 4 | 4 | 0.2222 | 0.3333 | 1.0000 | 157.3497 | 0.0000 | 3 |
| `supplemental` | `ftx_style_crash` | 9 | 1 | 1 | 0.1111 | 0.1111 | 1.0000 | 26.5597 | 0.0000 | 8 |
| `supplemental` | `sideways_transition` | 18 | 5 | 5 | 0.1667 | 0.1667 | 1.0000 | 187.2699 | 0.0000 | 7 |
| `supplemental` | `classic_rollercoaster_2021_2022` | 105 | 91 | 91 | 0.4286 | 0.3048 | 0.6667 | 3669.8769 | -249.5430 | 23 |
| `supplemental` | `recovery_2023_2024` | 106 | 87 | 87 | 0.4340 | 0.2642 | 0.6364 | 3055.8365 | -236.3211 | 11 |

## Phase 1 Decision

Phase 1 answers the roadmap gate as:

> **Participation gap dominates.**

Why:

- The contiguous 2026 read remains positive after the fee estimate, so the promoted three-leg baseline is not failing first on outright expectancy.
- The same contiguous read still has too many zero-entry weeks to support a weekly-profit operating claim.
- Positive-week density improves when measured only on active exit weeks, which suggests the first business gap is cadence coverage rather than immediate alpha collapse.

## Phase 2 Input

The KPI contract should now formalize:

- minimum acceptable active-entry week ratio
- maximum acceptable zero-entry week streak
- all-week versus active-week positive-rate distinction
- after-fee weekly loss tolerance
- whether Phase 4 research should target frequency complement before edge repair

## Artifacts

- Machine-readable local summary: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\promoted_three_leg_weekly_feasibility_summary.json` (generated under the ignored `extensions/Backtesting/results/*` tree)
- Source promotion summary: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\portfolio_ab_short_ablation_summary.json`
