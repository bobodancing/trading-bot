# rsi2_pullback_1h Trade Attribution

Date: 2026-04-25  
Status: `DIAGNOSTIC_ONLY`

## Scope

- Candidate: `rsi2_pullback_1h`
- Windows: standard `DEFAULT_WINDOWS` from `extensions/Backtesting/plugin_candidate_review.py`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Method: join each trade to the previous closed 1h and 4h candle before `entry_time`, then rebuild plugin-local `rsi_2`, `sma_5`, `sma_200`, and ATR context.
- Fee estimate: `0.0004` per side on entry and exit notional.
- Enriched trades CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\rsi2_pullback_1h\trade_attribution.csv`
- Segment summary CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\rsi2_pullback_1h\trade_attribution_summary.csv`

## Aggregate

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scope=TOTAL | 268 | 0.6642 | 589.4543 | 942.9427 | 0.2161 | -353.4884 | 0.0509 | 3.0784 |

## Window Summary

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED | 126 | 0.6190 | -94.7987 | 443.9525 | 0.2199 | -538.7511 | 0.0122 | 3.4524 |
| window=RANGING | 2 | 0.5000 | -4.4293 | 7.1099 | 0.7444 | -11.5393 | -0.0500 | 4.0000 |
| window=TRENDING_UP | 140 | 0.7071 | 688.6823 | 491.8803 | 0.2107 | 196.8020 | 0.0872 | 2.7286 |

## Exit Reason Attribution

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / exit_reason=sl_hit | 26 | 0.0000 | -1839.1858 | 90.7859 | n/a | -1929.9716 | -0.9808 | 3.8077 |
| window=TRENDING_UP / exit_reason=sl_hit | 26 | 0.0385 | -1460.0700 | 90.7547 | 2.4617 | -1550.8248 | -0.7358 | 1.8846 |
| window=RANGING / exit_reason=sma5_bounce_exit | 2 | 0.5000 | -4.4293 | 7.1099 | 0.7444 | -11.5393 | -0.0500 | 4.0000 |
| window=MIXED / exit_reason=sma5_bounce_exit | 45 | 0.6889 | 443.6063 | 158.9049 | 0.2379 | 284.7014 | 0.1331 | 3.3333 |
| window=TRENDING_UP / exit_reason=sma5_bounce_exit | 53 | 0.8113 | 829.6939 | 186.4157 | 0.2050 | 643.2782 | 0.2049 | 2.9057 |
| window=TRENDING_UP / exit_reason=rsi2_exit_target | 61 | 0.9016 | 1319.0584 | 214.7099 | 0.1546 | 1104.3486 | 0.3357 | 2.9344 |
| window=MIXED / exit_reason=rsi2_exit_target | 55 | 0.8545 | 1300.7808 | 194.2617 | 0.1437 | 1106.5191 | 0.3827 | 3.3818 |

## SMA5 Gap ATR Buckets

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / sma5_gap_atr_bucket=0.50-1.00 | 76 | 0.6053 | -165.5655 | 267.5194 | 0.2371 | -433.0850 | -0.0083 | 3.5000 |
| window=MIXED / sma5_gap_atr_bucket=0.25-0.50 | 15 | 0.7333 | -61.5459 | 52.7415 | 0.2838 | -114.2874 | -0.0160 | 3.0667 |
| window=TRENDING_UP / sma5_gap_atr_bucket=0.25-0.50 | 24 | 0.6667 | 3.6314 | 84.2956 | 0.2686 | -80.6642 | 0.0296 | 2.5000 |
| window=RANGING / sma5_gap_atr_bucket=>=1.00 | 1 | 0.0000 | -13.9801 | 3.5375 | n/a | -17.5177 | -0.2700 | 6.0000 |
| window=MIXED / sma5_gap_atr_bucket=<0.25 | 2 | 0.5000 | -3.1246 | 7.1323 | 0.7926 | -10.2569 | -0.0500 | 1.5000 |
| window=RANGING / sma5_gap_atr_bucket=0.50-1.00 | 1 | 1.0000 | 9.5508 | 3.5724 | 0.3740 | 5.9784 | 0.1700 | 2.0000 |
| window=TRENDING_UP / sma5_gap_atr_bucket=<0.25 | 2 | 1.0000 | 19.0140 | 7.0487 | 0.3707 | 11.9654 | 0.1450 | 1.5000 |
| window=MIXED / sma5_gap_atr_bucket=>=1.00 | 33 | 0.6061 | 135.4374 | 116.5592 | 0.1674 | 18.8782 | 0.0761 | 3.6364 |
| window=TRENDING_UP / sma5_gap_atr_bucket=>=1.00 | 41 | 0.6829 | 270.3467 | 143.9953 | 0.1646 | 126.3515 | 0.1215 | 2.5610 |
| window=TRENDING_UP / sma5_gap_atr_bucket=0.50-1.00 | 73 | 0.7260 | 395.6902 | 256.5407 | 0.2276 | 139.1495 | 0.0853 | 2.9315 |

