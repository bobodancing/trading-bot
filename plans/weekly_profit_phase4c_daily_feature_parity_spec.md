# Weekly Profit Phase 4C Daily Feature Parity Spec

Date: 2026-05-14
Status: `PHASE_4C_ACTIVE`

## Purpose

Phase 4B showed the BTC recovery-band candidate improved weekly participation
but damaged economics. Before deciding whether to freeze the lane, Phase 4C
repairs one methodological problem:

- Phase 4A probe used completed daily EMA from 4h-resampled candles.
- The StrategyRuntime backtest path uses a rolling `1d` snapshot with runtime
  closed-row selection.

The evidence chain must use the runtime path for all daily EMA features.

## Parity Rule

Diagnostic probes now compute `ema_spread_1d` from:

1. backtest `1d` cache matching the combined runtime window
2. rolling 260-bar daily snapshot
3. first 1h scan after the candidate 4h candle timestamp
4. the same completed-row rule as the plugin:
   use latest 1d row only when `latest_ts + 1 day <= now`, otherwise use the
   previous row

The backtest replay clock must also patch `trader.strategy_runtime.datetime`,
so `StrategyContext.now` follows the replay cursor instead of real wall-clock
time. Without this, the plugin can accidentally evaluate an unfinished `1d`
row during historical replay.

The backtest mock data provider must preserve a timestamp `DatetimeIndex` while
also keeping the `timestamp` column, matching the live data provider contract.
If the index degrades to a `RangeIndex`, completed-row checks cannot compare
daily candle timestamps correctly.

## Phase 4C Outputs

- Regenerated diagnostic probes
- Regenerated precision attribution
- Regenerated A+B+candidate weekly packet
- Candidate loss attribution report

## Decision Gate

The lane may continue only if both are true:

- daily-feature parity removes implementation drift
- loss attribution identifies a defensible, candle-feature-only filter that
  improves economics without destroying the participation gain

Otherwise, freeze this BTC recovery-band lane and move to the next frequency
complement family.
