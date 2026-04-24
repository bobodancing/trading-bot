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
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter` | 3 | 42 | 1848.6305 | 2.9860 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter` | 3 | 37 | 1230.6759 | 4.5977 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | 3 | 44 | 1682.5711 | 4.4059 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | 3 | 16 | 1856.8086 | 1.8572 |
| `donchian_range_fade_4h` | 3 | 9 | 78.4857 | 2.2463 |
| `donchian_range_fade_4h_range_width_cv_013` | 3 | 15 | 567.1316 | 2.1990 |
| `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` | 3 | 8 | 312.8271 | 0.0353 |
| `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` | 3 | 13 | 446.3331 | 2.1990 |

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
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter` | TRENDING_UP | 24 | 1670.0429 | 2.7932 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter` | MIXED | 15 | 352.4744 | 2.9860 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter` | TRENDING_UP | 22 | 992.0771 | 4.5977 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter` | MIXED | 14 | 283.8799 | 2.5850 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | TRENDING_UP | 9 | 1401.7272 | 1.8572 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter` | MIXED | 6 | 500.3624 | 1.7122 | 0 | 0 |
| `donchian_range_fade_4h` | TRENDING_UP | 2 | -83.0180 | 2.2463 | 0 | 0 |
| `donchian_range_fade_4h` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `donchian_range_fade_4h` | MIXED | 7 | 161.5037 | 0.6442 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013` | TRENDING_UP | 6 | 272.9137 | 2.1990 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013` | RANGING | 2 | 132.7142 | 0.0000 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013` | MIXED | 7 | 161.5037 | 0.6442 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` | TRENDING_UP | 4 | 145.9096 | 0.0353 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` | MIXED | 4 | 166.9175 | 0.0000 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` | TRENDING_UP | 6 | 272.9137 | 2.1990 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` | RANGING | 2 | 132.7142 | 0.0000 | 0 | 0 |
| `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` | MIXED | 5 | 40.7051 | 0.6442 | 0 | 0 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
