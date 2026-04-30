# Strategy Plugin Parameter Sweep

## Executive read

- Status: `RESEARCH_SWEEP_ONLY`.
- This is second-pass research for an existing cartridge, not an optimizer.
- Results do not modify runtime `Config` defaults or `_catalog.py`.
- This report is not promotion-eligible and does not replace `strategy_plugin_candidate_review.md`.
- `max_dd_pct` in aggregate tables is the max value across windows, not the sum.

## Sweep settings

- Sweep id: `macd_signal_btc_4h_partial67_transition_aware_tightened_extension_trigger_2p5_3p0_3p5`.
- Candidate: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`.
- Results root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\sweeps\macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter\macd_signal_btc_4h_partial67_transition_aware_tightened_extension_trigger_2p5_3p0_3p5`.
- Windows: `TRENDING_UP`, `RANGING`, `MIXED`.

## Cell Summary

| cell_id | params | windows | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"transition_extension_atr_trigger": 2.5}` | 3 | 41 | 1220.0044 | 4.5877 | 0 | 0 |
| `cell_002` | `{"transition_extension_atr_trigger": 3.0}` | 3 | 44 | 1682.5711 | 4.4059 | 0 | 0 |
| `cell_003` | `{"transition_extension_atr_trigger": 3.5}` | 3 | 44 | 1682.5711 | 4.4059 | 0 | 0 |

## Per-Window Detail

| cell_id | params | window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `cell_001` | `{"transition_extension_atr_trigger": 2.5}` | TRENDING_UP | 24 | 1005.9418 | 4.5877 | 0 | 0 |
| `cell_001` | `{"transition_extension_atr_trigger": 2.5}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_001` | `{"transition_extension_atr_trigger": 2.5}` | MIXED | 16 | 259.3436 | 3.0135 | 0 | 0 |
| `cell_002` | `{"transition_extension_atr_trigger": 3.0}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_002` | `{"transition_extension_atr_trigger": 3.0}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_002` | `{"transition_extension_atr_trigger": 3.0}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |
| `cell_003` | `{"transition_extension_atr_trigger": 3.5}` | TRENDING_UP | 26 | 1484.5085 | 4.4059 | 0 | 0 |
| `cell_003` | `{"transition_extension_atr_trigger": 3.5}` | RANGING | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `cell_003` | `{"transition_extension_atr_trigger": 3.5}` | MIXED | 17 | 243.3437 | 3.0192 | 0 | 0 |

## Decision Read

The locked `3.0` trigger remains the correct default-review cell.

| trigger | aggregate read | decision |
| ---: | --- | --- |
| `2.5` | `41 / +1220.0044`, max_dd `4.5877` | too tight; cuts trend winners |
| `3.0` | `44 / +1682.5711`, max_dd `4.4059` | keep locked value |
| `3.5` | `44 / +1682.5711`, max_dd `4.4059` | no default-window improvement over `3.0` |

`2.5` keeps the default `RANGING` repair but overcuts the default
`TRENDING_UP` cell. Versus `3.0`, it removes two `TRENDING_UP` trades for a net
loss of `478.5667`:

| entry_time | pnl_usdt | read |
| --- | ---: | --- |
| `2023-10-23T01:00:00+00:00` | -88.1867 | useful loser removal |
| `2023-10-23T03:00:00+00:00` | +566.7533 | missed major trend winner |

It also removes one default `MIXED` loser (`2025-05-10T21:00:00+00:00`,
`-15.9999`), but that small benefit does not offset the `TRENDING_UP` winner
tax.

`3.5` is identical to `3.0` across the default review matrix. Because it does
not improve the matrix and is a looser veto boundary, there is no reason to
re-lock the spec upward.

Conclusion:

- keep `transition_extension_atr_trigger = 3.0`
- no spec re-lock needed
- no promotion decision is implied by this sweep; this remains
  `RESEARCH_SWEEP_ONLY`
- Phase 1 Slot A can now treat `transition_aware_tightened_late_entry_filter`
  as sweep-confirmed at the locked value

## Interpretation Guardrails

- Compare cells as diagnostics only; there is no objective-function winner.
- A cleaner cell may justify another locked candidate review, not promotion.
- Any run errors or invariant failures keep the cell in investigation status.
