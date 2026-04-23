# Baseline Snapshot: macd_signal_btc_4h_trending_up (Frozen Baseline)

Established: `2026-04-22`

Purpose: freeze the original locked configuration and first clean candidate
review outcome as the `frozen baseline` in the family's dual-baseline setup.

## Dual Baseline Framing

This file remains the snapshot for the `frozen baseline` only.

- `frozen baseline`: `macd_signal_btc_4h_trending_up`
  - role: historical comparison anchor
  - why it stays frozen: earlier structural research and regime-side reads are
    all rooted in this first clean run
- `working baseline`:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
  - role: current practical hurdle for new research variants
  - why it is separate: it is the best locked candidate so far, but it should
    not erase the original baseline anchor

Current working-baseline snapshot:

- candidate_id: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
- aggregate: `46 trades`, `+1553.9654`, `max_dd_pct 4.4059`
- `TRENDING_UP`: `26 trades`, `+1484.5085`
- `RANGING`: `3 trades`, `-173.8867`
- `MIXED`: `17 trades`, `+243.3437`
- spec: [cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67.md:1>)
- plugin: [macd_signal_trending_up_4h_staged_derisk_giveback_partial67.py](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/trader/strategies/plugins/macd_signal_trending_up_4h_staged_derisk_giveback_partial67.py:1>)
- latest candidate review: [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

## Current Comparison Protocol

Future structural candidates in this family should now be read through the
same dual-baseline pipeline every time:

1. compare against the `working baseline` first
2. compare against the `frozen baseline` second
3. check the fixed supplemental market-phase matrix before calling the result
   structurally clean

Read intent:

- `working baseline` decides whether a new idea is worth continuing
- `frozen baseline` preserves the long research arc
- the supplemental windows catch false positives that only look good inside
  the default regime slices

## Supplemental Market-Phase Matrix

This family now carries a fixed second-layer test matrix in addition to the
standard candidate review windows.

Current matrix:

| bucket | window | dates | current working-baseline read |
| --- | --- | --- | --- |
| short | bull strong-up 1 | `2024-10-01 ~ 2025-03-31` | `10 trades`, `+2.2863%`, `max_dd_pct 6.0844` |
| short | bear persistent-down | `2025-04-01 ~ 2025-08-31` | `17 trades`, `+1.9478%`, `max_dd_pct 3.0337` |
| short | range / low-vol | `2025-09-01 ~ 2025-12-31` | `0 trades`, `0.0000%`, `4` rejects |
| short | bull recovery 2026 | `2026-01-01 ~ 2026-02-28` | `0 trades`, `0.0000%`, no candidates |
| short | FTX-style crash | `2022-11-01 ~ 2022-12-31` | `1 trade`, `-0.1629%`, `max_dd_pct 0.2905` |
| short | sideways transition | `2023-06-01 ~ 2023-09-30` | `4 trades`, `-1.9695%`, `max_dd_pct 3.2551` |
| long | classic rollercoaster | `2021-01-01 ~ 2022-12-31` | `28 trades`, `+15.6791%`, `max_dd_pct 5.1817` |
| long | recovery / ETF tape | `2023-01-01 ~ 2024-12-31` | `50 trades`, `+10.6388%`, `max_dd_pct 7.0284` |

Interpretation guardrail:

- these supplemental windows are market-phase slices, not pure regime-isolated
  windows
- a candidate that only improves the default regime report but degrades the
  long windows should not be treated as a clean step forward

## Locked Config

- candidate_id: `macd_signal_btc_4h_trending_up`
- symbol: `BTC/USDT`
- entry_timeframe: `4h`
- trend_timeframe: `1d`
- target_regime: `TRENDING_UP`
- stop_atr_mult: `1.5`
- require_signal_confirmation: `True`
- emit_once: `True`
- trend_spread_min: `0.005`

Source of truth:

- spec: [cartridge_spec_macd_signal_btc_4h_trending_up.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/plans/cartridge_spec_macd_signal_btc_4h_trending_up.md:1>)
- catalog entry: [_catalog.py](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/trader/strategies/plugins/_catalog.py:46>)
- plugin: [macd_signal_trending_up_4h.py](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/trader/strategies/plugins/macd_signal_trending_up_4h.py:1>)

## Baseline Run

Command:

```bash
python -m extensions.Backtesting.scripts.run_candidate_review --candidate macd_signal_btc_4h_trending_up
```

Primary report:

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

Artifacts:

- [TRENDING_UP summary.json](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/extensions/Backtesting/results/macd_signal_btc_4h_trending_up/TRENDING_UP/summary.json>)
- [RANGING summary.json](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/extensions/Backtesting/results/macd_signal_btc_4h_trending_up/RANGING/summary.json>)
- [MIXED summary.json](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/extensions/Backtesting/results/macd_signal_btc_4h_trending_up/MIXED/summary.json>)

## Baseline Metrics

- helper verdict: `KEEP_RESEARCH_ONLY`
- aggregate trades: `46`
- aggregate net_pnl: `+1394.7769`
- aggregate max_dd_pct: `5.1601`
- run_errors: `0`
- entry_stop_violations: `0`

Per-window:

| window | trades | net_pnl | max_dd_pct | win_rate | profit_factor | trades_per_week |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | 26 | `+1400.3197` | 5.1601 | 0.4231 | 2.5583 | 1.00 |
| `RANGING` | 3 | `-173.8867` | 1.9442 | 0.0000 | 0.0000 | 0.23 |
| `MIXED` | 17 | `+168.3439` | 3.1864 | 0.3529 | 1.3884 | 0.56 |

## Baseline Signal Funnel

| window | lane_candidates | entries | rejects | rejects_by_reason |
| --- | ---: | ---: | ---: | --- |
| `TRENDING_UP` | 96 | 26 | 70 | `position_slot_occupied=57`, `strategy_router_blocked=8`, `cooldown=5` |
| `RANGING` | 8 | 3 | 5 | `position_slot_occupied=4`, `cooldown=1` |
| `MIXED` | 72 | 17 | 55 | `position_slot_occupied=36`, `strategy_router_blocked=16`, `cooldown=3` |

## Next-Run Diff Checklist

When the next backtest lands, compare in this order:

1. `working baseline` aggregate / drawdown / `MIXED` delta
2. `working baseline` trade count stability across all windows
3. supplemental market-phase matrix, especially:
   - `sideways transition`
   - `classic rollercoaster`
   - `recovery / ETF tape`
4. `frozen baseline` aggregate / drawdown delta to preserve historical context
5. `run_errors` / `entry_stop_violations`
6. `rejects_by_reason` mix, especially `strategy_router_blocked` and
   `position_slot_occupied`

If a run needs the older reference point only, compare against the frozen
baseline in this order:

1. `Locked Config`
2. `run_errors` / `entry_stop_violations`
3. `aggregate trades`, `aggregate net_pnl`, `aggregate max_dd_pct`
4. `TRENDING_UP trades`, `TRENDING_UP net_pnl`, `TRENDING_UP profit_factor`
5. `RANGING trades` and `RANGING net_pnl`
6. `rejects_by_reason` mix, especially `strategy_router_blocked` and `position_slot_occupied`

Interpretation guardrail:

- If a later run gets more trades by weakening regime discipline or simply
  moving losses from `rejects` into executed `RANGING` entries, that is not an
  automatic improvement.

## End-of-Day Summary

Today's follow-up work produced two structural variants and one clear
conclusion:

- `macd_signal_btc_4h_trending_up_confirmed`
  - `23 trades`, `+969.1953`, `max_dd_pct 3.0588`
  - improved drawdown and `TRENDING_UP` quality
  - but over-cut participation and flipped `MIXED` negative
- `macd_signal_btc_4h_trending_up_confirmed_failfast`
  - `23 trades`, `+683.1721`, `max_dd_pct 3.4713`
  - live `FAILED_CONTINUATION_EXIT` behavior confirmed
  - but aggregate quality degraded further and `MIXED` worsened

Net read:

- baseline `macd_signal_btc_4h_trending_up` remains the best reference
  configuration
- `stop_atr_mult=1.5` stays locked
- `trend_spread_min` stays locked
- the next useful lever is neither more stop tuning nor more spread tuning

Reference note:

- [macd_signal_btc_4h_trending_up_research_note.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_research_note.md:1>)

## 2026-04-23 Follow-Up

Structural exit work resumed from the locked baseline cartridge, with entry,
stop, and trend gate left unchanged.

Tested variant:

- `macd_signal_btc_4h_trending_up_underwater_ema_exit`
  - adds `UNDERWATER_EMA20_EXIT` after `1` elapsed 4h bar when the latest 4h
    close is below both entry price and 4h `ema_20`

Candidate review outcome:

- aggregate: `46 trades`, `+1424.1869`, `max_dd_pct 5.1514`
- `TRENDING_UP`: `26 trades`, `+1416.8770`
- `RANGING`: `3 trades`, `-161.0339`
- `MIXED`: `17 trades`, `+168.3439`

Net read:

- this confirms that structural exit logic can move aggregate results without
  changing frequency
- but this exact rule did **not** improve `MIXED`
- it improved a few slower losers, while also clipping at least one
  trend-side winner earlier than baseline
- baseline remains the comparison anchor for the next iteration because the
  main target surface is still unresolved

## 2026-04-23 Follow-Up (Round 2)

The next structural run tested staged de-risk plus a give-back remainder exit:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback`
  - partial close after a trade first reaches `1.0R`, then gives back at
    least `0.75R`, with open profit back to `1.0R` or less
  - move the remaining stop to break-even after that partial
  - close the remainder as `GIVEBACK_EXIT` after a prior partial if a trade
    had first reached `1.5R` and later fades to `0.25R` or less

Candidate review outcome:

- aggregate: `46 trades`, `+1513.5037`, `max_dd_pct 4.6026`
- `TRENDING_UP`: `26 trades`, `+1462.5462`
- `RANGING`: `3 trades`, `-173.8867`
- `MIXED`: `17 trades`, `+224.8443`

Net read:

- this is the first exit-side variant that improved aggregate PnL, drawdown,
  and `MIXED` without reducing trade count
- improvement came from capture recovery on give-back trades, not from tighter
  stops or tighter entry
- `RANGING` stayed unchanged, so promotion is still not on the table
- the baseline cartridge stays frozen as the historical comparison baseline,
  while staged de-risk / give-back became the first credible path toward a
  separate working baseline

## 2026-04-23 Follow-Up (Round 3)

A narrow robustness pass was run before considering any re-lock inside the
staged exit family.

Sweep reports:

- [derisk_close_pct min-3 sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_derisk_close_pct_min3.md:1>)
- [giveback_exit_floor_r min-3 sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_giveback_floor_min3.md:1>)

Observed results:

- `derisk_close_pct = 0.33`: aggregate `+1472.6475`, `max_dd_pct 4.7994`,
  `MIXED +205.9503`
- `derisk_close_pct = 0.5`: aggregate `+1513.5037`, `max_dd_pct 4.6026`,
  `MIXED +224.8443`
- `derisk_close_pct = 0.67`: aggregate `+1553.9654`, `max_dd_pct 4.4059`,
  `MIXED +243.3437`
- `giveback_exit_floor_r = 0.15 / 0.25 / 0.35`: all three cells were
  identical to the default staged run

Net read:

- staged de-risk / give-back is now formally strong enough to keep in the
  baseline-candidate pool
- inside this family, `derisk_close_pct` is the active lever and `0.67` is
  the leading tested cell so far
- `giveback_exit_floor_r` was inactive in the tested range, so more sweep
  budget should not go there right now
- the frozen baseline cartridge still stays as the historical comparison anchor
  even after later candidates are tested

## 2026-04-23 Follow-Up (Round 4)

The sweep-leading cell was then locked into a named candidate:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
  - same staged exit structure
  - only locked change from the parent staged candidate:
    `derisk_close_pct = 0.67`

Candidate review outcome:

- aggregate: `46 trades`, `+1553.9654`, `max_dd_pct 4.4059`
- `TRENDING_UP`: `26 trades`, `+1484.5085`
- `RANGING`: `3 trades`, `-173.8867`
- `MIXED`: `17 trades`, `+243.3437`

Net read:

- this locked candidate fully reproduced the sweep-leading `0.67` cell
- compared with the frozen baseline, aggregate improved by `+159.1885` and
  max drawdown improved by `-0.7542`
- compared with the staged default candidate, aggregate improved by `+40.4617`
  and max drawdown improved by `-0.1967`
- `RANGING` remained unchanged, so the family is still research-only
- among current family members, this is now the leading locked
  baseline-candidate and the correct `working baseline`

## 2026-04-23 Follow-Up (Round 5)

The `working baseline`
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` was then
checked on a fixed 8-window supplemental market-phase matrix.

Key read:

- the long-window results were better than expected:
  - `2021-01-01 ~ 2022-12-31`: `28 trades`, `+15.6791%`, `PF 2.9306`
  - `2023-01-01 ~ 2024-12-31`: `50 trades`, `+10.6388%`, `PF 1.5470`
- the unresolved weak surface stayed the same:
  - `2023-06-01 ~ 2023-09-30`: `4 trades`, `-1.9695%`, `PF 0.3308`
- this supports using `partial67` as the practical `working baseline` for the
  next ordered structural comparisons

Ordered next-work queue from here:

1. `late-entry filtering`
2. `chop / no-trade discipline`
3. `post-entry management`
4. `transition bleed`

Only after those four structural passes:

1. `winner protection vs loser suppression`
2. `separate bullish and bearish families`

## 2026-04-23 Follow-Up (Round 6)

The first ordered pass after the dual-baseline reset tested a narrow
late-entry suppression child of the current `working baseline`:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
  - keeps the `partial67` staged exit path unchanged
  - only blocks entries when `max((close - 4h ema_20) / atr, 0)` is above a
    narrow cap

Sweep read:

- `entry_ema_extension_atr_max` was live in the tested range
- `0.75` and `1.0` over-cut participation too aggressively
- `1.25` was the sweep-leading cell and matched the plugin's default research
  value

Candidate review outcome (`entry_ema_extension_atr_max = 1.25`):

- aggregate: `16 trades`, `+1856.8086`, `max_dd_pct 1.8572`
- `TRENDING_UP`: `9 trades`, `+1401.7272`
- `RANGING`: `1 trade`, `-45.2810`
- `MIXED`: `6 trades`, `+500.3624`

Supplemental matrix read versus the current `working baseline`:

- better on:
  - `bear persistent-down`
  - `sideways transition`
  - `recovery / ETF tape`
- worse on:
  - `bull strong-up 1`
  - `classic rollercoaster`

Net read:

- this is a real structural improvement path, not a dead branch
- but it is not yet a clean enough all-window winner to replace
  `partial67` as the family's `working baseline`
- keep it in the baseline-candidate pool as the leading entry-side precision
  branch
- move the next ordered pass to `chop / no-trade discipline`

## 2026-04-23 Follow-Up (Round 7)

The second ordered pass tested `chop / no-trade discipline` around the same
`working baseline` without changing the staged exit structure.

Three probes were run:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter`
  - raw `4h adx` floor
  - read: too blunt; reduced participation without fixing the weak tape
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter`
  - local `4h ema_20 / ema_50` spread gate
  - read: mostly inactive; `0.001 / 0.002` were identical to the working
    baseline
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter`
  - block entries when `adx_slope_5 < 0` and `bbw / recent_mean_bbw` falls
    below a floor
  - this was the only active `chop` branch worth keeping as a reference

Sweep read for the active `chop-trend` branch:

- `entry_bbw_ratio_min = 0.6`: `39 trades`, `+637.7384`, `max_dd_pct 4.6397`
- `entry_bbw_ratio_min = 0.75`: `33 trades`, `+972.4305`, `max_dd_pct 2.9414`
- `entry_bbw_ratio_min = 0.9`: `24 trades`, `+674.1333`, `max_dd_pct 3.0589`

Net read:

- `0.75` was the best-balanced `chop` cell
- but even that best cell stayed well below the `working baseline`
  `+1553.9654 / 4.4059 / MIXED +243.3437`
- this confirms the family can become more defensive in weak tape, but the
  current `chop` implementations pay too much in participation
- result: `chop / no-trade discipline` is now logged as a completed pass, but
  not a new baseline-candidate path

Reference reports:

- [ADX floor sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter_entry_adx_min_min3.md:1>)
- [local spread sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter_entry_local_spread_min_min3.md:1>)
- [chop-trend sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter_entry_bbw_ratio_min_min3.md:1>)

## Resume Point

Resume from the `working baseline`
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` for the next
ordered structural check, while keeping the original baseline entry frozen as
the historical anchor.

Next structural pass should be:

- implement and compare a `post-entry management` candidate against both the
  `working baseline` and the `frozen baseline`, then validate it on the fixed
  supplemental market-phase matrix including the two long windows
