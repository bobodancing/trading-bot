# Phase 4/5 Research Closeout

Date: 2026-05-05
Status: `PHASE_4_5_CLOSED_PARKED`
Branch: `codex/post-promotion-control-20260430`

## Scope

This closeout resolves the remaining Phase 4/5 research lanes after the A+B
runtime promotion and scanner scope repair.

- Runtime baseline: promoted fixed A+B portfolio.
- Slot A:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
  on fixed `BTC/USDT`.
- Slot B: `donchian_range_fade_4h_range_width_cv_013` on fixed `BTC/USDT` and
  `ETH/USDT`.
- Scanner universe: infra-ready, observe-only by default after
  `e5dae15 fix(runtime): restore promoted slot fixed universe`.
- Out of scope: runtime promotion, testnet/production state changes, scanner
  universe activation, threshold loosening, and recovery backlog activation.

## Inputs

- A+B post-promotion control:
  `reports/portfolio_ab_post_promotion_control.md`
- Scanner scope repair:
  `e5dae15 fix(runtime): restore promoted slot fixed universe`
- Phase 4 RSI2 first pass:
  `reports/rsi2_pullback_1h_sma5_gap_guard_first_pass.md`
- Phase 4 RSI2 robustness shelf:
  `reports/rsi2_pullback_1h_sma5_gap_guard_min_sma5_gap_atr_shelf.md`
- Phase 4.1 RSI2 stop-out attribution:
  `reports/rsi2_pullback_1h_sma5_gap_guard_stop_out_attribution.md`
- Phase 5 BB first pass:
  `reports/bb_fade_squeeze_1h_first_pass.md`
- Phase 5 BB gate attribution:
  `reports/bb_fade_squeeze_1h_gate_attribution.md`

## Phase 4 Decision: Park RSI2

Decision: park `rsi2_pullback_1h_sma5_gap_guard`; do not proceed to Phase 4.2
child spec or Phase 4.3 A+B+RSI2 combined backtest.

Evidence:

- The child materially improved the parent: aggregate estimated after-fee PnL
  moved from `-353.4884` to `+582.7172`, fee drag improved from `0.2161` to
  `0.1829`, and max drawdown fell from `9.1553%` to `3.4737%`.
- The `min_sma5_gap_atr` shelf selected `0.75` as the best balance, but it did
  not create a clean promotion path.
- Residual stop-outs remained material: `32` `sl_hit` trades with
  `-1991.2423` estimated after-fee PnL.
- Phase 4.1 attribution found broad concentrations, not a clean plugin-local
  second guard. The visible cuts retained meaningful non-stop PnL and would
  overfit participation instead of isolating a bad mechanism.
- `TRENDING_UP BTC` was net-negative after fees, but it is a research-window
  label, not a live plugin-local guard.

Read:

- RSI2 is a useful research result, but not a third-slot promotion candidate
  from this evidence set.
- Do not loosen RSI2, SMA5-gap, trend, or stop thresholds to manufacture more
  trades.
- No `ENABLED_STRATEGIES` change is justified.

## Phase 5 Decision: Park BB Fade Squeeze

Decision: park `bb_fade_squeeze_1h`; do not write a rescue child spec now.

Evidence:

- First pass produced only `1` trade, in `TRENDING_UP`, with `-38.2332` PnL.
- Target `RANGING` and `MIXED` windows both produced `0` trades.
- Gate attribution evaluated `22476` valid bars and found only `1` fully
  qualified all-gate bar.
- The main bottleneck is the BBW squeeze definition: `RSI + lower touch`
  leaves `440` bars, while adding `BBW pctrank < 20` collapses the sample to
  `2`.
- The 4h ADX gate is not the first thing to loosen; it blocks only `1` of the
  `2` bars that survive RSI, lower touch, and BBW squeeze.

Read:

- BB Fade Squeeze is implemented and tested, but the locked signal shape is not
  promotion-shaped.
- A rescue would be a squeeze-definition redesign, not a narrow hygiene pass.
- Force-rescuing it now would mix a new mechanism-design problem into the A+B
  closeout. Park until a later trigger review proves a real Slot B
  ranging/frequency gap.

## Portfolio Implication

- The 3-slot ideal path `A+B+RSI2` is closed for now.
- BB Fade Squeeze does not become the next ranging slot.
- Promoted A+B remains the only runtime portfolio.
- Scanner universe stays observe-only by default so Phase 4/5 evidence remains
  on the fixed BTC/ETH baseline.
- Recovery backlog remains `DO-NOT-START` until Ruei explicitly approves a new
  trigger review outcome and Wave 1 candidate.

## Next Gate

The next useful document is a trigger review memo, not another Phase 4.2 or
Phase 5 rescue run.

The memo should classify the remaining gap, if any, as one of:

- Slot A trend/SHORT gap.
- Slot B ranging/frequency gap.
- Transition-window coverage gap.
- No material gap.

No backlog plugin should be activated until that memo exists and Ruei approves
the selected Wave 1 direction.
