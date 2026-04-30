# Cartridge Spec: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter

Derived from:
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter`.
Parallel to (not derived from) `partial67_transition_aware_late_entry_filter`:
both probes target the unresolved `sideways_transition` surface but through
structurally different gate mechanisms. This probe is the first explicit
`event-based` gate — it activates on the BBW squeeze→expansion transition plus
an unconfirmed first breakout bar, rather than on an instantaneous compression
state. Keeps the `partial67` entry, staged exit, and late-entry stretch cap
unchanged; only replaces the cap's activation context.

## Locked Spec
- id: macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter
- scope: BTC/USDT on 4h entries, 1d trend gate, long-only
- indicators:
  - entry timeframe (`4h`): macd, macd_signal, atr, ema_20, bbw, high, low, close
  - trend timeframe (`1d`): ema_20, ema_50
- entry gate:
  - keep the baseline `macd_signal_trending_up_4h` cross-up trigger
  - keep the same 1d trend gate
  - compute the squeeze-release context over `squeeze_pctrank_window` bars:
    - current BBW percentile rank ≥ `squeeze_release_current_pctrank_min` (currently expanding)
    - `min(bbw[t-squeeze_trough_lookback .. t-1])` percentile rank
      ≤ `squeeze_trough_pctrank_max` within the same `squeeze_pctrank_window`
      (true pre-window compression, not casually low)
  - compute the unconfirmed-breakout context on the prior 4h bar:
    - `prev_bar.close < prev_bar.high - weak_breakout_upper_fraction * (prev_bar.high - prev_bar.low)`
      (previous bar closed in the lower fraction of its range)
  - only when BOTH the squeeze-release context AND the unconfirmed-breakout
    context are active, block the signal if
    `max((close - ema_20) / atr, 0)` is greater than
    `entry_ema_extension_atr_max`
- stop hint: unchanged from `partial67`
- exit rules: unchanged from `partial67`
  - signal cross-down exit
  - trend-gate-lost exit
  - `DERISK_PARTIAL_GIVEBACK`
  - `GIVEBACK_EXIT`
- default research params:
  - stop_atr_mult=1.5
  - require_signal_confirmation=True
  - emit_once=True
  - trend_spread_min=0.005
  - derisk_arm_r=1.0
  - derisk_giveback_r=0.75
  - derisk_close_pct=0.67
  - giveback_exit_arm_r=1.5
  - giveback_exit_floor_r=0.25
  - entry_ema_extension_atr_max=1.25
  - squeeze_pctrank_window=100
  - squeeze_trough_lookback=20
  - squeeze_release_current_pctrank_min=60.0
  - squeeze_trough_pctrank_max=15.0
  - weak_breakout_upper_fraction=0.25
- regime: target_regime = TRENDING_UP
- off-regime entry suppression: the 1d trend gate suppresses entries unless
  `ema_20 > ema_50` and `(ema_20 - ema_50) / ema_50 >= trend_spread_min`.

## Regime Declaration
- target_regime: TRENDING_UP
- rationale: The cartridge is a BTC 4h long-only continuation strategy guarded
  by a 1d bullish EMA trend gate; its side-branch veto only localizes weak-tape
  defense and does not change the declared trend-following thesis.

## Research Intent
- primary question:
  does an explicit event-based gate — post-squeeze BBW expansion AND an
  unconfirmed first breakout bar — localize the side-branch defense onto
  `sideways_transition` where all prior state-based proxies failed?
- expected gain surface:
  default `RANGING`, `sideways_transition`, and other regime-flip slices where
  the unconditional `late_entry_filter` showed useful loser suppression that
  neither `chop_trend_only` nor `chop_trend_tightened` could reproduce.
- main failure mode:
  (a) event is too rare on the BTC 4h tape (5–15 squeeze-release instances
  over the 2023-06~09 window) so the sample is statistically noisy;
  (b) percentile-rank thresholds overfit the probe to the training window;
  (c) `weak_breakout_upper_fraction = 0.25` is too strict and blocks
  legitimate continuation breakouts in `bull_strong_up_1`.

## Pre-Committed Decision Gates

Evaluated from the Per-Window Detail table in
`reports/strategy_plugin_candidate_review.md` and the supplemental 8-window
matrix. Pinned before backtest so the result cannot be re-rationalized after
the fact.

- **Must pass (sideways_transition repair)**: `sideways_transition` net_pnl
  moves from `-196.9550` to **≥ `-50`** (ideally positive). This is the primary
  evidence window for the probe's thesis.
- **Must not break (bullish retention)**:
  - `bull_strong_up_1` ≥ `+100` (currently `chop_trend_tightened = +167.8664`)
  - `classic_rollercoaster_2021_2022` ≥ `+1700` (currently
    `chop_trend_tightened = +1816.9483`)
  - Default `TRENDING_UP` net_pnl ≥ `partial67 = +1484.5085`
- **Informative but not gating**:
  - Default `RANGING` recovery (still unresolved across the entire family;
    improvement here is a bonus, not a requirement)
  - `range_low_vol` stray loser (inherited from `chop_trend_only`; a clean
    zero here would be a bonus)

If the probe fails the `sideways_transition` gate, the result is still a
useful attribution signal: it says the 2023-06~09 bleed is not
squeeze-release driven, which collapses this mechanism class and redirects
the next pass toward window-specific macro analysis rather than more
structural gate design.

## No-Sweep Clause

Initial candidate review runs the pinned cell above only. Do **not** sweep
`squeeze_release_current_pctrank_min`, `squeeze_trough_pctrank_max`, or
`weak_breakout_upper_fraction` before the first candidate review lands. Sweep
only after the pinned cell demonstrates at least partial `sideways_transition`
repair without breaking the bullish-retention gates.

Rationale: the BTC-only 4h tape over the sample period plus percentile-rank
indicators give too much sweep surface relative to the number of actual
squeeze-release events. Sweeping before a pinned-cell signal is statistically
unreliable and tends to surface spurious best cells.

## Family Role
- structural role:
  first explicit `event-based` child inside the `weak-tape defense` side
  branch. Parallel to `partial67_transition_aware_late_entry_filter`
  (divergence-based): both probes target `sideways_transition` but test
  different underlying mechanisms.
- evaluation order:
  compare this child first against
  `partial67_chop_trend_tightened_late_entry_filter`, then against
  `partial67_transition_aware_late_entry_filter` (side-by-side on the same
  surface), then against the unconditional `late_entry_filter`, then against
  the `partial67` working baseline.
- guardrail:
  do not score this as a bullish-mainline replacement; it only answers whether
  an event-based squeeze-release + unconfirmed-breakout context can localize
  the side-branch defense better than state-based and divergence-based
  references.

## Out of Scope
- new exit logic
- stop redesign
- second-bar (post-signal) confirmation window beyond the current pinned
  prior-bar close-in-lower-quarter rule
- volume-based unconfirmed-breakout proxy in the same pass
- stacking with `remainder_ratchet`
- stacking with `transition_aware_late_entry_filter` (OR combination) before
  each child lands a clean individual candidate review
- retuning `chop_trend_tightened` thresholds in parallel
- bearish / short-side logic
- runtime default enablement
- parameter sweep before the pinned cell shows a signal (see No-Sweep Clause)
