# Transition-Aware Tightening: macd_signal_btc_4h_trending_up

Date: `2026-04-24`

Purpose: narrow the explicit `transition-aware` weak-tape proxy so it keeps the
`RANGING` / `sideways_transition` repair without over-cutting default
`TRENDING_UP`.

Tightened candidate:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`

Comparison set:

- `partial67` working baseline
- `partial67_transition_aware_late_entry_filter` first explicit transition probe
- `partial67_chop_trend_tightened_late_entry_filter` best aggregate localized proxy
- `partial67_late_entry_filter` raw defense reference

## Attribution Read

The first explicit transition-aware pass blocked four default `TRENDING_UP`
trades at `1.49`, `2.37`, `2.80`, and `2.80 ATR` extension, while the two
known `sideways_transition` losers sat much farther out at `3.55 ATR`.

That gap suggested a simple first narrowing pass:

- keep the same transition context
- but only let the veto fire when `entry_extension_atr >= 3.0`

This is intentionally a one-lever pass. No new divergence feature and no
OR-stacking were added.

## Candidate Shape

This child keeps the exact `transition_aware_late_entry_filter` context:

- `current_high >= prior_high_max`
- `prior_positive_hist_max >= transition_prior_positive_hist_min`
- `current_macd_hist / prior_positive_hist_max <= transition_hist_ratio_max`

The only change is the veto arm:

- previous pass: block any transition-context entry with
  `entry_extension_atr > 1.25`
- tightened pass: block only when that same context is active and
  `entry_extension_atr >= 3.0`

Interpretation intent:

- keep the explicit transition mechanism
- localize it to extreme chase entries instead of every moderate overshoot

## Default Review Matrix

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `transition_aware_late_entry_filter` | 37 | 1230.6759 | 4.5977 | transition surface repaired; too selective |
| `transition_aware_tightened_late_entry_filter` | 44 | 1682.5711 | 4.4059 | first strict default-review improvement over `partial67` |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | best aggregate localized proxy |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | raw defense ceiling |

Per-window:

| candidate | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `transition_aware` | `22 / +992.0771` | `1 / -45.2810` | `14 / +283.8799` |
| `transition_aware_tightened` | `26 / +1484.5085` | `1 / -45.2810` | `17 / +243.3437` |
| `chop_trend_tightened` | `24 / +1670.0429` | `3 / -173.8867` | `15 / +352.4744` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |

Default-window read:

- this child fully restored default `TRENDING_UP` back to `partial67`
- it also restored default `MIXED` back to `partial67`
- it kept the explicit transition repair in default `RANGING`:
  `1 / -45.2810`
- aggregate default review therefore improved from `1553.9654` to `1682.5711`
  without increasing max drawdown versus the `partial67` baseline

## Supplemental Matrix

| window | `partial67` | `transition_aware` | `transition_aware_tightened` | `chop_trend_tightened` | `late_entry_filter` | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `bull_strong_up_1` | +228.6339 | +595.7043 | +595.7043 | +167.8664 | +53.4542 | the transition repair stays intact without reintroducing bullish tax |
| `bear_persistent_down` | +194.7774 | +283.8799 | +243.3437 | +352.4744 | +473.0154 | still positive, but weaker than both bearish-defense references |
| `range_low_vol` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `1 / -4.2350` | `0 / 0.0000` | stray low-vol loser stays removed |
| `bull_recovery_2026` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | non-discriminating |
| `ftx_style_crash` | -16.2852 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | crash avoidance stays intact |
| `sideways_transition` | -196.9550 | +97.3769 | +97.3769 | -196.9550 | +38.5007 | the transition-surface repair survives intact |
| `classic_rollercoaster_2021_2022` | +1567.9070 | +1441.6339 | +1612.0356 | +1816.9483 | +880.8983 | long-cycle participation recovers above baseline, but still trails `chop_trend_tightened` |
| `recovery_2023_2024` | +1063.8774 | +1558.1664 | +2245.5016 | +1889.4412 | +1426.6116 | strongest recovery-window capture in the current side branch |

Family-level summary:

| family | `partial67` | `transition_aware` | `transition_aware_tightened` | `chop_trend_tightened` | `late_entry_filter` |
| --- | ---: | ---: | ---: | ---: | ---: |
| bullish family | `88 / +2860.4183` | `67 / +3595.5046` | `76 / +4453.2415` | `74 / +3874.2559` | `34 / +2360.9641` |
| bearish family | `18 / +178.4922` | `14 / +283.8799` | `17 / +243.3437` | `15 / +352.4744` | `7 / +473.0154` |
| ranging / transition family | `4 / -196.9550` | `2 / +97.3769` | `2 / +97.3769` | `5 / -201.1900` | `1 / +38.5007` |

## Interpretation

What improved:

- this is the first explicit transition child that strictly improves the
  default review over `partial67`
- it keeps the repaired `RANGING` and `sideways_transition` surface intact
- it keeps `range_low_vol` clean
- it keeps `ftx_style_crash` at `0.0000`
- it keeps the strong `bull_strong_up_1` / `recovery_2023_2024` behavior from
  the first explicit transition pass
- it recovered the large `2023-10-23T03:00:00+00:00` `+566.7533` trend winner
  while still blocking the two `2023-06-23` transition losers

What did not improve:

- `bear_persistent_down` fell back from `+283.8799` to `+243.3437`
- that bearish-defense read still trails both `chop_trend_tightened` and the
  unconditional `late_entry_filter`
- default aggregate pnl still trails `chop_trend_tightened` and the raw
  `late_entry_filter`

Best current read:

- the explicit transition mechanism is worth keeping
- the first pass failed because the veto arm was too wide, not because the
  mechanism itself was wrong
- this tightened child is now the leading explicit transition-surface
  candidate and the cleanest proof that the `RANGING` contamination can be
  repaired without giving away the baseline trend windows

## Decision

- keep `transition_aware_tightened_late_entry_filter` as the leading explicit
  transition-surface candidate
- treat it as the first side-branch child that strictly improves default review
  over `partial67`
- do not replace `late_entry_filter` as the raw defense ceiling
- do not yet replace `chop_trend_tightened_late_entry_filter` as the best
  bearish-defense reference
- next comparison should not be another micro-threshold sand:
  compare this tightened explicit-transition child against the pending
  event-based alternate mechanism

## References

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [transition-aware defense](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_transition_aware_defense.md:1>)
- [chop-trend localization](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_chop_trend_localization.md:1>)
