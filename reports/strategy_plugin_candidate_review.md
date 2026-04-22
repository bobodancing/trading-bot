# Strategy Plugin Candidate Review

## Executive read

- Verdict: `KEEP_RESEARCH_ONLY`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `rsi_mean_reversion_1h` | 3 | 14 | -169.0739 | 3.0004 |

## Per-Window Detail

| candidate_id | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `rsi_mean_reversion_1h` | TRENDING_UP | 4 | -244.7604 | 3.0004 | 0 | 0 |
| `rsi_mean_reversion_1h` | RANGING | 5 | -48.2845 | 1.9632 | 0 | 0 |
| `rsi_mean_reversion_1h` | MIXED | 5 | 123.9711 | 1.2669 | 0 | 0 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
