# Winner Protection vs Loser Suppression: macd_signal_btc_4h_trending_up

Date: `2026-04-23`

Purpose: decompose the leading post-dual-baseline branches around the current
`working baseline`:

- working baseline:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
- leading entry-side precision branch:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
- leading post-entry management branch:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`

Read guardrail:

- default review windows are additive enough for aggregate comparison
- supplemental market-phase windows overlap with the long windows, so they are
  diagnostic and should not be summed as one independent aggregate

## Default Review Windows

| candidate | trades | net_pnl | wins | losses | gross_profit | gross_loss | avg_win | avg_loss | read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | 1553.9654 | 18 | 27 | 3059.6490 | -1505.6835 | 169.9805 | -55.7661 | reference |
| `late_entry_filter` | 16 | 1856.8086 | 9 | 7 | 2126.8571 | -270.0485 | 236.3175 | -38.5784 | loser suppression, high selectivity |
| `remainder_ratchet` | 46 | 1597.8170 | 18 | 27 | 3103.5005 | -1505.6835 | 172.4167 | -55.7661 | winner protection / capture |

## Decomposition vs Working Baseline

For entry-filter candidates, `baseline-only` rows are trades the candidate
refused to take. Negative `baseline-only` PnL is avoided loss; positive
`baseline-only` PnL is missed winner.

| candidate | common trades | baseline-only trades | same-entry delta | avoided loser pnl | missed winner pnl | candidate-only pnl | net delta | primary mechanism |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `late_entry_filter` | 16 | 30 | 0.0000 | +1235.6351 | -932.7919 | 0.0000 | +302.8432 | loser suppression with winner tax |
| `remainder_ratchet` | 46 | 0 | +43.8515 | 0.0000 | 0.0000 | 0.0000 | +43.8515 | winner protection / capture |

## Default Window Detail

| candidate | window | base_trades | cand_trades | base_net | cand_net | delta | common | baseline-only | avoided loser pnl | missed winner pnl | same-entry winner delta | same-entry loser delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `late_entry_filter` | `TRENDING_UP` | 26 | 9 | 1484.5085 | 1401.7272 | -82.7813 | 9 | 17 | +747.6583 | -830.4396 | 0.0000 | 0.0000 |
| `late_entry_filter` | `RANGING` | 3 | 1 | -173.8867 | -45.2810 | +128.6057 | 1 | 2 | +128.6057 | 0.0000 | 0.0000 | 0.0000 |
| `late_entry_filter` | `MIXED` | 17 | 6 | 243.3437 | 500.3624 | +257.0188 | 6 | 11 | +359.3711 | -102.3523 | 0.0000 | 0.0000 |
| `remainder_ratchet` | `TRENDING_UP` | 26 | 26 | 1484.5085 | 1516.7409 | +32.2324 | 26 | 0 | 0.0000 | 0.0000 | +32.2324 | 0.0000 |
| `remainder_ratchet` | `RANGING` | 3 | 3 | -173.8867 | -173.8867 | 0.0000 | 3 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `remainder_ratchet` | `MIXED` | 17 | 17 | 243.3437 | 254.9628 | +11.6191 | 17 | 0 | 0.0000 | 0.0000 | +11.6191 | 0.0000 |

## Supplemental Market-Phase Detail

Only non-zero / informative windows are shown.

| candidate | window | base_trades | cand_trades | base_net | cand_net | delta | avoided loser pnl | missed winner pnl | same-entry winner delta | read |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `late_entry_filter` | `bull_strong_up_1` | 10 | 5 | 228.6339 | 53.4542 | -175.1797 | +479.2290 | -654.4087 | 0.0000 | winner tax dominates |
| `late_entry_filter` | `bear_persistent_down` | 17 | 7 | 194.7774 | 473.0154 | +278.2380 | +359.3711 | -81.1331 | 0.0000 | clean loser suppression |
| `late_entry_filter` | `ftx_style_crash` | 1 | 0 | -16.2852 | 0.0000 | +16.2852 | +16.2852 | 0.0000 | 0.0000 | avoids single loser |
| `late_entry_filter` | `sideways_transition` | 4 | 1 | -196.9550 | 38.5007 | +235.4557 | +294.3319 | -58.8762 | 0.0000 | useful weak-tape filter |
| `late_entry_filter` | `classic_rollercoaster_2021_2022` | 28 | 10 | 1567.9070 | 880.8983 | -687.0087 | +533.9435 | -1220.9522 | 0.0000 | winner tax dominates |
| `late_entry_filter` | `recovery_2023_2024` | 50 | 19 | 1063.8774 | 1426.6116 | +362.7342 | +1603.0822 | -1240.3481 | 0.0000 | net-positive but expensive |
| `remainder_ratchet` | `bull_strong_up_1` | 10 | 10 | 228.6339 | 261.7767 | +33.1428 | 0.0000 | 0.0000 | +33.1428 | improves winner capture |
| `remainder_ratchet` | `bear_persistent_down` | 17 | 17 | 194.7774 | 202.8854 | +8.1079 | 0.0000 | 0.0000 | +8.1079 | improves winner capture |
| `remainder_ratchet` | `sideways_transition` | 4 | 4 | -196.9550 | -190.0704 | +6.8846 | 0.0000 | 0.0000 | +6.8846 | small transition help |
| `remainder_ratchet` | `classic_rollercoaster_2021_2022` | 28 | 28 | 1567.9070 | 1564.3730 | -3.5340 | 0.0000 | 0.0000 | -3.5340 | tiny winner clip |
| `remainder_ratchet` | `recovery_2023_2024` | 50 | 50 | 1063.8774 | 1136.1372 | +72.2598 | 0.0000 | 0.0000 | +72.2598 | clean winner capture |

## Interpretation

`late_entry_filter` is primarily a loser-suppression branch:

- it does not change PnL on retained trades
- every default-review gain comes from refusing baseline trades
- default review improves because avoided losses are larger than missed winners
- supplemental windows show the weakness: in strong trend / classic
  rollercoaster tapes, missed winners overwhelm avoided losses

`remainder_ratchet` is primarily a winner-protection / winner-capture branch:

- it keeps the same trade set as the working baseline
- losses are unchanged
- all default-review improvement comes from positive same-entry winner delta
- supplemental windows are mostly positive, with one small 2021-2022 winner
  clip

## Conclusion

The next structural branch should not blindly combine late-entry filtering
with remainder ratcheting. That combination would likely inherit the
late-entry branch's winner tax.

Better next question:

- can the late-entry filter be gated only in bearish / transition contexts,
  where loser suppression dominates?
- can the ratchet branch be kept as the cleaner post-entry improvement while
  separating bullish and bearish families?

Decision:

- keep `partial67_remainder_ratchet` as the cleaner baseline-candidate branch
- keep `late_entry_filter` as a defensive diagnostic branch, not a replacement
- explicitly reserve a future branch study for `late_entry_filter` as a
  `RANGING` defense probe, because it cut `RANGING` from `3 trades /
  -173.8867` to `1 trade / -45.2810` in the default review window
- move the ordered queue to `separate bullish and bearish families`
