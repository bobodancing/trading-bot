# rsi2_pullback_1h_sma5_gap_guard First Pass

Date: 2026-04-25  
Status: `SUPERSEDED_BY_PHASE_4_CLOSEOUT`

Closeout update (2026-05-05): Phase 4 is parked in
`reports/phase_4_5_research_closeout.md`; do not promote or runtime-enable this
candidate from the first-pass result alone.

## Scope

- Candidate: `rsi2_pullback_1h_sma5_gap_guard`
- Parent: `rsi2_pullback_1h`
- Locked child spec: `plans/cartridge_spec_rsi2_pullback_1h_sma5_gap_guard.md`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate rsi2_pullback_1h_sma5_gap_guard`

## Candidate Review Read

| window | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 87 | 710.6851 | 3.1446 |
| RANGING | 1 | -13.9801 | 0.3455 |
| MIXED | 89 | 509.1524 | 3.4737 |
| aggregate | 177 | 1205.8574 | 3.4737 |

Primary source: `reports/strategy_plugin_candidate_review.md`.

## Fee Drag Read

Fee estimate uses `0.0004` per side on entry and exit notional.

| window | gross_positive | fees_est | fee_drag_ratio | net_after_fee_est |
| --- | ---: | ---: | ---: | ---: |
| TRENDING_UP | 1768.2937 | 305.6895 | 0.1729 | 404.9956 |
| RANGING | 0.0000 | 3.5375 | n/a | -17.5177 |
| MIXED | 1638.7592 | 313.9132 | 0.1916 | 195.2392 |
| aggregate | 3407.0529 | 623.1402 | 0.1829 | 582.7172 |

The child clears the C3 fee-drag hard fail threshold (`fee_drag_ratio <= 0.20`) on aggregate and on both active windows.

## Parent Delta

| candidate | trades | net_pnl | max_dd_pct | fees_est | fee_drag_ratio | net_after_fee_est |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| parent `rsi2_pullback_1h` | 268 | 589.4543 | 9.1553 | 942.9427 | 0.2161 | -353.4884 |
| child `rsi2_pullback_1h_sma5_gap_guard` | 177 | 1205.8574 | 3.4737 | 623.1402 | 0.1829 | 582.7172 |

The single `sma5_gap_atr >= 0.75` guard removed `91` trades, cut estimated fees by `319.8025`, reduced max drawdown by `5.6816` points, and flipped estimated after-fee aggregate PnL positive.

## Exit Attribution

| window | rsi2_exit_target | sma5_bounce_exit | sl_hit |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 30 | 39 | 18 |
| RANGING | 0 | 1 | 0 |
| MIXED | 31 | 44 | 14 |
| aggregate | 61 | 84 | 32 |

The guard reduced stop-outs from parent `52` to child `32`, but stop-outs still account for most residual drawdown.

## Signal Reject Read

| window | position_slot_occupied | strategy_router_blocked | cooldown |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 29 | 49 | 6 |
| RANGING | 3 | 3 | 0 |
| MIXED | 53 | 48 | 2 |

As with the parent, `strategy_router_blocked` comes from the current central arbiter path under default runtime config. The child does not bypass routing or risk.

## What Improved

- Aggregate net PnL improved from `589.4543` to `1205.8574`.
- Aggregate estimated after-fee PnL improved from `-353.4884` to `582.7172`.
- Aggregate fee drag improved from `0.2161` to `0.1829`.
- `TRENDING_UP` and `MIXED` both became positive after fee estimate.
- Max drawdown fell from `9.1553` to `3.4737`.

## What Still Blocks Promotion

- RANGING remains effectively absent: `1` trade, negative after fee estimate.
- This is still one fresh child pass, not robustness evidence.
- Stop-outs remain material: `32` aggregate `sl_hit` trades.
- The current review windows are not enough to prove stability across more market slices.

## Recommended Next Step

Do not promote or runtime-enable yet.

Next move should be robustness-focused, not another entry-threshold tweak:

1. Run a parameter shelf around `min_sma5_gap_atr` (`0.65`, `0.75`, `0.85`, `1.00`) using the same StrategyRuntime path.
2. Keep aggregate fee drag `<= 0.20` and after-fee PnL positive in at least `TRENDING_UP` and `MIXED`.
3. Inspect residual `sl_hit` trades before adding any second guard.

## Verdict

`rsi2_pullback_1h_sma5_gap_guard` is a real improvement over the parent and clears the C3 fee-drag hard gate, but it stays research-only until robustness review.
