# Research Note: macd_signal_btc_4h_trending_up family

## Status

- Research line established on `2026-04-22`.
- Scope: BTC-only, long-only, 4h continuation entries under a 1d trend gate.
- Current classification: active research, not promotion-ready.
- Dual-baseline framing now applies to this family:
  - `frozen baseline`: `macd_signal_btc_4h_trending_up` with locked
    `stop_atr_mult=1.5` and `trend_spread_min=0.005`
  - `working baseline`:
    `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`

## Dual Baseline Framing

This family now uses two comparison anchors on purpose:

- `frozen baseline` = `macd_signal_btc_4h_trending_up`
  - role: preserve the original historical anchor and keep all earlier
    structural work interpretable against the first clean baseline run
- `working baseline` =
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
  - role: act as the current family member that new research variants should
    beat in the next round

Guardrail:

- do not overwrite the frozen baseline with later winners
- do use the working baseline as the practical hurdle for new structural ideas

## Baseline Candidate Outcome

First clean candidate review for `macd_signal_btc_4h_trending_up`:

- aggregate: `46 trades`, `net_pnl = +1394.7769`, `max_dd_pct = 5.1601`
- `TRENDING_UP`: `26 trades`, `+1400.3197`, `PF 2.5583`
- `RANGING`: `3 trades`, `-173.8867`
- `MIXED`: `17 trades`, `+168.3439`
- no run errors and no `entry_stop_violations`

Interpretation:

- This cartridge solved the low-frequency problem left by the 1d zero-line
  probe.
- The declared `TRENDING_UP` thesis has real signal support.
- The main weakness is not frequency but quality drift outside the clean trend
  window, especially the still-negative `RANGING` cell.

## Sweep Findings

Second-pass sweeps on the baseline cartridge showed that the obvious tuning
knobs are not the main lever:

- `stop_atr_mult` min-3 sweep:
  - `1.5` remained the best balanced cell.
  - `1.25` increased trades but degraded aggregate quality.
  - `1.75` did not improve enough to justify a re-lock.
- `trend_spread_min` min-3 sweep:
  - `0.005 / 0.0065 / 0.008` produced identical results.
  - Conclusion: `trend_spread_min` in that range is not an active lever.

Interpretation:

- The problem is not stop placement.
- The problem is not a slightly tighter 1d spread threshold.
- The next useful move had to target signal architecture rather than keep
  sanding the same params.

## Confirmed-Entry Variant

`macd_signal_btc_4h_trending_up_confirmed` kept the same 1d gate, stop, and
exit logic, but tightened the 4h entry:

- added `macd_hist > 0`
- added `macd_hist > abs(previous_macd_hist)`
- required `close > 4h ema_20`

Candidate review outcome:

- aggregate: `23 trades`, `net_pnl = +969.1953`, `max_dd_pct = 3.0588`
- `TRENDING_UP`: `12 trades`, `+1227.9548`, `PF 3.8925`
- `RANGING`: `2 trades`, `-128.6057`
- `MIXED`: `9 trades`, `-130.1538`

Interpretation:

- Entry quality is an active lever.
- The tighter trigger improved drawdown and preserved strong trend-side
  quality.
- But it also cut participation heavily and flipped `MIXED` from positive to
  negative.
- This was a useful structural result, not a winner.

## Fail-Fast Exit Variant

`macd_signal_btc_4h_trending_up_confirmed_failfast` kept the confirmed entry
and added a plugin-owned early exit:

- close as `FAILED_CONTINUATION_EXIT` after `2` elapsed 4h bars when the trade
  still fails to close above both entry price and 4h `ema_20`

Candidate review outcome:

- aggregate: `23 trades`, `net_pnl = +683.1721`, `max_dd_pct = 3.4713`
- `TRENDING_UP`: `12 trades`, `+1065.4460`
- `RANGING`: `2 trades`, `-128.6057`
- `MIXED`: `9 trades`, `-253.6682`

Interpretation:

- The fail-fast rule is live and did trigger in replay.
- But this rule did not improve the weak windows.
- It reduced aggregate quality and made `MIXED` materially worse.
- Conclusion: this exact `2-bar` fail-fast design should be parked, not
  re-locked.

## Underwater EMA20 Exit Variant

`macd_signal_btc_4h_trending_up_underwater_ema_exit` kept the baseline entry,
1d gate, and ATR stop, then added a baseline-derived management rule:

- close as `UNDERWATER_EMA20_EXIT` after `1` elapsed 4h bar when the latest
  4h close is both below entry price and at or below 4h `ema_20`

Candidate review outcome:

- aggregate: `46 trades`, `net_pnl = +1424.1869`, `max_dd_pct = 5.1514`
- `TRENDING_UP`: `26 trades`, `+1416.8770`, `PF 2.6814`
- `RANGING`: `3 trades`, `-161.0339`
- `MIXED`: `17 trades`, `+168.3439`

Interpretation:

- Exit structure is a live lever on the baseline cartridge without cutting
  participation.
- This rule improved a few slower losers in `TRENDING_UP` and `RANGING`.
- But it did **not** improve `MIXED` at all.
- It also clipped at least one trend-side winner earlier than the baseline.
- Conclusion: useful structural signal, but not the `MIXED` fix and not ready
  to replace the baseline as the main research anchor.

## Staged De-Risk / Give-Back Variant

`macd_signal_btc_4h_trending_up_staged_derisk_giveback` kept the baseline
entry, 1d gate, and ATR stop, then added a two-step management path:

