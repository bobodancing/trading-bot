# Transition-Aware Defense: macd_signal_btc_4h_trending_up

Date: `2026-04-24`

Purpose: test whether an explicit `transition-aware` late-entry gate can attack
the known `RANGING` / `sideways_transition` weak surface more directly than the
current localized `chop_trend` proxy.

Transition-aware candidate:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter`

Comparison set:

- `partial67` working baseline
- `partial67_chop_trend_tightened_late_entry_filter` localized-proxy reference
- `partial67_late_entry_filter` raw defense reference

## Candidate Shape

This candidate keeps the `partial67` entry and staged exit path. It does **not**
reuse the `chop_trend` gate. Instead, it activates the late-entry veto only
when all of the following are true over `transition_lookback_bars = 12`:

- `current_high >= prior_high_max`
- `prior_positive_hist_max >= transition_prior_positive_hist_min`
- `current_macd_hist / prior_positive_hist_max <= transition_hist_ratio_max`

Then, as with the side-branch defense line, the signal is blocked only if
`max((close - ema_20) / atr, 0) > entry_ema_extension_atr_max`.

Interpretation intent:

- treat `price still chasing local highs while 4h impulse is already much
  weaker than the prior positive swing` as a transition-risk surface
- keep the defense on explicit momentum exhaustion instead of the indirect
  `chop_trend` proxy

Why this first pass did **not** add volume shrink:

- the known `2023-06-23` transition losers were high-volume impulse spikes, so
  `volume contraction` was not the clean first discriminator on that surface

## Default Review Matrix

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | best aggregate localized proxy so far |
| `transition_aware_late_entry_filter` | 37 | 1230.6759 | 4.5977 | transition surface repaired; aggregate too selective |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Per-window:

| candidate | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `chop_trend_tightened` | `24 / +1670.0429` | `3 / -173.8867` | `15 / +352.4744` |
| `transition_aware` | `22 / +992.0771` | `1 / -45.2810` | `14 / +283.8799` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |

Default-window read:

- this is the first localized side-branch pass that actually repaired default
  `RANGING`
- it matched the unconditional `late_entry_filter` on that cell:
  `1 / -45.2810`
- but it also over-cut the default `TRENDING_UP` window down to
  `22 / +992.0771`
- aggregate default review therefore stayed below `partial67`,
  `chop_trend_tightened`, and `late_entry_filter`

## Supplemental Matrix

| window | `partial67` | `chop_trend_tightened` | `transition_aware` | `late_entry_filter` | read |
| --- | ---: | ---: | ---: | ---: | --- |
| `bull_strong_up_1` | +228.6339 | +167.8664 | +595.7043 | +53.4542 | short bullish impulse handling is unexpectedly strong |
| `bear_persistent_down` | +194.7774 | +352.4744 | +283.8799 | +473.0154 | defense survives, but weaker than both defense references |
| `range_low_vol` | `0 / 0.0000` | `1 / -4.2350` | `0 / 0.0000` | `0 / 0.0000` | stray low-vol loser is removed |
| `bull_recovery_2026` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | non-discriminating |
| `ftx_style_crash` | -16.2852 | 0.0000 | 0.0000 | 0.0000 | crash avoidance stays intact |
| `sideways_transition` | -196.9550 | -196.9550 | +97.3769 | +38.5007 | first localized proxy to beat the raw defense reference here |
| `classic_rollercoaster_2021_2022` | +1567.9070 | +1816.9483 | +1441.6339 | +880.8983 | long-cycle participation is clipped versus the localized `chop_trend` proxy |
| `recovery_2023_2024` | +1063.8774 | +1889.4412 | +1558.1664 | +1426.6116 | still positive, but not the best bullish capture path |

Family-level summary:

| family | `partial67` | `chop_trend_tightened` | `transition_aware` | `late_entry_filter` |
| --- | ---: | ---: | ---: | ---: |
| bullish family | `88 / +2860.4183` | `74 / +3874.2559` | `67 / +3595.5046` | `34 / +2360.9641` |
| bearish family | `18 / +178.4922` | `15 / +352.4744` | `14 / +283.8799` | `7 / +473.0154` |
| ranging / transition family | `4 / -196.9550` | `5 / -201.1900` | `2 / +97.3769` | `1 / +38.5007` |

## Interpretation

What improved:

- this is the first localized proxy that truly explains the transition-defense
  surface instead of leaving `sideways_transition` untouched
- it filtered the two `2023-06-23` losers (`-159.5415`, `-134.7904`) that
  `chop_trend_tightened` still allowed
- unlike the unconditional `late_entry_filter`, it still kept the
  `2023-07-13T13:00:00+00:00` `+58.8762` winner inside `sideways_transition`
- it removed the `range_low_vol` stray loser
- it kept `ftx_style_crash` clean
- `bull_strong_up_1` improved to `+595.7043`, so this proxy is not simply
  another blunt winner tax

What did not improve:

- default `TRENDING_UP` dropped from `+1484.5085` (`partial67`) and
  `+1670.0429` (`chop_trend_tightened`) to `+992.0771`
- default aggregate pnl fell to `1230.6759`
- max drawdown rose to `4.5977`, worse than the `partial67` baseline
- `classic_rollercoaster_2021_2022` and `recovery_2023_2024` both stayed below
  `chop_trend_tightened`
- `bear_persistent_down` stayed positive but weaker than both the localized
  `chop_trend` probe and the unconditional defense reference

Best current read:

- explicit `transition-aware` gating is real
- it explains the `RANGING` / `sideways_transition` surface better than the
  current `chop_trend` proxy
- but the current activation is still too wide for default-window promotion or
  for replacing the existing side-branch anchors

## Decision

- keep `transition_aware_late_entry_filter` as the first explicit
  transition-surface probe
- do not replace `chop_trend_tightened_late_entry_filter` as the best aggregate
  localized proxy
- do not replace the unconditional `late_entry_filter` as the raw defense
  ceiling
- do not promote this candidate into the bullish mainline
- next pass should narrow the explicit transition proxy, not broaden defense
  further:
  - tighten the divergence threshold
  - or add one small secondary qualifier to recover default `TRENDING_UP`

## References

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [chop-trend localization](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_chop_trend_localization.md:1>)
- [weak-tape gate attribution](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_weak_tape_gate_attribution.md:1>)
