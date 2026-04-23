# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_giveback_floor_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback\macd_signal_btc_4h_trending_up_staged_derisk_giveback_giveback_floor_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"giveback_exit_floor_r": 0.15}` | 3 | 46 | 1513.5037 | 4.6026 | 0 | 0 |
| `cell_002` | `{"giveback_exit_floor_r": 0.25}` | 3 | 46 | 1513.5037 | 4.6026 | 0 | 0 |
| `cell_003` | `{"giveback_exit_floor_r": 0.35}` | 3 | 46 | 1513.5037 | 4.6026 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"giveback_exit_floor_r": 0.15}` | TRENDING_UP | 26 | 1462.5462 | 4.6026 | 0 | 0 |
| `cell_001` | `{"giveback_exit_floor_r": 0.15}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"giveback_exit_floor_r": 0.15}` | MIXED | 17 | 224.8443 | 3.0223 | 0 | 0 |
| `cell_002` | `{"giveback_exit_floor_r": 0.25}` | TRENDING_UP | 26 | 1462.5462 | 4.6026 | 0 | 0 |
| `cell_002` | `{"giveback_exit_floor_r": 0.25}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"giveback_exit_floor_r": 0.25}` | MIXED | 17 | 224.8443 | 3.0223 | 0 | 0 |
| `cell_003` | `{"giveback_exit_floor_r": 0.35}` | TRENDING_UP | 26 | 1462.5462 | 4.6026 | 0 | 0 |
| `cell_003` | `{"giveback_exit_floor_r": 0.35}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"giveback_exit_floor_r": 0.35}` | MIXED | 17 | 224.8443 | 3.0223 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
