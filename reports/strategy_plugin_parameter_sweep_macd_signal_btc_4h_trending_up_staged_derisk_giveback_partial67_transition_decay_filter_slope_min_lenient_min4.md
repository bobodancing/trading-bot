# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter_slope_min_lenient_min4`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter_slope_min_lenient_min4`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.01}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.005}` | 3 | 46 | 1553.9654 | 4.4059 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.002}` | 3 | 42 | 878.3848 | 4.6602 | 0 | 0 |
| `cell_004` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": 0}` | 3 | 36 | 969.9790 | 4.6554 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.01}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_001` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.01}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.01}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.005}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.005}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.005}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.002}` | TRENDING_UP | 23 | 814.1819 | 4.6602 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.002}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": -0.002}` | MIXED | 16 | 238.0897 | 3.0317 | 0 | 0 |
| `cell_004` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": 0}` | TRENDING_UP | 22 | 822.2919 | 4.6554 | 0 | 0 |
| `cell_004` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": 0}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_004` | `{"trend_spread_slope_bars": 3, "trend_spread_slope_min": 0}` | MIXED | 11 | 321.5739 | 2.3435 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
