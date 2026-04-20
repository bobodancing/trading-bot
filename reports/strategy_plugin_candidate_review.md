# Strategy Plugin Candidate Review

## Executive read

- Verdict: `KEEP_RESEARCH_ONLY`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `ema_cross_7_19_long_only` | 3 | 126 | 1191.5251 | 33.5825 |

## Per-Window Detail

| candidate_id | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `ema_cross_7_19_long_only` | TRENDING_UP | 43 | 4220.6031 | 14.3158 | 0 | 0 |
| `ema_cross_7_19_long_only` | RANGING | 28 | -2541.3711 | 33.5825 | 0 | 0 |
| `ema_cross_7_19_long_only` | MIXED | 55 | -487.7069 | 22.9905 | 0 | 0 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