- partial close as `DERISK_PARTIAL_GIVEBACK` once a trade has already reached
  `1.0R`, then gives back at least `0.75R`, and open profit has faded back to
  `1.0R` or less; the remaining stop moves to break-even
- close the remainder as `GIVEBACK_EXIT` after a prior partial when the trade
  had already reached `1.5R` and then fades to `0.25R` or less

Candidate review outcome:

- aggregate: `46 trades`, `net_pnl = +1513.5037`, `max_dd_pct = 4.6026`
- `TRENDING_UP`: `26 trades`, `+1462.5462`, `PF 2.6276`
- `RANGING`: `3 trades`, `-173.8867`
- `MIXED`: `17 trades`, `+224.8443`, `PF 1.5191`

Observed hits:

- `MIXED`: improved three give-back trades, including one explicit
  `GIVEBACK_EXIT`
- `TRENDING_UP`: improved one trend-side give-back trade without reducing
  trade count
- `RANGING`: unchanged

Interpretation:

- This is the first exit-side variant in this family that improved aggregate
  PnL, reduced max drawdown, and improved `MIXED` without cutting frequency.
- The improvement came from capture recovery on trades that had already shown
  follow-through, not from tighter entry or stop tuning.
- `RANGING` remains unresolved, so this is still research-only.
- But structurally, this is now the leading exit variant in the family.
- This variant is now strong enough to keep in the family's baseline-candidate
  pool, even though the original baseline remains the frozen comparison
  anchor.

## Narrow Robustness Sweeps

`BTC/USDT`-only min-3 sweeps were run on the staged de-risk / give-back
variant to test whether the gain depended on one exact parameter point.

- `derisk_close_pct` min-3 sweep (`0.33 / 0.5 / 0.67`):
  - `0.33`: aggregate `+1472.6475`, `max_dd_pct 4.7994`, `MIXED +205.9503`
  - `0.5`: aggregate `+1513.5037`, `max_dd_pct 4.6026`, `MIXED +224.8443`
  - `0.67`: aggregate `+1553.9654`, `max_dd_pct 4.4059`, `MIXED +243.3437`
- `giveback_exit_floor_r` min-3 sweep (`0.15 / 0.25 / 0.35`):
  - all three cells were identical to the default staged run
  - aggregate stayed `+1513.5037`
  - `MIXED` stayed `+224.8443`

Interpretation:

- partial monetization size is a live lever on this cartridge
- within the tested range, a larger first de-risk improved both aggregate PnL
  and drawdown without changing trade count
- the remainder give-back floor was not an active lever in the tested range
- the next locked candidate review, if this family gets another one, should
  start from the same staged structure with a larger `derisk_close_pct`, not
  from another sweep on `giveback_exit_floor_r`

## Locked Partial67 Candidate

`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` took the
same staged exit structure and locked only one sweep-proven change:

- `derisk_close_pct = 0.67`

Candidate review outcome:

- aggregate: `46 trades`, `net_pnl = +1553.9654`, `max_dd_pct = 4.4059`
- `TRENDING_UP`: `26 trades`, `+1484.5085`, `PF 2.6520`
- `RANGING`: `3 trades`, `-173.8867`
- `MIXED`: `17 trades`, `+243.3437`, `PF 1.5618`

Comparison:

- vs frozen baseline:
  - aggregate `+159.1885`
  - max drawdown `-0.7542`
  - `MIXED +74.9998`
- vs staged default (`derisk_close_pct=0.5`):
  - aggregate `+40.4617`
  - max drawdown `-0.1967`
  - `MIXED +18.4994`

Interpretation:

- the stronger `0.67` first monetization size survived a full candidate review,
  not just the sweep harness
- trade count stayed unchanged in all three windows
- `RANGING` is still unresolved, so this remains research-only
- but this is now the leading locked candidate in the family and the strongest
  baseline-candidate member so far

## Supplemental Market-Phase Window Check

The family now has a second evaluation layer beyond the standard candidate
review windows (`TRENDING_UP / RANGING / MIXED`).

Working rule from here:

- keep the standard regime-window candidate review as the first pass
- add a fixed market-phase window matrix as the second pass for structural
  candidate comparisons
- treat the long windows as stress tests for survival across multi-phase tape,
  not as pure regime-isolated reads

Current fixed supplemental window matrix:

| bucket | window | dates | why it stays in the matrix |
| --- | --- | --- | --- |
| short | bull strong-up 1 | `2024-10-01 ~ 2025-03-31` | clean recent upside impulse |
| short | bear persistent-down | `2025-04-01 ~ 2025-08-31` | checks whether the family avoids self-destruction in a long down tape |
| short | range / low-vol | `2025-09-01 ~ 2025-12-31` | no-trade discipline check |
| short | bull recovery 2026 | `2026-01-01 ~ 2026-02-28` | checks whether the trigger can re-engage after compression |
| short | FTX-style crash | `2022-11-01 ~ 2022-12-31` | extreme event damage control |
| short | sideways transition | `2023-06-01 ~ 2023-09-30` | current known bleed surface |
| long | classic rollercoaster | `2021-01-01 ~ 2022-12-31` | full bull-to-bear survival check |
| long | recovery / ETF tape | `2023-01-01 ~ 2024-12-31` | modern recovery and high-level chop check |

Current working-baseline read on that matrix
(`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`):

