# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_trending_up_trend_spread_min_min3`.
- Candidate: `macd_signal_btc_4h_trending_up`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up\macd_signal_btc_4h_trending_up_trend_spread_min_min3`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_min": 0.005}` | 3 | 46 | 1394.7769 | 5.1601 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.0065}` | 3 | 46 | 1394.7769 | 5.1601 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.008}` | 3 | 46 | 1394.7769 | 5.1601 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"trend_spread_min": 0.005}` | TRENDING_UP | 26 | 1400.3197 | 5.1601 | 0 | 0 |
| `cell_001` | `{"trend_spread_min": 0.005}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_001` | `{"trend_spread_min": 0.005}` | MIXED | 17 | 168.3439 | 3.1864 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.0065}` | TRENDING_UP | 26 | 1400.3197 | 5.1601 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.0065}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_002` | `{"trend_spread_min": 0.0065}` | MIXED | 17 | 168.3439 | 3.1864 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.008}` | TRENDING_UP | 26 | 1400.3197 | 5.1601 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.008}` | RANGING | 3 | -173.8867 | 1.9442 | 0 | 0 |
| `cell_003` | `{"trend_spread_min": 0.008}` | MIXED | 17 | 168.3439 | 3.1864 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
