# Weekly Profit Phase 4B Frequency Complement Candidate Packet

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Status: `A_B_PLUS_CANDIDATE_WEEKLY_PACKET_EVALUATED`

## Executive Read

Latest contract-grade packet state is `reopen_research` for the A+B+candidate combined run.

The candidate fixes cadence but damages economics. It should not be promoted; use Phase 4C loss attribution to decide whether this research lane deserves another filter pass.

This is a research packet over backtest artifacts. Runtime defaults remain unchanged.

## Combined Weekly Summary

| metric | value |
| --- | ---: |
| entry trades | 21 |
| exit trades | 21 |
| active entry weeks | 12 |
| active entry week ratio | 0.6667 |
| after-fee positive week ratio, all weeks | 0.2778 |
| net after fee estimate | -497.9958 |
| worst after-fee week | -201.7527 |

## Latest Contract-Grade Decision

| item | value |
| --- | --- |
| week_start | `2026-04-20` |
| state | `reopen_research` |
| pause triggers | `none` |
| reopen triggers | `positive_week_ratio_exit_active_8w_after_fee, rolling_8w_net_after_fee_pnl` |
| investigate triggers | `portfolio_max_drawdown_pct_review_window` |

## Baseline Packet Delta

| metric | delta vs Phase 3 baseline |
| --- | ---: |
| active-entry week ratio 8w | 0.2500 |
| rolling 8w entry trade count | 5 |
| positive all-week ratio 8w | 0.0000 |
| rolling 8w net after-fee pnl | -403.9335 |
| baseline state -> candidate state | `investigate -> reopen_research` |

## Artifact

- Candidate packet JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_frequency_complement_candidate\weekly_profit_frequency_complement_candidate_packets.json`
- Source combined summary: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_frequency_complement_candidate\portfolio_ab_frequency_complement_candidate_summary.json`
