# Weekly Profit Phase 4D Range-Break Retest Repair Filter

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Verdict: `REPAIR_FILTER_FOUND_BACKTEST_REQUIRED`

## Executive Read

Current candidate keeps 6 diagnostic candidates, hits 4 silent zero-entry weeks, and has known gross PnL `-165.1607` USDT.

Recommended repair filter: `breakout_close_quality >= 0.8325`. It keeps 3 candidates, hits 3 silent zero-entry weeks, and has known gross PnL `2.3564` USDT before rerouting effects.

This is not promotion evidence. It is only a backtest-only repair candidate; the next proof point is A+B+repaired-candidate packet evaluation.

## Recommended Params

`{"breakout_close_quality_min": 0.8325}`

## Current Vs Recommended

| metric | current | recommended |
| --- | ---: | ---: |
| candidates | 6 | 3 |
| accepted trades | 5 | 2 |
| known gross pnl | -165.1607 | 2.3564 |
| known after-fee pnl est | -182.6889 | -4.6554 |
| silent zero-entry weeks hit | 4 | 3 |
| silent-or-zero ratio | 0.8333 | 1.0000 |
| active-week ratio | 0.1667 | 0.0000 |

## Top Filters

| filter | candidates | silent weeks | silent/zero ratio | active ratio | known gross | known after-fee | pass cadence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `bbw_pctrank <= 30 AND retest_distance_atr >= 0` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `bbw_pctrank <= 30 AND breakout_close_quality >= 0.7203` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `bbw_pctrank <= 30 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `bbw_pctrank <= 38 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `bbw_pctrank <= 40 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `range_width_pct <= 0.119773 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `retest_distance_atr >= -0.492486 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `retest_distance_atr >= -0.115555 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `retest_distance_atr >= 0 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `break_strength_atr >= 0.2648 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |
| `break_strength_atr >= 0.3754 AND breakout_close_quality >= 0.8325` | 3 | 3 | 1.0000 | 0.0000 | 2.3564 | -4.6554 | `True` |

## Selected Candidates

| key | symbol | side | week | accepted | pnl | fee est | exit | bbw_pct | retest_dist | silent/zero | active |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `2026-02-18T20:00:00Z` | `BTC/USDT` | `SHORT` | `2026-02-16` | `True` | 0.9577 | 3.5088 | `RANGE_BREAK_RETEST_BOUNDARY_FAIL` | 2.0 | 0.0627 | `True` | `False` |
| `2026-03-04T12:00:00Z` | `BTC/USDT` | `LONG` | `2026-03-02` | `True` | -125.4576 | 3.4729 | `sl_hit` | 38.0 | 0.2907 | `True` | `False` |
| `2026-03-23T00:00:00Z` | `BTC/USDT` | `SHORT` | `2026-03-23` | `True` | -23.3779 | 3.5492 | `RANGE_BREAK_RETEST_BOUNDARY_FAIL` | 40.0 | -0.4925 | `False` | `True` |
| `2026-03-05T00:00:00Z` | `ETH/USDT` | `LONG` | `2026-03-02` | `False` | 0.0000 | 0.0000 | `not_accepted` | 18.0 | 0.2377 | `True` | `False` |
| `2026-03-13T04:00:00Z` | `ETH/USDT` | `LONG` | `2026-03-09` | `True` | -18.6816 | 3.4943 | `RANGE_BREAK_RETEST_BOUNDARY_FAIL` | 20.0 | -0.1156 | `True` | `False` |
| `2026-04-11T20:00:00Z` | `ETH/USDT` | `LONG` | `2026-04-06` | `True` | 1.3987 | 3.5030 | `RANGE_BREAK_RETEST_BOUNDARY_FAIL` | 30.0 | 0.0690 | `True` | `False` |

## Guardrails

- Runtime defaults remain unchanged.
- The candidate remains catalog-disabled.
- Filter inputs are candle-derived StrategyPlugin metadata; baseline week labels are attribution only.
