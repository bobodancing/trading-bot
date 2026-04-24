# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `donchian_range_fade_4h_range_width_cv_max_min3`.
- Candidate: `donchian_range_fade_4h`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\donchian_range_fade_4h\donchian_range_fade_4h_range_width_cv_max_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"range_width_cv_max": 0.08}` | 3 | 6 | 83.8995 | 2.2463 | 0 | 0 |
| `cell_002` | `{"range_width_cv_max": 0.1}` | 3 | 9 | 78.4857 | 2.2463 | 0 | 0 |
| `cell_003` | `{"range_width_cv_max": 0.13}` | 3 | 15 | 567.1316 | 2.1990 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"range_width_cv_max": 0.08}` | TRENDING_UP | 2 | -83.0180 | 2.2463 | 0 | 0 |
| `cell_001` | `{"range_width_cv_max": 0.08}` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_001` | `{"range_width_cv_max": 0.08}` | MIXED | 4 | 166.9175 | 0.0000 | 0 | 0 |
| `cell_002` | `{"range_width_cv_max": 0.1}` | TRENDING_UP | 2 | -83.0180 | 2.2463 | 0 | 0 |
| `cell_002` | `{"range_width_cv_max": 0.1}` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_002` | `{"range_width_cv_max": 0.1}` | MIXED | 7 | 161.5037 | 0.6442 | 0 | 0 |
| `cell_003` | `{"range_width_cv_max": 0.13}` | TRENDING_UP | 6 | 272.9137 | 2.1990 | 0 | 0 |
| `cell_003` | `{"range_width_cv_max": 0.13}` | RANGING | 2 | 132.7142 | 0.0000 | 0 | 0 |
| `cell_003` | `{"range_width_cv_max": 0.13}` | MIXED | 7 | 161.5037 | 0.6442 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
