# Weekly Profit Phase 4B Frequency Complement Candidate Backtest

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_A_B_PLUS_CANDIDATE_BACKTEST_COMPLETE`

## Scope

- Slot A LONG: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`
- Candidate: `btc_recovery_band_trend_breadth_4h`
- Window: `2026-01-01..2026-04-30`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Runtime defaults remain unchanged; the candidate is catalog-disabled outside this backtest-only run.

## Combined Portfolio

The combined run is not promotion-ready: the candidate raises participation but makes the contiguous-window economics negative.

| metric | value |
| --- | ---: |
| trades | 22 |
| net pnl | -407.1782 |
| max drawdown pct | 6.7132 |
| run errors | 0 |
| entry stop violations | 0 |

## Candidate Read

The candidate is the loss source in this run and must stay research-only.

| metric | value |
| --- | ---: |
| realized trades | 9 |
| net pnl | -662.1021 |
| win rate | 0.2222 |
| avg realized r | -0.7422 |
| emitted intents | 53 |
| accepted entries | 9 |
| rejects | 44 |
| router block rate | 0.0755 |

## Artifact

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_frequency_complement_candidate\portfolio_ab_frequency_complement_candidate_summary.json`
