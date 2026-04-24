# Chop-Trend Localization: macd_signal_btc_4h_trending_up

Date: `2026-04-24`

Purpose: test whether the active `chop_trend` proxy can be localized without
collapsing back into the noisy `bull_strong_up_1` misfire seen in the first
attribution pass.

Localization candidate:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter`

Comparison set:

- `partial67` working baseline
- `partial67_context_gated_late_entry_filter` OR-gated reference
- `partial67_chop_trend_only_late_entry_filter` raw localized-gate reference
- `partial67_late_entry_filter` unconditional defense reference

## Candidate Shape

This candidate keeps the `partial67` entry and staged exit path, keeps the
same `falling ADX + compressed BBW` activation proxy, and adds one localization
qualifier:

- only let the `chop_trend` veto fire when
  `max((close - ema_20) / atr, 0)` is at least
  `chop_trend_extension_atr_trigger = 1.5`

Interpretation intent:

- do not let mild `1.25 ~ 1.49 ATR` overstretches trigger the noisy
  `chop_trend` veto
- still block the obviously stretched chase entries when the same local
  compression signal is active

## Default Review Matrix

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | OR-gated reference |
| `chop_trend_only_late_entry_filter` | 41 | 1827.4113 | 2.9913 | raw localized-gate reference |
| `chop_trend_tightened_late_entry_filter` | 42 | 1848.6305 | 2.9860 | localization improved; one `MIXED` winner restored |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Per-window:

| candidate | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `context_gated` | `23 / +1696.9839` | `3 / -173.8867` | `10 / +354.6428` |
| `chop_trend_only` | `24 / +1670.0429` | `3 / -173.8867` | `14 / +331.2551` |
| `chop_trend_tightened` | `24 / +1670.0429` | `3 / -173.8867` | `15 / +352.4744` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |

Default-window read:

- this pass did not change `TRENDING_UP` or default `RANGING` relative to
  `chop_trend_only`
- it did improve `MIXED` from `14 / +331.2551` to `15 / +352.4744`
- the regained default-window trade was a new `+21.2192` winner
  (`2025-05-01T09:00:00+00:00`)

## Supplemental Matrix

| window | `partial67` | `context_gated` | `chop_trend_only` | `chop_trend_tightened` | `late_entry_filter` | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `bull_strong_up_1` | +228.6339 | -32.1112 | -83.5023 | +167.8664 | +53.4542 | most of the bullish false-positive tax was repaired |
| `bear_persistent_down` | +194.7774 | +354.6428 | +331.2551 | +352.4744 | +473.0154 | bearish defense survived the localization pass |
| `range_low_vol` | `0 / 0.0000` | `1 / -4.2350` | `1 / -4.2350` | `1 / -4.2350` | `0 / 0.0000` | stray low-vol loser still survives |
| `bull_recovery_2026` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | non-discriminating |
| `ftx_style_crash` | -16.2852 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | crash avoidance stayed intact |
| `sideways_transition` | -196.9550 | -196.9550 | -196.9550 | -196.9550 | +38.5007 | known weak surface still untouched |
| `classic_rollercoaster_2021_2022` | +1567.9070 | +1600.3338 | +1600.3338 | +1816.9483 | +880.8983 | long-cycle participation improved materially |
| `recovery_2023_2024` | +1063.8774 | +1716.4047 | +1638.0725 | +1889.4412 | +1426.6116 | localized proxy is strongest here so far |

Family-level summary:

| family | `partial67` | `context_gated` | `chop_trend_only` | `chop_trend_tightened` | `late_entry_filter` |
| --- | ---: | ---: | ---: | ---: | ---: |
| bullish family | `88 / +2860.4183` | `68 / +3284.6273` | `71 / +3154.9040` | `74 / +3874.2559` | `34 / +2360.9641` |
| bearish family | `18 / +178.4922` | `10 / +354.6428` | `14 / +331.2551` | `15 / +352.4744` | `7 / +473.0154` |
| ranging / transition family | `4 / -196.9550` | `5 / -201.1900` | `5 / -201.1900` | `5 / -201.1900` | `1 / +38.5007` |

## Interpretation

What improved:

- the noisy `chop_trend` proxy is now materially better localized than the raw
  `chop_trend_only` child
- `bull_strong_up_1` recovered from `-83.5023` to `+167.8664`
- `bear_persistent_down` did not collapse during that repair
- both long windows improved versus `chop_trend_only`

Concrete regained trades versus `chop_trend_only`:

- `2024-11-19T17:00:00+00:00` in `bull_strong_up_1` and `recovery_2023_2024`:
  `+251.3687`
- `2025-05-01T09:00:00+00:00` in default `MIXED` / `bear_persistent_down`:
  `+21.2192`
- `2021-10-14T01:00:00+00:00` in `classic_rollercoaster_2021_2022`:
  `+216.6144`

What did not improve:

- default `RANGING` remained `3 / -173.8867`
- `sideways_transition` stayed `4 / -196.9550`
- `range_low_vol` still kept the same `-4.2350` stray loser

Best current read:

- this is the best localized `chop_trend` proxy so far
- it is strong enough to replace `chop_trend_only` as the current localization
  reference inside the side branch
- it is **not** strong enough to replace the unconditional
  `late_entry_filter` as the side-branch defense reference, because the key
  `sideways_transition` / default `RANGING` thesis surfaces remain unresolved

## Decision

- keep `chop_trend_tightened_late_entry_filter` as the leading localized
  `chop_trend` probe
- supersede the raw `chop_trend_only` child as the next comparison anchor for
  this sub-branch
- do not promote it into the bullish mainline
- do not treat the side branch as solved
- next pass should target an explicit `transition-aware defense` or another
  trigger that can attack `sideways_transition`, rather than keep sanding the
  same extension-only lever indefinitely

## References

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [weak-tape gate attribution](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_weak_tape_gate_attribution.md:1>)
- [context-gated weak-tape defense](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_context_gated_weak_tape_defense.md:1>)
