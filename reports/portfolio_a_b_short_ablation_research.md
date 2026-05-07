# Portfolio A+B SHORT Ablation Research

Date: 2026-05-07
Status: `RESEARCH_ONLY_SHORT_ABLATION_SECOND_PASS`

## Scope

- Slot A LONG: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot A SHORT: `macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`
- Symbols: `BTC/USDT`, `ETH/USDT`
- `RISK_PER_TRADE`: `0.017`
- `MAX_TOTAL_RISK`: Config default `0.0642`; intentionally not overridden.
- Summary artifact: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\portfolio_ab_short_ablation_summary.json`
- Research direction: include SHORT side in the Slot A+B portfolio, but identify which SHORT leg can survive promotion-style risk review.
- This pass does not change scanner defaults, credentials, router policy, thresholds, or live/testnet service state.

## Variant Totals

| matrix | variant | windows | trades | long_trades | short_trades | net_pnl | pnl_delta_vs_matching_long_only | max_dd_pct | dd_delta_vs_matching_long_only | slot_a_short_net_pnl | slot_b_short_net_pnl | run_errors |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `default` | `long_only_reference` | `3 windows` | 59 | 59 | 0 | 2249.7027 | 0.0000 | 4.3144 | 0.0000 | 0.0000 | 0.0000 | 0 |
| `default` | `slot_b_short_overlay` | `3 windows` | 62 | 53 | 9 | 2319.6818 | 69.9791 | 2.7900 | -1.5244 | 0.0000 | 483.1704 | 0 |
| `default` | `bidirectional_reference` | `3 windows` | 69 | 56 | 13 | 2580.3711 | 330.6684 | 4.2333 | -0.0811 | -104.8090 | 528.2895 | 0 |
| `supplemental` | `long_only_reference` | `8 windows` | 156 | 156 | 0 | 7515.9710 | 0.0000 | 5.1770 | 0.0000 | 0.0000 | 0.0000 | 0 |
| `supplemental` | `slot_a_short_overlay` | `classic_rollercoaster_2021_2022` | 96 | 51 | 45 | 141.8197 | -2655.8997 | 19.4678 | 14.2908 | -2508.9498 | 0.0000 | 0 |
| `supplemental` | `slot_b_short_overlay` | `8 windows` | 233 | 159 | 74 | 8994.3783 | 1478.4073 | 6.0766 | 0.8996 | 0.0000 | 2090.2808 | 0 |
| `supplemental` | `bidirectional_reference` | `8 windows` | 291 | 150 | 141 | 7386.4701 | -129.5009 | 14.3409 | 9.1639 | -1978.9902 | 2125.0831 | 0 |
| `custom` | `slot_b_short_overlay` | `2026_01_01_2026_04_30` | 13 | 9 | 4 | 254.9239 | n/a | 2.1778 | n/a | 0.0000 | 171.4041 | 0 |

## Critical Stress Read

`classic_rollercoaster_2021_2022` is the stress window that exposed the all-four bidirectional drawdown problem.

| variant | trades | long_trades | short_trades | net_pnl | max_dd_pct | slot_a_short_net_pnl | slot_b_short_net_pnl |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `long_only_reference` | 50 | 50 | 0 | 2797.7194 | 5.1770 | 0.0000 | 0.0000 |
| `slot_a_short_overlay` | 96 | 51 | 45 | 141.8197 | 19.4678 | -2508.9498 | 0.0000 |
| `slot_b_short_overlay` | 91 | 53 | 38 | 3961.2237 | 6.0766 | 0.0000 | 1207.6330 |
| `bidirectional_reference` | 129 | 47 | 82 | 1585.3271 | 14.3409 | -2226.9271 | 1197.3162 |

## Custom Window Detail

| variant | window | trades | long_trades | short_trades | net_pnl | max_dd_pct | slot_a_short_net_pnl | slot_b_short_net_pnl | run_errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `slot_b_short_overlay` | `2026_01_01_2026_04_30` | 13 | 9 | 4 | 254.9239 | 2.1778 | 0.0000 | 171.4041 | 0 |

## Supplemental Window Detail

| variant | window | trades | long_trades | short_trades | net_pnl | max_dd_pct | slot_a_short_net_pnl | slot_b_short_net_pnl | run_errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `slot_a_short_overlay` | `classic_rollercoaster_2021_2022` | 96 | 51 | 45 | 141.8197 | 19.4678 | -2508.9498 | 0.0000 | 0 |
| `slot_b_short_overlay` | `bull_strong_up_1` | 18 | 12 | 6 | 867.1378 | 3.1625 | 0.0000 | 100.9272 | 0 |
| `slot_b_short_overlay` | `bear_persistent_down` | 24 | 22 | 2 | 320.8191 | 1.8359 | 0.0000 | 36.1308 | 0 |
| `slot_b_short_overlay` | `range_low_vol` | 3 | 2 | 1 | 95.1915 | 0.4446 | 0.0000 | -11.2717 | 0 |
| `slot_b_short_overlay` | `bull_recovery_2026` | 4 | 0 | 4 | 171.4041 | 0.9100 | 0.0000 | 171.4041 | 0 |
| `slot_b_short_overlay` | `ftx_style_crash` | 1 | 1 | 0 | 30.0738 | 0.6908 | 0.0000 | 0.0000 | 0 |
| `slot_b_short_overlay` | `sideways_transition` | 5 | 3 | 2 | 200.1262 | 0.9208 | 0.0000 | 58.8610 | 0 |
| `slot_b_short_overlay` | `classic_rollercoaster_2021_2022` | 91 | 53 | 38 | 3961.2237 | 6.0766 | 0.0000 | 1207.6330 | 0 |
| `slot_b_short_overlay` | `recovery_2023_2024` | 87 | 66 | 21 | 3348.4021 | 4.7630 | 0.0000 | 526.5964 | 0 |

## Read

- `slot_b_short_overlay` is the cleanest first promotion candidate if it adds PnL while keeping drawdown close to long-only A+B.
- `slot_a_short_overlay` must explain and repair Slot A SHORT drawdown before it can be considered runtime-ready.
- `short_only` is diagnostic only; it measures standalone SHORT behavior without long-side slot occupancy.
- References use existing long-only and all-four bidirectional summaries when present; ablation variants are rerun in this pass.
