# Slot A SHORT Failure Attribution

Date: 2026-05-07
Status: `RESEARCH_ONLY_FAILURE_ATTRIBUTION`

## Scope

- Goal: explain why the mirrored Slot A SHORT probe breaks; this is not a promotion lane.
- Runtime defaults are not changed.
- No thresholds, scanner defaults, router policy, credentials, or live/testnet state are changed.
- Attribution uses existing backtest artifacts. A full Slot A SHORT overlay supplemental rerun timed out before completing all cells, so this pass uses overlay default cells, overlay `classic_rollercoaster_2021_2022`, and the all-four supplemental matrix for wider window coverage.
- Summary artifact: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\slot_a_short_failure_attribution\slot_a_short_failure_attribution_summary.json`

## Stress Window Contrast

`classic_rollercoaster_2021_2022` is the failure window that exposed the mirror-SHORT problem.

| source | strategy | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Slot A SHORT overlay / Slot A LONG | 28 | 1567.9070 | 0.4643 | 2.9306 | 0.3839 | 3.5354 | -1.4611 | 33.5 | 3 | 1 | 0 |
| Slot A SHORT overlay / Slot A SHORT | 45 | -2508.9498 | 0.2222 | 0.1618 | -0.3956 | 1.0448 | -2.3250 | 18.4 | 16 | 8 | 1 |
| all-four reference / Slot A LONG | 24 | 1532.0756 | 0.5000 | 2.9949 | 0.4421 | 3.9820 | -1.4925 | 36.9 | 3 | 1 | 0 |
| all-four reference / Slot A SHORT | 43 | -2226.9271 | 0.2326 | 0.1786 | -0.3756 | 1.0934 | -2.2822 | 19.2 | 15 | 7 | 1 |
| all-four reference / Slot B SHORT | 39 | 1197.3162 | 0.7179 | 2.5286 | 0.2108 | 2.2699 | -0.7137 | 16.3 | 3 | 0 | 0 |
| Slot B SHORT overlay / Slot A LONG | 28 | 1567.9070 | 0.4643 | 2.9306 | 0.3839 | 3.5354 | -1.4611 | 33.5 | 3 | 1 | 0 |
| Slot B SHORT overlay / Slot B SHORT | 38 | 1207.6330 | 0.7368 | 2.5624 | 0.2179 | 2.2387 | -0.7160 | 16.4 | 3 | 0 | 0 |

## Window Read

Slot A SHORT is not failing because every SHORT is bad. It is specifically weak in the 2021-2022 rollercoaster stress window, while Slot B SHORT remains positive in the same broad regime.

Slot A SHORT in all-four supplemental:

| window | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `classic_rollercoaster_2021_2022` | 43 | -2226.9271 | 0.2326 | 0.1786 | -0.3756 | 1.0934 | -2.2822 | 19.2 | 15 | 7 | 1 |
| `range_low_vol` | 4 | -247.8465 | 0.0000 | 0.0000 | -0.5350 | 0.7375 | -1.5334 | 13.5 | 1 | 1 | 0 |
| `sideways_transition` | 2 | -93.3867 | 0.0000 | 0.0000 | -0.6200 | 0.4081 | -1.0621 | 14.5 | 1 | 0 | 0 |
| `recovery_2023_2024` | 7 | -35.8762 | 0.2857 | 0.8912 | -0.0229 | 2.0227 | -1.2834 | 22.6 | 2 | 0 | 1 |
| `bear_persistent_down` | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0 | 0 | 0 | 0 |
| `bull_strong_up_1` | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0 | 0 | 0 | 0 |
| `ftx_style_crash` | 4 | 23.2750 | 0.2500 | 1.3509 | -0.0850 | 1.2036 | -0.8436 | 18.2 | 0 | 0 | 1 |
| `bull_recovery_2026` | 4 | 601.7713 | 0.5000 | 5.2358 | 1.4600 | 7.2988 | -1.5727 | 39.8 | 2 | 1 | 0 |

Slot A SHORT overlay default cells completed before the supplemental rerun timed out:

| window | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `RANGING` | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0 | 0 | 0 | 0 |
| `TRENDING_UP` | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0 | 0 | 0 | 0 |
| `MIXED` | 3 | 91.3954 | 0.3333 | 1.8720 | 0.4967 | 4.0093 | -0.9689 | 26.7 | 0 | 0 | 0 |

## Loss Concentration

Worst Slot A SHORT months in the overlay stress window:

| month | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | giveback_exits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2022-09` | 7 | -792.4436 | 0.0000 | 0.0000 | -0.9314 | 0.7250 | -2.9015 | 9.0 | 5 | 2 | 0 |
| `2022-02` | 5 | -591.2605 | 0.2000 | 0.0073 | -0.7320 | 0.3919 | -3.7196 | 6.8 | 3 | 2 | 0 |
| `2022-01` | 6 | -470.8791 | 0.0000 | 0.0000 | -0.5333 | 0.2975 | -3.1019 | 6.3 | 4 | 2 | 0 |
| `2022-03` | 2 | -282.0226 | 0.0000 | 0.0000 | -0.8250 | 0.0000 | -3.2458 | 3.0 | 1 | 1 | 0 |
| `2022-05` | 5 | -166.5173 | 0.2000 | 0.0762 | -0.2300 | 0.8736 | -1.4370 | 27.2 | 0 | 0 | 0 |
| `2022-04` | 2 | -162.8411 | 0.0000 | 0.0000 | -0.6250 | 1.1197 | -1.8886 | 38.5 | 1 | 0 | 0 |
| `2021-12` | 4 | -132.0928 | 0.5000 | 0.2252 | -0.2150 | 1.9374 | -2.2840 | 34.0 | 0 | 0 | 0 |
| `2022-12` | 3 | -66.3332 | 0.0000 | 0.0000 | -0.4733 | 0.3134 | -0.5971 | 10.7 | 0 | 0 | 0 |
| `2021-05` | 1 | -34.3490 | 0.0000 | 0.0000 | -0.2000 | 0.0000 | -3.5429 | 4.0 | 0 | 0 | 0 |
| `2022-08` | 3 | 12.2949 | 0.3333 | 1.0627 | 0.0233 | 2.0975 | -2.1832 | 26.0 | 1 | 1 | 0 |

