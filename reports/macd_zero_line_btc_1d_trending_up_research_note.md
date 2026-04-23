# Research Note: macd_zero_line_btc_1d_trending_up

## Status

- Phase 1 candidate review completed.
- Result: `0 trades` across all 3 DEFAULT_WINDOWS, with no run errors.
- Classification: infra-bounded first pass, not an edge verdict.

## First-Pass Finding

- `TRENDING_UP`: 24 lane candidates, 0 entries, all rejects `central_risk_blocked`.
- `RANGING`: 48 lane candidates, 0 entries, all rejects `central_risk_blocked`.
- `MIXED`: 0 lane candidates, 0 entries.
- Reject detail in both active windows is `max_sl_distance`, not arbiter or router rejection.

Interpretation: the cartridge generated candidates, but the locked
`stop_atr_mult=2.0` is incompatible with the current central risk cap
`MAX_SL_DISTANCE_PCT = 0.06`. This run does not tell us whether the edge is
good or bad because nothing was allowed through execution sizing.

## Re-lock Decision

- Re-lock `stop_atr_mult` from `2.0` to `1.5`.
- Keep the regime declaration, entry gate, and symbol/timeframe scope unchanged.

Rationale:

- A quick BTC 1d signal diagnostic on the clean TRENDING_UP cross showed
  `atr / close ~= 3.39%`, implying `max stop_atr_mult ~= 1.77` under the
  current 6% SL-distance cap.
- `1.5` is a conservative first-compatible lock and matches the repo's prior
  ATR-stop research convention better than retrying `2.0`.

## Second-Pass Outcome

- Second candidate review completed on the re-locked cartridge.
- Result: `3 trades` aggregate, `net_pnl = 1722.1343`, `max_dd_pct = 7.7384`.
- Per-window:
  - `TRENDING_UP`: `1 trade`, `+2072.5450`
  - `RANGING`: `2 trades`, `-350.4107`
  - `MIXED`: `0 trades`, `0.0000`
- No run errors and no `entry_stop_violations`.

Interpretation: re-locking to `stop_atr_mult=1.5` fixed the `max_sl_distance`
compatibility problem. This establishes that the cartridge can pass through
central risk and execute trades under the current baseline.

## Backtest Timing Fix

- Follow-up audit found that backtest replay exposed bars whose timestamp
  equaled the replay cursor, which leaked still-forming 1H/4H/1D candles into
  both plugin snapshots and BTC regime probes.
- `TimeSeriesEngine` now exposes only closed bars, and `MarketSnapshotBuilder`
  no longer drops the last row a second time in backtests.
- After the fix, the cartridge still produces the same trade shape
  (`1 / 2 / 0` across `TRENDING_UP / RANGING / MIXED`), but entry timestamps
  shift to the next 1H cursor and the `TRENDING_UP` reject mix now includes
  explicit `strategy_router_blocked` events instead of a pure
  `position_slot_occupied` pool.

## Current Read

- This is no longer an infra-bounded zero-trade case.
- It is also not a promotion-ready cartridge: the sample is too small, the
  declared `TRENDING_UP` thesis is only lightly evidenced, and the `RANGING`
  window remains negative.
- The `entry_regime` mismatch is now understood: plugin gating is based on a
  1D EMA trend check, while the trade artifact records an audit-only BTC 4H
  regime probe snapshot. Those fields are comparable, but they are not the
  same contract.
