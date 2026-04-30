# Strategy Plugin Candidate Review

## Executive read

- Verdict: `KEEP_RESEARCH_ONLY`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter` | 3 | 40 | 1185.4120 | 4.5922 |

## Per-Window Detail

| candidate_id | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter` | TRENDING_UP | 22 | 987.3493 | 4.5922 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
