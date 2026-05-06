# Portfolio A+B Bidirectional Research

Date: 2026-05-06
Status: `RESEARCH_ONLY_BIDIRECTIONAL_FIRST_PASS`

## Scope

- Slot A LONG: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot A SHORT: `macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`
- Symbols: `BTC/USDT`, `ETH/USDT`
- `RISK_PER_TRADE`: `0.017`
- `MAX_TOTAL_RISK`: Config default `0.0642`; intentionally not overridden.
- Summary artifact: `extensions\Backtesting\results\portfolio_ab_bidirectional\slot_a_b_long_short\portfolio_ab_bidirectional_matrix_summary.json`
- This is research-only. The two SHORT plugins are catalog-disabled by default and no runtime defaults were changed.
- Current StrategyRuntime does not enforce `BTC_TREND_FILTER_ENABLED` or side-to-regime matching on plugin entries; this run measures current arbiter/runtime behavior, not SHORT promotion readiness.

## Long-Only Baseline vs Bidirectional

| matrix | baseline_trades | baseline_net_pnl | baseline_max_dd_pct | bidir_trades | bidir_long_trades | bidir_short_trades | bidir_net_pnl | pnl_delta | bidir_max_dd_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `default` | 59 | 2249.7027 | 4.3144 | 69 | 56 | 13 | 2580.3711 | 330.6684 | 4.2333 |
| `supplemental` | 156 | 7515.9710 | 5.1770 | 291 | 150 | 141 | 7386.4701 | -129.5009 | 14.3409 |

## Custom 2026-01..04 Window

Window: `2026-01-01` to `2026-04-30`

| metric | value |
| --- | ---: |
| trades | 17 |
| net_pnl | 856.6952 |
| total_return_pct | 8.5670 |
| max_drawdown_pct | 3.8578 |
| win_rate | 0.5294 |
| profit_factor | 3.5153 |
| sharpe | 2.4722 |
| run_errors | 0 |

| side | trades | win_rate | net_pnl | profit_factor | avg_r |
| --- | ---: | ---: | ---: | ---: | ---: |
| LONG | 9 | 0.3333 | 83.5198 | 1.4207 | 0.0156 |
| SHORT | 8 | 0.7500 | 773.1755 | 6.4422 | 0.9175 |

| slot_side | trades | win_rate | net_pnl | profit_factor | avg_r |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slot A LONG | 5 | 0.2000 | -71.8133 | 0.6070 | -0.2140 |
| Slot A SHORT | 4 | 0.5000 | 601.7713 | 5.2358 | 1.4600 |
| Slot B LONG | 4 | 0.5000 | 155.3331 | 10.8281 | 0.3025 |
| Slot B SHORT | 4 | 1.0000 | 171.4041 | inf | 0.3750 |

Custom artifact: `extensions/Backtesting/results/portfolio_ab_bidirectional/slot_a_b_long_short/custom/2026_01_01_2026_04_30/portfolio_ab_bidirectional_2026_01_04_summary.json`

## Default Windows Portfolio

| window | trades | long_trades | short_trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_entry_long_short |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | 37 | 32 | 5 | 2002.7824 | 4.2333 | 0 | 0 |
| `RANGING` | 5 | 3 | 2 | 289.1126 | 0.8809 | 0 | 0 |
| `MIXED` | 27 | 21 | 6 | 288.4761 | 3.2671 | 0 | 0 |

## Default Windows Per Strategy

