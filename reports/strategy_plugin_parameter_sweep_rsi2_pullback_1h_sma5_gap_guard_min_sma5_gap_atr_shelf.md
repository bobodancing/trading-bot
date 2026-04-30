# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `rsi2_pullback_1h_sma5_gap_guard_min_sma5_gap_atr_shelf`.
- Candidate: `rsi2_pullback_1h_sma5_gap_guard`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\rsi2_pullback_1h_sma5_gap_guard\rsi2_pullback_1h_sma5_gap_guard_min_sma5_gap_atr_shelf`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"min_sma5_gap_atr": 0.65}` | 3 | 201 | 996.3264 | 5.7831 | 0 | 0 |
| `cell_002` | `{"min_sma5_gap_atr": 0.75}` | 3 | 177 | 1205.8574 | 3.4737 | 0 | 0 |
| `cell_003` | `{"min_sma5_gap_atr": 0.85}` | 3 | 146 | 870.0809 | 4.0298 | 0 | 0 |
| `cell_004` | `{"min_sma5_gap_atr": 1}` | 3 | 110 | 804.3138 | 2.4494 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"min_sma5_gap_atr": 0.65}` | TRENDING_UP | 101 | 686.8366 | 3.5428 | 0 | 0 |
| `cell_001` | `{"min_sma5_gap_atr": 0.65}` | RANGING | 1 | -13.9801 | 0.3455 | 0 | 0 |
| `cell_001` | `{"min_sma5_gap_atr": 0.65}` | MIXED | 99 | 323.4699 | 5.7831 | 0 | 0 |
| `cell_002` | `{"min_sma5_gap_atr": 0.75}` | TRENDING_UP | 87 | 710.6851 | 3.1446 | 0 | 0 |
| `cell_002` | `{"min_sma5_gap_atr": 0.75}` | RANGING | 1 | -13.9801 | 0.3455 | 0 | 0 |
| `cell_002` | `{"min_sma5_gap_atr": 0.75}` | MIXED | 89 | 509.1524 | 3.4737 | 0 | 0 |
| `cell_003` | `{"min_sma5_gap_atr": 0.85}` | TRENDING_UP | 72 | 557.8180 | 2.4554 | 0 | 0 |
| `cell_003` | `{"min_sma5_gap_atr": 0.85}` | RANGING | 1 | -13.9801 | 0.3455 | 0 | 0 |
| `cell_003` | `{"min_sma5_gap_atr": 0.85}` | MIXED | 73 | 326.2430 | 4.0298 | 0 | 0 |
| `cell_004` | `{"min_sma5_gap_atr": 1}` | TRENDING_UP | 56 | 476.6791 | 2.1840 | 0 | 0 |
| `cell_004` | `{"min_sma5_gap_atr": 1}` | RANGING | 1 | -13.9801 | 0.3455 | 0 | 0 |
| `cell_004` | `{"min_sma5_gap_atr": 1}` | MIXED | 53 | 341.6148 | 2.4494 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
