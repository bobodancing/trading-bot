# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `ema_cross_7_19_long_only_20260420T031210Z`.
- Candidate: `ema_cross_7_19_long_only`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\ema_cross_7_19_long_only\ema_cross_7_19_long_only_20260420T031210Z`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"atr_mult": 1.0}` | 3 | 127 | 1104.8189 | 30.2754 | 0 | 0 |
| `cell_002` | `{"atr_mult": 1.25}` | 3 | 127 | 1817.1067 | 31.2448 | 0 | 0 |
| `cell_003` | `{"atr_mult": 1.5}` | 3 | 126 | 1191.5251 | 33.5825 | 0 | 0 |
| `cell_004` | `{"atr_mult": 1.75}` | 3 | 121 | 2636.9917 | 28.2186 | 0 | 0 |
| `cell_005` | `{"atr_mult": 2}` | 3 | 120 | 4529.3698 | 25.6600 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"atr_mult": 1.0}` | TRENDING_UP | 43 | 3834.8134 | 11.0771 | 0 | 0 |
| `cell_001` | `{"atr_mult": 1.0}` | RANGING | 28 | -2143.9916 | 30.2754 | 0 | 0 |
| `cell_001` | `{"atr_mult": 1.0}` | MIXED | 56 | -586.0030 | 21.6957 | 0 | 0 |
| `cell_002` | `{"atr_mult": 1.25}` | TRENDING_UP | 43 | 4632.1505 | 10.9606 | 0 | 0 |
| `cell_002` | `{"atr_mult": 1.25}` | RANGING | 28 | -2298.2937 | 31.2448 | 0 | 0 |
| `cell_002` | `{"atr_mult": 1.25}` | MIXED | 56 | -516.7502 | 23.2279 | 0 | 0 |
| `cell_003` | `{"atr_mult": 1.5}` | TRENDING_UP | 43 | 4220.6031 | 14.3158 | 0 | 0 |
| `cell_003` | `{"atr_mult": 1.5}` | RANGING | 28 | -2541.3711 | 33.5825 | 0 | 0 |
| `cell_003` | `{"atr_mult": 1.5}` | MIXED | 55 | -487.7069 | 22.9905 | 0 | 0 |
| `cell_004` | `{"atr_mult": 1.75}` | TRENDING_UP | 42 | 4775.0106 | 14.6835 | 0 | 0 |
| `cell_004` | `{"atr_mult": 1.75}` | RANGING | 26 | -1973.5455 | 28.2186 | 0 | 0 |
| `cell_004` | `{"atr_mult": 1.75}` | MIXED | 53 | -164.4735 | 19.6083 | 0 | 0 |
| `cell_005` | `{"atr_mult": 2}` | TRENDING_UP | 42 | 6069.5511 | 14.3075 | 0 | 0 |
| `cell_005` | `{"atr_mult": 2}` | RANGING | 26 | -1712.2242 | 25.6600 | 0 | 0 |
| `cell_005` | `{"atr_mult": 2}` | MIXED | 52 | 172.0429 | 17.1494 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
