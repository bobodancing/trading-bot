# Context-Gated Weak-Tape Defense: macd_signal_btc_4h_trending_up

Date: `2026-04-24`

Purpose: evaluate the first concrete `weak-tape defense` side-branch candidate:

- candidate:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`

Comparison set:

- `partial67` working baseline
- `partial67_late_entry_filter` unconditional defense reference

Read guardrails:

- default review windows remain the first-pass promotion-gated matrix
- the 8-window supplemental matrix remains diagnostic and overlapping
- this candidate should be judged first on whether it localizes defense to weak
  tape, not only on aggregate net PnL

## Candidate Shape

The candidate keeps the `partial67` entry and staged exit path, but only
activates the late-entry stretch cap when either weak-tape proxy is active:

- `trend_spread_delta <= 0` over the recent 1d slope window
- or local `falling ADX + compressed BBW`

## Default Review Matrix

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `context_gated_late_entry_filter` | 36 | 1877.7400 | 2.7856 | aggregate improved, still selective |
| `late_entry_filter` | 16 | 1856.8086 | 1.8572 | strongest raw defense, strongest participation cut |

Per-window:

| candidate | TRENDING_UP | RANGING | MIXED |
| --- | ---: | ---: | ---: |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `context_gated` | `23 / +1696.9839` | `3 / -173.8867` | `10 / +354.6428` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |

Default-window read:

- the context gate recovered much more `TRENDING_UP` participation than the
  unconditional `late_entry_filter`
- it also improved `MIXED` versus the `working baseline`
- but it did **not** recover the `RANGING` defense at all; the default
  `RANGING` cell stayed identical to `partial67`

Reference report:

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

## Supplemental Matrix

| window | `partial67` | `context_gated` | `late_entry_filter` | read |
| --- | ---: | ---: | ---: | --- |
| `bull_strong_up_1` | +228.6339 | -32.1112 | +53.4542 | context gate misfires on a clean bullish impulse |
| `bear_persistent_down` | +194.7774 | +354.6428 | +473.0154 | context gate helps, but less than unconditional defense |
| `range_low_vol` | `0 trades / 0.0000` | `1 / -4.2350` | `0 / 0.0000` | context gate introduces a new weak trade |
| `bull_recovery_2026` | `0 / 0.0000` | `0 / 0.0000` | `0 / 0.0000` | non-discriminating |
| `ftx_style_crash` | -16.2852 | 0.0000 | 0.0000 | context gate avoids the crash loser |
| `sideways_transition` | -196.9550 | -196.9550 | +38.5007 | context gate fails to activate on the known bleed surface |
| `classic_rollercoaster_2021_2022` | +1567.9070 | +1600.3338 | +880.8983 | context gate preserves most long-cycle winners |
| `recovery_2023_2024` | +1063.8774 | +1716.4047 | +1426.6116 | context gate is strong here, but still selective |

Family-level summary:

| family | `partial67` | `context_gated` | delta vs `partial67` | `late_entry_filter` | delta vs `partial67` |
| --- | ---: | ---: | ---: | ---: | ---: |
| bullish family | `88 / +2860.4183` | `68 / +3284.6274` | +424.2091 | `34 / +2360.9641` | -499.4542 |
| bearish family | `18 / +178.4922` | `10 / +354.6428` | +176.1506 | `7 / +473.0154` | +294.5232 |
| ranging / transition family | `4 / -196.9550` | `5 / -201.1900` | -4.2350 | `1 / +38.5007` | +235.4557 |

## Interpretation

This candidate is **not** a clean `weak-tape defense` successor to the
unconditional `late_entry_filter`.

What survived:

- it materially reduced the old winner tax versus the unconditional defense
- it preserved much more of the bullish-family capture
- it improved `bear_persistent_down`
- it fully avoided the single `ftx_style_crash` loser

What failed:

- it did not improve `sideways_transition`, which is the current known weak
  surface
- it did not improve the default `RANGING` review cell
- it introduced a new `range_low_vol` loser
- it actively misfired in `bull_strong_up_1`, where the branch turned a clean
  positive window into a small loser

Best current read:

- the current OR-gated weak-tape proxy is not well localized
- this branch now reads more like a selective hybrid cartridge than a targeted
  defense lane
- because the side-branch intent was `defense where weak tape dominates`, this
  pass does **not** yet validate the candidate for the `weak-tape defense`
  queue

## Decision

- keep the candidate as informative research evidence only
- do not promote it into the bullish mainline
- do not replace the unconditional `late_entry_filter` side-branch read with
  this candidate
- next weak-tape-defense pass should isolate gate attribution instead of keeping
  the current OR combination opaque:
  - `trend_decay`-only activation
  - `chop_trend`-only activation

## References

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [family split](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_family_split.md:1>)
