# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_derisk_close_pct_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback\macd_signal_btc_4h_trending_up_staged_derisk_giveback_derisk_close_pct_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"derisk_close_pct": 0.33}` | 3 | 46 | 1472.6475 | 4.7994 | 0 | 0 |
| `cell_002` | `{"derisk_close_pct": 0.5}` | 3 | 46 | 1513.5037 | 4.6026 | 0 | 0 |
| `cell_003` | `{"derisk_close_pct": 0.67}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"derisk_close_pct": 0.33}` | TRENDING_UP | 26 | 1440.5839 | 4.7994 | 0 | 0 |
| `cell_001` | `{"derisk_close_pct": 0.33}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"derisk_close_pct": 0.33}` | MIXED | 17 | 205.9503 | 3.0495 | 0 | 0 |
| `cell_002` | `{"derisk_close_pct": 0.5}` | TRENDING_UP | 26 | 1462.5462 | 4.6026 | 0 | 0 |
| `cell_002` | `{"derisk_close_pct": 0.5}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"derisk_close_pct": 0.5}` | MIXED | 17 | 224.8443 | 3.0223 | 0 | 0 |
| `cell_003` | `{"derisk_close_pct": 0.67}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_003` | `{"derisk_close_pct": 0.67}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"derisk_close_pct": 0.67}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
