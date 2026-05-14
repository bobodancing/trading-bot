# Weekly Profit Phase 4D Range-Break Retest Repair Candidate Backtest

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_A_B_PLUS_REPAIRED_RANGE_BREAK_RETEST_BACKTEST_COMPLETE`

## Scope

- Candidate: `range_break_retest_4h_conservative_30`
- Repair params: `{"breakout_close_quality_min": 0.8325}`
- Window: `2026-01-01..2026-04-30`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Runtime defaults remain unchanged; params are a backtest-only catalog overlay.

## Combined Portfolio

| metric | value |
| --- | ---: |
| trades | 15 |
| net pnl | 182.1184 |
| max drawdown pct | 2.1947 |
| run errors | 0 |
| entry stop violations | 0 |

## Candidate Read

The repaired candidate still added realized trades with negative standalone economics.

| metric | value |
| --- | ---: |
| realized trades | 2 |
| net pnl | -72.8054 |
| win rate | 0.5000 |
| avg realized r | -0.2100 |

## Artifact

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_range_break_retest_repair_candidate\portfolio_ab_range_break_retest_repair_candidate_summary.json`