- bull strong-up 1: `10 trades`, `+2.2863%`, `max_dd_pct 6.0844`, `PF 1.3611`
- bear persistent-down: `17 trades`, `+1.9478%`, `max_dd_pct 3.0337`,
  `PF 1.4229`
- range / low-vol: `0 trades`, `0.0000%`, `4` rejects
- bull recovery 2026: `0 trades`, no candidates formed
- FTX-style crash: `1 trade`, `-0.1629%`, `max_dd_pct 0.2905`
- sideways transition: `4 trades`, `-1.9695%`, `max_dd_pct 3.2551`,
  `PF 0.3308`
- classic rollercoaster: `28 trades`, `+15.6791%`, `max_dd_pct 5.1817`,
  `PF 2.9306`
- recovery / ETF tape: `50 trades`, `+10.6388%`, `max_dd_pct 7.0284`,
  `PF 1.5470`

Interpretation:

- the long-window checks support keeping `partial67` as the `working baseline`
- the worst surface is still not the clean trend tape but the sideways /
  transition tape
- the family already has enough trend-side survival to justify structural
  refinement instead of more baseline-level parameter sanding

## Late-Entry Filter Variant

`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
kept the `working baseline` exit structure and only added one new entry-side
suppression rule:

- block the entry when `max((close - 4h ema_20) / atr, 0)` is greater than
  `entry_ema_extension_atr_max`

This was intentionally narrower than the earlier `confirmed` entry variant:

- it does **not** require `close > ema_20`
- it does **not** add generic histogram stacking
- it only tries to stop obviously stretched chase entries

Min-3 sweep on `entry_ema_extension_atr_max`:

- `0.75`: `8 trades`, `+762.0800`, `max_dd_pct 1.1328`
- `1.0`: `12 trades`, `+919.1002`, `max_dd_pct 1.8422`
- `1.25`: `16 trades`, `+1856.8086`, `max_dd_pct 1.8572`

Candidate review outcome for the sweep-leading default (`1.25`):

- aggregate: `16 trades`, `net_pnl = +1856.8086`, `max_dd_pct = 1.8572`
- `TRENDING_UP`: `9 trades`, `+1401.7272`, `PF 10.2856`
- `RANGING`: `1 trade`, `-45.2810`
- `MIXED`: `6 trades`, `+500.3624`, `PF 7.7791`

Supplemental 8-window read versus the current `working baseline`:

- improved:
  - bear persistent-down: `+4.7302%` vs `+1.9478%`
  - sideways transition: `+0.3850%` vs `-1.9695%`
  - recovery / ETF tape: `+14.2661%` vs `+10.6388%`
  - FTX-style crash: `0 trades` vs one small loser
- degraded:
  - bull strong-up 1: `+0.5345%` vs `+2.2863%`
  - classic rollercoaster: `+8.8090%` vs `+15.6791%`

Interpretation:

- late-entry suppression is a very live structural lever
- unlike the older `confirmed` entry path, this variant improved `MIXED`
  instead of hollowing it out
- but the gain came with a major participation cut (`46 -> 16 trades` in the
  default review matrix)
- that tradeoff looks strong on the current and transition-heavy tape, but it
  also leaves too much money behind in the older full-cycle rollercoaster
  window
- conclusion: keep this variant in the family's baseline-candidate pool, but
  do **not** replace the current `working baseline` with it yet

## Chop / No-Trade Discipline Pass

The second ordered pass tested three increasingly specific ways to reduce
low-quality participation without rewriting the `working baseline` exit path.

### First probe: raw ADX floor

`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter`
added only `4h adx >= entry_adx_min`.

Read:

- the lever was too blunt
- stricter floors reduced participation, but did not solve `RANGING`
- the best cell still underperformed the `working baseline`, and one tighter
  cell flipped `MIXED` negative

Conclusion:

- park raw local ADX floors for this family

### Second probe: local EMA spread

`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter`
required a minimum local `4h (ema_20 - ema_50) / ema_50`.

Min-3 sweep on `entry_local_spread_min`:

- `0.001`: identical to the `working baseline`
- `0.002`: identical to the `working baseline`
- `0.003`: `45 trades`, `+1548.7114`, `max_dd_pct 4.4059`

Interpretation:

- this was effectively an inactive branch in the tested range
- local EMA spread size does not separate the weak tape cleanly enough here

Conclusion:

- park local spread gating for this family

### Third probe: chop-trend filter

`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter`
kept the `partial67` structure and only blocked entries when:

- `4h adx_slope_5 < 0`
- and `4h bbw / recent_mean_bbw < entry_bbw_ratio_min`

Min-3 sweep on `entry_bbw_ratio_min`:

- `0.6`: `39 trades`, `+637.7384`, `max_dd_pct 4.6397`, `MIXED -59.1606`
- `0.75`: `33 trades`, `+972.4305`, `max_dd_pct 2.9414`,
  `RANGING -128.6057`, `MIXED +44.7161`
- `0.9`: `24 trades`, `+674.1333`, `max_dd_pct 3.0589`, `RANGING 0.0000`,
  `MIXED +44.7161`

Interpretation:

- this is the first `chop / no-trade` branch in the family that looks truly
  active instead of inert
- `0.75` is the best-balanced chop cell in the tested range
- but even that best cell still sits well below the `working baseline` on
  aggregate and on `MIXED`
- the improvement came mostly from defensive participation cuts rather than a
  cleaner overall edge

Conclusion:

- keep the `falling ADX + compressed BBW` idea as a valid defensive reference
  branch
- do **not** promote it into the baseline-candidate pool
- the `chop / no-trade discipline` pass is now complete enough to move on
  without more brute-force sanding in this direction

### Post-entry management: remainder ratchet

The first `post-entry management` pass kept the `partial67` entry, stop, trend
gate, and first partial intact, then added a post-partial remainder ratchet:

- candidate:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`
- default tested cell:
  - `derisk_close_pct = 0.67`
  - `remainder_ratchet_arm_r = 1.0`
  - `remainder_ratchet_giveback_r = 1.0`
