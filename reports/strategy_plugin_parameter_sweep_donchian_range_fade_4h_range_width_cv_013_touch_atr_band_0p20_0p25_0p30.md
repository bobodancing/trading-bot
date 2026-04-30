# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `donchian_range_fade_4h_range_width_cv_013_touch_atr_band_0p20_0p25_0p30`.
- Candidate: `donchian_range_fade_4h_range_width_cv_013`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\donchian_range_fade_4h_range_width_cv_013\donchian_range_fade_4h_range_width_cv_013_touch_atr_band_0p20_0p25_0p30`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"touch_atr_band": 0.2}` | 3 | 9 | 330.9428 | 2.1649 | 0 | 0 |
| `cell_002` | `{"touch_atr_band": 0.25}` | 3 | 15 | 567.1316 | 2.1990 | 0 | 0 |
| `cell_003` | `{"touch_atr_band": 0.3}` | 3 | 16 | 630.5373 | 2.1990 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"touch_atr_band": 0.2}` | TRENDING_UP | 3 | 142.1491 | 2.1649 | 0 | 0 |
| `cell_001` | `{"touch_atr_band": 0.2}` | RANGING | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `cell_001` | `{"touch_atr_band": 0.2}` | MIXED | 6 | 188.7936 | 0.0000 | 0 | 0 |
| `cell_002` | `{"touch_atr_band": 0.25}` | TRENDING_UP | 6 | 272.9137 | 2.1990 | 0 | 0 |
| `cell_002` | `{"touch_atr_band": 0.25}` | RANGING | 2 | 132.7142 | 0.0000 | 0 | 0 |
| `cell_002` | `{"touch_atr_band": 0.25}` | MIXED | 7 | 161.5037 | 0.6442 | 0 | 0 |
| `cell_003` | `{"touch_atr_band": 0.3}` | TRENDING_UP | 6 | 272.9137 | 2.1990 | 0 | 0 |
| `cell_003` | `{"touch_atr_band": 0.3}` | RANGING | 2 | 132.7142 | 0.0000 | 0 | 0 |
| `cell_003` | `{"touch_atr_band": 0.3}` | MIXED | 8 | 224.9094 | 0.6404 | 0 | 0 |

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.

## Decision Read

- Status remains `RESEARCH_SWEEP_ONLY`; this sweep does not change runtime `Config` defaults, `_catalog.py`, or the locked candidate params.
- `touch_atr_band = 0.20` is too tight for the declared surface:
  default `RANGING` falls from 2 trades / +132.7142 to 0 trades / 0.0000.
- The locked default `0.25` preserves the current candidate review shape:
  15 trades / +567.1316 / max_dd 2.1990 with 0 run errors and 0 entry-stop violations.
- `0.30` is not a failure; it matches `0.25` in `TRENDING_UP` and `RANGING`, then adds one `MIXED` trade:
  16 trades / +630.5373 / max_dd 2.1990.
- Do not re-lock to `0.30` from this sweep alone. The extra `MIXED` trade is useful evidence that the touch band is not brittle on the loose side, but it is not a new structural thesis.

Decision: keep `donchian_range_fade_4h_range_width_cv_013` locked at `touch_atr_band = 0.25` and retain `KEEP_RESEARCH_ONLY`.
