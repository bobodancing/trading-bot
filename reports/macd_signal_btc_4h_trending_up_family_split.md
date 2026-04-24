# Separate Bullish and Bearish Families: macd_signal_btc_4h_trending_up

Date: `2026-04-24`

Purpose: resolve whether the next structural queue should keep one blended
long-side research family or split into:

- a `bullish mainline` family
- a `weak-tape defense` side branch for bearish / ranging contexts

Comparison set:

- working baseline:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
- leading bullish-family candidate:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`
- defensive side branch:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`

Read guardrails:

- default review windows remain the practical go / no-go matrix
- the 8-window supplemental matrix is diagnostic and overlapping; it should not
  be treated as one independent summed backtest
- `bull_recovery_2026` and `range_low_vol` produced `0 trades` across all three
  branches, so they are non-discriminating in this pass

## Default Review Matrix

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 4.4059 | reference |
| `partial67_remainder_ratchet` | 46 | 1597.8170 | 4.1130 | same-entry bullish leader |
| `partial67_late_entry_filter` | 16 | 1856.8086 | 1.8572 | selective defense branch, not same participation |

The promotion-gated default-window comparison is now formalized in:

- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)

## Informative Supplemental Windows

| window | family read | `partial67` | `ratchet` | `late_entry_filter` | dominant read |
| --- | --- | ---: | ---: | ---: | --- |
| `bull_strong_up_1` | bullish trend | +228.6339 | +261.7767 | +53.4542 | ratchet adds capture; late filter taxes winners |
| `classic_rollercoaster_2021_2022` | bullish / volatile | +1567.9070 | +1564.3730 | +880.8983 | ratchet is effectively flat; late filter misses too many winners |
| `recovery_2023_2024` | bullish recovery / transition | +1063.8774 | +1136.1372 | +1426.6116 | late filter can help, but only through heavy selectivity |
| `bear_persistent_down` | bearish persistent weak tape | +194.7774 | +202.8854 | +473.0154 | late filter is strongest loser suppression |
| `ftx_style_crash` | bearish shock | -16.2852 | -16.2852 | +0.0000 | late filter avoids the single loser |
| `sideways_transition` | ranging / transition | -196.9550 | -190.0704 | +38.5007 | late filter is the cleanest defense |

## Family-Level Read

| family | `partial67` | `ratchet` | delta vs `partial67` | `late_entry_filter` | delta vs `partial67` | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| bullish mainline family | `88 trades / +2860.4183` | `88 / +2962.2868` | +101.8685 | `34 / +2360.9641` | -499.4542 | ratchet is the clean bullish-family improvement; late filter underparticipates |
| bearish weak-tape family | `18 / +178.4922` | `18 / +186.6002` | +8.1080 | `7 / +473.0154` | +294.5232 | late filter is materially stronger as defense |
| ranging / transition family | `4 / -196.9550` | `4 / -190.0704` | +6.8846 | `1 / +38.5007` | +235.4557 | late filter is best defensively, but extremely selective |

## Interpretation

`partial67_remainder_ratchet` belongs in the `bullish mainline` family:

- it keeps the same trade set as the `working baseline`
- it improves the formal default review by `+43.8515`
- it adds `+101.8685` across the informative bullish-family windows without
  reducing participation
- its weakness is not bearish contamination; it is simply that `RANGING`
  remains unresolved

`partial67_late_entry_filter` does **not** belong in the bullish mainline:

- its gains come from refusing trades, not from a cleaner same-entry edge
- it is strongest in weak-tape windows such as `bear_persistent_down`,
  `ftx_style_crash`, and `sideways_transition`
- it still pays obvious winner tax in `bull_strong_up_1` and
  `classic_rollercoaster_2021_2022`
- even where it helps in `recovery_2023_2024`, that help still comes through a
  much smaller trade set

## Decision

- split the queue into a `bullish mainline` and a separate `weak-tape defense`
  branch
- keep `partial67` as the `working baseline` for the bullish mainline
- keep `partial67_remainder_ratchet` as the leading bullish-family candidate
- keep `partial67_late_entry_filter` as a `RANGING` / transition defense side
  branch, not as a direct replacement for the `working baseline`
- do not blindly combine `late_entry_filter` with `remainder_ratchet`; an
  explicit context gate would be required first

## References

- [winner / loser decomposition](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_winner_loser_decomposition.md:1>)
- [strategy_plugin_candidate_review.md](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
