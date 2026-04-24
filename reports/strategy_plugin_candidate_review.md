# Strategy Plugin Candidate Review

## Executive read

- Verdict: `KEEP_RESEARCH_ONLY`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` | 3 | 46 | 1553.9654 | 4.4059 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter` | 3 | 36 | 1877.7400 | 2.7856 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter` | 3 | 41 | 1604.2942 | 4.3940 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter` | 3 | 41 | 1827.4113 | 2.9913 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | 3 | 16 | 1856.8086 | 1.8572 |

## Per-Window Detail

| candidate_id | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter` | TRENDING_UP | 23 | 1696.9839 | 2.7856 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter` | MIXED | 10 | 354.6428 | 2.5646 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter` | TRENDING_UP | 25 | 1511.4495 | 4.3940 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter` | MIXED | 13 | 266.7314 | 2.5884 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter` | TRENDING_UP | 24 | 1670.0429 | 2.7932 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter` | MIXED | 14 | 331.2551 | 2.9913 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | TRENDING_UP | 9 | 1401.7272 | 1.8572 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | MIXED | 6 | 500.3624 | 1.7122 | 0 | 0 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
