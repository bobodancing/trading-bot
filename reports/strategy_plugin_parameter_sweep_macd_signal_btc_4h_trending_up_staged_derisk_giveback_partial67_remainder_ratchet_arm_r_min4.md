# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet_arm_r_min4`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet_arm_r_min4`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"remainder_ratchet_arm_r": 1.0}` | 3 | 46 | 1597.8170 | 4.1130 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_arm_r": 1.5}` | 3 | 46 | 1594.3058 | 4.1130 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_arm_r": 2}` | 3 | 46 | 1594.3058 | 4.1130 | 0 | 0 |
| `cell_004` | `{"remainder_ratchet_arm_r": 2.5}` | 3 | 46 | 1562.0733 | 4.4059 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"remainder_ratchet_arm_r": 1.0}` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `cell_001` | `{"remainder_ratchet_arm_r": 1.0}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"remainder_ratchet_arm_r": 1.0}` | MIXED | 17 | 254.9628 | 3.0182 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_arm_r": 1.5}` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_arm_r": 1.5}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"remainder_ratchet_arm_r": 1.5}` | MIXED | 17 | 251.4516 | 3.0192 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_arm_r": 2}` | TRENDING_UP | 26 | 1516.7409 | 4.1130 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_arm_r": 2}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"remainder_ratchet_arm_r": 2}` | MIXED | 17 | 251.4516 | 3.0192 | 0 | 0 |
| `cell_004` | `{"remainder_ratchet_arm_r": 2.5}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_004` | `{"remainder_ratchet_arm_r": 2.5}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_004` | `{"remainder_ratchet_arm_r": 2.5}` | MIXED | 17 | 251.4516 | 3.0192 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
