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

## Current Read

- `macd_signal_btc_4h_trending_up` remains the `frozen baseline` for this
  family.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67` is now
  the `working baseline` and the leading locked candidate in the family.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
  is now the leading entry-side precision candidate, but it is not yet a clean
  enough all-window winner to replace the `working baseline`.
- the `chop / no-trade discipline` pass is now complete:
  - raw ADX floors were too blunt
  - local EMA spread was inactive
  - `falling ADX + compressed BBW` was active but still too defensive
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback` remains the best
  unlocked exit-side research member and still matters as the parent shape
  behind the working baseline.
- `TRENDING_UP` sign is real and repeatable enough to justify keeping the
  family alive.
- `RANGING` contamination remains manageable but unresolved.
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
4. `transition bleed`
   - target: reduce damage near regime flips and unstable trend labels
   - success read: better `sideways transition` behavior and cleaner `MIXED`
     deltas
5. `winner protection vs loser suppression`
   - role: diagnostic decomposition after the first four structural passes
   - question: are gains coming from better winner retention, smaller medium
     losers, or both
6. `separate bullish and bearish families`
   - role: only after the long-side family is structurally understood
   - question: should trend-up and trend-down edges be separated rather than
     forced into one family

## Resume Point

When work resumes, do **not**:

- keep sweeping `stop_atr_mult`
- keep sweeping `trend_spread_min`
- re-lock the `confirmed` or `failfast` variants
- treat the underwater `ema_20` exit's small aggregate gain as a solved result

Next step should start from the `working baseline`
`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`, while
still keeping the `frozen baseline` as the historical reference point.

New candidate review reads should therefore follow this order:

1. compare against the `working baseline` for practical go / no-go value
2. compare against the `frozen baseline` to preserve the long research arc
3. check the 8-window supplemental market-phase matrix before calling a result
   clean

The next ordered comparison pass is now:

1. `post-entry management`
2. `transition bleed`
3. `winner protection vs loser suppression`

Only after those remaining passes land should this family move to:

1. `separate bullish and bearish families`

Guardrail:

- keep the baseline entry intact while testing the next structural move, so the
  diff remains interpretable.