- new exit reason: `REMAINDER_RATCHET_EXIT`

Parameter read:

- `remainder_ratchet_giveback_r = 0.75 / 1.0 / 1.25` was inactive in the
  first min-3 sweep when `arm_r = 1.5`
- `remainder_ratchet_arm_r` was live:

| arm_r | trades | net_pnl | max_dd_pct | MIXED net_pnl |
| ---: | ---: | ---: | ---: | ---: |
| `1.0` | 46 | 1597.8170 | 4.1130 | 254.9628 |
| `1.5` | 46 | 1594.3058 | 4.1130 | 251.4516 |
| `2.0` | 46 | 1594.3058 | 4.1130 | 251.4516 |
| `2.5` | 46 | 1562.0733 | 4.4059 | 251.4516 |

Candidate review read versus the `working baseline`:

| candidate | trades | net_pnl | max_dd_pct | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | 1484.5085 | -173.8867 | 243.3437 |
| `partial67_remainder_ratchet` | 46 | 1597.8170 | 4.1130 | 1516.7409 | -173.8867 | 254.9628 |
| delta | 0 | +43.8516 | -0.2929 | +32.2324 | 0.0000 | +11.6191 |

Supplemental 8-window read versus the `working baseline`:

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

Interpretation:

- this is a real post-entry management improvement, not an entry-filter effect
- it preserves trade count and leaves `RANGING` unchanged
- it improves `TRENDING_UP`, `MIXED`, and the modern `2023-2024` recovery /
  ETF tape window
- the tradeoff is small but real: it slightly clips the classic 2021-2022
  rollercoaster window

Conclusion:

- keep `partial67_remainder_ratchet` in the baseline-candidate pool as the
  leading `post-entry management` candidate
- do **not** replace the `working baseline` yet; defer that decision until the
  `transition bleed` and winner-vs-loser decomposition passes are complete
- next structural pass should move to `transition bleed`

### Transition bleed: persistence and decay probes

The `transition bleed` pass tested two entry-side probes around the same
`working baseline` without changing exits, stops, or `trend_spread_min`.

First probe:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer`
- rule: require the 1d trend gate to persist for `trend_persistence_bars`
- sweep:

| persistence bars | trades | net_pnl | max_dd_pct | read |
| ---: | ---: | ---: | ---: | --- |
| `1` | 46 | 1553.9654 | 4.4059 | baseline-equivalent |
| `2` | 46 | 1553.9654 | 4.4059 | inactive |
| `3` | 46 | 1553.9654 | 4.4059 | inactive |
| `5` | 44 | 1535.3729 | 4.4100 | over-waited and cut winners |

Second probe:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter`
- rule: reject entries when the 1d EMA20/EMA50 spread is contracting over a
  short lookback
- sweep with `trend_spread_slope_min = 0.0`:

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

Interpretation:

- persistence buffering does not catch the current weak surface
- trend-decay filtering does catch some `MIXED` / transition bleed, but it pays
  too much by removing profitable `TRENDING_UP` participation
- this pass produced a useful diagnostic branch, not a baseline candidate

Conclusion:

- do **not** promote either transition branch into the baseline-candidate pool
- keep `transition_decay_filter` only as evidence that a trend-weakening signal
  exists, but needs better targeting
- next ordered pass should move to `winner protection vs loser suppression`

### Winner protection vs loser suppression decomposition

The decomposition pass compared the current `working baseline` against the two
most informative surviving branches:

- `partial67_late_entry_filter`
- `partial67_remainder_ratchet`

Default review-window decomposition:

| candidate | common trades | baseline-only trades | same-entry delta | avoided loser pnl | missed winner pnl | net delta | primary mechanism |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `late_entry_filter` | 16 | 30 | 0.0000 | +1235.6351 | -932.7919 | +302.8432 | loser suppression with winner tax |
| `remainder_ratchet` | 46 | 0 | +43.8515 | 0.0000 | 0.0000 | +43.8515 | winner protection / capture |

Supplemental matrix read:

- `late_entry_filter` is net-positive in bearish / transition-heavy windows:
  - `bear_persistent_down`: `+278.2380`
  - `ftx_style_crash`: `+16.2852`
  - `sideways_transition`: `+235.4557`
  - `recovery_2023_2024`: `+362.7342`
- but it breaks on strong winner-rich tapes:
  - `bull_strong_up_1`: `-175.1797`
  - `classic_rollercoaster_2021_2022`: `-687.0087`
- `remainder_ratchet` keeps the same trade set and improves winner capture in
  most windows:
  - `bull_strong_up_1`: `+33.1428`
  - `bear_persistent_down`: `+8.1079`
  - `sideways_transition`: `+6.8846`
  - `recovery_2023_2024`: `+72.2598`
  - `classic_rollercoaster_2021_2022`: `-3.5340`

Interpretation:

- late-entry filtering is a defensive branch, not a clean baseline
  replacement
