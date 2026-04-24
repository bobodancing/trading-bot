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

## 2026-04-23 Follow-Up (Round 8)

The third ordered pass tested `post-entry management` around the same
`working baseline`:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`
  - keeps the `partial67` entry / stop / trend gate unchanged
  - keeps the first `DERISK_PARTIAL_GIVEBACK` unchanged
  - adds `REMAINDER_RATCHET_EXIT` for the remaining position after partial
  - locked research default after sweep:
    `remainder_ratchet_arm_r = 1.0`,
    `remainder_ratchet_giveback_r = 1.0`

Parameter read:

- `remainder_ratchet_giveback_r = 0.75 / 1.0 / 1.25` was inactive in the
  first sweep
- `remainder_ratchet_arm_r` was the active timing lever
- best tested review cell was `arm_r = 1.0`:
  `46 trades`, `+1597.8170`, `max_dd_pct 4.1130`

Candidate review outcome versus the current `working baseline`:

| candidate | trades | net_pnl | max_dd_pct | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | 1484.5085 | -173.8867 | 243.3437 |
| `partial67_remainder_ratchet` | 46 | 1597.8170 | 4.1130 | 1516.7409 | -173.8867 | 254.9628 |
| delta | 0 | +43.8516 | -0.2929 | +32.2324 | 0.0000 | +11.6191 |

Supplemental 8-window read:

| window | partial67 ret% | ratchet arm10 ret% | delta |
| --- | ---: | ---: | ---: |
| bull strong-up 1 | 2.2863 | 2.8066 | +0.5203 |
| bear persistent-down | 1.9478 | 2.0640 | +0.1162 |
| range / low-vol | 0.0000 | 0.0000 | +0.0000 |
| bull recovery 2026 | 0.0000 | 0.0000 | +0.0000 |
| FTX-style crash | -0.1629 | -0.1629 | +0.0000 |
| sideways transition | -1.9695 | -1.9007 | +0.0688 |
| classic rollercoaster 2021-2022 | 15.6791 | 15.5907 | -0.0884 |
| recovery / ETF tape 2023-2024 | 10.6388 | 11.4326 | +0.7938 |

Net read:

- this is the cleanest post-entry management branch so far
- it improves the review matrix without changing trade count
- it improves the modern recovery / ETF tape window and slightly improves
  `sideways transition`
- it does **not** fix `RANGING`
- it slightly clips the 2021-2022 classic rollercoaster window, so it should
  stay in the baseline-candidate pool rather than replace the `working
  baseline` immediately

Reference reports:

- [candidate review](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [giveback-r sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet_giveback_r_min3.md:1>)
- [arm-r sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet_arm_r_min4.md:1>)

## 2026-04-23 Follow-Up (Round 9)

The fourth ordered pass tested `transition bleed` around the same `working
baseline`, with entry direction, stops, trend gate, and staged exit structure
kept unchanged.

Two probes were run:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer`
  - requires the 1d trend gate to persist for `trend_persistence_bars`
    consecutive daily bars before entry
  - sweep result:
    `1 / 2 / 3` bars were baseline-equivalent; `5` bars cut trades from `46`
    to `44` and reduced aggregate from `+1553.9654` to `+1535.3729`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter`
  - rejects entries when the 1d EMA20/EMA50 trend spread is contracting over a
    short lookback
  - best diagnostic cells improved `MIXED`, but over-cut profitable
    `TRENDING_UP` participation

Transition buffer sweep:

| persistence bars | trades | net_pnl | max_dd_pct | read |
| ---: | ---: | ---: | ---: | --- |
| `1` | 46 | 1553.9654 | 4.4059 | baseline-equivalent |
| `2` | 46 | 1553.9654 | 4.4059 | inactive |
| `3` | 46 | 1553.9654 | 4.4059 | inactive |
| `5` | 44 | 1535.3729 | 4.4100 | over-waited and cut winners |

Transition decay sweep with `trend_spread_slope_min = 0.0`:

| slope bars | trades | net_pnl | max_dd_pct | TRENDING_UP | RANGING | MIXED |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `3` | 36 | 969.9790 | 4.6554 | 822.2919 | -173.8867 | 321.5739 |
| `5` | 38 | 924.7444 | 4.6554 | 822.2919 | -173.8867 | 276.3393 |
| `10` | 34 | 981.4051 | 4.7082 | 691.1179 | -45.2810 | 335.5683 |

Lenient threshold check with `slope_bars = 3`:

| slope min | trades | net_pnl | max_dd_pct | read |
| ---: | ---: | ---: | ---: | --- |
| `-0.010` | 46 | 1553.9654 | 4.4059 | inactive |
| `-0.005` | 46 | 1553.9654 | 4.4059 | inactive |
| `-0.002` | 42 | 878.3848 | 4.6602 | active but worse |
| `0.000` | 36 | 969.9790 | 4.6554 | active but too defensive |

Net read:

- persistence buffering did not catch the current weak surface
- trend-decay filtering confirms a real weakening signal exists, but the
  tested form pays too much by removing profitable trend entries
- no transition branch enters the baseline-candidate pool
- keep `transition_decay_filter` as diagnostic evidence only

Reference reports:

- [persistence sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer_persistence_min4.md:1>)
- [slope-bars sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter_slope_bars_min3.md:1>)
- [lenient slope-min sweep](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_parameter_sweep_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter_slope_min_lenient_min4.md:1>)

## 2026-04-23 Follow-Up (Round 10)

The diagnostic pass then decomposed the two most informative surviving branches
into `winner protection` versus `loser suppression`:

- `partial67_late_entry_filter`
- `partial67_remainder_ratchet`

Default review-window decomposition versus the `working baseline`:

| candidate | common trades | baseline-only trades | same-entry delta | avoided loser pnl | missed winner pnl | net delta | primary mechanism |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `late_entry_filter` | 16 | 30 | 0.0000 | +1235.6351 | -932.7919 | +302.8432 | loser suppression with winner tax |
| `remainder_ratchet` | 46 | 0 | +43.8515 | 0.0000 | 0.0000 | +43.8515 | winner protection / capture |

Supplemental read:

- `late_entry_filter` works best where avoided losers dominate:
  `bear_persistent_down`, `ftx_style_crash`, `sideways_transition`, and
  `recovery_2023_2024`
- it degrades winner-rich tapes:
  `bull_strong_up_1` and `classic_rollercoaster_2021_2022`
- `remainder_ratchet` keeps the same trade set and mostly adds winner capture,
  with only a tiny `classic_rollercoaster_2021_2022` clip

Net read:

- `late_entry_filter` is defensive and useful diagnostically, but not a clean
  replacement for the `working baseline`
- `late_entry_filter` should later get a dedicated side-branch study as a
  `RANGING` defense probe, because it cut the default review `RANGING` cell
  from `3 trades / -173.8867` to `1 trade / -45.2810`
- `remainder_ratchet` remains the cleaner baseline-candidate branch because it
  improves same-entry capture without sacrificing participation
- do not blindly stack late-entry filtering on top of ratchet; the combined
  branch would likely import too much winner tax

Reference report:

- [winner / loser decomposition](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_winner_loser_decomposition.md:1>)

## 2026-04-24 Follow-Up (Round 11)

The next pass split the read into a `bullish mainline` versus a `weak-tape
defense` side branch, while keeping the `working baseline` entry unchanged.

Default review comparison is now formalized in the promotion-gated matrix:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `partial67_remainder_ratchet` | 46 | 1597.8170 | 4.1130 | same-entry bullish leader |
| `partial67_late_entry_filter` | 16 | 1856.8086 | 1.8572 | selective defense branch |

Family-level supplemental read:

| family | `partial67` | `ratchet` | `late_entry_filter` | read |
| --- | ---: | ---: | ---: | --- |
| bullish mainline family | `88 trades / +2860.4183` | `88 / +2962.2868` | `34 / +2360.9641` | ratchet improves capture; late-entry pays winner tax via underparticipation |
| bearish weak-tape family | `18 / +178.4922` | `18 / +186.6002` | `7 / +473.0154` | late-entry is the strongest defensive branch |
| ranging / transition family | `4 / -196.9550` | `4 / -190.0704` | `1 / +38.5007` | late-entry is the cleanest defense, but extremely selective |

Net read:

- the `bullish mainline` should stay anchored on `partial67` and
  `partial67_remainder_ratchet`
- `remainder_ratchet` remains the leading mainline candidate because it adds
  `+43.8515` in the default review and `+101.8685` across the bullish
  supplemental family without reducing trade count
- `late_entry_filter` should stay outside the bullish mainline and be reserved
  for a separate `RANGING` / transition defense branch
- do not score `late_entry_filter` as a direct replacement for the `working
  baseline`; its gain comes from selective refusal, not from a cleaner
  same-entry edge

Reference reports:

- [family split](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_family_split.md:1>)
- [candidate review](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

## 2026-04-24 Follow-Up (Round 12)

The first concrete `weak-tape defense` side-branch candidate then tested a
context-gated version of the late-entry filter:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`

