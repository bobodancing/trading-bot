# EMA/VB Entry Lane Review

## Executive read

- Verdict: `KEEP_2B_ONLY`.
- Runtime EMA/VB remains off; this report does not modify `bot_config.json`.
- Matrix used V54 exits for all tested lanes under runtime-parity filters.
- `RANGING` and `MIXED` windows overlap; aggregate trade counts are deduped by entry time / symbol / signal type.
- Any promotion still requires Ruei decision and second-pass stress windows.

## Matrix summary

| run_id | total_trades | profit_factor | win_rate | max_drawdown_pct | sharpe | net_pnl | avg_r | max_losing_streak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BASE_2B_ONLY | 44 | 2.0030 | 0.5455 | 1.0335 | 0.9491 | 246.1198 | 0.1261 | 4 |
| EMA_ONLY | 356 | 1.6158 | 0.5000 | 4.4023 | 1.1843 | 2344.6555 | 0.2825 | 8 |
| VB_ONLY | 143 | 1.6012 | 0.5105 | 3.9628 | 1.5219 | 1086.6506 | 0.2531 | 6 |
| EMA_VB_ONLY | 361 | 1.6277 | 0.5180 | 5.5696 | 1.1021 | 2475.1591 | 0.2724 | 9 |
| 2B_EMA | 372 | 1.6438 | 0.5027 | 4.1723 | 1.3174 | 2516.1727 | 0.2922 | 7 |
| 2B_VB | 172 | 1.7202 | 0.5291 | 4.0667 | 1.7577 | 1363.3410 | 0.2547 | 7 |
| 2B_EMA_VB | 377 | 1.6291 | 0.5146 | 5.3373 | 1.2007 | 2582.0417 | 0.2815 | 8 |

## By-window table

| run_id | window | trades | pf | max_dd_pct | net_pnl |
| --- | --- | --- | --- | --- | --- |
| BASE_2B_ONLY | TRENDING_UP | 20 | 2.1424 | 0.7929 | 124.1841 |
| BASE_2B_ONLY | TRENDING_DOWN | 12 | 1.2449 | 1.0335 | 20.2250 |
| BASE_2B_ONLY | RANGING | 7 | 7.2377 | 0.6703 | 115.1273 |
| BASE_2B_ONLY | MIXED | 12 | 2.8795 | 0.9490 | 101.7107 |
| EMA_ONLY | TRENDING_UP | 128 | 1.8038 | 2.6310 | 1007.9465 |
| EMA_ONLY | TRENDING_DOWN | 121 | 1.6939 | 3.9436 | 879.9734 |
| EMA_ONLY | RANGING | 47 | 1.0276 | 3.5389 | 17.1260 |
| EMA_ONLY | MIXED | 105 | 1.3722 | 4.4023 | 466.4509 |
| VB_ONLY | TRENDING_UP | 48 | 1.5417 | 2.2007 | 259.0969 |
| VB_ONLY | TRENDING_DOWN | 53 | 1.3479 | 2.7820 | 236.6385 |
| VB_ONLY | RANGING | 19 | 2.1546 | 1.7260 | 305.1337 |
| VB_ONLY | MIXED | 41 | 1.8538 | 3.9628 | 564.0606 |
| EMA_VB_ONLY | TRENDING_UP | 129 | 1.6345 | 3.1880 | 838.4884 |
| EMA_VB_ONLY | TRENDING_DOWN | 123 | 2.1926 | 3.6832 | 1313.1637 |
| EMA_VB_ONLY | RANGING | 47 | 0.9332 | 4.4713 | -47.7741 |
| EMA_VB_ONLY | MIXED | 107 | 1.2239 | 5.5696 | 333.2223 |
| 2B_EMA | TRENDING_UP | 139 | 1.8134 | 2.5258 | 1101.1816 |
| 2B_EMA | TRENDING_DOWN | 123 | 1.7695 | 3.6808 | 958.2465 |
| 2B_EMA | RANGING | 49 | 1.1161 | 3.5529 | 70.9225 |
| 2B_EMA | MIXED | 108 | 1.3652 | 4.1723 | 466.4600 |
| 2B_VB | TRENDING_UP | 64 | 1.6920 | 2.0003 | 393.5081 |
| 2B_VB | TRENDING_DOWN | 58 | 1.5250 | 2.1929 | 334.3383 |
| 2B_VB | RANGING | 24 | 2.3370 | 1.7236 | 376.6277 |
| 2B_VB | MIXED | 49 | 1.8705 | 4.0667 | 608.6399 |
| 2B_EMA_VB | TRENDING_UP | 140 | 1.6267 | 3.0837 | 905.3222 |
| 2B_EMA_VB | TRENDING_DOWN | 125 | 2.2135 | 3.3703 | 1353.2035 |
| 2B_EMA_VB | RANGING | 49 | 1.0085 | 4.4825 | 6.0224 |
| 2B_EMA_VB | MIXED | 110 | 1.2203 | 5.3373 | 333.2313 |

## By-regime table