- remainder ratchet is the cleaner baseline-candidate branch because it
  improves capture without changing entry participation
- blindly stacking late-entry filtering on top of ratchet is risky because it
  would probably import the winner tax

Reference report:

- [winner / loser decomposition](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_winner_loser_decomposition.md:1>)

Conclusion:

- keep `partial67_remainder_ratchet` as the leading baseline-candidate branch
- keep `partial67_late_entry_filter` as a defensive diagnostic branch
- explicitly reserve a future branch study for `partial67_late_entry_filter`
  as a `RANGING` defense probe, because its default review result cut
  `RANGING` from `3 trades / -173.8867` to `1 trade / -45.2810`
- move the next ordered pass to `separate bullish and bearish families`

### Separate bullish and bearish families

The next pass resolved the family split around the current `working baseline`:

- `partial67` remains the `bullish mainline` reference
- `partial67_remainder_ratchet` is the leading `bullish mainline` candidate
- `partial67_late_entry_filter` is reclassified as a `weak-tape defense` side
  branch, not a direct mainline replacement

Default review comparison:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `partial67_remainder_ratchet` | 46 | 1597.8170 | 4.1130 | same-entry bullish leader |
| `partial67_late_entry_filter` | 16 | 1856.8086 | 1.8572 | selective defense branch |

Family-level supplemental read:

| family | `partial67` | `ratchet` | delta vs `partial67` | `late_entry_filter` | delta vs `partial67` | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| bullish mainline family | `88 trades / +2860.4183` | `88 / +2962.2868` | +101.8685 | `34 / +2360.9641` | -499.4542 | ratchet is the clean bullish-family improvement; late-entry underparticipates |
| bearish weak-tape family | `18 / +178.4922` | `18 / +186.6002` | +8.1080 | `7 / +473.0154` | +294.5232 | late-entry is materially stronger as defense |
| ranging / transition family | `4 / -196.9550` | `4 / -190.0704` | +6.8846 | `1 / +38.5007` | +235.4557 | late-entry is best defensively, but extremely selective |

Interpretation:

- `remainder_ratchet` stays inside the `bullish mainline` because it preserves
  participation and improves same-entry capture
- `late_entry_filter` does **not** stay in the bullish mainline because its
  gain comes from trade refusal, not from a cleaner same-entry edge
- the weak-tape read is now explicit: `late_entry_filter` is strongest in
  `bear_persistent_down`, `ftx_style_crash`, and `sideways_transition`
- the bullish-mainline read is also explicit: `late_entry_filter` still pays
  obvious winner tax in `bull_strong_up_1` and
  `classic_rollercoaster_2021_2022`

Reference reports:

