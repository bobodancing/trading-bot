# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_zero_line_btc_1d_trending_up_stop_atr_mult_min3`.
- Candidate: `macd_zero_line_btc_1d_trending_up`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_zero_line_btc_1d_trending_up\macd_zero_line_btc_1d_trending_up_stop_atr_mult_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"stop_atr_mult": 1.25}` | 3 | 3 | 2077.6333 | 8.9828 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | 3 | 3 | 1722.1343 | 7.7384 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | 3 | 1 | 1780.2630 | 6.8263 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"stop_atr_mult": 1.25}` | TRENDING_UP | 1 | 2497.6825 | 8.9828 | 0 | 0 |
| `cell_001` | `{"stop_atr_mult": 1.25}` | RANGING | 2 | -420.0491 | 5.8899 | 0 | 0 |
| `cell_001` | `{"stop_atr_mult": 1.25}` | MIXED | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | TRENDING_UP | 1 | 2072.5450 | 7.7384 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | RANGING | 2 | -350.4107 | 4.9190 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | MIXED | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | TRENDING_UP | 1 | 1780.2630 | 6.8263 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | MIXED | 0 | 0.0000 | 0.0000 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