Default review read:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | aggregate improved, still selective |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Key read:

- the context gate reclaimed much more `TRENDING_UP` participation than the
  unconditional `late_entry_filter`
- `MIXED` also improved materially
- but `RANGING` stayed unchanged from `partial67`, so the candidate did **not**
  actually preserve the original side-branch defense thesis

Supplemental read:

- strong positive recovery in `bear_persistent_down` and `recovery_2023_2024`
- `ftx_style_crash` loser was avoided
- but `sideways_transition` stayed unchanged at `-196.9550`
- `bull_strong_up_1` degraded to `-32.1112`
- `range_low_vol` introduced a new `1 trade / -4.2350`

Net read:

- the current OR-gated weak-tape proxy is not localized enough
- this candidate is informative research evidence, but not yet a clean
  replacement for the unconditional `late_entry_filter` side-branch read
- next side-branch pass should isolate gate attribution instead of keeping the
  current combined gate opaque

Reference report:

- [context-gated weak-tape defense](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_context_gated_weak_tape_defense.md:1>)

## 2026-04-24 Follow-Up (Round 13)

The next side-branch pass isolated the OR-gated proxy into two attribution
children:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter`

Default review read:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | OR-gated reference |
| `trend_decay_only_late_entry_filter` | 41 | 1604.2942 | 4.3940 | near-baseline, weak defense |
| `chop_trend_only_late_entry_filter` | 41 | 1827.4113 | 2.9913 | most OR-gated uplift survives |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Attribution read:

- `trend_decay_only` preserved bullish capture and improved
  `classic_rollercoaster_2021_2022`, but it failed to avoid `ftx_style_crash`
  and left `RANGING` / `sideways_transition` unchanged
- `chop_trend_only` reproduced most of the OR-gated defensive uplift and kept
  crash avoidance
- `bull_strong_up_1` identified the noisy component:
  - `trend_decay_only`: `+268.1561`
  - `chop_trend_only`: `-83.5023`
- `sideways_transition` stayed unchanged at `-196.9550` for all localized-gate
  variants, so neither current proxy reproduces the unconditional
  `late_entry_filter` defense

Net read:

- the current OR-gated result is mostly a `chop_trend` story
- `trend_decay` is not the live weak-tape defense lever at the current
  threshold
- `chop_trend` is the active weak-tape proxy, but it is still too noisy to
  become the side-branch reference

Reference report:

- [weak-tape gate attribution](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_weak_tape_gate_attribution.md:1>)

## 2026-04-24 Follow-Up (Round 14)

The next side-branch pass localized the active `chop_trend` proxy instead of
re-opening `trend_decay`:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter`
  - keeps the same `falling ADX + compressed BBW` trigger
  - only lets that trigger veto entries once the late entry is already at least
    `1.5 ATR` stretched above `ema_20`

