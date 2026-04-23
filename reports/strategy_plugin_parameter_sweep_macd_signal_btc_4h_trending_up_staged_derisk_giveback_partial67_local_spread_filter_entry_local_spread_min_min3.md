# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter_entry_local_spread_min_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter_entry_local_spread_min_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_local_spread_min": 0.001}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_002` | `{"entry_local_spread_min": 0.002}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_003` | `{"entry_local_spread_min": 0.003}` | 3 | 45 | 1548.7114 | 4.4059 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_local_spread_min": 0.001}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_001` | `{"entry_local_spread_min": 0.001}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"entry_local_spread_min": 0.001}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_002` | `{"entry_local_spread_min": 0.002}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_002` | `{"entry_local_spread_min": 0.002}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"entry_local_spread_min": 0.002}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_003` | `{"entry_local_spread_min": 0.003}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_003` | `{"entry_local_spread_min": 0.003}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"entry_local_spread_min": 0.003}` | MIXED | 16 | 238.0897 | 3.0317 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
