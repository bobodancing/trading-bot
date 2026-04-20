# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.

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
| `cell_005` | `{"atr_mult": 2.0}` | 3 | 120 | 4529.3698 | 25.6600 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
