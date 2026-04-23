# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter_entry_ema_extension_atr_max_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter_entry_ema_extension_atr_max_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_ema_extension_atr_max": 0.75}` | 3 | 8 | 762.0800 | 1.1328 | 0 | 0 |
| `cell_002` | `{"entry_ema_extension_atr_max": 1}` | 3 | 12 | 919.1002 | 1.8422 | 0 | 0 |
| `cell_003` | `{"entry_ema_extension_atr_max": 1.25}` | 3 | 16 | 1856.8086 | 1.8572 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_ema_extension_atr_max": 0.75}` | TRENDING_UP | 3 | 474.4387 | 0.7563 | 0 | 0 |
| `cell_001` | `{"entry_ema_extension_atr_max": 0.75}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_001` | `{"entry_ema_extension_atr_max": 0.75}` | MIXED | 4 | 332.9223 | 1.1328 | 0 | 0 |
| `cell_002` | `{"entry_ema_extension_atr_max": 1}` | TRENDING_UP | 6 | 691.5555 | 1.8422 | 0 | 0 |
| `cell_002` | `{"entry_ema_extension_atr_max": 1}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_002` | `{"entry_ema_extension_atr_max": 1}` | MIXED | 5 | 272.8258 | 1.7488 | 0 | 0 |
| `cell_003` | `{"entry_ema_extension_atr_max": 1.25}` | TRENDING_UP | 9 | 1401.7272 | 1.8572 | 0 | 0 |
| `cell_003` | `{"entry_ema_extension_atr_max": 1.25}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_003` | `{"entry_ema_extension_atr_max": 1.25}` | MIXED | 6 | 500.3624 | 1.7122 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
