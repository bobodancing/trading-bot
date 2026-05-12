# Weekly Profit Phase 4 Trigger Review

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_4_TRIGGER_REVIEW_READY_FOR_LANE_DISCUSSION`

## Executive Read

Formal trigger review verdict: `OPEN_BOUNDED_FREQUENCY_COMPLEMENT_DISCUSSION`. Dominant gap is `participation_gap`.

The packet history justifies discussing one bounded frequency-complement research lane, but it does not authorize runtime-default changes, scanner runtime activation, threshold loosening, or live/testnet state changes.

## Source

- Phase 3 packet JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\weekly_profit_control_packets.json`
- Source packet schema: `strategy_plugin_weekly_profit_control_packets.v1`
- Source packet count: `18`
- Contract-grade packet count: `9`

## Contract-Grade State Counts

| state | count |
| --- | ---: |
| `investigate` | 2 |
| `reopen_research` | 7 |

## Trigger Counts

| trigger | count |
| --- | ---: |
| `active_entry_week_ratio_8w` | 7 |
| `positive_week_ratio_all_8w_after_fee` | 2 |
| `rolling_8w_entry_trade_count` | 6 |
| `zero_entry_week_streak` | 2 |

## Latest Contract-Grade Packet

| KPI | value |
| --- | ---: |
| week_start | `2026-04-20` |
| state | `investigate` |
| active_entry_week_ratio_8w | 0.6250 |
| rolling_8w_entry_trade_count | 9 |
| zero_entry_week_streak | 0 |
| positive_week_ratio_all_8w_after_fee | 0.3750 |
| positive_week_ratio_exit_active_8w_after_fee | 0.6000 |
| rolling_8w_net_after_fee_pnl | 106.4680 |
| worst_week_after_fee_pnl_pct_equity_8w | -1.2335 |
| portfolio_max_drawdown_pct_review_window | 2.1778 |

## Contract-Grade Packet Timeline

| week_start | state | active-entry ratio 8w | entries 8w | zero-entry streak | positive all 8w | positive active-exit 8w | net 8w | primary trigger |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2026-02-23` | `reopen_research` | 0.2500 | 4 | 2 | 0.3750 | 1.0000 | 157.3497 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-03-02` | `reopen_research` | 0.2500 | 4 | 3 | 0.3750 | 1.0000 | 157.3497 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count, zero_entry_week_streak |
| `2026-03-09` | `reopen_research` | 0.1250 | 3 | 4 | 0.2500 | 1.0000 | 155.8731 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count, zero_entry_week_streak |
| `2026-03-16` | `reopen_research` | 0.2500 | 4 | 0 | 0.2500 | 0.6667 | 136.8349 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-03-23` | `reopen_research` | 0.3750 | 6 | 0 | 0.3750 | 0.7500 | 252.8689 | active_entry_week_ratio_8w |
| `2026-03-30` | `investigate` | 0.5000 | 7 | 0 | 0.5000 | 0.8000 | 297.0647 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-04-06` | `reopen_research` | 0.3750 | 4 | 1 | 0.3750 | 0.7500 | 203.7461 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-04-13` | `reopen_research` | 0.5000 | 6 | 0 | 0.2500 | 0.5000 | 17.8436 | positive_week_ratio_all_8w_after_fee |
| `2026-04-20` | `investigate` | 0.6250 | 9 | 0 | 0.3750 | 0.6000 | 106.4680 | positive_week_ratio_all_8w_after_fee |

## Diagnosis

- Participation pressure is the dominant historical trigger: active-entry ratio and entry-count gates caused most formal reopen windows.
- Latest contract-grade economics are not a hard failure: rolling `8w` net PnL is positive, worst-week loss is inside the risk envelope, and no operational pause condition appears in the packet.
- Positive-week density is now the watch item. The latest packet sits at the `0.3750` all-week lower watch line while active-exit positivity is still at the continue threshold.

## Lane Discussion Menu

| rank | lane | stance | reason |
| ---: | --- | --- | --- |
| 1 | `frequency_complement_low_overlap` | `recommended_first_discussion` | Participation triggers dominate the contract-grade packet history, while latest contract-grade economics remain net-positive and risk-clean. |
| 2 | `positive_week_density_stabilizer` | `secondary_discussion` | All-week positive density should be protected while frequency repair adds trade opportunities. |
| 3 | `exit_quality_repair` | `not_first` | Exit-active quality and rolling net PnL are not the dominant historical failure in this packet set. |

## Guardrails

- Discuss exactly one bounded lane before implementation.
- Do not change promoted runtime defaults.
- Do not loosen current strategy thresholds to manufacture volume.
- Do not reactivate legacy RSI2 / BB / Slot A SHORT lanes by default.
- Any candidate must add weekly participation without degrading after-fee packet economics or risk integrity.
