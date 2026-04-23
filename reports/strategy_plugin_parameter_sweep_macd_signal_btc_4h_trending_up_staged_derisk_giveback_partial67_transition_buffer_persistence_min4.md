# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer_persistence_min4`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer_persistence_min4`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_persistence_bars": 1}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_002` | `{"trend_persistence_bars": 2}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_003` | `{"trend_persistence_bars": 3}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_004` | `{"trend_persistence_bars": 5}` | 3 | 44 | 1535.3729 | 4.4100 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_persistence_bars": 1}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_001` | `{"trend_persistence_bars": 1}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"trend_persistence_bars": 1}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_002` | `{"trend_persistence_bars": 2}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_002` | `{"trend_persistence_bars": 2}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"trend_persistence_bars": 2}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_003` | `{"trend_persistence_bars": 3}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_003` | `{"trend_persistence_bars": 3}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"trend_persistence_bars": 3}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_004` | `{"trend_persistence_bars": 5}` | TRENDING_UP | 24 | 1465.9160 | 4.4100 | 0 | 0 |
| `cell_004` | `{"trend_persistence_bars": 5}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_004` | `{"trend_persistence_bars": 5}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