Default review read:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | OR-gated reference |
| `chop_trend_only_late_entry_filter` | 41 | 1827.4113 | 2.9913 | raw localized-gate reference |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | best localized `chop_trend` probe so far |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Key read:

- this pass restored one default-window `MIXED` winner and improved that cell
  from `14 / +331.2551` to `15 / +352.4744`
- `bull_strong_up_1` recovered from `-83.5023` to `+167.8664`
- `bear_persistent_down` stayed strong at `+352.4744`
- `ftx_style_crash` stayed at `0.0000`
- but default `RANGING` stayed `3 / -173.8867`
- and `sideways_transition` stayed unchanged at `-196.9550`

Net read:

- this is the strongest localized `chop_trend` proxy yet
- it is good enough to supersede `chop_trend_only` as the current localization
  reference
- it is still **not** enough to replace the unconditional `late_entry_filter`
  side-branch reference, because the known transition-defense surfaces remain
  unresolved

Reference report:

- [chop-trend localization](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_chop_trend_localization.md:1>)

## Resume Point

Resume from a split queue, not one blended family:

- `bullish mainline`: `partial67` stays the `working baseline`, and
  `partial67_remainder_ratchet` stays the leading same-entry capture candidate
- `weak-tape defense side branch`: `partial67_late_entry_filter` stays reserved
  for `RANGING` / transition defense research
- first concrete side-branch candidate
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`
  is now informative but not clean enough
- gate attribution is now complete:
  - `trend_decay`-only is not the active defense lever
  - `chop_trend`-only carries most of the defense uplift and most of the
    bullish false-positive tax
  - neither localized gate fixed `sideways_transition`
- first localization pass is now complete:
  - `chop_trend_tightened_late_entry_filter` is the best localized proxy so far
  - it repaired most of the bullish tax without solving the transition surface
- next side-branch pass should add a more explicit transition-aware trigger
- new bullish candidates should compare first against `partial67` and then
  against the `frozen baseline`
- do not merge `late_entry_filter` into the mainline unless an explicit context
  gate is defined and separately justified
