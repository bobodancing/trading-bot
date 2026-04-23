# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter_entry_bbw_ratio_min_min3`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter_entry_bbw_ratio_min_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_bbw_ratio_min": 0.6}` | 3 | 39 | 637.7384 | 4.6397 | 0 | 0 |
| `cell_002` | `{"entry_bbw_ratio_min": 0.75}` | 3 | 33 | 972.4305 | 2.9414 | 0 | 0 |
| `cell_003` | `{"entry_bbw_ratio_min": 0.9}` | 3 | 24 | 674.1333 | 3.0589 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"entry_bbw_ratio_min": 0.6}` | TRENDING_UP | 23 | 870.7857 | 4.6397 | 0 | 0 |
| `cell_001` | `{"entry_bbw_ratio_min": 0.6}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"entry_bbw_ratio_min": 0.6}` | MIXED | 13 | -59.1606 | 2.4316 | 0 | 0 |
| `cell_002` | `{"entry_bbw_ratio_min": 0.75}` | TRENDING_UP | 21 | 1056.3201 | 2.9414 | 0 | 0 |
| `cell_002` | `{"entry_bbw_ratio_min": 0.75}` | RANGING | 2 | -128.6057 | 1.9442 | 0 | 0 |
| `cell_002` | `{"entry_bbw_ratio_min": 0.75}` | MIXED | 10 | 44.7161 | 2.4167 | 0 | 0 |
| `cell_003` | `{"entry_bbw_ratio_min": 0.9}` | TRENDING_UP | 14 | 629.4173 | 3.0589 | 0 | 0 |
| `cell_003` | `{"entry_bbw_ratio_min": 0.9}` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_003` | `{"entry_bbw_ratio_min": 0.9}` | MIXED | 10 | 44.7161 | 2.4167 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
