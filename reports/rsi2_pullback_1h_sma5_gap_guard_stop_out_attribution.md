# rsi2_pullback_1h_sma5_gap_guard Stop-Out Attribution

Date: 2026-04-30
Status: `PHASE_4_CLOSEOUT_PARKED`

Closeout update (2026-05-05): this attribution closes Phase 4. RSI2 is parked;
do not proceed to Phase 4.2 or an A+B+RSI2 combined run without fresh Ruei
approval.

## Scope

- Candidate: `rsi2_pullback_1h_sma5_gap_guard`
- Purpose: attribute residual `sl_hit` trades before any Phase 4.2 child spec.
- Windows: standard `DEFAULT_WINDOWS` from `extensions/Backtesting/plugin_candidate_review.py`.
- Symbols: `BTC/USDT`, `ETH/USDT`.
- Fee estimate: `0.0004` per side on entry and exit notional.
- Stop-out CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\rsi2_pullback_1h_sma5_gap_guard\stop_out_attribution.csv`
- Segment summary CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\rsi2_pullback_1h_sma5_gap_guard\stop_out_attribution_summary.csv`

## Aggregate

| scope | trades | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h |
| --- | --- | --- | --- | --- | --- | --- |
| all_trades | 177 | 1205.8574 | 582.7172 | 0.1181 | -0.4507 | 3.1299 |
| sl_hit | 32 | -1879.3944 | -1991.2423 | -0.7975 | -1.4117 | 2.8750 |
| non_sl_hit | 145 | 3085.2518 | 2573.9596 | 0.3201 | -0.2386 | 3.1862 |

## Window Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=TRENDING_UP | 18 | 87 | 0.2069 | -964.0606 | -1026.9279 | -0.6772 | -1.3102 | 1.8889 | 0.7044 |
| window=MIXED | 14 | 89 | 0.1573 | -915.3338 | -964.3144 | -0.9521 | -1.5422 | 4.1429 | 0.9806 |

## Window And Symbol Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| window=TRENDING_UP / symbol=BTC/USDT | 13 | 41 | 0.3171 | -754.9986 | -800.4372 | -0.7838 | -1.3912 | 1.7692 | 0.7986 |
| window=MIXED / symbol=BTC/USDT | 8 | 49 | 0.1633 | -342.0931 | -370.2839 | -0.9650 | -1.0077 | 4.7500 | 1.0063 |
| window=MIXED / symbol=ETH/USDT | 6 | 40 | 0.1500 | -573.2407 | -594.0305 | -0.9350 | -2.2549 | 3.3333 | 0.9464 |
| window=TRENDING_UP / symbol=ETH/USDT | 5 | 46 | 0.1087 | -209.0620 | -226.4908 | -0.4000 | -1.0994 | 2.2000 | 0.4594 |

## Symbol Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| symbol=BTC/USDT | 21 | 91 | 0.2308 | -1097.0917 | -1170.7211 | -0.8529 | -1.2451 | 2.9048 | 0.8777 |
| symbol=ETH/USDT | 11 | 86 | 0.1279 | -782.3027 | -820.5213 | -0.6918 | -1.7297 | 2.8182 | 0.7250 |

## Entry-Regime Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| entry_regime=TRENDING | 16 | 120 | 0.1333 | -1130.9284 | -1186.8183 | -0.8756 | -1.6220 | 3.0625 | 0.8691 |
| entry_regime=RANGING | 16 | 57 | 0.2807 | -748.4660 | -804.4240 | -0.7194 | -1.2014 | 2.6875 | 0.7813 |

## SMA5 Gap ATR Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sma5_gap_atr_bucket=>=1.00 | 21 | 97 | 0.2165 | -1234.3422 | -1307.7030 | -0.7729 | -1.3931 | 2.7143 | 0.7905 |
| sma5_gap_atr_bucket=0.50-1.00 | 11 | 80 | 0.1375 | -645.0522 | -683.5394 | -0.8445 | -1.4472 | 3.1818 | 0.8915 |

