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
| trades | 21 |
| net pnl | -426.7498 |
| max drawdown pct | 6.7099 |
| run errors | 0 |
| entry stop violations | 0 |

## Candidate Read

The candidate is the loss source in this run and must stay research-only.

| metric | value |
| --- | ---: |
| realized trades | 8 |
| net pnl | -681.6736 |
| win rate | 0.1250 |
| avg realized r | -0.8875 |
| emitted intents | 41 |
| accepted entries | 8 |
| rejects | 33 |
| router block rate | 0.0976 |

## Artifact

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_frequency_complement_candidate\portfolio_ab_frequency_complement_candidate_summary.json`
