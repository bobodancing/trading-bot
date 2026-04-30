# Cartridge Spec: rsi2_pullback_1h_sma5_gap_guard

Source: `reports/rsi2_pullback_1h_trade_attribution.md` (2026-04-25).

## Locked Child Hypothesis

- parent: `rsi2_pullback_1h`
- child id: `rsi2_pullback_1h_sma5_gap_guard`
- change: add one entry guard, `sma5_gap_atr >= min_sma5_gap_atr`
- locked param: `min_sma5_gap_atr = 0.75`
- definition: `(sma_5[1h] - close[1h]) / atr[1h]`
- intent: require enough expected bounce distance to pay for churn and fees

## What Stays Fixed

- Same symbols, timeframes, long-only side, RSI(2) entry, 1h/4h SMA200 trend gates, ATR stop, exits, max hold, cooldown, central risk path, and runtime defaults as parent.
- Parent remains available unchanged when `min_sma5_gap_atr` is unset.

## Attribution Rationale

- Parent aggregate fee drag: `0.2161`; net after estimated fees: `-353.4884`.
- Ex-post trade attribution for `sma5_gap_atr >= 0.75`:
  - trades: `144`
  - net_pnl: `1001.9927`
  - fees_est: `506.9982`
  - fee_drag_ratio: `0.1777`
  - net_after_fee_est: `494.9944`
  - `TRENDING_UP` and `MIXED` both positive after fee estimate.
- This is a churn-reduction guard, not a threshold loosening.

## Promotion Constraint

This child still requires a fresh StrategyRuntime candidate review. Ex-post attribution is only a hypothesis source, not promotion evidence.
