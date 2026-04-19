# Strategy Plugin Candidate Review

## Executive read

- Verdict: `NEEDS_SECOND_PASS`.
- Candidates are StrategyRuntime plugins; this report does not modify runtime `Config` defaults.
- Promotion requires Ruei decision after matrix completeness, run-error, risk, and robustness review.

## Report validity

- Warning: this report is not promotion-eligible; verdict is forced to `NEEDS_SECOND_PASS`.
- Trade invariant failures: 2.
  - `ema_cross_7_19_long_only/TRENDING_UP` row 3 BTC/USDT LONG entry=27252.99 entry_initial_sl=27334.295
  - `ema_cross_7_19_long_only/RANGING` row 4 ETH/USDT LONG entry=3215.12 entry_initial_sl=3276.5761

## Candidate summary

| candidate_id | windows | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: | ---: |
| `ema_cross_7_19_long_only` | 3 | 126 | 1222.0141 | 30.7723 |

## Run settings

- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results`.
- Backtests must use per-run Config overrides and StrategyRuntime central risk path.