| window | slot_side | trades | win_rate | net_pnl | profit_factor | avg_r | realized_trade_dd_pct | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | Slot A LONG | 26 | 0.4231 | 1484.5085 | 2.6520 | 0.8177 | 3.0920 | 0 |
| `TRENDING_UP` | Slot A SHORT | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `TRENDING_UP` | Slot B LONG | 6 | 0.6667 | 272.9137 | 4.2874 | 0.4783 | 0.8119 | 0 |
| `TRENDING_UP` | Slot B SHORT | 5 | 0.6000 | 245.3601 | 25.4749 | 0.5220 | 0.0583 | 0 |
| `RANGING` | Slot A LONG | 1 | 0.0000 | -45.2810 | 0.0000 | -0.3200 | 0.4528 | 0 |
| `RANGING` | Slot A SHORT | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `RANGING` | Slot B LONG | 2 | 1.0000 | 132.7142 | inf | 0.3900 | 0.0000 | 0 |
| `RANGING` | Slot B SHORT | 2 | 1.0000 | 201.6795 | inf | 0.7050 | 0.0000 | 0 |
| `MIXED` | Slot A LONG | 15 | 0.4000 | 235.8377 | 1.5622 | 0.3140 | 1.9293 | 0 |
| `MIXED` | Slot A SHORT | 2 | 0.0000 | -104.8090 | 0.0000 | -0.3650 | 1.0481 | 0 |
| `MIXED` | Slot B LONG | 6 | 0.8333 | 76.1975 | 3.7921 | 0.1633 | 0.2716 | 0 |
| `MIXED` | Slot B SHORT | 4 | 0.7500 | 81.2499 | 2.6720 | 0.2925 | 0.4838 | 0 |

## Default Windows Reject Mix

| window | slot_side | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | Slot A LONG | 26 | 70 | 57 | 8 | 5 | 0 | 0 | 0.0833 |
| `TRENDING_UP` | Slot A SHORT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `TRENDING_UP` | Slot B LONG | 6 | 10 | 4 | 0 | 6 | 0 | 0 | 0.0000 |
| `TRENDING_UP` | Slot B SHORT | 5 | 15 | 13 | 0 | 2 | 0 | 0 | 0.0000 |
| `RANGING` | Slot A LONG | 1 | 3 | 3 | 0 | 0 | 0 | 0 | 0.0000 |
| `RANGING` | Slot A SHORT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `RANGING` | Slot B LONG | 2 | 6 | 0 | 4 | 2 | 0 | 0 | 0.5000 |
| `RANGING` | Slot B SHORT | 2 | 2 | 0 | 0 | 2 | 0 | 0 | 0.0000 |
| `MIXED` | Slot A LONG | 15 | 57 | 36 | 16 | 5 | 0 | 0 | 0.2222 |
| `MIXED` | Slot A SHORT | 2 | 10 | 6 | 4 | 0 | 0 | 0 | 0.3333 |
| `MIXED` | Slot B LONG | 6 | 10 | 4 | 0 | 6 | 0 | 0 | 0.0000 |
| `MIXED` | Slot B SHORT | 4 | 16 | 14 | 0 | 2 | 0 | 0 | 0.0000 |

## Supplemental Portfolio

| window | trades | long_trades | short_trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_entry_long_short |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | 17 | 11 | 6 | 855.2689 | 3.2401 | 0 | 0 |
| `bear_persistent_down` | 25 | 21 | 4 | 393.2852 | 1.8585 | 0 | 0 |
| `range_low_vol` | 7 | 2 | 5 | -152.6550 | 2.7528 | 0 | 0 |
| `bull_recovery_2026` | 8 | 0 | 8 | 773.1755 | 3.8578 | 0 | 0 |
| `ftx_style_crash` | 5 | 1 | 4 | 53.3487 | 1.4265 | 0 | 0 |
| `sideways_transition` | 7 | 3 | 4 | 106.7394 | 1.3804 | 0 | 0 |
| `classic_rollercoaster_2021_2022` | 129 | 47 | 82 | 1585.3271 | 14.3409 | 0 | 0 |
| `recovery_2023_2024` | 93 | 65 | 28 | 3771.9803 | 4.9857 | 0 | 0 |

## Supplemental Per Strategy

