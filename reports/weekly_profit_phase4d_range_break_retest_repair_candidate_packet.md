# Weekly Profit Phase 4D Range-Break Retest Candidate Packet

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Variant: `slot_a_b_promoted_plus_range_break_retest_quality_repair`
Status: `A_B_PLUS_RANGE_BREAK_RETEST_WEEKLY_PACKET_EVALUATED`

## Executive Read

Latest contract-grade packet state is `investigate` for the A+B+range-break-retest combined run.

The candidate improves cadence but damages economics. It should stay research-only until trade-level attribution proves this is repairable.

This is a research packet over backtest artifacts. Runtime defaults remain unchanged.

## Combined Weekly Summary

| metric | value |
| --- | ---: |
| entry trades | 15 |
| exit trades | 15 |
| active entry weeks | 9 |
| active entry week ratio | 0.5000 |
| after-fee positive week ratio, all weeks | 0.3333 |
| net after fee estimate | 132.0668 |
| worst after-fee week | -123.3480 |

## Latest Contract-Grade Decision

| item | value |
| --- | --- |
| week_start | `2026-04-20` |
| state | `investigate` |
| pause triggers | `none` |
| reopen triggers | `none` |
| investigate triggers | `positive_week_ratio_all_8w_after_fee, positive_week_ratio_exit_active_8w_after_fee` |

## Baseline Packet Delta

| metric | delta vs Phase 3 baseline |
| --- | ---: |
| active-entry week ratio 8w | 0.1250 |
| rolling 8w entry trade count | 1 |
| positive all-week ratio 8w | 0.0000 |
| rolling 8w net after-fee pnl | -76.8629 |
| baseline state -> candidate state | `investigate -> investigate` |

## Artifact

- Candidate packet JSON: `extensions\Backtesting\results\portfolio_ab_range_break_retest_repair_candidate\weekly_profit_range_break_retest_repair_candidate_packets.json`
- Source combined summary: `extensions\Backtesting\results\portfolio_ab_range_break_retest_repair_candidate\portfolio_ab_range_break_retest_repair_candidate_summary.json`
