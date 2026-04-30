# rsi2_pullback_1h First Pass

Date: 2026-04-25  
Status: `KEEP_RESEARCH_ONLY`

## Scope

- Candidate: `rsi2_pullback_1h`
- Locked spec: `plans/cartridge_spec_rsi2_pullback_1h.md`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate rsi2_pullback_1h`

## Candidate Review Read

| window | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 140 | 688.6823 | 4.6422 |
| RANGING | 2 | -4.4293 | 0.3453 |
| MIXED | 126 | -94.7987 | 9.1553 |
| aggregate | 268 | 589.4543 | 9.1553 |

Primary source: `reports/strategy_plugin_candidate_review.md`.

## Fee Drag Read

Fee estimate uses `0.0004` per side on entry and exit notional.

| window | gross_positive | fees_est | fee_drag_ratio | net_after_fee_est |
| --- | ---: | ---: | ---: | ---: |
| TRENDING_UP | 2334.7473 | 491.8803 | 0.2107 | 196.8020 |
| RANGING | 9.5508 | 7.1099 | 0.7444 | -11.5393 |
| MIXED | 2019.3167 | 443.9525 | 0.2199 | -538.7511 |
| aggregate | 4363.6148 | 942.9427 | 0.2161 | -353.4884 |

The locked C3 promotion guard treats `fee_drag_ratio > 0.20` as hard fail. The first pass fails this gate despite positive gross aggregate PnL.

## Exit Attribution

| window | rsi2_exit_target | sma5_bounce_exit | sl_hit |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 61 | 53 | 26 |
| RANGING | 0 | 2 | 0 |
| MIXED | 55 | 45 | 26 |
| aggregate | 116 | 100 | 52 |

`position_monitor` now maps C3 close reasons into readable trade exit reasons, so the result is no longer hidden under `unknown`.

## Signal Reject Read

| window | position_slot_occupied | strategy_router_blocked | cooldown |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 85 | 80 | 10 |
| RANGING | 5 | 5 | 0 |
| MIXED | 117 | 75 | 4 |

C3 declares `target_regime = ANY`, but the current candidate review still runs through the central arbiter path because runtime defaults keep `REGIME_ARBITER_ENABLED = true` and router disabled. The `strategy_router_blocked` rejects are therefore runtime-path behavior, not a plugin-local off-regime gate.

## What Landed Cleanly

- Plugin contract, catalog registration, focused unit tests, and StrategyRuntime candidate review path all worked.
- No backtest run errors.
- No entry-stop violations.
- Runtime defaults stayed unchanged; the strategy remains disabled in the catalog.
- Internal `rsi_2` and `sma_5` calculations work without requiring registry changes.

## What Failed

- The locked ANY-regime checklist wants positive net in at least two of three default windows; only `TRENDING_UP` was positive.
- RANGING participation was effectively absent: 2 trades, both net negative after fee estimate.
- MIXED had enough trades to matter and still lost before fee estimate.
- Aggregate gross PnL was positive, but estimated fees flipped it to `-353.4884`, which fails the C3 fee-drag hard gate.

## Interpretation

- The signal is structurally valid but too trade-dense for the observed gross edge.
- TRENDING_UP is the only window with a live-looking first pass, and even there the fee drag ratio is already above the hard gate.
- The current result argues against threshold loosening. A rescue would need to reduce churn or improve expectancy per trade, not simply increase trade count.

## Recommended Next Step

Do not promote or runtime-enable this candidate.

If the lane continues, use an attribution-first child spec:

1. Segment TRENDING_UP winners and losers by `rsi_2`, SMA distance, ATR distance, holding hours, and exit reason.
2. Test one churn-reduction hypothesis at a time, such as stricter 4h trend distance or minimum expected bounce distance.
3. Keep fee-drag as a hard gate before any promotion discussion.

## Verdict

`rsi2_pullback_1h` is implemented and tested, but baseline v0.1.0 stays research-only: the first pass has positive gross aggregate PnL, fails 2-of-3 window quality, and fails the C3 fee-drag hard gate.
