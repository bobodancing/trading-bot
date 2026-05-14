# Weekly Profit Phase 4D Range-Break Retest Candidate Backtest

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_A_B_PLUS_RANGE_BREAK_RETEST_BACKTEST_COMPLETE`

## Scope

- Slot A LONG: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`
- Candidate: `range_break_retest_4h_conservative_30`
- Window: `2026-01-01..2026-04-30`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Runtime defaults remain unchanged; the candidate is catalog-disabled outside this backtest-only run.

## Combined Portfolio

| metric | value |
| --- | ---: |
| trades | 18 |
| net pnl | 89.7631 |
| max drawdown pct | 3.1991 |
| run errors | 0 |
| entry stop violations | 0 |

## Candidate Read

The candidate added realized trades but damaged standalone economics in this run.

| metric | value |
| --- | ---: |
| realized trades | 5 |
| net pnl | -165.1608 |
| win rate | 0.4000 |
| avg realized r | -0.2380 |
| emitted intents | 24 |
| accepted entries | 5 |
| rejects | 19 |
| router block rate | 0.0000 |

## Artifact

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_range_break_retest_candidate\portfolio_ab_range_break_retest_candidate_summary.json`