## 1h SMA200 Distance Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sma200_dist_bucket=2-5% | 12 | 53 | 0.2264 | -680.9176 | -722.7543 | -0.7208 | -1.4677 | 2.4167 | 0.7842 |
| sma200_dist_bucket=0-2% | 11 | 68 | 0.1618 | -685.5446 | -724.0482 | -0.9864 | -1.4460 | 3.8182 | 1.0098 |
| sma200_dist_bucket=5-10% | 7 | 46 | 0.1522 | -371.3205 | -395.8268 | -0.7100 | -1.2044 | 2.4286 | 0.6966 |
| sma200_dist_bucket=>=10% | 2 | 10 | 0.2000 | -141.6117 | -148.6130 | -0.5250 | -1.6130 | 2.0000 | 0.5065 |

## 4h SMA200 Distance Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| htf_sma200_dist_bucket=>=10% | 18 | 81 | 0.2222 | -946.3313 | -1009.2492 | -0.5994 | -1.3126 | 2.0000 | 0.6382 |
| htf_sma200_dist_bucket=2-5% | 6 | 23 | 0.2609 | -563.7845 | -584.6575 | -1.3917 | -2.1534 | 3.3333 | 1.3906 |
| htf_sma200_dist_bucket=5-10% | 4 | 46 | 0.0870 | -220.3051 | -234.2937 | -0.8625 | -1.2518 | 3.0000 | 0.8492 |
| htf_sma200_dist_bucket=0-2% | 4 | 27 | 0.1481 | -148.9735 | -163.0420 | -0.7325 | -0.9048 | 6.0000 | 0.7950 |

## ATR Percent Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| atr_pct_bucket=0.5-1.0% | 14 | 94 | 0.1489 | -758.6590 | -807.7026 | -0.8821 | -1.2298 | 2.2857 | 0.8704 |
| atr_pct_bucket=1.0-1.5% | 11 | 44 | 0.2500 | -686.8658 | -725.2647 | -0.6027 | -1.6055 | 2.7273 | 0.6707 |
| atr_pct_bucket=<0.5% | 5 | 33 | 0.1515 | -143.6680 | -161.2567 | -0.9400 | -0.7170 | 5.2000 | 1.0158 |
| atr_pct_bucket=>=1.5% | 2 | 6 | 0.3333 | -290.2015 | -297.0184 | -0.9200 | -3.3558 | 2.0000 | 0.8821 |

## Holding-Time Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| holding_bucket=<=2h | 18 | 68 | 0.2647 | -943.0222 | -1005.9374 | -0.7022 | -1.2679 | 1.3333 | 0.7213 |
| holding_bucket=3-5h | 10 | 91 | 0.1099 | -670.7310 | -705.6581 | -0.8260 | -1.6076 | 3.9000 | 0.8582 |
| holding_bucket=6-10h | 4 | 18 | 0.2222 | -265.6411 | -279.6468 | -1.1550 | -1.5692 | 7.2500 | 1.2104 |

## RSI2 Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rsi2_bucket=5-8 | 11 | 55 | 0.2000 | -634.8125 | -673.1722 | -0.9127 | -1.3704 | 2.8182 | 0.9288 |
| rsi2_bucket=2-5 | 10 | 52 | 0.1923 | -588.4608 | -623.4764 | -0.7090 | -1.4462 | 3.6000 | 0.7615 |
| rsi2_bucket=8-10 | 6 | 43 | 0.1395 | -308.8269 | -329.8876 | -0.6383 | -1.2869 | 2.1667 | 0.6827 |
| rsi2_bucket=<2 | 5 | 27 | 0.1852 | -347.2942 | -364.7061 | -0.9120 | -1.5832 | 2.4000 | 0.8959 |

## Entry-Hour Stop-Outs

| group | stop_outs | all_trades | stop_rate | pnl_usdt | net_after_fee_est | avg_r | avg_mae_pct | avg_hold_h | avg_mae_to_stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| entry_hour_bucket=12-17 | 17 | 60 | 0.2833 | -794.3779 | -854.0099 | -0.6882 | -1.1881 | 2.2353 | 0.7460 |
| entry_hour_bucket=18-23 | 6 | 36 | 0.1667 | -569.9660 | -590.6935 | -0.9617 | -2.1828 | 2.5000 | 0.9407 |
| entry_hour_bucket=06-11 | 5 | 48 | 0.1042 | -328.7396 | -346.2020 | -1.0880 | -1.4967 | 4.2000 | 1.0713 |
| entry_hour_bucket=00-05 | 4 | 33 | 0.1212 | -186.3109 | -200.3370 | -0.6525 | -1.0991 | 4.5000 | 0.6810 |