| window | slot_side | trades | win_rate | net_pnl | profit_factor | avg_r | realized_trade_dd_pct | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | Slot A LONG | 6 | 0.5000 | 595.7043 | 3.9014 | 1.0783 | 1.0197 | 0 |
| `bull_strong_up_1` | Slot A SHORT | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `bull_strong_up_1` | Slot B LONG | 5 | 0.8000 | 158.6374 | 4.5984 | 0.1760 | 0.4409 | 0 |
| `bull_strong_up_1` | Slot B SHORT | 6 | 0.6667 | 100.9272 | 1.6929 | 0.1250 | 1.4567 | 0 |
| `bear_persistent_down` | Slot A LONG | 15 | 0.4000 | 235.8377 | 1.5622 | 0.3140 | 1.9293 | 0 |
| `bear_persistent_down` | Slot A SHORT | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `bear_persistent_down` | Slot B LONG | 6 | 0.8333 | 76.1975 | 3.7921 | 0.1633 | 0.2716 | 0 |
| `bear_persistent_down` | Slot B SHORT | 4 | 0.7500 | 81.2499 | 2.6720 | 0.2925 | 0.4838 | 0 |
| `range_low_vol` | Slot A LONG | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `range_low_vol` | Slot A SHORT | 4 | 0.0000 | -247.8465 | 0.0000 | -0.5350 | 2.4785 | 0 |
| `range_low_vol` | Slot B LONG | 2 | 1.0000 | 106.4633 | inf | 0.5500 | 0.0000 | 0 |
| `range_low_vol` | Slot B SHORT | 1 | 0.0000 | -11.2717 | 0.0000 | -0.0900 | 0.1127 | 0 |
| `bull_recovery_2026` | Slot A LONG | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `bull_recovery_2026` | Slot A SHORT | 4 | 0.5000 | 601.7713 | 5.2358 | 1.4600 | 1.4207 | 0 |
| `bull_recovery_2026` | Slot B LONG | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `bull_recovery_2026` | Slot B SHORT | 4 | 1.0000 | 171.4041 | inf | 0.3750 | 0.0000 | 0 |
| `ftx_style_crash` | Slot A LONG | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `ftx_style_crash` | Slot A SHORT | 4 | 0.2500 | 23.2750 | 1.3509 | -0.0850 | 0.6574 | 0 |
| `ftx_style_crash` | Slot B LONG | 1 | 1.0000 | 30.0738 | inf | 0.4500 | 0.0000 | 0 |
| `ftx_style_crash` | Slot B SHORT | 0 | 0.0000 | 0.0000 | inf | 0.0000 | 0.0000 | 0 |
| `sideways_transition` | Slot A LONG | 2 | 1.0000 | 97.3769 | inf | 0.7400 | 0.0000 | 0 |
| `sideways_transition` | Slot A SHORT | 2 | 0.0000 | -93.3867 | 0.0000 | -0.6200 | 0.9339 | 0 |
| `sideways_transition` | Slot B LONG | 1 | 1.0000 | 43.8883 | inf | 0.5200 | 0.0000 | 0 |
| `sideways_transition` | Slot B SHORT | 2 | 1.0000 | 58.8610 | inf | 0.7100 | 0.0000 | 0 |
| `classic_rollercoaster_2021_2022` | Slot A LONG | 24 | 0.5000 | 1532.0756 | 2.9949 | 0.4421 | 3.4925 | 0 |
| `classic_rollercoaster_2021_2022` | Slot A SHORT | 43 | 0.2326 | -2226.9271 | 0.1786 | -0.3756 | 23.3203 | 0 |
| `classic_rollercoaster_2021_2022` | Slot B LONG | 23 | 0.7391 | 1082.8625 | 2.7414 | 0.3287 | 2.4891 | 0 |
| `classic_rollercoaster_2021_2022` | Slot B SHORT | 39 | 0.7179 | 1197.3162 | 2.5286 | 0.2108 | 2.3490 | 0 |
| `recovery_2023_2024` | Slot A LONG | 45 | 0.4444 | 2245.5016 | 2.7035 | 0.6289 | 4.4591 | 0 |
| `recovery_2023_2024` | Slot A SHORT | 7 | 0.2857 | -35.8762 | 0.8912 | -0.0229 | 3.2773 | 0 |
| `recovery_2023_2024` | Slot B LONG | 20 | 0.8500 | 1035.7585 | 9.1490 | 0.5480 | 0.7840 | 0 |
| `recovery_2023_2024` | Slot B SHORT | 21 | 0.6190 | 526.5964 | 2.1783 | 0.3119 | 1.7509 | 0 |

## Supplemental Reject Mix