## 1h SMA200 Distance Buckets

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / sma200_dist_bucket=2-5% | 30 | 0.5000 | -463.7860 | 105.7172 | 0.2807 | -569.5032 | -0.1957 | 3.5667 |
| window=TRENDING_UP / sma200_dist_bucket=>=10% | 7 | 0.2857 | -258.9701 | 24.5451 | 0.7053 | -283.5151 | -0.2600 | 3.5714 |
| window=MIXED / sma200_dist_bucket=0-2% | 58 | 0.6379 | 4.6486 | 204.3433 | 0.2867 | -199.6948 | 0.0724 | 3.3621 |
| window=TRENDING_UP / sma200_dist_bucket=0-2% | 43 | 0.6512 | -44.3652 | 150.9323 | 0.2210 | -195.2975 | -0.0130 | 2.4884 |
| window=RANGING / sma200_dist_bucket=0-2% | 1 | 0.0000 | -13.9801 | 3.5375 | n/a | -17.5177 | -0.2700 | 6.0000 |
| window=RANGING / sma200_dist_bucket=2-5% | 1 | 1.0000 | 9.5508 | 3.5724 | 0.3740 | 5.9784 | 0.1700 | 2.0000 |
| window=MIXED / sma200_dist_bucket=5-10% | 30 | 0.6667 | 195.4799 | 105.7991 | 0.1586 | 89.6808 | 0.0687 | 3.7000 |
| window=MIXED / sma200_dist_bucket=>=10% | 8 | 0.7500 | 168.8589 | 28.0928 | 0.1069 | 140.7661 | 0.1437 | 2.7500 |
| window=TRENDING_UP / sma200_dist_bucket=5-10% | 41 | 0.7561 | 417.0927 | 144.1856 | 0.2170 | 272.9071 | 0.1210 | 2.7073 |
| window=TRENDING_UP / sma200_dist_bucket=2-5% | 49 | 0.7755 | 574.9249 | 172.2173 | 0.1808 | 402.7076 | 0.1965 | 2.8367 |

## 4h SMA200 Distance Buckets

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / htf_sma200_dist_bucket=2-5% | 17 | 0.5294 | -207.3953 | 59.9775 | 0.2388 | -267.3728 | -0.1182 | 3.9412 |
| window=MIXED / htf_sma200_dist_bucket=>=10% | 49 | 0.6122 | -76.2693 | 172.1591 | 0.1714 | -248.4284 | -0.0443 | 3.2857 |
| window=TRENDING_UP / htf_sma200_dist_bucket=2-5% | 16 | 0.5625 | -182.8304 | 56.0766 | 0.2675 | -238.9069 | -0.1987 | 2.8125 |
| window=MIXED / htf_sma200_dist_bucket=0-2% | 26 | 0.6923 | 52.5237 | 91.8574 | 0.3702 | -39.3337 | 0.0862 | 3.5000 |
| window=RANGING / htf_sma200_dist_bucket=0-2% | 2 | 0.5000 | -4.4293 | 7.1099 | 0.7444 | -11.5393 | -0.0500 | 4.0000 |
| window=MIXED / htf_sma200_dist_bucket=5-10% | 34 | 0.6176 | 136.3422 | 119.9584 | 0.2325 | 16.3838 | 0.1024 | 3.4118 |
| window=TRENDING_UP / htf_sma200_dist_bucket=0-2% | 9 | 0.6667 | 102.7098 | 31.6306 | 0.2523 | 71.0792 | 0.1333 | 3.2222 |
| window=TRENDING_UP / htf_sma200_dist_bucket=>=10% | 72 | 0.7083 | 330.3258 | 253.0253 | 0.1959 | 77.3005 | 0.1074 | 2.5694 |
| window=TRENDING_UP / htf_sma200_dist_bucket=5-10% | 43 | 0.7674 | 438.4771 | 151.1479 | 0.2135 | 287.3292 | 0.1502 | 2.8605 |