Worst Slot A SHORT trades in the overlay stress window:

| entry_time | exit_time | pnl_usdt | realized_r | mfe_pct | mae_pct | hold_h | exit_reason | entry_regime | entry_regime_direction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| `2022-01-21T01:00:00+00:00` | `2022-01-21T01:00:00+00:00` | -276.9231 | -1.6800 | 0.0000 | -6.3151 | 0.0 | `sl_hit` | `TRENDING` | `SHORT` |
| `2022-09-06T17:00:00+00:00` | `2022-09-06T17:00:00+00:00` | -215.0217 | -1.8900 | 0.0000 | -4.9024 | 0.0 | `sl_hit` | `RANGING` | `SHORT` |
| `2022-02-24T01:00:00+00:00` | `2022-02-24T01:00:00+00:00` | -194.6255 | -1.1400 | 0.0000 | -5.2063 | 0.0 | `sl_hit` | `TRENDING` | `SHORT` |
| `2022-08-26T13:00:00+00:00` | `2022-08-26T13:00:00+00:00` | -181.1878 | -1.5700 | 0.0000 | -4.1322 | 0.0 | `sl_hit` | `TRENDING` | `SHORT` |
| `2022-03-07T17:00:00+00:00` | `2022-03-07T17:00:00+00:00` | -177.7686 | -1.0400 | 0.0000 | -4.0725 | 0.0 | `sl_hit` | `TRENDING` | `SHORT` |
| `2022-02-21T09:00:00+00:00` | `2022-02-21T09:00:00+00:00` | -173.6537 | -1.2100 | 0.0000 | -3.9498 | 0.0 | `sl_hit` | `TRENDING` | `SHORT` |
| `2022-09-19T01:00:00+00:00` | `2022-09-19T01:00:00+00:00` | -159.4172 | -1.2700 | 0.0000 | -3.6282 | 0.0 | `sl_hit` | `TRENDING` | `SHORT` |
| `2022-01-05T17:00:00+00:00` | `2022-01-05T17:00:00+00:00` | -158.3376 | -1.2000 | 0.0000 | -3.6157 | 0.0 | `sl_hit` | `RANGING` | `SHORT` |

## Attribution

1. The mirror breaks at the thesis level, not at runtime routing. Slot A SHORT uses the expected SHORT side, has no entry-stop violations in the inspected stress artifacts, and its losses persist in both overlay and all-four references.
2. The stress-window signature is late-breakdown / snapback risk. In the overlay stress window, Slot A SHORT has weak favorable excursion, larger adverse excursion, many stop hits, and several zero-hour stop hits; this is exactly the profile of shorting after the bearish move is already crowded or exhausted.
3. The LONG cartridge has asymmetric payoff support. In the same stress window, Slot A LONG carries far better MFE/MAE and profit factor, so the staged derisk/giveback lifecycle fits upside continuation better than downside continuation.
4. The current SHORT transition-aware veto is too narrow for crash-rebound structure. It only catches a specific breakdown plus MACD-hist exhaustion plus high extension state; the worst losses show immediate stop behavior that slips through that gate.
5. Lifecycle protection is not the main repair. Slot A SHORT rarely reaches protected giveback exits in the failure window; repair should start at entry/regime context, not by overfitting the exit.

## Repair Directions

- Treat Slot A SHORT as an independent bearish-continuation thesis, not a symmetric mirror of Slot A LONG.
- Add an exhaustion/snapback guard before any parameter tuning: regime age, distance from EMA, recent downside velocity, and failed-breakdown context are better candidates than loosening MACD confirmation.
- Consider a side-specific transition filter that blocks late bearish breakdowns after large downside excursion unless follow-through is confirmed.
- If lifecycle is revisited, test it after entry filtering; the current evidence says the bad trades often fail before derisk/giveback can help.
- Keep Slot A SHORT research-only until this attribution can be converted into a falsifiable repair experiment.
