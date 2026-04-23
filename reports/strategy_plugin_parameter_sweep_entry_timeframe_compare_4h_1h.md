# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `entry_timeframe_compare_4h_1h`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67\entry_timeframe_compare_4h_1h`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_timeframe": "4h"}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_002` | `{"entry_timeframe": "1h"}` | 3 | 90 | 1033.7938 | 3.8937 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_timeframe": "4h"}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_001` | `{"entry_timeframe": "4h"}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"entry_timeframe": "4h"}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_002` | `{"entry_timeframe": "1h"}` | TRENDING_UP | 48 | 705.8485 | 3.8937 | 0 | 0 |
| `cell_002` | `{"entry_timeframe": "1h"}` | RANGING | 13 | -67.7666 | 3.3671 | 0 | 0 |
| `cell_002` | `{"entry_timeframe": "1h"}` | MIXED | 29 | 395.7118 | 2.5203 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
