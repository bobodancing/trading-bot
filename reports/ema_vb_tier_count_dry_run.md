# EMA/VB Tier Count Dry Run

Runtime-parity dry count: Tier A, Neutral Arbiter on, Macro Overlay off, BTC trend filter on.

Caveat: `market_filter_pass_count` is counted after market filter because lane detection only runs once market filter passes.

## Aggregate By Lane

| lane | raw_signal_count | tier_A_count | tier_B_count | tier_C_count | final_candidate_count |
| --- | --- | --- | --- | --- | --- |
| 2B | 782 | 111 | 35 | 222 | 66 |
| EMA_PULLBACK | 3170 | 1385 | 202 | 251 | 1124 |
| VOLUME_BREAKOUT | 1568 | 807 | 66 | 130 | 643 |

## By Window

| window | lane | raw_signal_count | market_filter_pass_count | trend_filter_pass_count | mtf_aligned_count | tier_A_count | tier_B_count | tier_C_count | final_candidate_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRENDING_UP | 2B | 233 | 233 | 123 | 50 | 36 | 13 | 74 | 23 |
| TRENDING_UP | EMA_PULLBACK | 981 | 981 | 582 | 539 | 494 | 66 | 22 | 381 |
| TRENDING_UP | VOLUME_BREAKOUT | 374 | 374 | 246 | 231 | 212 | 19 | 15 | 171 |
| TRENDING_DOWN | 2B | 203 | 203 | 74 | 24 | 19 | 5 | 50 | 13 |
| TRENDING_DOWN | EMA_PULLBACK | 820 | 820 | 476 | 374 | 366 | 24 | 86 | 301 |
| TRENDING_DOWN | VOLUME_BREAKOUT | 472 | 472 | 312 | 265 | 258 | 7 | 47 | 195 |
| RANGING | 2B | 110 | 110 | 52 | 26 | 22 | 4 | 26 | 12 |
| RANGING | EMA_PULLBACK | 437 | 437 | 238 | 173 | 152 | 30 | 56 | 135 |
| RANGING | VOLUME_BREAKOUT | 257 | 257 | 155 | 131 | 121 | 10 | 24 | 105 |
| MIXED | 2B | 236 | 236 | 119 | 50 | 34 | 13 | 72 | 18 |
| MIXED | EMA_PULLBACK | 932 | 932 | 542 | 433 | 373 | 82 | 87 | 307 |
| MIXED | VOLUME_BREAKOUT | 465 | 465 | 290 | 246 | 216 | 30 | 44 | 172 |

CSV: `C:\Users\user\Documents\tradingbot\feat-regime-router\extensions\Backtesting\results\ema_vb_entry_lane_review_20260415\tier_count_summary.csv`