## RSI2 Buckets

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / rsi2_bucket=5-8 | 52 | 0.6154 | -103.9944 | 183.0417 | 0.2085 | -287.0361 | -0.0104 | 3.5000 |
| window=MIXED / rsi2_bucket=8-10 | 43 | 0.5814 | -63.7079 | 151.5997 | 0.2539 | -215.3076 | -0.0463 | 3.5349 |
| window=TRENDING_UP / rsi2_bucket=8-10 | 56 | 0.6607 | 99.2175 | 196.5667 | 0.2356 | -97.3492 | 0.0561 | 2.8036 |
| window=MIXED / rsi2_bucket=2-5 | 24 | 0.6667 | 15.9149 | 84.6988 | 0.2241 | -68.7839 | 0.1192 | 3.5000 |
| window=RANGING / rsi2_bucket=2-5 | 1 | 0.0000 | -13.9801 | 3.5375 | n/a | -17.5177 | -0.2700 | 6.0000 |
| window=RANGING / rsi2_bucket=8-10 | 1 | 1.0000 | 9.5508 | 3.5724 | 0.3740 | 5.9784 | 0.1700 | 2.0000 |
| window=TRENDING_UP / rsi2_bucket=<2 | 4 | 0.7500 | 21.3045 | 14.0301 | 0.2078 | 7.2743 | 0.1725 | 2.2500 |
| window=MIXED / rsi2_bucket=<2 | 7 | 0.7143 | 56.9887 | 24.6122 | 0.1479 | 32.3765 | 0.1729 | 2.4286 |
| window=TRENDING_UP / rsi2_bucket=2-5 | 26 | 0.6538 | 148.9466 | 91.4805 | 0.1750 | 57.4661 | 0.0838 | 2.5000 |
| window=TRENDING_UP / rsi2_bucket=5-8 | 54 | 0.7778 | 419.2138 | 189.8030 | 0.2086 | 229.4108 | 0.1148 | 2.7963 |

## Holding-Time Buckets

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / holding_bucket=3-5h | 64 | 0.5781 | -396.0204 | 225.3685 | 0.2796 | -621.3889 | -0.0608 | 3.7812 |
| window=MIXED / holding_bucket=6-10h | 17 | 0.1765 | -368.6701 | 59.8153 | 0.6520 | -428.4855 | -0.3859 | 6.7647 |
| window=TRENDING_UP / holding_bucket=6-10h | 5 | 0.0000 | -92.1562 | 17.4773 | n/a | -109.6335 | -0.2480 | 6.6000 |
| window=RANGING / holding_bucket=6-10h | 1 | 0.0000 | -13.9801 | 3.5375 | n/a | -17.5177 | -0.2700 | 6.0000 |
| window=RANGING / holding_bucket=<=2h | 1 | 1.0000 | 9.5508 | 3.5724 | 0.3740 | 5.9784 | 0.1700 | 2.0000 |
| window=TRENDING_UP / holding_bucket=<=2h | 61 | 0.7049 | 334.5308 | 214.3648 | 0.1607 | 120.1660 | 0.0754 | 1.5246 |
| window=TRENDING_UP / holding_bucket=3-5h | 74 | 0.7568 | 446.3077 | 260.0382 | 0.2598 | 186.2696 | 0.1196 | 3.4595 |
| window=MIXED / holding_bucket=<=2h | 45 | 0.8444 | 669.8919 | 158.7686 | 0.1415 | 511.1233 | 0.2664 | 1.7333 |

