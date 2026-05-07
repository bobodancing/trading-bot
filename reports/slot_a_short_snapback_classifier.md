# Slot A SHORT Snapback Guard Dry Classifier

Date: 2026-05-07
Status: `RESEARCH_ONLY_DRY_CLASSIFIER`

## Scope

- Goal: answer whether V2 preserves any useful bearish continuation that V1's blunt late-breakdown guard would cut.
- This pass does not run a backtest and does not change runtime defaults.
- Source trades: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\slot_a_short_overlay\supplemental\classic_rollercoaster_2021_2022\trades.csv`
- Classified trades CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\slot_a_short_snapback_classifier\slot_a_short_snapback_classifier_trades.csv`
- Summary artifact: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\slot_a_short_snapback_classifier\slot_a_short_snapback_classifier_summary.json`

## Verdict

Verdict: `V2_NOT_DIFFERENTIATED_FROM_V1`.

V2 has value only if `v1_block_v2_keep` is positive and not dominated by stop-outs. That bucket represents trades V1 would remove but V2 would preserve as non-exhausted bearish continuation.

## Baseline And Guard Buckets

| bucket | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | avg_downside_move_atr | avg_entry_extension_atr | avg_close_through_atr | exhaustion_trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline all Slot A SHORT | 45 | -2508.9498 | 0.2222 | 0.1618 | -0.3956 | 1.0448 | -2.3250 | 18.4 | 16 | 8 | 2.8776 | 1.6183 | 0.5512 | 11 |
| V1 keep | 26 | -792.5118 | 0.2308 | 0.1854 | -0.2181 | 1.0735 | -1.6255 | 21.7 | 3 | 1 | 2.3000 | 1.0813 | 0.1316 | 0 |
| V1 block | 19 | -1716.4380 | 0.2105 | 0.1505 | -0.6384 | 1.0055 | -3.2822 | 14.0 | 13 | 7 | 3.6680 | 2.3532 | 1.1254 | 11 |
| V2 keep | 32 | -832.4356 | 0.2812 | 0.3657 | -0.1841 | 1.2875 | -1.7660 | 22.8 | 6 | 3 | 2.4514 | 1.2071 | 0.2516 | 0 |
| V2 block | 13 | -1676.5142 | 0.0769 | 0.0026 | -0.9162 | 0.4472 | -3.7011 | 7.8 | 10 | 5 | 3.9266 | 2.6305 | 1.2887 | 11 |

## V2 Vs V1 Differentiation

| bucket | trades | net_pnl | win_rate | profit_factor | avg_r | avg_mfe_pct | avg_mae_pct | avg_hold_h | sl_hits | zero_h_sl_hits | avg_downside_move_atr | avg_entry_extension_atr | avg_close_through_atr | exhaustion_trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `v1_keep_v2_keep` | 26 | -792.5118 | 0.2308 | 0.1854 | -0.2181 | 1.0735 | -1.6255 | 21.7 | 3 | 1 | 2.3000 | 1.0813 | 0.1316 | 0 |
| `v1_block_v2_block` | 13 | -1676.5142 | 0.0769 | 0.0026 | -0.9162 | 0.4472 | -3.7011 | 7.8 | 10 | 5 | 3.9266 | 2.6305 | 1.2887 | 11 |
| `v1_block_v2_keep` | 6 | -39.9238 | 0.5000 | 0.8824 | -0.0367 | 2.2152 | -2.3747 | 27.3 | 3 | 2 | 3.1075 | 1.7525 | 0.7715 | 0 |
| `v1_keep_v2_block` | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 |
| `v1_missing_v2_missing` | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 |

## V2-Kept V1-Blocked Trades

| entry_time | pnl_usdt | realized_r | mfe_pct | mae_pct | hold_h | exit_reason | V1 | V2 | exhaustion_reason |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| `2022-08-26T13:00:00+00:00` | -181.1878 | -1.5700 | 0.0000 | -4.1322 | 0.0 | `sl_hit` | `block` | `keep` | `none` |
| `2022-01-05T17:00:00+00:00` | -158.3376 | -1.2000 | 0.0000 | -3.6157 | 0.0 | `sl_hit` | `block` | `keep` | `none` |
| `2022-01-05T19:00:00+00:00` | 0.0000 | 0.0000 | 0.0000 | -2.7615 | 1.0 | `sl_hit` | `block` | `keep` | `none` |
| `2021-07-19T13:00:00+00:00` | 0.5223 | 0.0000 | 4.1302 | -0.5443 | 41.0 | `unknown` | `block` | `keep` | `none` |
| `2021-07-12T17:00:00+00:00` | 90.7464 | 0.7500 | 3.2641 | -1.3715 | 56.0 | `unknown` | `block` | `keep` | `none` |
| `2022-08-26T15:00:00+00:00` | 208.3330 | 1.8000 | 5.8970 | -1.8231 | 66.0 | `unknown` | `block` | `keep` | `none` |

## Read

- V2 is not differentiated enough from V1 on the classic Slot A SHORT trade set.
- Recommended action is to freeze this repair lane, not to spend more runs on a V3 or full classic backtest.
- Reopen only if the portfolio later needs a separate trend-continuation SHORT thesis; do not restart from a Slot A LONG mirror.
- This remains research-only; no runtime activation is implied.
