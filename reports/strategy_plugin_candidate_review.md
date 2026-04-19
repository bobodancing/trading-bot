# Strategy Plugin Candidate Review

## Executive read

- Verdict: `KEEP_RESEARCH_ONLY`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `ema_cross_7_19_long_only` | 3 | 126 | 1191.5251 | 33.5825 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
