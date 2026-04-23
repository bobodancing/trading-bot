# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_zero_line_btc_1d_trending_up_trend_spread_min_min3`.
- Candidate: `macd_zero_line_btc_1d_trending_up`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_zero_line_btc_1d_trending_up\macd_zero_line_btc_1d_trending_up_trend_spread_min_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_min": 0.005}` | 3 | 3 | 1722.1343 | 7.7384 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.01}` | 3 | 2 | -350.4107 | 4.9190 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.02}` | 3 | 1 | -147.3149 | 2.7763 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_min": 0.005}` | TRENDING_UP | 1 | 2072.5450 | 7.7384 | 0 | 0 |
| `cell_001` | `{"trend_spread_min": 0.005}` | RANGING | 2 | -350.4107 | 4.9190 | 0 | 0 |
| `cell_001` | `{"trend_spread_min": 0.005}` | MIXED | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.01}` | TRENDING_UP | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.01}` | RANGING | 2 | -350.4107 | 4.9190 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.01}` | MIXED | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.02}` | TRENDING_UP | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.02}` | RANGING | 1 | -147.3149 | 2.7763 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.02}` | MIXED | 0 | 0.0000 | 0.0000 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
