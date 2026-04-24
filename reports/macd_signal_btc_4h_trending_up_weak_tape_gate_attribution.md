# Weak-Tape Gate Attribution: macd_signal_btc_4h_trending_up

Date: `2026-04-24`

Purpose: isolate which proxy actually drives the `weak-tape defense` side
branch after the first OR-gated context pass.

Attribution probes:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter`

Comparison set:

- `partial67` working baseline
- `partial67_context_gated_late_entry_filter` OR-gated reference
- `partial67_late_entry_filter` unconditional defense reference

Read guardrails:

- default review windows remain the first-pass promotion-gated matrix
- the 8-window supplemental matrix remains diagnostic and overlapping
- attribution is about `which gate is doing the work`, not about forcing a new
  promotion candidate

## Candidate Shape

Both attribution probes keep the `partial67` entry and staged exit path and
reuse the same late-entry stretch cap:

- `trend_decay_only` activates the cap only when 1d
  `trend_spread_delta <= 0`
- `chop_trend_only` activates the cap only when local
  `falling ADX + compressed BBW` is active

## Default Review Matrix

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | OR-gated reference |
| `trend_decay_only_late_entry_filter` | 41 | 1604.2942 | 4.3940 | near-baseline, weak defense |
| `chop_trend_only_late_entry_filter` | 41 | 1827.4113 | 2.9913 | most of the OR-gated uplift survives |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Per-window:

| candidate | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `context_gated` | `23 / +1696.9839` | `3 / -173.8867` | `10 / +354.6428` |
| `trend_decay_only` | `25 / +1511.4495` | `3 / -173.8867` | `13 / +266.7314` |
| `chop_trend_only` | `24 / +1670.0429` | `3 / -173.8867` | `14 / +331.2551` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |

Default-window read:

- `trend_decay_only` behaves like a mild selectivity trim, not a meaningful
  weak-tape defense
- `chop_trend_only` preserves most of the OR-gated aggregate uplift and lower
  drawdown profile
- neither localized gate repaired the default `RANGING` cell; all of
  `partial67`, `context_gated`, `trend_decay_only`, and `chop_trend_only`
  stayed at `3 trades / -173.8867`

Reference report:

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

## Supplemental Matrix

| window | `partial67` | `context_gated` | `trend_decay_only` | `chop_trend_only` | `late_entry_filter` | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `bull_strong_up_1` | +228.6339 | -32.1112 | +268.1561 | -83.5023 | +53.4542 | bullish misfire comes from `chop_trend`, not `trend_decay` |
| `bear_persistent_down` | +194.7774 | +354.6428 | +266.7314 | +331.2551 | +473.0154 | both help, but `chop_trend` drives most of the defense uplift |
| `range_low_vol` | `0 / 0.0000` | `1 / -4.2350` | `1 / -4.2350` | `1 / -4.2350` | `0 / 0.0000` | both localized gates inherit the new stray loser |
| `bull_recovery_2026` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | non-discriminating |
| `ftx_style_crash` | -16.2852 | 0.0000 | -16.2852 | 0.0000 | 0.0000 | crash avoidance comes from `chop_trend`, not `trend_decay` |
| `sideways_transition` | -196.9550 | -196.9550 | -196.9550 | -196.9550 | +38.5007 | neither current proxy localizes the known weak surface |
| `classic_rollercoaster_2021_2022` | +1567.9070 | +1600.3338 | +1827.5301 | +1600.3338 | +880.8983 | `trend_decay` preserves long-cycle winners; `chop_trend` matches the OR gate |
| `recovery_2023_2024` | +1063.8774 | +1716.4047 | +1601.6640 | +1638.0725 | +1426.6116 | both active, `chop_trend` slightly stronger, OR gate strongest |

Family-level summary:

| family | `partial67` | `context_gated` | `trend_decay_only` | `chop_trend_only` | `late_entry_filter` |
| --- | ---: | ---: | ---: | ---: | ---: |
| bullish family | `88 / +2860.4183` | `68 / +3284.6274` | `78 / +3697.3502` | `71 / +3154.9041` | `34 / +2360.9641` |
| bearish family | `18 / +178.4922` | `10 / +354.6428` | `14 / +250.4462` | `14 / +331.2551` | `7 / +473.0154` |
| ranging / transition family | `4 / -196.9550` | `5 / -201.1900` | `5 / -201.1900` | `5 / -201.1900` | `1 / +38.5007` |

## Interpretation

Main attribution read:

- the current OR-gated candidate gets most of its useful `weak-tape` behavior
  from `chop_trend`, not from `trend_decay`
- the current OR-gated candidate also gets its worst bullish false positives
  from `chop_trend`
- `trend_decay_only` behaves more like a bullish participation / winner
  preservation probe than a defense trigger

What `trend_decay` proved:

- it preserved `bull_strong_up_1`
- it improved the long-cycle `classic_rollercoaster_2021_2022` winner set
- it did **not** avoid `ftx_style_crash`
- it did **not** improve `sideways_transition`
- it did **not** improve default `RANGING`

What `chop_trend` proved:

- it recovered most of the OR-gated aggregate uplift
- it avoided the `ftx_style_crash` loser
- it materially helped `bear_persistent_down`
- it still misfired in `bull_strong_up_1`
- it still failed on `sideways_transition`
- it still introduced the `range_low_vol` loser

Best current read:

- `trend_decay` is not the live weak-tape defense lever at the current threshold
- `chop_trend` is the live weak-tape proxy, but it is not localized enough to
  become the side-branch reference
- the unconditional `late_entry_filter` remains the strongest defense read
  because neither localized proxy explains its `sideways_transition` recovery

## Decision

- keep both attribution probes as informative research evidence only
- do not replace the unconditional `late_entry_filter` side-branch reference
  with either localized gate
- do not keep the current OR-gated proxy as a solved result
- if the side branch continues, prioritize `chop_trend` localization retuning
  or an explicit `sideways_transition` trigger over further `trend_decay`-only
  work

## References

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [context-gated weak-tape defense](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_context_gated_weak_tape_defense.md:1>)
- [family split](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_family_split.md:1>)