| window | slot_side | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | Slot A LONG | 6 | 22 | 13 | 8 | 1 | 0 | 0 | 0.2857 |
| `bull_strong_up_1` | Slot A SHORT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `bull_strong_up_1` | Slot B LONG | 5 | 15 | 3 | 8 | 4 | 0 | 0 | 0.4000 |
| `bull_strong_up_1` | Slot B SHORT | 6 | 10 | 6 | 0 | 4 | 0 | 0 | 0.0000 |
| `bear_persistent_down` | Slot A LONG | 15 | 57 | 36 | 16 | 5 | 0 | 0 | 0.2222 |
| `bear_persistent_down` | Slot A SHORT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `bear_persistent_down` | Slot B LONG | 6 | 10 | 4 | 0 | 6 | 0 | 0 | 0.0000 |
| `bear_persistent_down` | Slot B SHORT | 4 | 16 | 14 | 0 | 2 | 0 | 0 | 0.0000 |
| `range_low_vol` | Slot A LONG | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `range_low_vol` | Slot A SHORT | 4 | 20 | 7 | 12 | 1 | 0 | 0 | 0.5000 |
| `range_low_vol` | Slot B LONG | 2 | 6 | 0 | 4 | 2 | 0 | 0 | 0.5000 |
| `range_low_vol` | Slot B SHORT | 1 | 15 | 3 | 12 | 0 | 0 | 0 | 0.7500 |
| `bull_recovery_2026` | Slot A LONG | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `bull_recovery_2026` | Slot A SHORT | 4 | 16 | 7 | 8 | 1 | 0 | 0 | 0.4000 |
| `bull_recovery_2026` | Slot B LONG | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `bull_recovery_2026` | Slot B SHORT | 4 | 8 | 6 | 0 | 2 | 0 | 0 | 0.0000 |
| `ftx_style_crash` | Slot A LONG | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `ftx_style_crash` | Slot A SHORT | 4 | 16 | 12 | 4 | 0 | 0 | 0 | 0.2000 |
| `ftx_style_crash` | Slot B LONG | 1 | 7 | 3 | 4 | 0 | 0 | 0 | 0.5000 |
| `ftx_style_crash` | Slot B SHORT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `sideways_transition` | Slot A LONG | 2 | 10 | 6 | 4 | 0 | 0 | 0 | 0.3333 |
| `sideways_transition` | Slot A SHORT | 2 | 18 | 6 | 12 | 0 | 0 | 0 | 0.6000 |
| `sideways_transition` | Slot B LONG | 1 | 3 | 3 | 0 | 0 | 0 | 0 | 0.0000 |
| `sideways_transition` | Slot B SHORT | 2 | 2 | 0 | 0 | 2 | 0 | 0 | 0.0000 |
| `classic_rollercoaster_2021_2022` | Slot A LONG | 24 | 92 | 66 | 24 | 2 | 0 | 0 | 0.2069 |
| `classic_rollercoaster_2021_2022` | Slot A SHORT | 43 | 177 | 94 | 56 | 7 | 20 | 0 | 0.2545 |
| `classic_rollercoaster_2021_2022` | Slot B LONG | 23 | 89 | 49 | 20 | 12 | 8 | 0 | 0.1786 |
| `classic_rollercoaster_2021_2022` | Slot B SHORT | 39 | 133 | 103 | 4 | 22 | 4 | 0 | 0.0233 |
| `recovery_2023_2024` | Slot A LONG | 45 | 151 | 104 | 40 | 7 | 0 | 0 | 0.2041 |
| `recovery_2023_2024` | Slot A SHORT | 7 | 45 | 21 | 24 | 0 | 0 | 0 | 0.4615 |
| `recovery_2023_2024` | Slot B LONG | 20 | 60 | 22 | 24 | 14 | 0 | 0 | 0.3000 |
| `recovery_2023_2024` | Slot B SHORT | 21 | 51 | 37 | 4 | 10 | 0 | 0 | 0.0556 |

## Read

- SHORT side adds raw coverage only if it improves portfolio PnL without increasing max drawdown or crowding LONG entries through `position_slot_occupied`.
- `same_symbol_same_entry_long_short` uses actual trade `entry_time`, not wall-clock signal audit timestamps.
- Validation windows overlap; totals are research attribution, not live expectancy estimates.
- No production scanner defaults, credentials, router policy, runtime defaults, or live/testnet service state were changed.