## Guardability Check

These broad cuts are not recommendations; they test whether the obvious concentrations are actually net-bad after winner retention.

| candidate_guard | trades | stop_outs | stop_rate | pnl_usdt | net_after_fee_est | stop_pnl | non_stop_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BTC only | 91 | 21 | 0.2308 | 199.2802 | -122.2098 | -1097.0917 | 1296.3719 |
| TRENDING_UP BTC | 41 | 13 | 0.3171 | -5.3931 | -149.6699 | -754.9986 | 749.6055 |
| SMA5 gap >= 1.00 ATR | 97 | 21 | 0.2165 | 473.8254 | 132.3041 | -1234.3422 | 1708.1676 |
| entry hour 12-17 UTC | 60 | 17 | 0.2833 | 15.4448 | -195.9176 | -794.3779 | 809.8226 |
| entry regime RANGING | 57 | 16 | 0.2807 | 174.5957 | -25.9344 | -748.4660 | 923.0616 |
| 4h SMA200 distance >=10% | 81 | 18 | 0.2222 | 750.1000 | 465.3382 | -946.3313 | 1696.4313 |

## Top Stop-Outs

| window | symbol | entry_time | pnl_usdt | realized_r | mae_pct | sma5_gap_atr | sma200_bucket | htf_sma200_bucket | holding_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MIXED | ETH/USDT | 2025-06-12T21:00:00+00:00 | -181.7269 | -1.4700 | -4.1500 | 2.0315 | 0-2% | 2-5% | 3-5h |
| TRENDING_UP | BTC/USDT | 2024-03-05T19:00:00+00:00 | -172.6851 | -1.0100 | -4.0279 | 1.6547 | 2-5% | >=10% | <=2h |
| MIXED | BTC/USDT | 2025-08-14T06:00:00+00:00 | -117.6620 | -2.2500 | -2.6761 | 1.3196 | 2-5% | 2-5% | 6-10h |
| TRENDING_UP | ETH/USDT | 2024-01-12T19:00:00+00:00 | -117.5164 | -0.8300 | -2.6837 | 0.9169 | >=10% | >=10% | 3-5h |
| MIXED | ETH/USDT | 2025-08-15T14:00:00+00:00 | -105.5420 | -0.9800 | -2.4089 | 1.2947 | 5-10% | >=10% | <=2h |
| MIXED | ETH/USDT | 2025-07-23T08:00:00+00:00 | -102.4047 | -1.1100 | -2.3387 | 0.9210 | 2-5% | >=10% | 6-10h |
| TRENDING_UP | BTC/USDT | 2024-01-12T15:00:00+00:00 | -95.0610 | -1.0200 | -2.1566 | 0.7867 | 0-2% | 2-5% | <=2h |
| TRENDING_UP | BTC/USDT | 2024-01-03T12:00:00+00:00 | -92.2635 | -1.0800 | -2.0903 | 2.7909 | 0-2% | 2-5% | <=2h |
| MIXED | ETH/USDT | 2025-04-24T04:00:00+00:00 | -82.3765 | -0.7600 | -1.8816 | 0.7793 | 5-10% | 0-2% | 3-5h |
| TRENDING_UP | BTC/USDT | 2024-02-13T14:00:00+00:00 | -74.3951 | -1.2100 | -1.6877 | 1.0396 | 5-10% | >=10% | <=2h |

## Decision Read

- Residual stop-outs total `32` across the default review matrix.
- Strongest single segmentation is `symbol`: symbol=BTC/USDT has 21 stop-outs (65.6% of stop-outs).
- The visible concentrations are broad participation buckets with material non-stop PnL, so they do not justify a clean second guard.
- `TRENDING_UP BTC` is net-negative after fees, but it is a research-window label, not a live plugin-local guard.
- Phase 4.2 should park RSI2 for now unless Ruei explicitly wants a defensive low-participation variant.
- Do not loosen RSI, SMA5-gap, or trend thresholds from this read.
- This report is diagnostic only and does not modify runtime defaults, catalog flags, scanner behavior, or production/testnet state.
