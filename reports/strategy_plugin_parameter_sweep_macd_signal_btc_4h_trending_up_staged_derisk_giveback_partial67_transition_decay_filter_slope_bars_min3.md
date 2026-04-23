# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter_slope_bars_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter_slope_bars_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_slope_bars": 3}` | 3 | 36 | 969.9790 | 4.6554 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 5}` | 3 | 38 | 924.7444 | 4.6554 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 10}` | 3 | 34 | 981.4051 | 4.7082 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_slope_bars": 3}` | TRENDING_UP | 22 | 822.2919 | 4.6554 | 0 | 0 |
| `cell_001` | `{"trend_spread_slope_bars": 3}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"trend_spread_slope_bars": 3}` | MIXED | 11 | 321.5739 | 2.3435 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 5}` | TRENDING_UP | 22 | 822.2919 | 4.6554 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 5}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"trend_spread_slope_bars": 5}` | MIXED | 13 | 276.3393 | 2.4339 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 10}` | TRENDING_UP | 21 | 691.1179 | 4.7082 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 10}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_003` | `{"trend_spread_slope_bars": 10}` | MIXED | 12 | 335.5683 | 2.3435 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
