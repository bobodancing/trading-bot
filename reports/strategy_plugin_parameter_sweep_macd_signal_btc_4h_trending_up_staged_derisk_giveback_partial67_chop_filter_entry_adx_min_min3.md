# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter_entry_adx_min_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter_entry_adx_min_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_adx_min": 18}` | 3 | 28 | 876.6790 | 3.7431 | 0 | 0 |
| `cell_002` | `{"entry_adx_min": 22}` | 3 | 18 | 950.2827 | 1.9442 | 0 | 0 |
| `cell_003` | `{"entry_adx_min": 26}` | 2 | 10 | 449.8287 | 1.9442 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_adx_min": 18}` | TRENDING_UP | 16 | 925.6360 | 3.7431 | 0 | 0 |
| `cell_001` | `{"entry_adx_min": 18}` | RANGING | 2 | -128.6057 | 1.9442 | 0 | 0 |
| `cell_001` | `{"entry_adx_min": 18}` | MIXED | 10 | 79.6486 | 2.2400 | 0 | 0 |
| `cell_002` | `{"entry_adx_min": 22}` | TRENDING_UP | 11 | 1241.4056 | 1.8334 | 0 | 0 |
| `cell_002` | `{"entry_adx_min": 22}` | RANGING | 2 | -128.6057 | 1.9442 | 0 | 0 |
| `cell_002` | `{"entry_adx_min": 22}` | MIXED | 5 | -162.5171 | 1.9434 | 0 | 0 |
| `cell_003` | `{"entry_adx_min": 26}` | TRENDING_UP | 8 | 578.4344 | 1.9266 | 0 | 0 |
| `cell_003` | `{"entry_adx_min": 26}` | RANGING | 2 | -128.6057 | 1.9442 | 0 | 0 |
| `cell_003` | `{"entry_adx_min": 26}` | MIXED (missing) | — | — | — | — | — |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
