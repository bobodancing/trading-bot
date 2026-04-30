# rsi2_pullback_1h_sma5_gap_guard Robustness Shelf

Date: 2026-04-25  
Status: `RESEARCH_SWEEP_ONLY`

## Scope

- Candidate: `rsi2_pullback_1h_sma5_gap_guard`
- Sweep id: `rsi2_pullback_1h_sma5_gap_guard_min_sma5_gap_atr_shelf`
- Parameter shelf: `min_sma5_gap_atr = 0.65, 0.75, 0.85, 1.00`
- Runner:
  `python -m extensions.Backtesting.scripts.run_parameter_sweep --candidate rsi2_pullback_1h_sma5_gap_guard --sweep-id rsi2_pullback_1h_sma5_gap_guard_min_sma5_gap_atr_shelf --param min_sma5_gap_atr=0.65,0.75,0.85,1.0`
- Base sweep report: `reports/strategy_plugin_parameter_sweep_rsi2_pullback_1h_sma5_gap_guard_min_sma5_gap_atr_shelf.md`

## Aggregate Fee Shelf

Fee estimate uses `0.0004` per side on entry and exit notional.

| cell | min_sma5_gap_atr | trades | net_pnl | max_dd_pct | fees_est | fee_drag_ratio | net_after_fee_est | sl_hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cell_001 | 0.65 | 201 | 996.3264 | 5.7831 | 707.3992 | 0.1971 | 288.9271 | 37 |
| cell_002 | 0.75 | 177 | 1205.8574 | 3.4737 | 623.1402 | 0.1829 | 582.7172 | 32 |
| cell_003 | 0.85 | 146 | 870.0809 | 4.0298 | 513.9848 | 0.1862 | 356.0961 | 27 |
| cell_004 | 1.00 | 110 | 804.3138 | 2.4494 | 387.2656 | 0.1712 | 417.0482 | 23 |

## Per-Window Fee Shelf

| cell | min_sma5_gap_atr | window | trades | net_pnl | max_dd_pct | fee_drag_ratio | net_after_fee_est |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| cell_001 | 0.65 | TRENDING_UP | 101 | 686.8366 | 3.5428 | 0.1889 | 332.0153 |
| cell_001 | 0.65 | RANGING | 1 | -13.9801 | 0.3455 | n/a | -17.5177 |
| cell_001 | 0.65 | MIXED | 99 | 323.4699 | 5.7831 | 0.2040 | -25.5705 |
| cell_002 | 0.75 | TRENDING_UP | 87 | 710.6851 | 3.1446 | 0.1729 | 404.9956 |
| cell_002 | 0.75 | RANGING | 1 | -13.9801 | 0.3455 | n/a | -17.5177 |
| cell_002 | 0.75 | MIXED | 89 | 509.1524 | 3.4737 | 0.1916 | 195.2392 |
| cell_003 | 0.85 | TRENDING_UP | 72 | 557.8180 | 2.4554 | 0.1779 | 304.8915 |
| cell_003 | 0.85 | RANGING | 1 | -13.9801 | 0.3455 | n/a | -17.5177 |
| cell_003 | 0.85 | MIXED | 73 | 326.2430 | 4.0298 | 0.1924 | 68.7222 |
| cell_004 | 1.00 | TRENDING_UP | 56 | 476.6791 | 2.1840 | 0.1676 | 279.9525 |
| cell_004 | 1.00 | RANGING | 1 | -13.9801 | 0.3455 | n/a | -17.5177 |
| cell_004 | 1.00 | MIXED | 53 | 341.6148 | 2.4494 | 0.1719 | 154.6134 |

## Exit Count Shelf

| cell | min_sma5_gap_atr | rsi2_exit_target | sma5_bounce_exit | sl_hit |
| --- | ---: | ---: | ---: | ---: |
| cell_001 | 0.65 | 72 | 92 | 37 |
| cell_002 | 0.75 | 61 | 84 | 32 |
| cell_003 | 0.85 | 43 | 76 | 27 |
| cell_004 | 1.00 | 28 | 59 | 23 |

Stop-outs decline as the guard tightens, but so do target exits and sample size. The useful region is not a simple "higher is always better" rule.

## Read

- `0.65` is too loose: aggregate fee drag stays under `0.20`, but `MIXED` fails after fees and max drawdown rises to `5.7831`.
- `0.75` is the best balance in this shelf: highest aggregate after-fee estimate, positive after-fee `TRENDING_UP` and `MIXED`, and max drawdown stays materially lower than `0.65`.
- `0.85` remains viable but weaker than `0.75` on after-fee PnL and weaker than `1.00` on drawdown.
- `1.00` is the defensive variant: lower drawdown and fee drag, but fewer trades and less aggregate after-fee PnL than `0.75`.
- RANGING remains non-informative across the shelf: exactly `1` trade in every cell.

## Decision

Keep the locked child param at `min_sma5_gap_atr = 0.75`.

This shelf supports the existing child as a research candidate for the next robustness step, not promotion. The next useful move is residual stop-out attribution, not another entry guard.
