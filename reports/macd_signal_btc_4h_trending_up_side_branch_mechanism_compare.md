# MACD 4h Side-Branch Mechanism Compare

Date: `2026-04-29`

Purpose: insert the pinned `squeeze_release_unconfirmed` candidate result into
the existing weak-tape side-branch comparison, without rerunning the established
reference candidates.

New candidate:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter`

Evaluation order from the squeeze-release spec:

1. `chop_trend_tightened` as the localized-state reference
2. `transition_aware_tightened` as the divergence-based reference
3. `late_entry_filter` as the raw defense ceiling
4. `partial67` as the working baseline

## Default Aggregate

| layer | candidate | role | trades | net_pnl | max_dd_pct | read |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | `chop_trend_tightened` | localized-state reference | 42 | +1848.6305 | 2.9860 | best aggregate localized proxy |
| 2 | `transition_aware_tightened` | divergence-based reference | 44 | +1682.5711 | 4.4059 | leading explicit transition candidate |
| 3 | `late_entry_filter` | raw defense ceiling | 16 | +1856.8086 | 1.8572 | strongest defense, heavy participation cut |
| 4 | `partial67` | working baseline | 46 | +1553.9654 | 4.4059 | baseline |
| new | `squeeze_release_unconfirmed` | event-based probe | 40 | +1185.4120 | 4.5922 | repairs RANGING but fails trend retention |

## Per-Window Detail

| candidate | `TRENDING_UP` | `RANGING` | `MIXED` |
| --- | ---: | ---: | ---: |
| `chop_trend_tightened` | `24 / +1670.0429` | `3 / -173.8867` | `15 / +352.4744` |
| `transition_aware_tightened` | `26 / +1484.5085` | `1 / -45.2810` | `17 / +243.3437` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `squeeze_release_unconfirmed` | `22 / +987.3493` | `1 / -45.2810` | `17 / +243.3437` |

## Mechanism Attribution

Against `chop_trend_tightened`:

- squeeze-release loses `663.2185` aggregate PnL
- it repairs default `RANGING`, which chop-trend does not
- but it gives back too much default `TRENDING_UP` PnL
- `chop_trend_tightened` remains the better aggregate localized-state reference

Against `transition_aware_tightened`:

- `RANGING` and `MIXED` are identical
- squeeze-release removes four default `TRENDING_UP` trades worth `+497.1592`
- the removed set contains two losers (`-177.4937`) and two winners
  (`+674.6528`)
- `transition_aware_tightened` remains the better explicit transition-surface
  candidate

Against raw `late_entry_filter`:

- raw late-entry defense is still the default aggregate ceiling:
  `+1856.8086` versus `+1185.4120`
- squeeze-release keeps much more participation, but the retained participation
  is not high-quality enough to offset the bullish misses
- raw late-entry filter remains a diagnostic ceiling, not a direct promotion
  target

Against `partial67`:

- default `RANGING` improves by `+128.6057`
- default `MIXED` is unchanged
- default `TRENDING_UP` degrades by `-497.1592`
- aggregate default delta is `-368.5534`

## Decision

The event-based squeeze-release mechanism does activate on a relevant weak-tape
surface, but it is not clean enough at the pinned cell. It reproduces the
default `RANGING` repair, yet fails the pre-committed default `TRENDING_UP`
retention gate.

Decision:

- keep `squeeze_release_unconfirmed` as research evidence only
- do not advance it to parameter sweep
- keep `transition_aware_tightened` as the leading explicit transition-surface
  candidate
- keep `chop_trend_tightened` as the best aggregate localized proxy
- keep raw `late_entry_filter` as the defense ceiling reference

## References

- [squeeze-release first pass](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_squeeze_release_unconfirmed_first_pass.md:1>)
- [candidate review](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [transition-aware tightening](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md:1>)
- [chop-trend localization](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_chop_trend_localization.md:1>)