## ATR Percent Buckets

| group | trades | win_rate | pnl_usdt | fees_est | fee_drag_ratio | net_after_fee_est | avg_r | avg_hold_h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / atr_pct_bucket=0.5-1.0% | 53 | 0.6038 | -189.6853 | 186.8452 | 0.2448 | -376.5305 | -0.0492 | 3.4151 |
| window=MIXED / atr_pct_bucket=1.0-1.5% | 31 | 0.5484 | -226.1722 | 108.5064 | 0.1459 | -334.6786 | -0.0652 | 3.4839 |
| window=TRENDING_UP / atr_pct_bucket=>=1.5% | 6 | 0.5000 | -240.6050 | 20.9066 | 0.3147 | -261.5117 | -0.2567 | 3.0000 |
| window=RANGING / atr_pct_bucket=0.5-1.0% | 2 | 0.5000 | -4.4293 | 7.1099 | 0.7444 | -11.5393 | -0.0500 | 4.0000 |
| window=TRENDING_UP / atr_pct_bucket=<0.5% | 12 | 0.7500 | 63.9614 | 42.1724 | 0.3550 | 21.7890 | 0.0983 | 2.8333 |
| window=TRENDING_UP / atr_pct_bucket=1.0-1.5% | 30 | 0.7000 | 144.8853 | 105.5118 | 0.1923 | 39.3735 | 0.0513 | 2.8333 |
| window=MIXED / atr_pct_bucket=<0.5% | 39 | 0.6667 | 191.1768 | 138.0402 | 0.3610 | 53.1366 | 0.1364 | 3.5641 |
| window=MIXED / atr_pct_bucket=>=1.5% | 3 | 1.0000 | 129.8820 | 10.5607 | 0.0813 | 119.3213 | 0.2833 | 2.3333 |
| window=TRENDING_UP / atr_pct_bucket=0.5-1.0% | 92 | 0.7174 | 720.4407 | 323.2895 | 0.2020 | 397.1512 | 0.1199 | 2.6630 |

## Best/Worst Segments

Minimum trades per segment: `10`.

### Best

| group | trades | pnl_usdt | fees_est | net_after_fee_est | fee_drag_ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / exit_reason=rsi2_exit_target | 55 | 1300.7808 | 194.2617 | 1106.5191 | 0.1437 |
| window=TRENDING_UP / exit_reason=rsi2_exit_target | 61 | 1319.0584 | 214.7099 | 1104.3486 | 0.1546 |
| window=TRENDING_UP / exit_reason=sma5_bounce_exit | 53 | 829.6939 | 186.4157 | 643.2782 | 0.2050 |
| window=MIXED / holding_bucket=<=2h | 45 | 669.8919 | 158.7686 | 511.1233 | 0.1415 |
| window=TRENDING_UP / sma200_dist_bucket=2-5% | 49 | 574.9249 | 172.2173 | 402.7076 | 0.1808 |

### Worst

| group | trades | pnl_usdt | fees_est | net_after_fee_est | fee_drag_ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| window=MIXED / exit_reason=sl_hit | 26 | -1839.1858 | 90.7859 | -1929.9716 | n/a |
| window=TRENDING_UP / exit_reason=sl_hit | 26 | -1460.0700 | 90.7547 | -1550.8248 | 2.4617 |
| window=MIXED / holding_bucket=3-5h | 64 | -396.0204 | 225.3685 | -621.3889 | 0.2796 |
| window=MIXED / sma200_dist_bucket=2-5% | 30 | -463.7860 | 105.7172 | -569.5032 | 0.2807 |
| window=MIXED / sma5_gap_atr_bucket=0.50-1.00 | 76 | -165.5655 | 267.5194 | -433.0850 | 0.2371 |

## Read

- This is diagnostic evidence only; it does not modify runtime defaults or promote the candidate.
- The selected child hypothesis is `sma5_gap_atr >= 0.75`, implemented as `rsi2_pullback_1h_sma5_gap_guard`.
- This is a churn-reduction guard, not an entry-threshold loosening.
- Use child review output, not this ex-post attribution alone, for any next promotion discussion.
