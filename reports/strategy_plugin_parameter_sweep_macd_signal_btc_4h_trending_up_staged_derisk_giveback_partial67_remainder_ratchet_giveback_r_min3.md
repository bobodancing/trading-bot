# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet_giveback_r_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet_giveback_r_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"remainder_ratchet_giveback_r": 0.75}` | 3 | 46 | 1594.3058 | 4.1130 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_giveback_r": 1}` | 3 | 46 | 1594.3058 | 4.1130 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_giveback_r": 1.25}` | 3 | 46 | 1594.3058 | 4.1130 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"remainder_ratchet_giveback_r": 0.75}` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `cell_001` | `{"remainder_ratchet_giveback_r": 0.75}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"remainder_ratchet_giveback_r": 0.75}` | MIXED | 17 | 251.4516 | 3.0192 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_giveback_r": 1}` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_giveback_r": 1}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_giveback_r": 1}` | MIXED | 17 | 251.4516 | 3.0192 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_giveback_r": 1.25}` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_giveback_r": 1.25}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_giveback_r": 1.25}` | MIXED | 17 | 251.4516 | 3.0192 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
