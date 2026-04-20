# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.

## Sweep settings

- Sweep id: `ema719_atr_mult_smoke`.
- Candidate: `ema_cross_7_19_long_only`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\ema_cross_7_19_long_only\ema719_atr_mult_smoke`.
- Windows: `RANGING`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"atr_mult": 1.0}` | 1 | 28 | -2143.9916 | 30.2754 | 0 | 0 |
| `cell_002` | `{"atr_mult": 1.5}` | 1 | 28 | -2541.3711 | 33.5825 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