| run_id | regime | trades | pf | net_pnl |
| --- | --- | --- | --- | --- |
| BASE_2B_ONLY | RANGING | 18 | 1.4303 | 58.3551 |
| BASE_2B_ONLY | TRENDING | 26 | 2.7103 | 187.7647 |
| EMA_ONLY | RANGING | 131 | 1.5803 | 719.2014 |
| EMA_ONLY | TRENDING | 225 | 1.6330 | 1625.4541 |
| VB_ONLY | RANGING | 66 | 1.4104 | 368.3407 |
| VB_ONLY | TRENDING | 77 | 1.7895 | 718.3099 |
| EMA_VB_ONLY | RANGING | 135 | 1.6346 | 802.5155 |
| EMA_VB_ONLY | TRENDING | 226 | 1.6245 | 1672.6437 |
| 2B_EMA | RANGING | 139 | 1.5239 | 696.7860 |
| 2B_EMA | TRENDING | 233 | 1.7055 | 1819.3867 |
| 2B_VB | RANGING | 76 | 1.4185 | 407.9098 |
| 2B_VB | TRENDING | 96 | 2.0405 | 955.4312 |
| 2B_EMA_VB | RANGING | 142 | 1.5335 | 741.2250 |
| 2B_EMA_VB | TRENDING | 235 | 1.6780 | 1840.8167 |

## Incremental contribution

| run_id | new_trades | new_pf | new_net_pnl | pure_new | replaced | unchanged_2b | priority_suppressed | overlap_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2B_EMA | 343 | 1.6087 | 2272.1100 | 343 | 0 | 29 | 30 | 0.6591 |
| 2B_VB | 135 | 1.6368 | 1086.2340 | 135 | 0 | 37 | 10 | 0.8409 |
| 2B_EMA_VB | 349 | 1.5854 | 2313.6800 | 349 | 0 | 28 | 171 | 0.6364 |

## Exit compatibility

| run_id | signal_type | trades | avg_capture_ratio | near_0r_timeout_count | v54_lock_15r | v54_lock_20r | exit_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BASE_2B_ONLY | 2B | 44 | -0.6105 | 10 | 7 | 2 | stage1_timeout:20; sl_hit:18; v54_structure_break:6 |
| EMA_ONLY | EMA_PULLBACK | 356 | -1.2587 | 40 | 34 | 59 | sl_hit:238; stage1_timeout:113; v54_structure_break:4; backtest_end:1 |
| VB_ONLY | VOLUME_BREAKOUT | 143 | -1.9262 | 36 | 6 | 18 | stage1_timeout:75; sl_hit:59; v54_structure_break:8; backtest_end:1 |
| EMA_VB_ONLY | EMA_PULLBACK | 305 | -1.2191 | 32 | 32 | 50 | sl_hit:211; stage1_timeout:93; v54_structure_break:1 |
| EMA_VB_ONLY | VOLUME_BREAKOUT | 56 | -1.7699 | 15 | 3 | 9 | stage1_timeout:28; sl_hit:23; v54_structure_break:4; backtest_end:1 |
| 2B_EMA | 2B | 31 | -0.8358 | 9 | 4 | 2 | stage1_timeout:17; sl_hit:11; v54_structure_break:3 |
| 2B_EMA | EMA_PULLBACK | 341 | -1.5094 | 38 | 32 | 57 | sl_hit:229; stage1_timeout:107; v54_structure_break:4; backtest_end:1 |
| 2B_VB | 2B | 37 | -0.3376 | 9 | 7 | 2 | stage1_timeout:17; sl_hit:16; v54_structure_break:4 |
| 2B_VB | VOLUME_BREAKOUT | 135 | -1.9576 | 33 | 5 | 18 | stage1_timeout:71; sl_hit:56; v54_structure_break:7; backtest_end:1 |
| 2B_EMA_VB | 2B | 30 | -0.7410 | 9 | 4 | 2 | stage1_timeout:17; sl_hit:10; v54_structure_break:3 |
| 2B_EMA_VB | EMA_PULLBACK | 292 | -1.2726 | 30 | 30 | 48 | sl_hit:203; stage1_timeout:88; v54_structure_break:1 |
| 2B_EMA_VB | VOLUME_BREAKOUT | 55 | -2.0389 | 13 | 3 | 9 | stage1_timeout:26; sl_hit:24; v54_structure_break:4; backtest_end:1 |

## Failure modes

- Worst run/window: `EMA_VB_ONLY/RANGING` net_pnl=-47.7741, PF=0.9332, trades=47.
- Worst symbol: `VB_ONLY` `DOGE/USDT` net_pnl=-55.9743.
- Worst single trade: `EMA_ONLY` `ETH/USDT` EMA_PULLBACK pnl=-134.5928 exit=sl_hit.

## Acceptance checks

- `2B_EMA` failed: PF below 90% of BASE_2B_ONLY; MaxDD above 1.25x BASE_2B_ONLY.
- `2B_VB` failed: PF below 90% of BASE_2B_ONLY; MaxDD above 1.25x BASE_2B_ONLY.
- `2B_EMA_VB` failed: PF below 90% of BASE_2B_ONLY; MaxDD above 1.25x BASE_2B_ONLY.

## Run settings

- Symbols: `BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT DOGE/USDT`.
- Fee rate: `0.0004`; initial balance: `10000`; warmup bars: `100`.
- Runtime parity: Tier A, neutral arbiter on, macro overlay off, BTC trend filter on, counter-trend multiplier 0.
- Results root: `C:\Users\user\Documents\tradingbot\feat-regime-router\extensions\Backtesting\results\ema_vb_entry_lane_review_20260415`.
