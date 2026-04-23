# Strategy Plugin Candidate Review

## Executive read

- Verdict: `KEEP_RESEARCH_ONLY`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet` | 3 | 46 | 1597.8170 | 4.1130 |

## Per-Window Detail

| candidate_id | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet` | MIXED | 17 | 254.9628 | 3.0182 | 0 | 0 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