- [family split](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_family_split.md:1>)
- [candidate review](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

### Context-gated weak-tape defense

The first concrete side-branch candidate was then tested via:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`

Default review comparison:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | aggregate improved, still selective |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Key matrix read:

- `TRENDING_UP`: `context_gated` improved to `23 trades / +1696.9839`,
  reclaiming much more bullish participation than the unconditional
  `late_entry_filter`
- `RANGING`: unchanged from `partial67` at `3 trades / -173.8867`
- `MIXED`: improved to `10 trades / +354.6428`

Supplemental read:

- genuine recovery in some weak-tape slices:
  - `bear_persistent_down`: `+354.6428`
  - `ftx_style_crash`: `0.0000` versus `partial67 -16.2852`
- but the gate missed the known weak surface:
  - `sideways_transition`: unchanged at `-196.9550`
- and it introduced new localization problems:
  - `bull_strong_up_1`: degraded to `-32.1112`
  - `range_low_vol`: introduced `1 trade / -4.2350`

Interpretation:

- this candidate is **not** a clean `weak-tape defense` successor to the
  unconditional `late_entry_filter`
- it reduces the old winner tax, but the current OR-gated weak-tape proxy is
  not well localized
- best current read: the branch behaves more like a selective hybrid cartridge
  than a targeted defense lane

Reference report:

- [context-gated weak-tape defense](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_context_gated_weak_tape_defense.md:1>)

### Weak-tape gate attribution

The attribution pass then isolated the two gate components behind the OR-gated
proxy:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter`

Default review comparison:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | OR-gated reference |
| `trend_decay_only_late_entry_filter` | 41 | 1604.2942 | 4.3940 | near-baseline, weak defense |
| `chop_trend_only_late_entry_filter` | 41 | 1827.4113 | 2.9913 | most OR-gated uplift survives |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Attribution read:

- `trend_decay_only` did **not** fix `RANGING`, `sideways_transition`, or
  `ftx_style_crash`
- `chop_trend_only` recovered most of the OR-gated uplift and also kept the
  crash avoidance
- `bull_strong_up_1` split the gates cleanly:
  - `trend_decay_only`: `+268.1561`
  - `chop_trend_only`: `-83.5023`
- `sideways_transition` stayed unchanged at `-196.9550` for all of
  `partial67`, `context_gated`, `trend_decay_only`, and `chop_trend_only`

Interpretation:

- the current OR-gated candidate gets most of its useful weak-tape behavior
  from `chop_trend`, not from `trend_decay`
- the same `chop_trend` proxy also causes the bullish false-positive tax
- `trend_decay_only` behaves more like winner preservation than side-branch
  defense
- neither localized proxy reproduces the unconditional `late_entry_filter`
  strength in `sideways_transition`

Reference report:

- [weak-tape gate attribution](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_weak_tape_gate_attribution.md:1>)

### Chop-trend localization

The next side-branch pass retuned the active `chop_trend` proxy itself:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter`

Default review comparison:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | OR-gated reference |
| `chop_trend_only_late_entry_filter` | 41 | 1827.4113 | 2.9913 | raw localized-gate reference |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | best localized `chop_trend` proxy so far |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Localization read:

- `bull_strong_up_1` recovered from `-83.5023` to `+167.8664`
- `bear_persistent_down` stayed strong at `+352.4744`
- `ftx_style_crash` stayed clean at `0.0000`
- default `MIXED` improved from `14 / +331.2551` to `15 / +352.4744`
- but `RANGING` stayed `3 / -173.8867`
- and `sideways_transition` stayed unchanged at `-196.9550`

Interpretation:

- the localization pass materially repaired the old bullish false-positive tax
  without losing the crash-avoidance behavior
- this is the best localized `chop_trend` probe so far
- but it still does **not** reproduce the unconditional `late_entry_filter`
  strength on the key `sideways_transition` / transition-defense surface

Reference report:

- [chop-trend localization](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_chop_trend_localization.md:1>)

### Transition-aware defense

The next side-branch pass stopped sanding the `chop_trend` proxy and tested an
explicit transition-risk trigger:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter`

Default review comparison:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | best aggregate localized proxy |
| `transition_aware_late_entry_filter` | 37 | 1230.6759 | 4.5977 | transition surface repaired; aggregate too selective |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Transition-aware read:

- default `RANGING` repaired from `3 / -173.8867` to `1 / -45.2810`
- `sideways_transition` flipped from `-196.9550` to `+97.3769`
- `range_low_vol` returned to `0 / 0.0000`
- `bull_strong_up_1` jumped to `+595.7043`
- but default `TRENDING_UP` fell to `22 / +992.0771`
- and both long windows stayed below `chop_trend_tightened`

Interpretation:

- this is the first localized side-branch pass that actually explains the
  transition-defense surface
- it filtered the two `2023-06-23` losers that the localized `chop_trend`
  proxy still allowed
- it even kept the `2023-07-13` winner that the unconditional
  `late_entry_filter` cut
- but the current explicit trigger is still too wide in the default
  `TRENDING_UP` window, so it is not yet a promotion candidate

Reference report:

- [transition-aware defense](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_transition_aware_defense.md:1>)

### Transition-aware tightening

The next pass kept the same explicit transition context and only narrowed the
veto arm:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`

Attribution that justified the tightening:

- the first explicit pass blocked default `TRENDING_UP` trades at
  `1.49`, `2.37`, `2.80`, and `2.80 ATR`
- the known `2023-06-23` `sideways_transition` losers sat out at `3.55 ATR`
- so the narrowed child only vetoes transition-context entries at
  `>= 3.0 ATR`

Default review comparison:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `transition_aware_late_entry_filter` | 37 | 1230.6759 | 4.5977 | first explicit transition probe; too selective |
| `transition_aware_tightened_late_entry_filter` | 44 | 1682.5711 | 4.4059 | first strict default-review improvement over `partial67` |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | best aggregate localized proxy |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Transition-aware tightening read:

- default `TRENDING_UP` recovered fully to `26 / +1484.5085`
- default `MIXED` also recovered fully to `17 / +243.3437`
- repaired default `RANGING` stayed intact at `1 / -45.2810`
- `sideways_transition` stayed at `+97.3769`
- `range_low_vol` and `ftx_style_crash` stayed at `0 / 0.0000`
- `bull_strong_up_1` stayed at `+595.7043`
- `recovery_2023_2024` jumped to `+2245.5016`, the strongest read in the
  current side branch
- but `bear_persistent_down` softened to `+243.3437`, still below
  `chop_trend_tightened` and the unconditional defense reference

Interpretation:

- this is the first explicit transition child that strictly improves the
  default review over `partial67`
- the first explicit mechanism was valid; its arm was just too wide
- this child becomes the leading explicit transition-surface candidate
- but it does not replace `late_entry_filter` as the raw defense ceiling and
  does not yet replace `chop_trend_tightened` as the bearish-defense reference

Reference report:

- [transition-aware tightening](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md:1>)

## Current Read

- `macd_signal_btc_4h_trending_up` remains the `frozen baseline` for this
  family.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` is now
  the `working baseline` and the leading locked candidate in the family.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
  is now the leading entry-side precision candidate, but it is not yet a clean
  enough all-window winner to replace the `working baseline`.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
  should later get its own branch study specifically for `RANGING` defense,
  not as a direct baseline replacement.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`
  is now the leading post-entry management candidate, but it is not yet a
  clean enough all-window winner to replace the `working baseline`.
- the `winner protection vs loser suppression` decomposition is now complete:
  - `late_entry_filter` is mostly loser suppression, but its winner tax is too
    large in strong trend tapes
  - `remainder_ratchet` is mostly winner protection / capture improvement, and
    remains the cleaner baseline-candidate branch
- the `separate bullish and bearish families` pass is now complete:
  - the `bullish mainline` stays anchored on `partial67`
  - `partial67_remainder_ratchet` is the leading same-entry candidate inside
    that mainline
  - `partial67_late_entry_filter` is reserved for a separate `RANGING` /
    transition defense branch
- the first `context-gated weak-tape defense` pass is now complete:
  - aggregate default-window result improved
  - but `RANGING` and `sideways_transition` were not repaired
  - the current OR gate is not localized enough to become the side-branch
    reference
- the `weak-tape gate attribution` pass is now complete:
  - `trend_decay_only` preserved bullish winners but did not solve the defense
    problem
  - `chop_trend_only` reproduced most of the OR-gated defense uplift and crash
    avoidance
  - `chop_trend_only` also reproduced the bullish misfire, so the active proxy
    is identified but still not localized enough
  - neither localized gate fixed `sideways_transition`, so the unconditional
    `late_entry_filter` remains the best side-branch reference
- the first `chop-trend localization` pass is now complete:
  - `chop_trend_tightened_late_entry_filter` repaired most of the old
    `bull_strong_up_1` tax and improved default `MIXED`
  - it preserved `bear_persistent_down` and `ftx_style_crash` behavior
  - it still left default `RANGING`, `sideways_transition`, and the
    `range_low_vol` stray loser unresolved
  - it replaces `chop_trend_only` as the current localized-proxy reference,
    but not as the side-branch defense reference
- the first `transition-aware defense` pass is now complete:
  - `transition_aware_late_entry_filter` is the first localized proxy that
    repaired default `RANGING` and flipped `sideways_transition` positive
  - it also removed the `range_low_vol` stray loser and kept
    `bull_strong_up_1` strong
  - but default `TRENDING_UP` and the long windows paid too much tax
  - it becomes the explicit transition-surface reference, but not the overall
    side-branch reference
- the first `transition-aware tightening` pass is now complete:
  - `transition_aware_tightened_late_entry_filter` restored default
    `TRENDING_UP` and `MIXED` back to `partial67`
  - it kept the repaired default `RANGING`, `sideways_transition`,
    `range_low_vol`, and `ftx_style_crash` surfaces intact
  - it becomes the leading explicit transition-surface candidate and the first
    side-branch child that strictly improves default review over `partial67`
  - but `bear_persistent_down` still trails `chop_trend_tightened` and the
    unconditional `late_entry_filter`
- the `transition bleed` pass is now complete enough to move on:
  - persistence buffer was inactive until it over-waited
  - trend-decay filter was active but too defensive
  - no transition branch enters the baseline-candidate pool
- the `chop / no-trade discipline` pass is now complete:
  - raw ADX floors were too blunt
  - local EMA spread was inactive
  - `falling ADX + compressed BBW` was active but still too defensive
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback` remains the best
  unlocked exit-side research member and still matters as the parent shape
  behind the working baseline.
- `TRENDING_UP` sign is real and repeatable enough to justify keeping the
  family alive.
- `RANGING` contamination is now explicitly localizable in the
  `transition_aware_tightened` lane, but broader side-branch ranking still
  depends on how much bearish-defense weight we want to keep.
- `derisk_close_pct` is now the main active tuning lever inside the staged
  exit family, with `0.67` now surviving both the min-3 sweep and a locked
  candidate review.
- `giveback_exit_floor_r` did not move results in the tested range, so it is
  currently a low-priority knob.
- the fixed comparison stack is now:
  - standard candidate review windows
  - then the 8-window supplemental market-phase matrix
- `MIXED` is the current failure surface:
  - stricter entry helped drawdown but over-cut participation
  - generic fail-fast exit cut trades too early without improving the weak set
  - underwater `ema_20` exit slightly improved aggregate quality but left
  `MIXED` unchanged
  - staged de-risk / give-back exit is the first variant that actually
    improved `MIXED` while preserving trade count
  - narrow late-entry suppression improved `MIXED` and the transition-heavy
    windows, but at the cost of a major participation cut
  - chop-trend suppression reduced some weak participation, but not enough to
    beat the working baseline
  - remainder ratchet improved post-entry capture without changing entry
    count, but slightly clipped the 2021-2022 long window
  - transition filters can identify weak transition tape, but current forms
    still over-cut broader trend participation

## Ordered Research Queue

Future structural comparisons should now run in this order:

1. `late-entry filtering`
   - first pass complete via
     `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
   - read: active lever, strong default-window result, but not yet a full
     `working baseline` replacement because the classic rollercoaster window
     degraded too much
2. `chop / no-trade discipline`
   - pass complete via:
     `partial67_chop_filter`, `partial67_local_spread_filter`, and
     `partial67_chop_trend_filter`
   - read: active only in the `chop-trend` form, but still too defensive to
     replace the `working baseline`
3. `post-entry management`
   - target: improve capture after entry without rewriting the baseline entry
   - success read: better give-back control or better winner retention on the
     same entry set
   - first pass complete via `partial67_remainder_ratchet`
   - read: active and baseline-candidate worthy, but wait for transition bleed
     before changing the working baseline
4. `transition bleed`
   - target: reduce damage near regime flips and unstable trend labels
   - success read: better `sideways transition` behavior and cleaner `MIXED`
     deltas
   - first pass complete via `partial67_transition_buffer` and
     `partial67_transition_decay_filter`
   - read: no baseline-candidate; current transition filters are either
     inactive or too defensive
5. `winner protection vs loser suppression`
   - role: diagnostic decomposition after the first four structural passes
   - question: are gains coming from better winner retention, smaller medium
     losers, or both
   - pass complete via the winner / loser decomposition report
   - read: `late_entry_filter` is defensive loser suppression with winner tax;
     `remainder_ratchet` is cleaner winner protection / capture
6. `separate bullish and bearish families`
   - pass complete via the family split report
   - read: `partial67` and `partial67_remainder_ratchet` stay in the bullish
     mainline, while `partial67_late_entry_filter` moves to a separate
     `RANGING` / transition defense branch
7. `context-gated weak-tape defense`
   - first pass complete via
     `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`
   - read: aggregate improved, but the OR-gated proxy failed to fix
     `sideways_transition` and introduced a new `bull_strong_up_1` misfire
8. `weak-tape gate attribution`
   - pass complete via:
     `partial67_trend_decay_only_late_entry_filter` and
     `partial67_chop_trend_only_late_entry_filter`
   - read: `chop_trend` is the live defense proxy; `trend_decay` is mostly a
     winner-preservation companion
   - unresolved: neither localized gate repaired `sideways_transition`
9. `chop-trend localization`
   - first pass complete via:
     `partial67_chop_trend_tightened_late_entry_filter`
   - read: this recovered most of the old bullish false-positive tax while
     keeping `bear_persistent_down` and `ftx_style_crash` intact
   - unresolved: default `RANGING`, `sideways_transition`, and the
     `range_low_vol` stray loser remain unchanged
   - next step: design explicit transition-aware triggers instead of
     continuing to sand the same extension-only lever
10. `transition-aware defense`
    - first pass complete via:
      `partial67_transition_aware_late_entry_filter`
    - read: this is the first localized pass that repaired default `RANGING`
      and turned `sideways_transition` positive
    - read: it also removed the `range_low_vol` stray loser and kept
      `bull_strong_up_1` strong
    - unresolved: default `TRENDING_UP` and both long windows paid too much
      tax, so the candidate is still too wide
    - tightening pass complete via:
      `partial67_transition_aware_tightened_late_entry_filter`
    - read: restored default `TRENDING_UP` and `MIXED` back to `partial67`
      while keeping repaired `RANGING` and `sideways_transition`
    - read: this is now the leading explicit transition-surface candidate and
      the first strict default-review improvement over `partial67`
    - unresolved: `bear_persistent_down` still trails both
      `chop_trend_tightened` and `late_entry_filter`
    - pending alternate mechanism:
      `partial67_squeeze_release_unconfirmed_late_entry_filter` remains an
      unrun event-based follow-up spec, not yet a landed candidate
    - next step: compare the tightened explicit-transition child against the
      pending event-based alternate mechanism before any further stacking

## Resume Point

When work resumes, do **not**:

- keep sweeping `stop_atr_mult`
- keep sweeping `trend_spread_min`
- re-lock the `confirmed` or `failfast` variants
- treat the underwater `ema_20` exit's small aggregate gain as a solved result
- score `partial67_late_entry_filter` as a direct replacement for the bullish
  `working baseline`
- treat the current OR-gated weak-tape proxy as solved
- reopen `trend_decay_only` as the leading side-branch path at the current
  threshold
- treat the localized `chop_trend` result as a solved transition-defense
  branch
- treat the tightened `transition_aware` result as a solved side-branch
  outcome
- keep micro-sweeping the tightened `transition_aware` threshold before an
  alternate mechanism gets the same head-to-head review
- OR-stack the explicit `transition_aware` probe with another transition
  trigger before each has a clean individual candidate review

Next step should start from the `working baseline`
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`, while
still keeping the `frozen baseline` as the historical reference point.

The queue is now explicitly split:

1. `bullish mainline`
   - use `partial67` as the `working baseline`
   - use `partial67_remainder_ratchet` as the leading same-entry comparison
     branch
   - compare against the `working baseline` first, then the `frozen baseline`,
     then the 8-window supplemental matrix
2. `weak-tape defense side branch`
   - keep `partial67_late_entry_filter` reserved for `RANGING` / transition
     defense research only
   - first concrete candidate
     `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`
     is now complete and informative, but not clean enough
   - gate attribution is now complete:
     - `trend_decay`-only is not the live defense lever
     - `chop_trend`-only carries most of the useful defense behavior and most
       of the bullish misfire
   - first localization pass is now complete:
     - `chop_trend_tightened_late_entry_filter` is the best localized proxy so
       far
     - it repaired most of the bullish tax without losing crash avoidance
     - it still did not fix `sideways_transition`
   - first explicit transition-aware pass is now complete:
     - `transition_aware_late_entry_filter` repaired default `RANGING` and
       flipped `sideways_transition` positive
     - it also removed the `range_low_vol` stray loser
     - but it over-cut default `TRENDING_UP`
   - first transition-aware tightening pass is now complete:
     - `transition_aware_tightened_late_entry_filter` restored default
       `TRENDING_UP` and `MIXED` back to `partial67`
     - it kept the repaired `RANGING`, `sideways_transition`,
       `range_low_vol`, and `ftx_style_crash` surfaces intact
     - it is now the leading explicit transition-surface candidate
     - but `bear_persistent_down` still trails the stronger bearish-defense
       references
   - pending alternate mechanism:
     - `partial67_squeeze_release_unconfirmed_late_entry_filter` stays as an
       unrun follow-up spec only
   - do not promote any side-branch result into the bullish mainline without an
     explicit context gate that is actually localized
   - do not OR-stack transition probes before each lands a clean individual
     candidate review

Guardrail:

- keep the baseline entry intact while testing the next structural move, so the
  diff remains interpretable.
- do not blindly stack `late_entry_filter` on top of `remainder_ratchet`; that
  combination still needs an explicit context gate before it deserves mainline
  evaluation
