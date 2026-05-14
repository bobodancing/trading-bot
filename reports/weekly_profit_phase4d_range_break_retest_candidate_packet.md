# Weekly Profit Phase 4D Range-Break Retest Candidate Packet

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Status: `A_B_PLUS_RANGE_BREAK_RETEST_WEEKLY_PACKET_EVALUATED`

## Executive Read

Latest contract-grade packet state is `reopen_research` for the A+B+range-break-retest combined run.

The candidate improves cadence but damages economics. It should stay research-only until trade-level attribution proves this is repairable.

This is a research packet over backtest artifacts. Runtime defaults remain unchanged.

## Combined Weekly Summary

| metric | value |
| --- | ---: |
| entry trades | 18 |
| exit trades | 18 |
| active entry weeks | 11 |
| active entry week ratio | 0.6111 |
| after-fee positive week ratio, all weeks | 0.3333 |
| net after fee estimate | 28.7919 |
| worst after-fee week | -128.9305 |

## Latest Contract-Grade Decision

| item | value |
| --- | --- |
| week_start | `2026-04-20` |
| state | `reopen_research` |
| pause triggers | `none` |
| reopen triggers | `max_consecutive_losing_weeks_after_fee_8w, positive_week_ratio_exit_active_8w_after_fee, rolling_8w_net_after_fee_pnl` |
| investigate triggers | `none` |

## Baseline Packet Delta

| metric | delta vs Phase 3 baseline |
| --- | ---: |
| active-entry week ratio 8w | 0.3750 |
| rolling 8w entry trade count | 4 |
| positive all-week ratio 8w | 0.0000 |
| rolling 8w net after-fee pnl | -180.1378 |
| baseline state -> candidate state | `investigate -> reopen_research` |

## Artifact

- Candidate packet JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_range_break_retest_candidate\weekly_profit_range_break_retest_candidate_packets.json`
- Source combined summary: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_range_break_retest_candidate\portfolio_ab_range_break_retest_candidate_summary.json`
