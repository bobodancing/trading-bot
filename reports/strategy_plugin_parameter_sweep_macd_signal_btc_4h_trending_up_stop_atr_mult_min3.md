# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_stop_atr_mult_min3`.
- Candidate: `macd_signal_btc_4h_trending_up`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up\macd_signal_btc_4h_trending_up_stop_atr_mult_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"stop_atr_mult": 1.25}` | 3 | 49 | 1043.8396 | 5.6521 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | 3 | 46 | 1394.7769 | 5.1601 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | 3 | 45 | 1310.4755 | 5.1335 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"stop_atr_mult": 1.25}` | TRENDING_UP | 27 | 1253.5297 | 5.6521 | 0 | 0 |
| `cell_001` | `{"stop_atr_mult": 1.25}` | RANGING | 3 | -234.5563 | 2.4601 | 0 | 0 |
| `cell_001` | `{"stop_atr_mult": 1.25}` | MIXED | 19 | 24.8662 | 3.8069 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | TRENDING_UP | 26 | 1400.3197 | 5.1601 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"stop_atr_mult": 1.5}` | MIXED | 17 | 168.3439 | 3.1864 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | TRENDING_UP | 26 | 1402.9140 | 5.1335 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | RANGING | 3 | -233.9603 | 2.4668 | 0 | 0 |
| `cell_003` | `{"stop_atr_mult": 1.75}` | MIXED | 16 | 141.5218 | 3.8800 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
